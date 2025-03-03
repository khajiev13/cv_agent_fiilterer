from string import Template
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field, validator
from app.pyd_models.models import PersonResponse,PositionResponse,  EducationResponse, SkillResponse,ProjectResponse
from typing import Optional, List
import logging
import openai
import asyncio
import os
import json
import re



# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add this after the JobPostingData class

class CVData(BaseModel):
    person_name: str = Field(default="")
    current_role: str = Field(default="")
    years_experience: int = Field(default=0)
    summary: str = Field(default="")
    skills: List[dict] = Field(default_factory=list)  # List of {name, level, years_experience, last_used}
    positions: List[dict] = Field(default_factory=list)  # List of position details
    education: List[dict] = Field(default_factory=list)  # List of education details
    projects: List[dict] = Field(default_factory=list)  # List of project details
    
    @validator('years_experience')
    def validate_experience(cls, v):
        return max(0, v)  # Ensure non-negative


class JobPostingData(BaseModel):
    job_title: str = Field(default="")
    degree_requirement: str = Field(default="Any")
    field_of_study: str = Field(default="")
    experience_years: int = Field(default=0)
    required_skills: str = Field(default="")
    location_remote: str = Field(default="")
    industry_sector: str = Field(default="")
    role_level: str = Field(default="")
    
    @validator('degree_requirement')
    def validate_degree(cls, v):
        valid_degrees = ["Any", "Bachelor's", "Master's", "PhD"]
        return v if v in valid_degrees else "Any"
    
    @validator('experience_years')
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
        self.person_prompt_tpl = """From the Resume text for a job aspirant below, extract Entities strictly as instructed below
1. First, look for the Person Entity type in the text and extract the needed information defined below:
   `id` property of each entity must be alphanumeric and must be unique among the entities. You will be referring this property to define the relationship between entities. NEVER create new entity types that aren't mentioned below. Document must be summarized and stored inside Person entity under `description` property
    Entity Types:
    label:'Person',id:string,role:string,description:string,cv_file_name:string //Person Node
2. Description property should be a crisp text summary and MUST NOT be more than 100 characters
3. If you cannot find any information on the entities & relationships above, it is okay to return empty value. DO NOT create fictitious data
4. Do NOT create duplicate entities
5. Restrict yourself to extract only Person information. No Position, Company, Education or Skill information should be focused.
6. NEVER Impute missing values
7. Set the cv_file_name property to "$cv_filename"
Example Output JSON:
{"entities": [{"label":"Person","id":"person1","role":"Prompt Developer","description":"Prompt Developer with more than 30 years of LLM experience","cv_file_name":"example_cv.pdf"}]}

Question: Now, extract the Person for the text below -
$ctext

Answer:
"""

        self.position_prompt_tpl = """From the Resume text for a job aspirant below, extract Entities & relationships strictly as instructed below
1. First, look for Position & Company types in the text and extract information in comma-separated format. Position Entity denotes the Person's previous or current job. Company node is the Company where they held that position.
   `id` property of each entity must be alphanumeric and must be unique among the entities. You will be referring this property to define the relationship between entities. NEVER create new entity types that aren't mentioned below. You will have to generate as many entities as needed as per the types below:
    Entity Types:
    label:'Position',id:string,title:string,location:string,startDate:string,endDate:string,url:string,years_of_experience:integer //Position Node
    label:'Company',id:string,name:string //Company Node
2. Next generate each relationships as triples of head, relationship and tail. To refer the head and tail entity, use their respective `id` property. NEVER create new Relationship types that aren't mentioned below:
    Relationship definition:
    position|AT_COMPANY|company //Ensure this is a string in the generated output
3. If you cannot find any information on the entities & relationships above, it is okay to return empty value. DO NOT create fictitious data
4. Do NOT create duplicate entities. 
5. No Education or Skill information should be extracted.
6. DO NOT MISS out any Position or Company related information
7. NEVER Impute missing values
8. Calculate years_of_experience for each position based on startDate and endDate
 Example Output JSON:
{"entities": [{"label":"Position","id":"position1","title":"Software Engineer","location":"Singapore","startDate":"2021-01-01","endDate":"present","years_of_experience":3},{"label":"Position","id":"position2","title":"Senior Software Engineer","location":"Mars","startDate":"2020-01-01","endDate":"2020-12-31","years_of_experience":1},{"label":"Company","id":"company1","name":"Neo4j Singapore Pte Ltd"},{"label":"Company","id":"company2","name":"Neo4j Mars Inc"}],"relationships": ["position1|AT_COMPANY|company1","position2|AT_COMPANY|company2"]}

Question: Now, extract entities & relationships as mentioned above for the text below -
$ctext

Answer:
"""

        self.skill_prompt_tpl = """From the Resume text below, extract Entities strictly as instructed below
1. Look for prominent Skill Entities in the text. The`id` property of each entity must be alphanumeric and must be unique among the entities. NEVER create new entity types that aren't mentioned below:
    Entity Definition:
    label:'Skill',id:string,name:string,level:string,years_experience:integer,last_used:string //Skill Node
2. NEVER Impute missing values
3. If you do not find any level information: assume it as `expert` if the experience in that skill is more than 5 years, `intermediate` for 2-5 years and `beginner` otherwise.
4. Focus especially on technical skills, programming languages, tools, frameworks, and domain knowledge
5. Try to extract the number of years of experience with each skill and when it was last used
Example Output Format:
{"entities": [{"label":"Skill","id":"skill1","name":"Neo4j","level":"expert","years_experience":6,"last_used":"2023"},{"label":"Skill","id":"skill2","name":"Pytorch","level":"intermediate","years_experience":3,"last_used":"2022"}]}

Question: Now, extract entities as mentioned above for the text below -
$ctext

Answer:
"""

        self.edu_prompt_tpl = """From the Resume text for a job aspirant below, extract Entities strictly as instructed below
1. Look for Education entity type and generate the information defined below:
   `id` property of each entity must be alphanumeric and must be unique among the entities. You will be referring this property to define the relationship between entities. NEVER create other entity types that aren't mentioned below. You will have to generate as many entities as needed as per the types below:
    Entity Definition:
    label:'Education',id:string,degree:string,university:string,graduationDate:string,score:string,url:string,field_of_study:string //Education Node
2. If you cannot find any information on the entities above, it is okay to return empty value. DO NOT create fictitious data
3. Do NOT create duplicate entities or properties
4. Strictly extract only Education. No Skill or other Entities should be extracted
5. DO NOT MISS out any Education related entity
6. NEVER Impute missing values
7. Make sure to extract the field_of_study separately from the degree when possible
Output JSON (Strict):
{"entities": [{"label":"Education","id":"education1","degree":"Bachelor of Science","graduationDate":"May 2022","score":"0.0","field_of_study":"Computer Science"}]}

Question: Now, extract Education information as mentioned above for the text below -
$ctext

Answer:

"""
        self.project_prompt_tpl = """From the Resume text for a job aspirant, extract Project information:
    Entity Definition:
    label:'Project',id:string,name:string,description:string,technologies:string,start_date:string,end_date:string,outcomes:string,url:string //Project Node

1. Look for significant projects mentioned in the resume
2. Extract measurable outcomes where available
3. List technologies used as comma-separated values
4. Create relationships between projects and skills

Output Format:
{"entities": [{"label":"Project","id":"project1","name":"Database Migration","description":"Migrated legacy database to cloud","technologies":"PostgreSQL,AWS,Python","outcomes":"Reduced costs by 30%, improved query speed by 50%"}]}

Question: Now, extract Project information from the text below -
$ctext

Answer:
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
            # Replace $cv_filename placeholder if present in the prompt
            if cv_filename and '$cv_filename' in prompt:
                prompt = prompt.replace('$cv_filename', cv_filename)
                
            # Prepare the prompt with CV text
            _prompt = Template(prompt).substitute(ctext=self.clean_text(cv_text))
            
            # Add JSON instruction if using response_format
            messages_content = _prompt
            if response_model:
                if "json" not in _prompt.lower():
                    messages_content = _prompt + "\n\nProvide the answer in JSON format."
            
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
                self.person_prompt_tpl, 
                cv_text, 
                cv_filename, 
                PersonResponse
            )
            
            position_data = await self.extract_entities(
                self.position_prompt_tpl, 
                cv_text, 
                None, 
                PositionResponse
            )
            
            education_data = await self.extract_entities(
                self.edu_prompt_tpl, 
                cv_text, 
                None, 
                EducationResponse
            )
            
            skill_data = await self.extract_entities(
                self.skill_prompt_tpl, 
                cv_text, 
                None, 
                SkillResponse
            )
            
            project_data = await self.extract_entities(
                self.project_prompt_tpl, 
                cv_text, 
                None, 
                ProjectResponse
            )
            
            # Process person data
            person_name = ""
            current_role = ""
            summary = ""
            
            if hasattr(person_data, 'entities') and person_data.entities:
                person_entity = person_data.entities[0]
                person_name = person_entity.id.replace("person", "").strip()
                current_role = person_entity.role
                summary = person_entity.description
            
            # Process position data to calculate total experience
            positions = []
            total_years = 0
            
            if hasattr(position_data, 'entities'):
                for entity in position_data.entities:
                    if hasattr(entity, 'label') and entity.label == 'Position':
                        years = entity.years_experience
                        total_years += years
                        
                        positions.append({
                            'title': entity.title,
                            'location': entity.location,
                            'start_date': entity.startDate,
                            'end_date': entity.endDate,
                            'years_experience': years
                        })
            
            # Process skills
            skills = []
            if hasattr(skill_data, 'entities'):
                for entity in skill_data.entities:
                    skills.append({
                        'name': entity.name,
                        'level': entity.level,
                        'years_experience': entity.years_experience,
                        'last_used': entity.last_used
                    })
            
            # Process education
            education = []
            if hasattr(education_data, 'entities'):
                for entity in education_data.entities:
                    education.append({
                        'degree': entity.degree,
                        'university': entity.university,
                        'graduation_date': entity.graduationDate,
                        'field_of_study': entity.field_of_study
                    })
            
            # Process projects
            projects = []
            if hasattr(project_data, 'entities'):
                for entity in project_data.entities:
                    projects.append({
                        'name': entity.name,
                        'description': entity.description,
                        'technologies': entity.technologies.split(',') if entity.technologies else [],
                        'outcomes': entity.outcomes
                    })
            
            # Create and return CVData object
            cv_data = CVData(
                person_name=person_name,
                current_role=current_role,
                years_experience=int(total_years),
                summary=summary,
                skills=skills,
                positions=positions,
                education=education,
                projects=projects
            )
            
            return cv_data
            
        except Exception as e:
            logger.error(f"Error extracting CV data: {e}")
            return CVData()  # Return empty object on error