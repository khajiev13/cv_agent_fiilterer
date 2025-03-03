from typing import List, Optional, Union
from pydantic import BaseModel

class PersonEntity(BaseModel):
    label: str = "Person"
    id: str
    role: str = ""
    description: str = ""
    cv_file_name: str = ""

class PositionEntity(BaseModel):
    label: str = "Position"
    id: str
    title: str = ""
    location: str = ""
    startDate: str = ""
    endDate: str = ""
    years_experience: int = 0
    url: str = ""

class CompanyEntity(BaseModel):
    label: str = "Company"
    id: str
    name: str = ""

class SkillEntity(BaseModel):
    label: str = "Skill"
    id: str
    name: str = ""
    level: str = ""
    years_experience: int = 0
    last_used: str = ""

class EducationEntity(BaseModel):
    label: str = "Education"
    id: str
    degree: str = ""
    university: str = ""
    graduationDate: str = ""
    score: str = ""
    url: str = ""
    field_of_study: str = ""

class ProjectEntity(BaseModel):
    label: str = "Project"
    id: str
    name: str = ""
    description: str = ""
    technologies: str = ""
    start_date: str = ""
    end_date: str = ""
    outcomes: str = ""
    url: str = ""

class PersonResponse(BaseModel):
    entities: List[PersonEntity]

class PositionResponse(BaseModel):
    entities: List[Union[PositionEntity, CompanyEntity]]
    relationships: List[str] = []

class EducationResponse(BaseModel):
    entities: List[EducationEntity]

class SkillResponse(BaseModel):
    entities: List[SkillEntity]

class ProjectResponse(BaseModel):
    entities: List[ProjectEntity]

class CVExtraction(BaseModel):
    """Complete CV extraction containing all entity types"""
    person: Optional[PersonResponse] = None
    positions: Optional[PositionResponse] = None
    education: Optional[EducationResponse] = None
    skills: Optional[SkillResponse] = None
    projects: Optional[ProjectResponse] = None