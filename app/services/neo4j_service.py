import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv
import re
from string import Template
from pathlib import Path
import json  # Add this import
import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Neo4jService:
    def __init__(self):
        """Initialize the Neo4j service"""
        self.uri = os.getenv("NEO4J_URI")
        self.username = os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
        
        
    def connect(self):
        """Connect to the Neo4j database"""
        if not self.driver:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
                self.driver.verify_connectivity()
                logger.info("Connected to Neo4j database")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                return False
        return True
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j connection closed")
    
    def is_connected(self):
        """Check if connected to Neo4j"""
        try:
            if self.driver:
                self.driver.verify_connectivity()
                return True
            return False
        except Exception:
            return False
    
    def run_query(self, query, params=None):
        """Run a Cypher query"""
        if not self.connect():
            return None
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return None
    
    def get_prop_str(self, prop_dict, _id):
        """Generate property string for Cypher query"""
        s = []
        for key, val in prop_dict.items():
            if key != 'label' and key != 'id':
                escaped_val = str(val).replace('"', '\\"')
                s.append(f'{_id}.{key} = "{escaped_val}"')
        return ' ON CREATE SET ' + ','.join(s)
    
    def get_cypher_compliant_var(self, _id):
        """Generate a Cypher-compliant variable name"""
        s = "_" + re.sub(r'[\W_]', '', _id).lower()  # avoid numbers appearing as firstchar
        return s[:20]  # restrict variable size
    
    def generate_cypher(self, file_name, in_json):
        """Generate Cypher statements for entity and relationship insertion"""
        e_map = {}
        e_stmt = []
        r_stmt = []
        e_stmt_tpl = Template("($id:$label{id:'$key'})")
        r_stmt_tpl = Template("""
          MATCH $src
          MATCH $tgt
          MERGE ($src_id)-[:$rel]->($tgt_id)
        """)
        
        # Handle entities
        for obj in in_json:
            for j in obj['entities']:
                props = ''
                label = j['label']
                id = ''
                if label == 'Person':
                    id = 'p' + str(file_name)
                elif label == 'Position':
                    c = j['id'].replace('position', '_')
                    id = f'j{str(file_name)}{c}'
                elif label == 'Education':
                    c = j['id'].replace('education', '_')
                    id = f'e{str(file_name)}{c}'
                else:
                    id = self.get_cypher_compliant_var(j['name'])
                
                if label in ['Person', 'Position', 'Education', 'Skill', 'Company']:
                    varname = self.get_cypher_compliant_var(j['id'])
                    stmt = e_stmt_tpl.substitute(id=varname, label=label, key=id)
                    e_map[varname] = stmt
                    e_stmt.append('MERGE ' + stmt + self.get_prop_str(j, varname))
            
            # Handle relationships
            for st in obj['relationships']:
                rels = st.split("|")
                src_id = self.get_cypher_compliant_var(rels[0].strip())
                rel = rels[1].strip()
                if rel in ['HAS_SKILL', 'HAS_EDUCATION', 'AT_COMPANY', 'HAS_POSITION']:
                    tgt_id = self.get_cypher_compliant_var(rels[2].strip())
                    stmt = r_stmt_tpl.substitute(
                        src_id=src_id, tgt_id=tgt_id, src=e_map[src_id], tgt=e_map[tgt_id], rel=rel)
                    r_stmt.append(stmt)
        
        return e_stmt, r_stmt
    
    def create_constraints(self):
        """Create necessary constraints in Neo4j"""
        constraints = [
            'CREATE CONSTRAINT unique_person_id IF NOT EXISTS FOR (n:Person) REQUIRE (n.id) IS UNIQUE',
            'CREATE CONSTRAINT unique_position_id IF NOT EXISTS FOR (n:Position) REQUIRE (n.id) IS UNIQUE',
            'CREATE CONSTRAINT unique_skill_id IF NOT EXISTS FOR (n:Skill) REQUIRE n.id IS UNIQUE',
            'CREATE CONSTRAINT unique_education_id IF NOT EXISTS FOR (n:Education) REQUIRE n.id IS UNIQUE',
            'CREATE CONSTRAINT unique_company_id IF NOT EXISTS FOR (n:Company) REQUIRE n.id IS UNIQUE'
        ]
        
        for constraint in constraints:
            self.run_query(constraint)
        
        logger.info("Neo4j constraints created")
        
    def delete_cv_data(self, cv_filename):
        """
        Delete all data related to a specific CV from Neo4j
        
        Args:
            cv_filename: The filename of the CV
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # Generate ID based on filename (similar to what's used in generate_cypher)
            file_id = cv_filename.replace(".", "_").replace(" ", "_")
            person_id = f"p{file_id}"
            
            # First find the person node
            query = """
            MATCH (p:Person {id: $person_id})
            RETURN p
            """
            result = self.run_query(query, {"person_id": person_id})
            
            if not result:
                logger.warning(f"Person node not found for CV: {cv_filename}")
                return False
                
            # Delete all relationships and nodes created from this CV
            # Use this pattern to match the CV-specific IDs
            delete_query = """
            // Match person and all connected entities
            MATCH (p:Person {id: $person_id})
            OPTIONAL MATCH (p)-[r1]-(connected)
            OPTIONAL MATCH (connected)-[r2]-(secondary)
            WHERE connected:Position OR connected:Education OR connected:Skill OR connected:Company
            
            // Delete all relationships first
            DETACH DELETE p, connected, secondary
            """
            
            self.run_query(delete_query, {"person_id": person_id})
            logger.info(f"Deleted Neo4j data for CV: {cv_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Neo4j data for CV {cv_filename}: {e}")
            return False
    
    def get_all_roles(self):
        """
        Retrieve all role nodes from Neo4j with their skill relationships
        
        Returns:
            list: List of dictionaries containing role information
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to retrieve roles")
            return []
        
        try:
            query = """
            MATCH (role:Role)
            OPTIONAL MATCH (role)-[rel:REQUIRES_SKILL]->(skill:Skill)
            WITH role, 
                 collect({name: skill.name, importance: rel.importance, is_required: rel.is_required}) AS skills
            RETURN role {
                .*, 
                skills: skills,
                required_skills: CASE 
                    WHEN size(skills) > 0 
                    THEN reduce(s = "", skill IN skills | s + (CASE WHEN s = "" THEN "" ELSE ", " END) + skill.name) 
                    ELSE "" 
                END
            } as role
            """
            
            results = self.run_query(query)
            
            # Process results into the expected format
            roles = []
            if results:
                for record in results:
                    if 'role' in record:
                        role_data = record['role']
                        roles.append(role_data)
                        
                logger.info(f"Retrieved {len(roles)} Role nodes from Neo4j")
            else:
                logger.warning("No Role nodes found in Neo4j database")
                
            return roles
            
        except Exception as e:
            logger.error(f"Error retrieving Role nodes: {e}")
            return []
    
    def get_all_cv_nodes(self):
        """
        Retrieve all CV nodes from Neo4j
        
        Returns:
            list: List of dictionaries containing CV information
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to retrieve CVs")
            return []
        
        try:
            # Use the same query you've verified works in Neo4j Browser
            query = """
            MATCH (cv:CV) 
            RETURN cv {.*} as cv
            """
            
            results = self.run_query(query)
            
            # Process results into the expected format
            cvs = []
            if results:
                for record in results:
                    if 'cv' in record:
                        cv_data = record['cv']
                        
                        # Ensure consistent property names
                        if 'file_name' in cv_data and 'filename' not in cv_data:
                            cv_data['filename'] = cv_data['file_name']
                        
                        # Ensure upload_date is properly formatted
                        if 'upload_date' in cv_data and cv_data['upload_date']:
                            # Check if it's already a datetime
                            if not isinstance(cv_data['upload_date'], datetime):
                                try:
                                    cv_data['upload_date'] = datetime.fromisoformat(cv_data['upload_date'])
                                except:
                                    # Keep as is if parsing fails
                                    pass
                        
                        cvs.append(cv_data)
                        
                logger.info(f"Retrieved {len(cvs)} CV nodes from Neo4j")
            else:
                logger.warning("No CV nodes found in Neo4j database")
                
            return cvs
            
        except Exception as e:
            logger.error(f"Error retrieving CV nodes: {e}")
            return []
    
    
    def delete_cv_node(self, cv_id):
        """
        Delete a CV node and its connected data
        
        Args:
            cv_id: The ID of the CV node
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # Delete the CV node and all its relationships
            query = """
            MATCH (p:Person {id: $cv_id})
            OPTIONAL MATCH (p)-[r]->(n)
            DETACH DELETE p, n
            """
            
            self.run_query(query, {'cv_id': cv_id})
            logger.info(f"Deleted CV node with ID: {cv_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting CV node: {e}")
            return False
    
    def delete_all_cv_nodes(self):
        """
        Delete all CV nodes and their connected data including derived Person nodes 
        and all related data (Skills, Education, etc.), preserving Role nodes
        
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # First get all CV file_names for logging
            query_get_cvs = """
            MATCH (c:CV)
            RETURN c.file_name as file_name
            """
            cv_results = self.run_query(query_get_cvs)
            cv_count = len(cv_results) if cv_results else 0
            
            # Delete all Person nodes and cascading delete all connected nodes (except Role)
            delete_query = """
            // Match all Person nodes (derived from CVs)
            MATCH (p:Person)
            
            // Match all directly connected nodes
            OPTIONAL MATCH (p)-[r1]-(connected)
            WHERE NOT connected:Role
            
            // Match secondary connected nodes
            OPTIONAL MATCH (connected)-[r2]-(secondary)
            WHERE NOT secondary:Role AND connected:Position OR connected:Education OR connected:Project
            
            // Delete all relationships and nodes
            DETACH DELETE p, connected, secondary
            """
            self.run_query(delete_query)
            
            # Delete CV nodes
            cv_query = """
            MATCH (c:CV)
            DETACH DELETE c
            """
            self.run_query(cv_query)
            
            logger.info(f"Deleted all CV nodes ({cv_count} total) and their associated data")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting all CV nodes and their data: {e}")
            return False
    def insert_cv_node(self, file_name):
        """
        Insert a new CV node into the Neo4j database
        
        Args:
            file_name (str): The filename of the CV
            
        Returns:
            bool: True if inserted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            upload_time = datetime.datetime.now().isoformat()
            
            # Notice we're using self.driver directly, not self.driver.driver
            with self.driver.session() as session:
                session.run(
                    """
                    CREATE (c:CV {
                        file_name: $file_name,
                        upload_datetime: $upload_datetime,
                        extracted: false
                    })
                    """,
                    file_name=file_name,
                    upload_datetime=upload_time
                )
                
            logger.info(f"Created CV node for file: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating CV node: {e}")
            return False
        
    def update_cv_extraction_status(self, file_name, status=True):
        """
        Update the extraction status of a CV node
        
        Args:
            file_name (str): The filename of the CV
            status (bool): The extraction status to set
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            query = """
            MATCH (c:CV {file_name: $file_name})
            SET c.extracted = $status
            RETURN c
            """
            
            result = self.run_query(query, {"file_name": file_name, "status": status})
            if result:
                logger.info(f"Updated extraction status to {status} for CV: {file_name}")
                return True
            else:
                logger.warning(f"CV node not found for file: {file_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating CV extraction status: {e}")
            return False
        
    
    def get_unextracted_cvs(self):
        """
        Get all CV nodes that have not been extracted
        
        Returns:
            list: List of CV nodes with extracted=false
        """
        if not self.connect():
            return []
            
        try:
            query = """
            MATCH (c:CV {extracted: false})
            RETURN c.file_name as file_name
            """
            
            results = self.run_query(query)
            if results:
                return [result['file_name'] for result in results]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting unextracted CVs: {e}")
            return []

    def add_role(self, role_id, job_title, degree_requirement, field_of_study, 
                experience_years, required_skills, location_remote,
                industry_sector="", role_level=""):
        """
        Add a new role to Neo4j with improved skill representation
        
        Returns:
            bool: Success or failure
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to add role")
            return False
        
        try:
            # Parse required_skills into a structured format with importance
            # Input format should be: "Skill:importance:required,Skill2:importance:required"
            # Example: "Python:8:true,SQL:5:false"
            skill_relationships = []
            skills_to_process = []
            
            if isinstance(required_skills, str) and required_skills:
                skills_list = [s.strip() for s in required_skills.split(',')]
                for skill_entry in skills_list:
                    if ':' in skill_entry:
                        parts = skill_entry.split(':')
                        if len(parts) >= 3:
                            skill_name = parts[0].strip()
                            try:
                                importance = int(parts[1].strip())
                                is_required = parts[2].lower() == 'true'
                            except ValueError:
                                importance = 5  # Default importance
                                is_required = True  # Default required
                            
                            skills_to_process.append({
                                "name": skill_name,
                                "importance": importance,
                                "is_required": is_required
                            })
                    else:
                        # Default format if no importance/required flags
                        skills_to_process.append({
                            "name": skill_entry,
                            "importance": 5,
                            "is_required": True
                        })
            
            # Create the role node
            query = """
            CREATE (r:Role {
                id: $id,
                job_title: $job_title,
                degree_requirement: $degree_requirement,
                field_of_study: $field_of_study,
                experience_years: $experience_years,
                location_remote: $location_remote,
                industry_sector: $industry_sector,
                role_level: $role_level,
                created_at: datetime()
            })
            RETURN r.id as id
            """
            
            params = {
                "id": role_id,
                "job_title": job_title,
                "degree_requirement": degree_requirement,
                "field_of_study": field_of_study,
                "experience_years": int(experience_years),
                "location_remote": location_remote,
                "industry_sector": industry_sector,
                "role_level": role_level
            }
            
            results = self.run_query(query, params)
            
            if results and len(results) > 0:
                # Now create skill nodes and relationships
                for skill_data in skills_to_process:
                    skill_query = """
                    MERGE (s:Skill {name: $skill_name})
                    WITH s
                    MATCH (r:Role {id: $role_id})
                    MERGE (r)-[rel:REQUIRES_SKILL {
                        importance: $importance,
                        is_required: $is_required
                    }]->(s)
                    """
                    
                    skill_params = {
                        "role_id": role_id,
                        "skill_name": skill_data["name"],
                        "importance": skill_data["importance"],
                        "is_required": skill_data["is_required"]
                    }
                    
                    self.run_query(skill_query, skill_params)
                    
                logger.info(f"Added new Role with ID: {role_id} and associated skills")
                return True
            else:
                logger.error("Failed to add Role")
                return False
                
        except Exception as e:
            logger.error(f"Error adding Role: {e}")
            return False

    def update_role(self, role_id, job_title, degree_requirement, field_of_study, 
                    experience_years, required_skills, location_remote,
                    industry_sector="", role_level=""):
        """
        Update an existing role in Neo4j with improved skill representation
        
        Returns:
            bool: Success or failure
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to update role")
            return False
        
        try:
            # Parse required_skills into a structured format
            # Input format should be: "Skill:importance:required,Skill2:importance:required"
            skills_to_process = []
            
            if isinstance(required_skills, str) and required_skills:
                skills_list = [s.strip() for s in required_skills.split(',')]
                for skill_entry in skills_list:
                    if ':' in skill_entry:
                        parts = skill_entry.split(':')
                        if len(parts) >= 3:
                            skill_name = parts[0].strip()
                            try:
                                importance = int(parts[1].strip())
                                is_required = parts[2].lower() == 'true'
                            except ValueError:
                                importance = 5
                                is_required = True
                            
                            skills_to_process.append({
                                "name": skill_name,
                                "importance": importance,
                                "is_required": is_required
                            })
                    else:
                        skills_to_process.append({
                            "name": skill_entry,
                            "importance": 5,
                            "is_required": True
                        })
            
            # Update the role node
            query = """
            MATCH (r:Role {id: $id})
            SET r.job_title = $job_title,
                r.degree_requirement = $degree_requirement,
                r.field_of_study = $field_of_study,
                r.experience_years = $experience_years,
                r.location_remote = $location_remote,
                r.industry_sector = $industry_sector,
                r.role_level = $role_level,
                r.updated_at = datetime()
            RETURN r.id as id
            """
            
            params = {
                "id": role_id,
                "job_title": job_title,
                "degree_requirement": degree_requirement,
                "field_of_study": field_of_study,
                "experience_years": int(experience_years),
                "location_remote": location_remote,
                "industry_sector": industry_sector,
                "role_level": role_level
            }
            
            results = self.run_query(query, params)
            
            if results and len(results) > 0:
                # First remove all existing skill relationships
                delete_skills_query = """
                MATCH (r:Role {id: $role_id})-[rel:REQUIRES_SKILL]->()
                DELETE rel
                """
                self.run_query(delete_skills_query, {"role_id": role_id})
                
                # Now create new skill nodes and relationships
                for skill_data in skills_to_process:
                    skill_query = """
                    MERGE (s:Skill {name: $skill_name})
                    WITH s
                    MATCH (r:Role {id: $role_id})
                    MERGE (r)-[rel:REQUIRES_SKILL {
                        importance: $importance,
                        is_required: $is_required
                    }]->(s)
                    """
                    
                    skill_params = {
                        "role_id": role_id,
                        "skill_name": skill_data["name"],
                        "importance": skill_data["importance"],
                        "is_required": skill_data["is_required"]
                    }
                    
                    self.run_query(skill_query, skill_params)
                    
                logger.info(f"Updated Role with ID: {role_id} and associated skills")
                return True
            else:
                logger.error(f"Failed to update Role with ID: {role_id} - Role not found")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Role: {e}")
            return False

    def delete_role(self, role_id):
        """
        Delete a role from Neo4j
        
        Returns:
            bool: Success or failure
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to delete role")
            return False
        
        try:
            query = """
            MATCH (r:Role {id: $id})
            DETACH DELETE r
            RETURN count(r) as deleted_count
            """
            
            params = {"id": role_id}
            
            results = self.run_query(query, params)
            
            if results and results[0]['deleted_count'] > 0:
                logger.info(f"Deleted Role with ID: {role_id}")
                return True
            else:
                logger.warning(f"No Role found with ID: {role_id} to delete")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting Role: {e}")
            return False
        
    # Add this method to the Neo4jService class

        # Update the insert_cv_data method
    
    def insert_cv_data(self, cv_data, cv_filename):
        """
        Insert structured CV data into Neo4j all at once using a transaction
        
        Args:
            cv_data: Structured CV data
            cv_filename: The filename of the CV
            
        Returns:
            bool: True if inserted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # Create a unique ID for the person based on filename
            file_id = cv_filename.replace(".", "_").replace(" ", "_")
            person_id = f"p{file_id}"
            
            with self.driver.session() as session:
                result = session.execute_write(self._create_cv_data_transaction, person_id, cv_data, cv_filename)
                
            logger.info(f"Successfully inserted CV data for {cv_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting CV data: {e}")
            return False
    
    def _create_cv_data_transaction(self, tx, person_id, cv_data, cv_filename):
        """
        Create all CV data in a single transaction
        
        Args:
            tx: Neo4j transaction
            person_id: Person ID
            cv_data: CV data
            cv_filename: CV filename
        """
        # Create file_id from cv_filename
        file_id = cv_filename.replace(".", "_").replace(" ", "_")
        # Create Person node
        tx.run("""
        CREATE (p:Person {
            id: $id,
            name: $name,
            role: $role,
            description: $summary,
            cv_file_name: $cv_filename,
            years_experience: $years_experience
        })
        """, {
            "id": person_id,
            "name": cv_data.person_name,
            "role": cv_data.current_role,
            "summary": cv_data.summary,
            "cv_filename": cv_filename,
            "years_experience": cv_data.years_experience
        })
        
        # Create Skills
        for idx, skill in enumerate(cv_data.skills):
            tx.run("""
            MERGE (s:Skill {name: $skill_name})
            WITH s
            MATCH (p:Person {id: $person_id})
            CREATE (p)-[r:HAS_SKILL {
                level: $level,
                years_experience: $years,
                last_used: $last_used
            }]->(s)
            """, {
                "person_id": person_id,
                "skill_name": skill['name'],
                "level": skill.get('level', ''),
                "years": skill.get('years_experience', 0),
                "last_used": skill.get('last_used', '')
            })
        
        # Create Education nodes
        for idx, edu in enumerate(cv_data.education):
            edu_id = f"e{file_id}_{idx}"
            tx.run("""
            CREATE (e:Education {
                id: $id,
                degree: $degree,
                university: $university,
                graduation_date: $graduation_date,
                field_of_study: $field_of_study
            })
            WITH e
            MATCH (p:Person {id: $person_id})
            CREATE (p)-[r:HAS_EDUCATION]->(e)
            """, {
                "id": edu_id,
                "person_id": person_id,
                "degree": edu.get('degree', ''),
                "university": edu.get('university', ''),
                "graduation_date": edu.get('graduation_date', ''),
                "field_of_study": edu.get('field_of_study', '')
            })
        
        # Create Position nodes
        for idx, pos in enumerate(cv_data.positions):
            pos_id = f"pos{file_id}_{idx}"
            company_name = pos.get('company', '')  # We'll need to add this to your position data model
            
            # Create position node
            tx.run("""
            CREATE (j:Position {
                id: $id,
                title: $title,
                location: $location,
                start_date: $start_date,
                end_date: $end_date,
                years_experience: $years
            })
            WITH j
            MATCH (p:Person {id: $person_id})
            CREATE (p)-[r:HAS_POSITION]->(j)
            """, {
                "id": pos_id,
                "person_id": person_id,
                "title": pos.get('title', ''),
                "location": pos.get('location', ''),
                "start_date": pos.get('start_date', ''),
                "end_date": pos.get('end_date', ''),
                "years": pos.get('years_experience', 0)
            })
            
            # If company name exists, create company relationship
            if company_name:
                tx.run("""
                MERGE (c:Company {name: $company_name})
                WITH c
                MATCH (j:Position {id: $pos_id})
                CREATE (j)-[r:AT_COMPANY]->(c)
                """, {
                    "company_name": company_name,
                    "pos_id": pos_id
                })
        
        # Create Project nodes  
        for idx, proj in enumerate(cv_data.projects):
            proj_id = f"proj{file_id}_{idx}"
            
            tx.run("""
            CREATE (p:Project {
                id: $id,
                name: $name,
                description: $description,
                outcomes: $outcomes
            })
            WITH p
            MATCH (person:Person {id: $person_id})
            CREATE (person)-[r:WORKED_ON]->(p)
            """, {
                "id": proj_id,
                "person_id": person_id,
                "name": proj.get('name', ''),
                "description": proj.get('description', ''),
                "outcomes": proj.get('outcomes', '')
            })
            
            # Add technology relationships for each project
            for tech in proj.get('technologies', []):
                if tech and isinstance(tech, str):
                    tech = tech.strip()
                    if tech:
                        tx.run("""
                        MERGE (s:Skill {name: $tech_name})
                        WITH s
                        MATCH (p:Project {id: $proj_id})
                        CREATE (p)-[r:USES_TECHNOLOGY]->(s)
                        """, {
                            "proj_id": proj_id,
                            "tech_name": tech
                        })
        
        # Update the CV node extraction status
        tx.run("""
        MATCH (c:CV {file_name: $cv_filename})
        SET c.extracted = true
        """, {"cv_filename": cv_filename})
        
        return True
        
    def find_matching_candidates(self, role_id, limit=10):

        pass
        #Don't consider the code below. It might change
        # """Find candidates matching a specific role"""
        # query = """
        # MATCH (role:Role {id: $role_id})
        # MATCH (role)-[req:REQUIRES_SKILL]->(skill:Skill)<-[has:HAS_SKILL]-(person:Person)
        # WITH person, 
        #      sum(CASE WHEN req.is_required THEN req.importance * 2 ELSE req.importance END) as skillScore
        # ORDER BY skillScore DESC
        # LIMIT $limit
        # RETURN person.id as id, person.role as role, person.description as description, 
        #        skillScore as score
        # """
        # return self.run_query(query, {"role_id": role_id, "limit": limit})