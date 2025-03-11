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




class JobPostingData(BaseModel):
    job_title: str = ""
    alternative_titles: Optional[str] = None
    degree_requirement: str = "Any"
    field_of_study: str = ""
    experience_years: int = 0
    required_skills: str = ""
    alternative_skills:Optional[str] = None
    location_remote: str = ""
    industry_sector: str = ""
    role_level: str = ""
    
    @validator('degree_requirement')
    def validate_degree(cls, v):
        valid_degrees = ["any", "bachelor", "master", "phd"]
        return v if v in valid_degrees else "Any"
    
    @validator('experience_years')
    def validate_experience(cls, v):
        return max(0, v)  # Ensure non-negative


