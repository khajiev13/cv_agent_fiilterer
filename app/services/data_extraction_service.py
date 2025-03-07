import logging
import openai
import asyncio
import os
import json
import re
from string import Template
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field, validator
from app.pyd_models.models import JobPostingData, PersonResponse,PositionResponse,  EducationResponse, SkillResponse,ProjectResponse
from typing import Optional, List
from typing import Literal


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add this after the JobPostingData class


    
    @validator('degree_requirement')
    def validate_degree(cls, v):
        valid_degrees = ["Any", "Bachelor", "Master", "PhD"]
        return v if v in valid_degrees else "Any"
    
    @validator('total_years_experience')
    def validate_experience(cls, v):
        return max(0, v)  # Ensure non-negative


class DataExtractionService:
    def __init__(self):
        """Initialize the data extraction service with Azure OpenAI client"""
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        # Define prompt templates for different entity types
        self._initialize_prompt_templates()

    def _initialize_prompt_templates(self):
        """Initialize prompt templates for entity extraction"""
        self.candidate_prompt_tpl = """From the Resume text below, extract person information with consistent formatting.
                
        1. Extract the following information about the candidate:
           Required fields:
           name:string,current_role:string,description:string,last_field_of_study:string
           
        2. IMPORTANT: Convert all text values to lowercase (name, role, etc.)
        3. For the description field, summarize the candidate's background and specialization in 1-2 sentences (max 100 characters)
        4. Extract the candidate's full name and current professional role/title
        5. For last_field_of_study, determine the highest level of education completed using ONLY one of these values: "bachelor", "master", "phd", or "any" (if unclear)
        6. DO NOT include other education details, position, or skill information - those will be extracted separately
        
        Example Output Format (note all text is lowercase):
        {"entities": [
          {"name":"john smith","current_role":"senior software engineer","description":"backend developer with 7 years experience specializing in python and cloud architecture","last_field_of_study":"master"}
        ]}
        
        Question: Extract person information from the text below -
        $ctext
        
        Return ONLY valid JSON:
        """
        self.experience_prompt_tpl = """From the Resume text for a job aspirant below, extract Experience information with consistent formatting.
        
        1. Extract Position & Company information from the text:
           Required fields for each position:
           job_title:string,company_name:string,experience_in_years:integer,description:string
        
        2. IMPORTANT: Convert all text values to lowercase (job_titles, company names, etc.)
        3. Calculate experience_in_years based on the duration at each position 
        4. For each position, include a brief description (1-2 sentences) of responsibilities or achievements
        
        Example Output Format:
        {"entities": [
          {"job_title":"software engineer","company_name":"acme tech","experience_in_years":3,"description":"developed backend apis and optimized database queries"},
          {"job_title":"junior developer","company_name":"xyz solutions","experience_in_years":2,"description":"maintained legacy codebase and implemented new features"}
        ]}
        
        Question: Extract work experience information from the text below -
        $ctext
        
        Return ONLY valid JSON:
        """

        self.skills_prompt_tpl = """From the Resume text below, extract skill information with consistent formatting.
        
        1. Look for all professional skills in the text:
            Required fields for each skill:
            name:string,years_experience:integer,last_used:string,category:string
        2. IMPORTANT: Convert ALL text values to lowercase (skill names, categories, etc.)
        3. If years_experience cannot be determined, default to 1
        Example Output Format (note all text is lowercase):
        {"entities": [
          {"name":"python","years_experience":6,"last_used":"2023"},
          {"name":"project management","years_experience":3,"last_used":"2022"}
        ]}
        
        Question: Extract skill information from the text below -
        $ctext
        
        Return ONLY valid JSON:
        """


    def clean_text(self, text):
        """Clean text to remove non-ASCII characters"""
        return re.sub(r'[^\x00-\x7F]+', ' ', text)

    
# Update the extract_entities method

    async def extract_entities(self, prompt, cv_text, cv_filename=None, response_model=None):
        """
        Extract entities from CV text using Azure OpenAI with Pydantic model validation
        
        Args:
            prompt: Prompt template to use
            cv_text: CV text content
            cv_filename: Optional CV filename to replace in template
            response_model: Pydantic model class to validate response against
            
        Returns:
            Validated Pydantic model or dict with entities
        """
        try:          
            # Prepare the prompt with CV text
            _prompt = Template(prompt).substitute(ctext=self.clean_text(cv_text))
            
            messages_content = _prompt
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": messages_content}],
                temperature=0,
                max_tokens=1024,
                top_p=0.8,
                response_format={"type": "json_object"} if response_model else None
            )
            
            # Extract and parse result
            result_text = response.choices[0].message.content
            if 'Answer:' in result_text:
                result_text = result_text.split('Answer:')[1].strip()
            
            # Remove JSON code block markers if present
            result_text = self._clean_json_response(result_text)
            
            try:
                # Parse as JSON first
                extraction_dict = json.loads(result_text)
                
                # If a response model is provided, validate against it
                if response_model:
                    try:
                        validated_model = response_model.parse_obj(extraction_dict)
                        return validated_model
                    except Exception as validation_error:
                        logger.error(f"Model validation error: {validation_error}")
                        # Fall back to returning the raw dictionary
                        return extraction_dict
                else:
                    return extraction_dict
                    
            except json.JSONDecodeError as e:
                # Handle incomplete JSON responses
                logger.error(f"JSON parse error: {e}")
                # Attempt to recover from common JSON issues
                try:
                    # Try to fix the JSON
                    cleaned_json = self._fix_json_response(result_text)
                    extraction_dict = json.loads(cleaned_json)
                    
                    # If a response model is provided, validate
                    if response_model:
                        try:
                            validated_model = response_model.parse_obj(extraction_dict)
                            return validated_model
                        except:
                            return extraction_dict
                    else:
                        return extraction_dict
                        
                except:
                    logger.error(f"Failed to recover malformed JSON: {result_text[:200]}...")
                    # Return empty response matching expected model if provided
                    if response_model:
                        try:
                            return response_model.parse_obj({"entities": []})
                        except:
                            pass
                    return {"entities": []}
                    
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            if response_model:
                try:
                    return response_model.parse_obj({"entities": []})
                except:
                    pass
            return {"entities": []}
        

    def _clean_json_response(self, text):
        """Clean JSON response from code blocks and other formatting"""
        # Remove code block markers if present
        json_pattern = r'```(?:json)?(.*?)```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Use the first match that looks like JSON
            for match in matches:
                cleaned = match.strip()
                if cleaned.startswith('{') and ('}' in cleaned):
                    return cleaned
        
        # If no code blocks found or they didn't contain valid JSON,
        # try to extract JSON directly
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            return text[json_start:json_end+1]
            
        # Return original if we couldn't extract anything
        return text
    def _fix_json_response(self, text):
        """Attempt to fix common JSON issues in API responses"""
        # Replace single quotes with double quotes
        text = text.replace("'", '"')
        
        # Make sure we have a valid JSON object
        if not text.strip().startswith('{'):
            text = '{' + text
        
        if not text.strip().endswith('}'):
            text = text + '}'
            
        # Try to find and fix simple syntax errors
        # Ensure "entities" has proper array brackets
        if '"entities":' in text and not '"entities": [' in text:
            text = text.replace('"entities":', '"entities": [')
            if not ']' in text.split('"entities": [')[1]:
                # Add closing bracket before the final }
                text = text[:-1] + ']}'
                
        return text

    
    async def extract_job_posting_information_for_form(self, job_posting_text):
        """Extract job posting information to pre-fill the role form using Pydantic"""
        logger.info("Extracting job posting information")
        
        try:
            # Define prompt for job posting extraction
            prompt = """Extract key information from the job posting text below. Return ONLY a JSON object with these fields:
            - job_title: The title of the job position
            - degree_requirement: One of ["Any", "Bachelor's", "Master's", "PhD"]
            - field_of_study: Required field of study (e.g., "Computer Science, Engineering")
            - experience_years: Required years of experience as an integer
            - required_skills: List key skills in format "Skill1:importance:required,Skill2:importance:required"
              where importance is 1-10 and required is true/false
            - location_remote: Job location or remote policy
            - industry_sector: Industry the role belongs to
            - role_level: Seniority level (e.g., "Junior", "Senior", "Manager")
    
            Job posting:
            {job_posting}
    
            Return ONLY valid JSON:
            """
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt.format(job_posting=job_posting_text)}],
                temperature=0.1,
                max_tokens=1024
            )
            
            result_text = response.choices[0].message.content
            
            # Extract JSON content from response
            json_match = re.search(r'(\{.*\})', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                extracted_dict = json.loads(json_str)
                
                # Create and return JobPostingData object
                job_data = JobPostingData(
                    job_title=extracted_dict.get('job_title', ''),
                    degree_requirement=extracted_dict.get('degree_requirement', 'Any'),
                    field_of_study=extracted_dict.get('field_of_study', ''),
                    experience_years=extracted_dict.get('experience_years', 0),
                    required_skills=extracted_dict.get('required_skills', ''),
                    location_remote=extracted_dict.get('location_remote', ''),
                    industry_sector=extracted_dict.get('industry_sector', ''),
                    role_level=extracted_dict.get('role_level', '')
                )
                return job_data
            else:
                logger.error("Failed to extract JSON from response")
                return JobPostingData()  # Return empty object
                
        except Exception as e:
            logger.error(f"Error extracting job posting information: {e}")
            return JobPostingData()  # Return empty object on error
        
    # Add this method to the DataExtractionService class

        # Update the extract_cv_data method
    
    async def extract_cv_data(self, cv_text, cv_filename=None):
        """
        Extract structured data from a CV using Pydantic models for validation
        
        Args:
            cv_text: The text content of the CV
            cv_filename: The filename of the CV
            
        Returns:
            CVData: Structured CV data
        """
        logger.info(f"Extracting data from CV: {cv_filename}")
        
        try:
            # Extract all entities with proper model validation
            person_data = await self.extract_entities(
                self.candidate_prompt_tpl,  # Updated from self.person_prompt_tpl
                cv_text,
                None, 
                PersonResponse
            )
            
            experience_data = await self.extract_entities(
                self.experience_prompt_tpl,  # This is what you defined
                cv_text, 
                None, 
                PositionResponse
            )

            
            
            
            skill_data = await self.extract_entities(
                self.skills_prompt_tpl,  # This is what you defined
                cv_text, 
                None, 
                SkillResponse
            )
            
           
            
            return cv_data
            
        except Exception as e:
            logger.error(f"Error extracting CV data: {e}")
            return CVData(cv_file_addess=cv_filename or "") 