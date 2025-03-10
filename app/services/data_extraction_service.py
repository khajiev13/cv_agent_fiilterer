import logging
import os
import re
from string import Template
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from app.pyd_models.models import (
    PersonEntity,
    PersonEntityWithMetadata,
    ResponseSkills,
    ResponseExperiences,
    JobPostingData,

)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()




class DataExtractionService:
    def __init__(self):
        """Initialize the data extraction service with LangChain AzureChatOpenAI client"""
        self.langchain_model = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0
        )
        
        # Initialize the structured output models
        self.person_model = self.langchain_model.with_structured_output(PersonEntity)
        self.position_model = self.langchain_model.with_structured_output(ResponseExperiences)
        self.skill_model = self.langchain_model.with_structured_output(ResponseSkills)
        self.job_posting_model = self.langchain_model.with_structured_output(JobPostingData)
        
        # Define prompt templates for different entity types
        self._initialize_prompt_templates()

    def _initialize_prompt_templates(self):
        """Initialize prompt templates for entity extraction"""
        self.candidate_prompt_tpl = """From the Resume text below, extract person information with consistent formatting.
        
        You MUST extract the list of following fields exactly as specified:
        - id: Generate a unique identifier based on the name (e.g., "person_john_smith")
        - name: Full name of the candidate (lowercase)
        - job_title: Current professional role/title (lowercase)
        - description: Brief summary of background and specialization (1-2 sentences, max 100 characters, lowercase)
        - last_field_of_study: The field or major of study (e.g., "computer science", "business") (lowercase)
        - last_degree: MUST be EXACTLY one of these values only: "bachelor", "master", "phd", or "any" if unclear
        
        IMPORTANT:
        1. ALL text values MUST be lowercase
        2. Do NOT include other education details, position, or skill information
        3. Use "any" for last_degree ONLY if the degree level cannot be determined
        4. Ensure all fields are filled with appropriate values
        
        Resume text:
        $ctext
        """
        
        self.experience_prompt_tpl = """From the Resume text below, extract ALL work experience information with consistent formatting.
        
        For EACH position, extract the following fields exactly:
        - job_title: The position title (lowercase)
        - company_name: Name of the employer/company (lowercase)
        - experience_in_years: Number of years in this position as an INTEGER (must be non-negative)
        - description: Brief summary of responsibilities or achievements (1-2 sentences, lowercase)
        
        IMPORTANT:
        1. ALL text values MUST be lowercase
        2. Extract ALL positions/jobs mentioned in the resume
        3. Calculate experience_in_years based on start/end dates (round to nearest year)
        4. If exact dates aren't available, provide your best estimate
        5. experience_in_years MUST be a non-negative integer (0 if unclear)
        
        Resume text:
        $ctext
        """
    
        self.skills_prompt_tpl = """From the Resume text below, extract ALL professional skills with consistent formatting.
        
        For EACH skill, extract the following fields exactly:
        - name: The specific skill (lowercase)
        - level: MUST be EXACTLY one of: "beginner", "intermediate", or "expert"
        - years_experience: Number of years using this skill as an INTEGER (must be non-negative)
        
        IMPORTANT:
        1. ALL text values MUST be lowercase
        2. Extract EVERY technical and professional skill mentioned
        3. Infer the skill level from context (defaulting to "beginner" if unclear)
        4. If years_experience cannot be determined, use 1
        5. years_experience MUST be a non-negative integer
        6. Skills must be only one. No values allowed such as project management and marketing. It should be 2 seperate skills in the list for keyword matching with jobs.

        
        Resume text:
        $ctext
        """
    def clean_text(self, text):
        """Clean text to remove non-ASCII characters"""
        return re.sub(r'[^\x00-\x7F]+', ' ', text)

    async def extract_entities(self, prompt_template, cv_text, model):
        """
        Extract entities from CV text using LangChain's structured output
        
        Args:
            prompt_template: Template string for the prompt
            cv_text: CV text content
            model: LangChain model with structured output
            
        Returns:
            Validated structured data
        """
        try:
            # Prepare the prompt with CV text
            prompt = Template(prompt_template).substitute(ctext=self.clean_text(cv_text))
            
            # Call the model with structured output
            result = await model.ainvoke(prompt)
            return result
            
        except Exception as e:
            logger.error(f"Entity extraction error: {str(e)}")
            return None
            

    async def extract_job_posting_information_for_form(self, job_posting_text):
        """Extract job posting information to pre-fill the role form using LangChain"""
        logger.info("Extracting job posting information")
        
        try:
            prompt = """Extract key information from the job posting text below with consistent formatting for keyword matching with candidate resumes.
    
            Job posting:
            {0}
            
            Extract the following fields EXACTLY as specified:
            - job_title: The exact title of the position (lowercase)
            - alternative_titles: Comma-separated list of similar job titles that would qualify (lowercase, e.g., "software developer, software engineer, coder")
            - degree_requirement: MUST be EXACTLY one of these values only: "any", "bachelor", "master", "phd"
            - field_of_study: Required field or major (lowercase, e.g., "computer science", "business")
            - experience_years: Required minimum experience as a non-negative INTEGER (0 if unspecified)
            - required_skills: A comma-separated list of INDIVIDUAL skills required (lowercase, e.g., "python, sql, react")
            - alternative_skills: Comma-separated list of related/equivalent skills that would also qualify (lowercase, e.g., "django for python, mysql for sql, react.js for react")
            - location_remote: Job location or remote policy (lowercase)
            - industry_sector: Industry the role belongs to (lowercase)
            - role_level: Seniority level (lowercase, e.g., "junior", "senior", "manager")
            
            IMPORTANT:
            1. ALL text values MUST be lowercase
            2. For required_skills and alternative_skills, list EACH skill individually (not combined skills)
            3. For alternative_skills, include variations, abbreviations, and related technologies for each required skill
            4. Split compound skills (e.g., "project management" → "project, management")
            5. Include at least 3 alternative job titles that would be suitable for the same position
            6. Use "any" for degree_requirement ONLY if no specific requirement is mentioned
            7. Extract experience_years as a single number (the minimum required years)
            8. If specific years are not mentioned, use context to estimate or default to 0
            9. Be precise and concise for maximum keyword matching effectiveness
            """
            
            result = await self.job_posting_model.ainvoke(prompt.format(job_posting_text))
            return result
        
        except Exception as e:
            logger.error(f"Error extracting job posting information: {e}")
            return JobPostingData()  # Return empty object on error
        
    async def extract_cv_data(self, cv_text, cv_filename=None):
        """
        Extract structured data from a CV using LangChain models
        
        Args:
            cv_text: The text content of the CV
            cv_filename: The filename of the CV
            
        Returns:
            Structured CV data
        """
        logger.info(f"Extracting data from CV: {cv_filename}")
        
        try:
            # Extract all entities with LangChain structured output models
            person_data = await self.extract_entities(
                self.candidate_prompt_tpl,
                cv_text,
                self.person_model
            )
            
            experience_data = await self.extract_entities(
                self.experience_prompt_tpl,
                cv_text, 
                self.position_model
            )
            
            skill_data = await self.extract_entities(
                self.skills_prompt_tpl,
                cv_text, 
                self.skill_model
            )
            
            
            extracted_data = {
                "person": PersonEntityWithMetadata(person_data, cv_text=cv_text,cv_file_address=cv_filename),
                "experiences": experience_data,
                "skills": skill_data,
                "cv_file_address": cv_filename or ""
            }
            logger.info("Extracted data: %s", extracted_data)
            
        except Exception as e:
            logger.error(f"Error extracting CV data: {e}")
            return {
                "person": PersonEntity(),
                "experience": [],
                "skills": [],
                "cv_file_address": cv_filename or ""
            }
        finally:
            logger.info(f"Finished extracting data from CV: {cv_filename}")
            