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
        Retrieve all role nodes from Neo4j
        
        Returns:
            list: List of dictionaries containing role information
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to retrieve roles")
            return []
        
        try:
            query = """
            MATCH (role:Role) 
            RETURN role {.*} as role
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
        Delete all CV nodes and their connected data
        
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.connect():
            return False
            
        try:
            # Delete all Person nodes and their relationships
            query = """
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[r]->(n)
            DETACH DELETE p, n
            """
            
            self.run_query(query)
            logger.info("Deleted all CV nodes")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting all CV nodes: {e}")
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


    def add_role(self, role_id, job_title, degree_requirement, field_of_study, 
                experience_years, required_skills, location_remote):
        """
        Add a new role to Neo4j
        
        Returns:
            bool: Success or failure
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to add role")
            return False
        
        try:
            query = """
            CREATE (r:Role {
                id: $id,
                job_title: $job_title,
                degree_requirement: $degree_requirement,
                field_of_study: $field_of_study,
                experience_years: $experience_years,
                required_skills: $required_skills,
                location_remote: $location_remote,
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
                "required_skills": required_skills,
                "location_remote": location_remote
            }
            
            results = self.run_query(query, params)
            
            if results and len(results) > 0:
                logger.info(f"Added new Role with ID: {role_id}")
                return True
            else:
                logger.error("Failed to add Role")
                return False
                
        except Exception as e:
            logger.error(f"Error adding Role: {e}")
            return False

    def update_role(self, role_id, job_title, degree_requirement, field_of_study, 
                    experience_years, required_skills, location_remote):
        """
        Update an existing role in Neo4j
        
        Returns:
            bool: Success or failure
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to update role")
            return False
        
        try:
            query = """
            MATCH (r:Role {id: $id})
            SET r.job_title = $job_title,
                r.degree_requirement = $degree_requirement,
                r.field_of_study = $field_of_study,
                r.experience_years = $experience_years,
                r.required_skills = $required_skills,
                r.location_remote = $location_remote,
                r.updated_at = datetime()
            RETURN r.id as id
            """
            
            params = {
                "id": role_id,
                "job_title": job_title,
                "degree_requirement": degree_requirement,
                "field_of_study": field_of_study,
                "experience_years": int(experience_years),
                "required_skills": required_skills,
                "location_remote": location_remote
            }
            
            results = self.run_query(query, params)
            
            if results and len(results) > 0:
                logger.info(f"Updated Role with ID: {role_id}")
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