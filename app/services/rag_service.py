import os
import logging
from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.graph_databases.neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class RAGCandidateService:
    """
    RAG service for candidate filtering using LangChain and Neo4j
    """
    
    def __init__(self, neo4j_uri, neo4j_username, neo4j_password, openai_api_key=None):
        """Initialize the RAG service with Neo4j and OpenAI credentials"""
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize Neo4j graph for LangChain
        self.graph = Neo4jGraph(
            url=self.neo4j_uri,
            username=self.neo4j_username,
            password=self.neo4j_password
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=self.openai_api_key
        )
        
        # Schema information to help the LLM understand the database
        self._refresh_schema()
    
    def _refresh_schema(self):
        """Get the current Neo4j schema"""
        self.schema = self.graph.get_schema
        
    def _generate_cypher_query(self, user_query: str) -> str:
        """Generate a Cypher query from a natural language query"""
        cypher_prompt = PromptTemplate(
            template="""
            You are an expert in translating natural language into Neo4j Cypher queries.
            
            Database schema:
            Person nodes with properties: id, name, role, description, cv_file_name, years_experience
            Skill nodes with properties: name
            Position nodes with properties: id, title, location, start_date, end_date, years_experience
            Education nodes with properties: id, degree, university, graduation_date, field_of_study
            Company nodes with properties: name
            
            Relationships:
            (Person)-[HAS_SKILL]->(Skill) with properties: level, years_experience, last_used
            (Person)-[HAS_POSITION]->(Position)
            (Position)-[AT_COMPANY]->(Company)
            (Person)-[HAS_EDUCATION]->(Education)
            
            User query: {user_query}
            
            Convert this query to a Cypher query that returns Person nodes with their name and cv_file_name.
            Always include LIMIT 10 to avoid excessive results. If the query mentions expertise or skill in something,
            look for that in the Skill nodes connected to Person nodes. If it mentions experience, use the Person's years_experience
            or the specific experience in a skill. For ordering, use ORDER BY clauses appropriately.
            
            Return ONLY the Cypher query without any explanation.
            """,
            input_variables=["user_query"],
        )
        
        cypher_chain = LLMChain(llm=self.llm, prompt=cypher_prompt)
        cypher_query = cypher_chain.invoke({"user_query": user_query})
        
        return cypher_query["text"].strip()
    
    def query_candidates(self, query: str) -> List[Dict[str, Any]]:
        """
        Process a natural language query and return matching candidates
        
        Args:
            query: Natural language query (e.g., "Find candidates with React experience")
            
        Returns:
            List of candidate dictionaries with name and cv_file_name
        """
        try:
            # Generate Cypher query from natural language
            cypher_query = self._generate_cypher_query(query)
            logger.info(f"Generated Cypher query: {cypher_query}")
            
            # Execute the query
            results = self.graph.query(cypher_query)
            
            # Process results to ensure consistent format
            candidates = []
            for result in results:
                # Make sure we have the essential fields
                if isinstance(result, dict) and 'name' in result and 'cv_file_name' in result:
                    candidates.append({
                        'name': result['name'],
                        'cv_file_name': result['cv_file_name'],
                        'role': result.get('role', ''),
                        'years_experience': result.get('years_experience', 0),
                    })
                    
                    # Include any additional fields that might be present
                    for key, value in result.items():
                        if key not in ['name', 'cv_file_name', 'role', 'years_experience']:
                            candidates[-1][key] = value
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return []
            
    def get_candidate_details(self, cv_file_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific candidate
        
        Args:
            cv_file_name: The CV filename to look up
            
        Returns:
            Dictionary with candidate details
        """
        try:
            query = """
            MATCH (p:Person {cv_file_name: $cv_file_name})
            OPTIONAL MATCH (p)-[hs:HAS_SKILL]->(s:Skill)
            OPTIONAL MATCH (p)-[he:HAS_EDUCATION]->(e:Education)
            OPTIONAL MATCH (p)-[hp:HAS_POSITION]->(pos:Position)
            OPTIONAL MATCH (pos)-[ac:AT_COMPANY]->(c:Company)
            
            WITH p, 
                collect(distinct {
                    skill: s.name, 
                    level: hs.level, 
                    years: hs.years_experience
                }) as skills,
                collect(distinct {
                    degree: e.degree, 
                    university: e.university, 
                    field: e.field_of_study, 
                    graduation: e.graduation_date
                }) as education,
                collect(distinct {
                    title: pos.title, 
                    company: c.name, 
                    start: pos.start_date, 
                    end: pos.end_date, 
                    years: pos.years_experience
                }) as positions
                
            RETURN p {
                .name, 
                .role, 
                .description, 
                .cv_file_name, 
                .years_experience, 
                skills: skills, 
                education: education, 
                positions: positions
            } as candidate
            """
            
            results = self.graph.query(query, {'cv_file_name': cv_file_name})
            
            if results and len(results) > 0:
                return results[0].get('candidate', {})
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting candidate details: {e}")
            return {}
