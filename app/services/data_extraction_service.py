import os
import json
import re
from string import Template
from pathlib import Path
import asyncio
from dotenv import load_dotenv
import openai
from openai import AsyncAzureOpenAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    label:'Skill',id:string,name:string,level:string //Skill Node
2. NEVER Impute missing values
3. If you do not find any level information: assume it as `expert` if the experience in that skill is more than 5 years, `intermediate` for 2-5 years and `beginner` otherwise.
4. Focus especially on technical skills, programming languages, tools, frameworks, and domain knowledge
Example Output Format:
{"entities": [{"label":"Skill","id":"skill1","name":"Neo4j","level":"expert"},{"label":"Skill","id":"skill2","name":"Pytorch","level":"expert"}]}

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

    def clean_text(self, text):
        """Clean text to remove non-ASCII characters"""
        return re.sub(r'[^\x00-\x7F]+', ' ', text)

    async def extract_entities(self, prompt, cv_text, cv_filename=None):
        """Extract entities from CV text using Azure OpenAI"""
        try:
            # Replace $cv_filename placeholder if present in the prompt
            if cv_filename and '$cv_filename' in prompt:
                prompt = prompt.replace('$cv_filename', cv_filename)
                
            # Prepare the prompt with CV text
            _prompt = Template(prompt).substitute(ctext=self.clean_text(cv_text))
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": _prompt}],
                temperature=0,
                max_tokens=1024,
                top_p=0.8
            )
            
            # Extract and parse result
            result_text = response.choices[0].message.content
            if 'Answer:' in result_text:
                result_text = result_text.split('Answer:')[1].strip()
                
            # Parse JSON from result
            try:
                extraction = json.loads(result_text.replace("'", '"').replace('`', ''))
                return extraction
            except json.JSONDecodeError as e:
                # Handle incomplete JSON responses
                logger.error(f"JSON parse error: {e}")
                # Attempt to recover from common JSON issues
                # Find the last complete object and add closing brackets
                result_text = result_text[:result_text.rfind("}")+1] + ']}'
                try:
                    return json.loads(result_text.replace("'", '"'))
                except:
                    logger.error(f"Failed to recover malformed JSON: {result_text}")
                    return {"entities": []}
                
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {"entities": []}

    async def extract_all_entities(self, cv_text, cv_filename):
        """Extract all entity types from a CV"""
        results = {"entities": [], "relationships": []}
        
        # Extract Person entities
        person_result = await self.extract_entities(self.person_prompt_tpl, cv_text, cv_filename)
        if person_result and "entities" in person_result:
            results["entities"].extend(person_result["entities"])
            
            # If we found a person, extract other entities
            if person_result["entities"]:
                # Get the person ID for relationship creation
                person_id = person_result["entities"][0]["id"]
                
                # Extract Position and Company entities 
                position_result = await self.extract_entities(self.position_prompt_tpl, cv_text)
                if position_result:
                    if "entities" in position_result:
                        results["entities"].extend(position_result["entities"])
                    if "relationships" in position_result:
                        results["relationships"].extend(position_result["relationships"])
                        # Add relationships from Person to each Position
                        for entity in position_result.get("entities", []):
                            if entity.get("label") == "Position":
                                results["relationships"].append(f"{person_id}|HAS_POSITION|{entity['id']}")
                
                # Extract Skills
                skill_result = await self.extract_entities(self.skill_prompt_tpl, cv_text)
                if skill_result and "entities" in skill_result:
                    results["entities"].extend(skill_result["entities"])
                    # Add relationships from Person to each Skill
                    for entity in skill_result.get("entities", []):
                        if entity.get("label") == "Skill":
                            results["relationships"].append(f"{person_id}|HAS_SKILL|{entity['id']}")
                
                # Extract Education
                edu_result = await self.extract_entities(self.edu_prompt_tpl, cv_text)
                if edu_result and "entities" in edu_result:
                    results["entities"].extend(edu_result["entities"])
                    # Add relationships from Person to each Education
                    for entity in edu_result.get("entities", []):
                        if entity.get("label") == "Education":
                            results["relationships"].append(f"{person_id}|HAS_EDUCATION|{entity['id']}")
        
        return results

    async def process_cv(self, cv_text, cv_filename):
        """Process a CV and extract all entities and relationships"""
        logger.info(f"Processing CV: {cv_filename}")
        return await self.extract_all_entities(cv_text, cv_filename)
