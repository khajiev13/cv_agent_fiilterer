import os
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Transaction
from dotenv import load_dotenv
import re
from app.pyd_models.models import (
    PersonEntityWithMetadata,
    ResponseExperiences,
    ResponseSkills,
    JobPostingData,
    EducationEntity
)
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
    
    # def generate_cypher(self, file_name, in_json):
    #     """Generate Cypher statements for entity and relationship insertion"""
    #     e_map = {}
    #     e_stmt = []
    #     r_stmt = []
    #     e_stmt_tpl = Template("($id:$label{id:'$key'})")
    #     r_stmt_tpl = Template("""
    #       MATCH $src
    #       MATCH $tgt
    #       MERGE ($src_id)-[:$rel]->($tgt_id)
    #     """)
        
    #     # Handle entities
    #     for obj in in_json:
    #         for j in obj['entities']:
    #             props = ''
    #             label = j['label']
    #             id = ''
    #             if label == 'Person':
    #                 id = 'p' + str(file_name)
    #             elif label == 'Position':
    #                 c = j['id'].replace('position', '_')
    #                 id = f'j{str(file_name)}{c}'
    #             elif label == 'Education':
    #                 c = j['id'].replace('education', '_')
    #                 id = f'e{str(file_name)}{c}'
    #             else:
    #                 id = self.get_cypher_compliant_var(j['name'])
                
    #             if label in ['Person', 'Position', 'Education', 'Skill', 'Company']:
    #                 varname = self.get_cypher_compliant_var(j['id'])
    #                 stmt = e_stmt_tpl.substitute(id=varname, label=label, key=id)
    #                 e_map[varname] = stmt
    #                 e_stmt.append('MERGE ' + stmt + self.get_prop_str(j, varname))
            
    #         # Handle relationships
    #         for st in obj['relationships']:
    #             rels = st.split("|")
    #             src_id = self.get_cypher_compliant_var(rels[0].strip())
    #             rel = rels[1].strip()
    #             if rel in ['HAS_SKILL', 'HAS_EDUCATION', 'AT_COMPANY', 'HAS_POSITION']:
    #                 tgt_id = self.get_cypher_compliant_var(rels[2].strip())
    #                 stmt = r_stmt_tpl.substitute(
    #                     src_id=src_id, tgt_id=tgt_id, src=e_map[src_id], tgt=e_map[tgt_id], rel=rel)
    #                 r_stmt.append(stmt)
        
    #     return e_stmt, r_stmt
    
    # def create_constraints(self):
    #     """Create necessary constraints in Neo4j"""
    #     constraints = [
    #         'CREATE CONSTRAINT unique_person_id IF NOT EXISTS FOR (n:Person) REQUIRE (n.id) IS UNIQUE',
    #         'CREATE CONSTRAINT unique_position_id IF NOT EXISTS FOR (n:Position) REQUIRE (n.id) IS UNIQUE',
    #         'CREATE CONSTRAINT unique_skill_id IF NOT EXISTS FOR (n:Skill) REQUIRE n.id IS UNIQUE',
    #         'CREATE CONSTRAINT unique_education_id IF NOT EXISTS FOR (n:Education) REQUIRE n.id IS UNIQUE',
    #         'CREATE CONSTRAINT unique_company_id IF NOT EXISTS FOR (n:Company) REQUIRE n.id IS UNIQUE'
    #     ]
        
    #     for constraint in constraints:
    #         self.run_query(constraint)
        
    #     logger.info("Neo4j constraints created")
        
    def get_all_roles(self) -> List[Dict[str, Any]]:
        pass

        
        
    def add_role(
        self, 
        role_id: str, 
        job_title: str, 
        alternative_titles: Optional[str] = None, 
        degree_requirement: Optional[str] = None, 
        fields_of_study: Optional[List[Dict[str, Any]]] = None,  # Changed to match actual input type 
        total_experience_years: int = 0, 
        required_skills: Optional[List[Dict[str, Any]]] = None,  # Changed to match actual input type
        location_city: Optional[str] = None,  # Changed from location to location_city
        remote_option: Optional[bool] = False, 
        industry_sector: Optional[str] = None, 
        role_level: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> bool:
        """
        Add a new role to Neo4j with support for alternative titles and fields
        
        Args:
            role_id: Unique identifier for the role
            job_title: Title of the job
            alternative_titles: Alternative titles for the job (comma-separated)
            degree_requirement: Required degree level
            fields_of_study: List of dictionaries with name, alternative_fields and importance
            total_experience_years: Required years of experience
            required_skills: List of dictionaries with name, alternative_names, importance and minimum_years
            location_city: Job location city
            remote_option: Remote work options
            industry_sector: Industry sector
            role_level: Level of the role
            keywords: Keywords related to the role (comma-separated)
            
        Returns:
            True if added successfully, False otherwise
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to add role")
            return False
        
        try:
            # Begin transaction for atomic operation
            with self.driver.session() as session:
                session.execute_write(
                    self._create_or_update_role_transaction, 
                    role_id, 
                    job_title,
                    alternative_titles,
                    degree_requirement,
                    fields_of_study,
                    total_experience_years,
                    required_skills,
                    location_city,  # Changed from location to location_city
                    remote_option,
                    industry_sector,
                    role_level,
                    keywords
                )
                
            logger.info(f"Role {role_id} added/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding role: {e}")
            return False
    
    def _create_role_transaction(
        self, 
        tx: Transaction, 
        role_id: str, 
        job_title: str, 
        alternative_titles: Optional[str] = None, 
        degree_requirement: Optional[str] = None, 
        fields_of_study: Optional[List[Dict[str, Any]]] = None, 
        total_experience_years: int = 0, 
        required_skills: Optional[List[Dict[str, Any]]] = None,
        location_city: Optional[str] = None,  
        remote_option: Optional[bool] = False, 
        industry_sector: Optional[str] = None, 
        role_level: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> bool:
        """
        Create a new JobPosting node and its relationships in Neo4j without updating existing data
        """
        # First check if the job posting already exists
        check_result = tx.run(
            "MATCH (j:JobPosting {id: $posting_id}) RETURN count(j) as count",
            {"posting_id": role_id}
        ).single()
        
        if check_result and check_result["count"] > 0:
            return False
        
        # Convert boolean to string for Neo4j compatibility
        remote_option_str = str(remote_option).lower()
        
        # Create JobPosting node with all properties (excluding location)
        tx.run("""
        CREATE (jp:JobPosting {
            id: $posting_id,
            title: $job_title,
            job_title: $job_title,
            alternative_titles: $alternative_titles,
            degree_requirement: $degree_requirement,
            total_experience_years: $total_experience_years,
            remote_option: $remote_option,
            industry_sector: $industry_sector,
            role_level: $role_level,
            keywords: $keywords,
            description: $job_description,
            posting_text: $posting_text,
            created_at: datetime()
        })
        RETURN jp
        """, {
            "posting_id": role_id,
            "job_title": job_title,
            "alternative_titles": alternative_titles or "",
            "degree_requirement": degree_requirement or "any",
            "total_experience_years": total_experience_years or 0,
            "remote_option": remote_option_str,
            "industry_sector": industry_sector or "",
            "role_level": role_level or "",
            "keywords": keywords or "",
            "job_description": keywords or "",
            "posting_text": f"{job_title} - {industry_sector or ''} - {keywords or ''}"
        })
        
        # Create LocationCity node and relationship if location_city is provided
        if location_city and location_city.strip():
            tx.run("""
            MERGE (lc:LocationCity {name: $location})
            WITH lc
            MATCH (jp:JobPosting {id: $posting_id})
            CREATE (jp)-[:AT]->(lc)
            """, {
                "posting_id": role_id,
                "location": location_city.strip().lower()
            })
        
        # Process fields of study relationships directly to JobPosting
        if fields_of_study:
            for field in fields_of_study:
                if isinstance(field, dict) and 'name' in field and field['name'].strip():
                    field_name = field['name'].strip().lower()
                    alternative_fields = field.get('alternative_fields', '').strip().lower() if field.get('alternative_fields') else ""
                    importance = field.get('importance', 'required')
                    
                    # Create main field of study node and relationship directly to JobPosting
                    tx.run("""
                    MERGE (f:FieldOfStudy {name: $field_name})
                    WITH f
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[rel:REQUIRES_FIELD_OF_STUDY {importance: $importance}]->(f)
                    """, {
                        "posting_id": role_id,
                        "field_name": field_name,
                        "importance": importance
                    })           
                    
                    # Create alternative fields
                    if alternative_fields:
                        for alt_field in [f.strip() for f in alternative_fields.split(",") if f.strip()]:
                            tx.run("""
                            MERGE (af:FieldOfStudy {name: $alt_field_name})
                            WITH af
                            MATCH (f:FieldOfStudy {name: $field_name})
                            CREATE (af)-[:ALTERNATIVE_OF]->(f)
                            """, {
                                "alt_field_name": alt_field,
                                "field_name": field_name
                            })
        
        # Process required skills
        if required_skills:
            for skill in required_skills:
                if isinstance(skill, dict) and 'name' in skill and skill['name'].strip():
                    skill_name = skill['name'].strip().lower()
                    importance = skill.get('importance', 'required')
                    minimum_years = skill.get('minimum_years', 0)
                    alt_names = skill.get('alternative_names', '')
                    
                    tx.run("""
                    MERGE (s:Skill {name: $skill_name})
                    WITH s
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[rel:REQUIRES_SKILL {
                        importance: $importance, 
                        is_required: $is_required,
                        minimum_years: $minimum_years
                    }]->(s)
                    """, {
                        "posting_id": role_id,
                        "skill_name": skill_name,
                        "importance": importance,
                        "is_required": importance == "required",
                        "minimum_years": minimum_years
                    })
                    
                    # Process alternative skill names
                    if alt_names:
                        for alt_name in [n.strip() for n in alt_names.split(",") if n.strip()]:
                            tx.run("""
                            MERGE (as:Skill {name: $alt_name})
                            WITH as
                            MATCH (s:Skill {name: $skill_name})
                            CREATE (as)-[:ALTERNATIVE_OF]->(s)
                            """, {
                                "alt_name": alt_name,
                                "skill_name": skill_name
                            })
    
        # Create REQUIRES_EXPERIENCE relationship
        if job_title and total_experience_years:
            #Create job title experience as Experience node
            tx.run("""
            MERGE (e:Experience {title: $job_title})
            WITH e
            MATCH (jp:JobPosting {id: $posting_id})
            CREATE (jp)-[:REQUIRES_EXPERIENCE {years: $total_experience_years}]->(e)
            """, {
                "posting_id": role_id,
                "job_title": job_title,
                "total_experience_years": total_experience_years
            })
            #Create similar job titles as experience nodes
            if alternative_titles:
                for alt_title in [t.strip() for t in alternative_titles.split(",") if t.strip()]:
                    tx.run("""
                    MERGE (e:Experience {title: $alt_title})
                    WITH e
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[:REQUIRES_EXPERIENCE {years: $total_experience_years}]->(e)
                    """, {
                        "posting_id": role_id,
                        "alt_title": alt_title,
                        "total_experience_years": total_experience_years
                    })
            
        # Add any explicit keywords as Keyword nodes
        if keywords:
            for keyword in [k.strip() for k in keywords.split(",") if k.strip()]:
                tx.run("""
                MERGE (k:Keyword {name: $keyword})
                WITH k
                MATCH (jp:JobPosting {id: $posting_id})
                CREATE (jp)-[:HAS_KEYWORD]->(k)
                """, {
                    "posting_id": role_id,
                    "keyword": keyword
                })
        
        return True
    
    def _update_role_transaction(
        self, 
        tx: Transaction, 
        role_id: str, 
        job_title: str, 
        alternative_titles: Optional[str] = None, 
        degree_requirement: Optional[str] = None, 
        fields_of_study: Optional[List[Dict[str, Any]]] = None, 
        total_experience_years: int = 0, 
        required_skills: Optional[List[Dict[str, Any]]] = None,
        location_city: Optional[str] = None,  
        remote_option: Optional[bool] = False, 
        industry_sector: Optional[str] = None, 
        role_level: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> bool:
        """
        Update an existing JobPosting node and its relationships in Neo4j
        """
        # First delete all existing relationships
        tx.run("""
        MATCH (jp:JobPosting {id: $posting_id})
        OPTIONAL MATCH (jp)-[r]-()
        DELETE r
        """, {"posting_id": role_id})
        
        # Update node properties (excluding location which will be a separate node)
        remote_option_str = str(remote_option).lower()
        
        tx.run("""
        MATCH (jp:JobPosting {id: $posting_id})
        SET jp.title = $job_title,
            jp.job_title = $job_title,
            jp.alternative_titles = $alternative_titles,
            jp.degree_requirement = $degree_requirement,
            jp.total_experience_years = $total_experience_years,
            jp.remote_option = $remote_option,
            jp.industry_sector = $industry_sector,
            jp.role_level = $role_level,
            jp.keywords = $keywords,
            jp.description = $job_description,
            jp.posting_text = $posting_text,
            jp.updated_at = datetime()
        """, {
            "posting_id": role_id,
            "job_title": job_title,
            "alternative_titles": alternative_titles or "",
            "degree_requirement": degree_requirement or "any",
            "total_experience_years": total_experience_years or 0,
            "remote_option": remote_option_str,
            "industry_sector": industry_sector or "",
            "role_level": role_level or "",
            "keywords": keywords or "",
            "job_description": keywords or "",
            "posting_text": f"{job_title} - {industry_sector or ''} - {keywords or ''}"
        })
        
        # Create LocationCity node and relationship if location_city is provided
        if location_city and location_city.strip():
            tx.run("""
            MERGE (lc:LocationCity {name: $location})
            WITH lc
            MATCH (jp:JobPosting {id: $posting_id})
            CREATE (jp)-[:AT]->(lc)
            """, {
                "posting_id": role_id,
                "location": location_city.strip().lower()
            })
        
        # Process fields of study
        if fields_of_study:
            for field in fields_of_study:
                if isinstance(field, dict) and 'name' in field and field['name'].strip():
                    field_name = field['name'].strip().lower()
                    alternative_fields = field.get('alternative_fields', '').strip().lower() if field.get('alternative_fields') else ""
                    importance = field.get('importance', 'required')
                    
                    tx.run("""
                    MERGE (f:FieldOfStudy {name: $field_name})
                    WITH f
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[rel:REQUIRES_FIELD_OF_STUDY {importance: $importance}]->(f)
                    """, {
                        "posting_id": role_id,
                        "field_name": field_name,
                        "importance": importance
                    })
                    
                    # Create alternative fields
                    if alternative_fields:
                        for alt_field in [f.strip() for f in alternative_fields.split(",") if f.strip()]:
                            tx.run("""
                            MERGE (af:FieldOfStudy {name: $alt_field_name})
                            WITH af
                            MATCH (f:FieldOfStudy {name: $field_name})
                            CREATE (af)-[:ALTERNATIVE_OF]->(f)
                            """, {
                                "alt_field_name": alt_field,
                                "field_name": field_name
                            })
        
        # Process required skills - using same logic as create transaction
        if required_skills:
            for skill in required_skills:
                if isinstance(skill, dict) and 'name' in skill and skill['name'].strip():
                    skill_name = skill['name'].strip().lower()
                    importance = skill.get('importance', 'required')
                    minimum_years = skill.get('minimum_years', 0)
                    alt_names = skill.get('alternative_names', '')
                    
                    tx.run("""
                    MERGE (s:Skill {name: $skill_name})
                    WITH s
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[rel:REQUIRES_SKILL {
                        importance: $importance, 
                        is_required: $is_required,
                        minimum_years: $minimum_years
                    }]->(s)
                    """, {
                        "posting_id": role_id,
                        "skill_name": skill_name,
                        "importance": importance,
                        "is_required": importance == "required",
                        "minimum_years": minimum_years
                    })
                    
                    # Process alternative skill names
                    if alt_names:
                        for alt_name in [n.strip() for n in alt_names.split(",") if n.strip()]:
                            tx.run("""
                            MERGE (as:Skill {name: $alt_name})
                            WITH as
                            MATCH (s:Skill {name: $skill_name})
                            CREATE (as)-[:ALTERNATIVE_OF]->(s)
                            """, {
                                "alt_name": alt_name,
                                "skill_name": skill_name
                            })
        
        # Create REQUIRES_EXPERIENCE relationship - same as in create transaction
        if job_title and total_experience_years:
            tx.run("""
            MERGE (e:Experience {title: $job_title})
            WITH e
            MATCH (jp:JobPosting {id: $posting_id})
            CREATE (jp)-[:REQUIRES_EXPERIENCE {years: $total_experience_years}]->(e)
            """, {
                "posting_id": role_id,
                "job_title": job_title,
                "total_experience_years": total_experience_years
            })
            
            if alternative_titles:
                for alt_title in [t.strip() for t in alternative_titles.split(",") if t.strip()]:
                    tx.run("""
                    MERGE (e:Experience {title: $alt_title})
                    WITH e
                    MATCH (jp:JobPosting {id: $posting_id})
                    CREATE (jp)-[:REQUIRES_EXPERIENCE {years: $total_experience_years}]->(e)
                    """, {
                        "posting_id": role_id,
                        "alt_title": alt_title,
                        "total_experience_years": total_experience_years
                    })
        
        # Add keywords
        if keywords:
            for keyword in [k.strip() for k in keywords.split(",") if k.strip()]:
                tx.run("""
                MERGE (k:Keyword {name: $keyword})
                WITH k
                MATCH (jp:JobPosting {id: $posting_id})
                CREATE (jp)-[:HAS_KEYWORD]->(k)
                """, {
                    "posting_id": role_id,
                    "keyword": keyword
                })
        
        return True
    
    def _create_or_update_role_transaction(
        self, 
        tx: Transaction, 
        role_id: str, 
        job_title: str, 
        alternative_titles: Optional[str] = None, 
        degree_requirement: Optional[str] = None, 
        fields_of_study: Optional[List[Dict[str, Any]]] = None, 
        total_experience_years: int = 0, 
        required_skills: Optional[List[Dict[str, Any]]] = None,
        location_city: Optional[str] = None,  
        remote_option: Optional[bool] = False, 
        industry_sector: Optional[str] = None, 
        role_level: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> bool:
        """
        Create a new role or update an existing one in Neo4j
        
        This function checks if the role exists and delegates to the appropriate
        create or update transaction method.
        """
        # Check if the job posting already exists
        check_result = tx.run(
            "MATCH (j:JobPosting {id: $posting_id}) RETURN count(j) as count",
            {"posting_id": role_id}
        ).single()
        
        # Determine whether to create or update
        if check_result and check_result["count"] > 0:
            # Role exists, update it
            logger.info(f"Updating existing role with ID {role_id}")
            return self._update_role_transaction(
                tx, 
                role_id, 
                job_title,
                alternative_titles,
                degree_requirement,
                fields_of_study,
                total_experience_years,
                required_skills,
                location_city,  
                remote_option,
                industry_sector,
                role_level,
                keywords
            )
        else:
            # Role doesn't exist, create it
            logger.info(f"Creating new role with ID {role_id}")
            return self._create_role_transaction(
                tx, 
                role_id, 
                job_title,
                alternative_titles,
                degree_requirement,
                fields_of_study,
                total_experience_years,
                required_skills,
                location_city,  
                remote_option,
                industry_sector,
                role_level,
                keywords
            )
        
    def add_candidate(
        self,
        candidate_id: str,
        person_data: PersonEntityWithMetadata,
        experiences: ResponseExperiences,
        skills: ResponseSkills
    ) -> bool:
        logger.info(f"Attempting to add candidate with metadata: {person_data}")

        if not self.connect():
            return False
        
        try:
            with self.driver.session() as session:
                session.execute_write(
                    self._create_candidate_transaction,
                    candidate_id,
                    person_data,
                    experiences,
                    skills
                )
            return True
        except Exception as e:
            logger.error(f"Error adding candidate: {e}")
            return False
        
    def _create_candidate_transaction(
        self,
        tx: Transaction,
        candidate_id: str,
        person_data: PersonEntityWithMetadata,
        experiences: ResponseExperiences,
        skills: ResponseSkills
    ) -> bool:
        
        # Prepare all parameters for the first query
        # Education parameters
        education_params = []
        alt_fields_params = []
        for edu in person_data.has_degrees or []:
            if edu.field_of_study and edu.field_of_study.strip():
                education_params.append({
                    "field": edu.field_of_study.lower(),
                    "university": edu.university.lower() if edu.university else "",
                    "degree": edu.degree or "",
                    "year": edu.graduation_year or 0
                })
                
                if edu.alternative_fields:
                    for alt_field in edu.alternative_fields:
                        if alt_field.strip():
                            alt_fields_params.append({
                                "main_field": edu.field_of_study.lower(),
                                "alt_field": alt_field.lower()
                            })
        
        # Experience parameters
        experience_params = []
        alt_exp_params = []
        for exp in experiences.experience or []:
            if exp.job_title and exp.job_title.strip():
                experience_params.append({
                    "title": exp.job_title.lower(),
                    "years": exp.experience_in_years or 0,
                    "company": exp.company_name or "",
                    "description": exp.description or ""
                })
                
                if exp.alternative_job_titles:
                    for alt in [t.strip() for t in exp.alternative_job_titles.split(",") if t.strip()]:
                        alt_exp_params.append({
                            "main_title": exp.job_title.lower(),
                            "alt_title": alt.lower()
                        })
        
        # Skill parameters
        skill_params = []
        alt_skill_params = []
        for skill in skills.skills or []:
            if skill.name and skill.name.strip():
                skill_params.append({
                    "name": skill.name.lower(),
                    "level": skill.level or "beginner",
                    "years": skill.years_experience or 0
                })
                
                if skill.alternative_names:
                    for alt in [n.strip() for n in skill.alternative_names.split(",") if n.strip()]:
                        alt_skill_params.append({
                            "main_skill": skill.name.lower(),
                            "alt_skill": alt.lower()
                        })
        
        # Execute the first query with all direct relationships
        tx.run("""
        MERGE (c:Candidate {id: $candidate_id})
        SET c.name = $name,
            c.job_title = $job_title,
            c.description = $description,
            c.cv_text = $cv_text,
            c.cv_file_address = $cv_file_address,
            c.created_at = datetime()
    
        // Location if provided
        WITH c
        FOREACH (loc IN CASE WHEN $location <> '' THEN [1] ELSE [] END |
          MERGE (lc:LocationCity {name: $location})
          MERGE (c)-[:FROM]->(lc)
        )
    
        // Add all educational backgrounds
        WITH c
        UNWIND $education AS edu
        MERGE (f:FieldOfStudy {name: edu.field})
        MERGE (c)-[:HAS_FIELD_OF_STUDY {
          university: edu.university,
          degree: edu.degree,
          graduation_year: edu.year
        }]->(f)
    
        // Add all experiences
        WITH c
        UNWIND $experiences AS exp
        MERGE (e:Experience {title: exp.title})
        MERGE (c)-[:HAS_EXPERIENCE {
          years: exp.years,
          company: exp.company,
          description: exp.description
        }]->(e)
    
        // Add all skills
        WITH c
        UNWIND $skills AS skill
        MERGE (s:Skill {name: skill.name})
        MERGE (c)-[:HAS_SKILL {
          level: skill.level,
          years: skill.years
        }]->(s)
        """, {
            "candidate_id": candidate_id,
            "name": person_data.name,
            "job_title": person_data.job_title,
            "description": person_data.description,
            "cv_text": person_data.cv_text,
            "cv_file_address": person_data.cv_file_address,
            "location": person_data.location_city.strip().lower() if hasattr(person_data, 'location_city') and person_data.location_city else "",
            "education": education_params,
            "experiences": experience_params,
            "skills": skill_params
        })
        
        # Execute second query for all alternatives if needed
        if alt_fields_params or alt_exp_params or alt_skill_params:
            tx.run("""
            // Process alternative fields
            UNWIND $alt_fields AS alt
            MERGE (af:FieldOfStudy {name: alt.alt_field})
            WITH af, alt
            MATCH (f:FieldOfStudy {name: alt.main_field})
            MERGE (af)-[:ALTERNATIVE_OF]->(f)
    
            // Process alternative experiences
            WITH 1 as dummy
            UNWIND $alt_experiences AS alt_exp
            MERGE (ae:Experience {title: alt_exp.alt_title})
            WITH ae, alt_exp
            MATCH (e:Experience {title: alt_exp.main_title})
            MERGE (ae)-[:ALTERNATIVE_OF]->(e)
    
            // Process alternative skills
            WITH 1 as dummy
            UNWIND $alt_skills AS alt_skill
            MERGE (as:Skill {name: alt_skill.alt_skill})
            WITH as, alt_skill
            MATCH (s:Skill {name: alt_skill.main_skill})
            MERGE (as)-[:ALTERNATIVE_OF]->(s)
            """, {
                "alt_fields": alt_fields_params,
                "alt_experiences": alt_exp_params,
                "alt_skills": alt_skill_params
            })
        
        return True

    def get_all_candidates(self) -> List[Dict[str, Any]]:
        """
        Get all candidates from the database
        
        Returns:
            List of dictionaries containing candidate data
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to fetch candidates")
            return []
        
        query = """
        MATCH (c:Candidate)
        RETURN 
            c.id as id,
            c.name as name,
            c.job_title as job_title,
            c.description as description,
            c.cv_file_address as file_path,
            c.created_at as upload_date,
            EXISTS((c)-[:HAS_SKILL]->()) as has_skills,
            EXISTS((c)-[:HAS_EXPERIENCE]->()) as has_experience,
            EXISTS((c)-[:HAS_FIELD_OF_STUDY]->()) as has_education
        """
        
        try:
            result = self.run_query(query)
            return result if result else []
        except Exception as e:
            logger.error(f"Error fetching candidates: {e}")
            return []

    def delete_candidate(self, candidate_id: str) -> tuple[str, bool]:
        """
        Delete a candidate and all their relationships
        
        Args:
            candidate_id: ID of the candidate to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to delete candidate")
            return False
        
        # First get the file path before deleting
        query_file_path = """
        MATCH (c:Candidate {id: $candidate_id})
        RETURN c.cv_file_address as file_path
        """
        
        try:
            result = self.run_query(query_file_path, {"candidate_id": candidate_id})
            file_path = result[0]["file_path"] if result and "file_path" in result[0] else None
            
            # Delete the candidate and all relationships using DETACH DELETE
            delete_query = """
            MATCH (c:Candidate {id: $candidate_id})
            DETACH DELETE c
            """
            
            self.run_query(delete_query, {"candidate_id": candidate_id})
            
            return file_path, True
        except Exception as e:
            logger.error(f"Error deleting candidate: {e}")
            return None, False

    def delete_all_candidates(self) -> tuple[list[str], bool]:
        """
        Delete all candidates and their relationships
        
        Returns:
            tuple: (list of file paths to delete, success boolean)
        """
        if not self.connect():
            logger.warning("Cannot connect to Neo4j to delete all candidates")
            return [], False
        
        # First get all file paths
        query_file_paths = """
        MATCH (c:Candidate)
        RETURN c.cv_file_address as file_path
        """
        
        try:
            result = self.run_query(query_file_paths)
            file_paths = [r["file_path"] for r in result if r.get("file_path")]
            
            # Delete all candidates and relationships using DETACH DELETE
            delete_query = """
            MATCH (c:Candidate)
            DETACH DELETE c
            """
            
            self.run_query(delete_query)
            
            return file_paths, True
        except Exception as e:
            logger.error(f"Error deleting all candidates: {e}")
            return [], False