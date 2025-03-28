Schema: 1 [(:Candidate {name: "Candidate", indexes: ["name"], constraints: []}), (:Experience {name: "Experience", indexes: ["name"], constraints: []}), (:Skill {name: "Skill", indexes: ["name"], constraints: []}), (:JobPosting {name: "JobPosting", indexes: ["job_title"], constraints: []}), (:Keyword {name: "Keyword", indexes: [], constraints: []}), (:FieldOfStudy {name: "FieldOfStudy", indexes: [], constraints: []}), (:LocationCity {name: "LocationCity", indexes: [], constraints: []})] [[:REQUIRES_FIELD_OF_STUDY {name: "REQUIRES_FIELD_OF_STUDY"}], [:HAS_EXPERIENCE {name: "HAS_EXPERIENCE"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:ALTERNATIVE_OF {name: "ALTERNATIVE_OF"}], [:AT {name: "AT"}], [:REQUIRES_SKILL {name: "REQUIRES_SKILL"}], [:FROM {name: "FROM"}], [:REQUIRES_EXPERIENCE {name: "REQUIRES_EXPERIENCE"}], [:HAS_KEYWORD {name: "HAS_KEYWORD"}], [:HAS_FIELD_OF_STUDY {name: "HAS_FIELD_OF_STUDY"}], [:HAS_SKILL {name: "HAS_SKILL"}]]

Candidate Relationships
Experiences: (:Candidate)-[:HAS_EXPERIENCE]->(:Experience)
Skills: (:Candidate)-[:HAS_SKILL]->(:Skill)
Education: (:Candidate)-[:HAS_FIELD_OF_STUDY]->(:FieldOfStudy)
LocationCity: (:Candidate)-[:FROM]->(:LocationCity)

Job Posting Relationships
Required Experience: (:JobPosting)-[:REQUIRES_EXPERIENCE]->(:Experience)
Required Skills: (:JobPosting)-[:REQUIRES_SKILL]->(:Skill)
Required Education: (:JobPosting)-[:REQUIRES_FIELD_OF_STUDY]->(:FieldOfStudy)
Location: (:JobPosting)-[:AT]->(:LocationCity)
Keywords: (:JobPosting)-[:HAS_KEYWORD]->(:Keyword)

Experience Relationships
Similar Experiences: (:Experience)-[:ALTERNATIVE_OF]-(:Experience)

Alternative Connections
Similar Skills: (:Skill)-[:ALTERNATIVE_OF]-(:Skill)
Related Fields: (:FieldOfStudy)-[:ALTERNATIVE_OF]-(:FieldOfStudy)
This schema allows matching candidates to jobs through direct comparisons and alternative connections, supporting flexible experience and skill matching algorithms.




Node properties:
nodeType,nodeLabels,propertyName,propertyTypes,mandatory
:`LocationCity`,[LocationCity],name,[String],true
:`FieldOfStudy`,[FieldOfStudy],name,[String],true
:`Experience`,[Experience],title,[String],true
:`Skill`,[Skill],name,[String],true
:`JobPosting`,[JobPosting],id,[String],true
:`JobPosting`,[JobPosting],job_title,[String],true
:`JobPosting`,[JobPosting],description,[String],true
:`JobPosting`,[JobPosting],created_at,[DateTime],true
:`JobPosting`,[JobPosting],title,[String],true
:`JobPosting`,[JobPosting],keywords,[String],true
:`JobPosting`,[JobPosting],industry_sector,[String],true
:`JobPosting`,[JobPosting],role_level,[String],true
:`JobPosting`,[JobPosting],total_experience_years,[Long],true
:`JobPosting`,[JobPosting],alternative_titles,[String],true
:`JobPosting`,[JobPosting],remote_option,[String],true
:`JobPosting`,[JobPosting],posting_text,[String],true
:`JobPosting`,[JobPosting],degree_requirement,[String],true
:`Keyword`,[Keyword],name,[String],true
:`Candidate`,[Candidate],id,[String],true
:`Candidate`,[Candidate],name,[String],true
:`Candidate`,[Candidate],job_title,[String],true
:`Candidate`,[Candidate],description,[String],true
:`Candidate`,[Candidate],cv_text,[String],true
:`Candidate`,[Candidate],cv_file_address,[String],true
:`Candidate`,[Candidate],created_at,[DateTime],true


Relationship properties:
relType,propertyName,propertyTypes,mandatory
:`FROM`,null,null,false
:`HAS_FIELD_OF_STUDY`,university,[String],true
:`HAS_FIELD_OF_STUDY`,graduation_year,[Long],true
:`HAS_FIELD_OF_STUDY`,degree,[String],true
:`HAS_EXPERIENCE`,description,[String],true
:`HAS_EXPERIENCE`,company,[String],true
:`HAS_EXPERIENCE`,years,[Long],true
:`HAS_SKILL`,years,[Long],true
:`HAS_SKILL`,level,[String],true
:`ALTERNATIVE_OF`,null,null,false
:`AT`,null,null,false
:`REQUIRES_FIELD_OF_STUDY`,importance,[String],true
:`REQUIRES_SKILL`,importance,[String],true
:`REQUIRES_SKILL`,is_required,[Boolean],true
:`REQUIRES_SKILL`,minimum_years,[Long],true
:`REQUIRES_EXPERIENCE`,years,[Long],true
:`HAS_KEYWORD`,null,null,false