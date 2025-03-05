import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate

# Load environment variables
load_dotenv()

class RAGService:
    def __init__(self):
        # Initialize Azure OpenAI
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            temperature=0
        )
        
        # Initialize Neo4j connection 
        self.graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            enhanced_schema=True,
        )
        
        # Refresh schema to ensure we have the latest
        self.graph.refresh_schema()
        
        # Create the Cypher generation template
        self._setup_cypher_chain()
    
    def _setup_cypher_chain(self):
        # Cypher generation template with resume matching examples
        CYPHER_GENERATION_TEMPLATE = """Task: Generate Cypher statement to query a graph database.
        
        Instructions:
        Use only the provided relationship types and properties in the schema.
        Do not use any other relationship types or properties that are not provided.
        
        Schema:
        {schema}
        
        Examples:
        # Find candidates with Python skills
        MATCH (p:Person)-[r:HAS_SKILL]->(s:Skill) 
        WHERE s.name = "Python" 
        RETURN p.name, p.role, p.years_experience
        
        # Find candidates with at least bachelor's degree in Computer Science
        MATCH (p:Person)-[:HAS_EDUCATION]->(e:Education)
        WHERE e.field_of_study CONTAINS "Computer Science" 
        AND (e.degree CONTAINS "Bachelor" OR e.degree CONTAINS "Master" OR e.degree CONTAINS "PhD")
        RETURN p.name, p.role, e.degree, e.university
        
        Note: Do not include any explanations or apologies in your responses.
        Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
        Do not include any text except the generated Cypher statement.
        
        The question is:
        {question}
        """
        
        CYPHER_GENERATION_PROMPT = PromptTemplate(
            input_variables=["schema", "question"], 
            template=CYPHER_GENERATION_TEMPLATE
        )
        
        # Configure chain to provide natural language responses
        self.chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            validate_cypher=True,
            return_intermediate_steps=True,
            return_direct=True,  # Process results with LLM
            verbose=True,
            allow_dangerous_requests=True
        )

    def query(self, query_text: str) -> str:
        """
        Process a query using the RAG system and return a text response.
        """        
        try:
            # Execute the chain and get text response
            result = self.chain({
                "query": query_text,
                "schema": self.graph.schema
            })
            
            # Return the text response
            return result.get("result", "I couldn't find an answer to that question.")
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    def get_schema(self) -> str:
        """Returns the current Neo4j graph schema"""
        return self.graph.schema
    
    def clear_memory(self) -> None:
        """Clear the conversation memory"""
        # This is a placeholder in case memory is implemented later
        pass