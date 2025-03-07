from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, validator





class PersonEntity(BaseModel):
    label: str = "Person"
    id: str
    name: str
    job_title: str = ""
    description: str = ""
    cv_file_address: str = ""
    cv_text: str = ""
    last_field_of_study: str = ""
    last_degree: Literal["bachelor", "master", "phd", "any"] = Field(default="any")

    
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





# class EducationEntity(BaseModel):
#     label: str = "Education"
#     id: str
#     institution: str = ""
#     degree: str = ""
#     field: str = ""
#     start_date: str = ""
#     end_date: str = ""

class JobPostingEntity(BaseModel):
    label: str = "JobPosting"
    id: str
    title: str = ""
    description: str = ""
    posting_text: str = ""
