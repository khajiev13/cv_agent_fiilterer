from typing import Literal
from pydantic import BaseModel, Field, validator
from typing import List, Optional




class PersonEntity(BaseModel):
    label: str = "Person"
    id: Optional[str]
    name: Optional[str]
    job_title: str = ""
    description: str = ""
    last_field_of_study: str = ""
    last_degree: Literal["bachelor", "master", "phd", "any"] = Field(default="any")


class PersonEntityWithMetadata(PersonEntity):
    cv_file_address: str = ""
    cv_text: str = ""

    
class HasExperienceRelationship(BaseModel):
    company_name: str = ""
    experience_in_years: int = 0
    description: str = ""
    @validator('experience_in_years')
    def check_experience_in_years(cls, v):
        if v < 0:
            raise ValueError('experience_in_years cannot be negative')
        return v
    

class ExperienceEntity(HasExperienceRelationship):
    job_title: str = ""
    alternative_job_titles: Optional[str] = None


class ResponseExperiences(BaseModel):
    experience: List[ExperienceEntity] = []

class HasSkillRelationship(BaseModel):
    level: Literal["beginner","intermediate","expert"] = Field(default="beginner")
    years_experience: int = Field(default=0, ge=0)
    
    @validator('years_experience')
    def check_years_experience(cls, v):
        if v < 0:
            raise ValueError('years_experience cannot be negative')
        return v

class SkillEntity(HasSkillRelationship):
    name: str = ""
    alternative_names: Optional[str] = None


class ResponseSkills(BaseModel):
    skills: List[SkillEntity] = []


class SkillRequirement(BaseModel):
    name: str
    importance: Literal["required", "preferred", "nice-to-have"] = "required"
    alternative_names: str = ""  # Comma-separated alternatives
    minimum_years: int = 0
    
    @validator('minimum_years')
    def check_minimum_years(cls, v):
        return max(0, v)  # Ensure non-negative

class FieldOfStudy(BaseModel):
    name: str
    alternative_fields: str = ""  # Comma-separated alternatives
    importance: Literal["required", "preferred", "nice-to-have"] = "required"

class JobPostingData(BaseModel):
    job_title: str = ""
    alternative_titles: str = ""  # Store as comma-separated values
    
    # Education requirements
    degree_requirement: str = "any"
    fields_of_study: List[FieldOfStudy] = []
    
    # Experience
    total_experience_years: int = 0
    
    # Skills - now more structured
    required_skills: List[SkillRequirement] = []
    
    # Location and other info
    location: str = ""
    remote_option: bool = False
    industry_sector: str = ""
    role_level: str = ""
    keywords: str = ""  # Additional keywords for matching
    
    @validator('degree_requirement')
    def validate_degree(cls, v):
        valid_degrees = ["any", "bachelor", "master", "phd"]
        return v.lower() if v.lower() in valid_degrees else "any"
    
    @validator('total_experience_years')
    def validate_experience(cls, v):
        return max(0, v)  # Ensure non-negative

