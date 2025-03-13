# What is a Hybrid Approach in Neo4j?

A hybrid approach in Neo4j means integrating:

- **Graph-based queries**: Use nodes and relationships to filter candidates based on structured data (e.g., specific skills or experience).
- **Vector embeddings**: Convert unstructured text (e.g., CVs and job descriptions) into numerical vectors to perform similarity searches, capturing deeper semantic matches.

This combination allows you to filter candidates who meet basic job requirements using the graph, then rank them based on how well their profiles align with the job using embeddings.

## Step 1: Model the Graph for Structured Data

First, design the Neo4j graph to represent the key entities and their relationships:

### Nodes
- **Candidate**: Represents a job candidate. Properties: name, job title, description, cv_text. cv_embedding, last_field_of_study,cv_file_address
- **JobPosting**: Represents a job listing. Properties: title, description, posting_text, posting_embedding.
- **Skill**: Represents a specific skill (e.g., "python," "project management").
- **Experience**: Represents a candidate's work experience . Properties: job_title
- **Keyword**: Represents keywords related to the job posting or candidate CV. 



### Relationships
- **Candidate -[:HAS_SKILL]-> Skill**: Connects a candidate to their skills. (e.g., "5")
- **JobPosting -[:REQUIRES_SKILL]-> Skill**: Connects a job to its required skills.
- **Candidate -[:HAS_EXPERIENCE]-> Experience**: Links a candidate to their experience.Properties: experience_in_years,company_name
- **JobPosting -[:REQUIRES_EXPERIENCE]-> ExperienceLevel**: Specifies the experience level a job requires. Properties: experience_in_years (e.g., "5").
- **JobPosting -[:HAS_KEYWORD]-> Keywords**: Connects a job to its keywords. Properties: keyword (e.g., "python")
- **Candidate -[:HAS_KEYWORD]-> Keyword**: Connects a candidate to their keywords. Properties: keyword (e.g., "python")

### Purpose
These nodes and relationships allow you to filter candidates who meet the job's hard requirements using graph queries. For example, you can find candidates with specific skills or experience levels.

## Step 2: Identify Entities to Embed

Vector embeddings are best suited for unstructured text where semantic meaning needs to be captured. Based on the use case of matching candidates to jobs, the following entities should be embedded:

### 1. Entire CV Text (for Candidate Nodes)
- **What**: The full text of a candidate's CV, including work experience, education, skills, and other details.
- **Why**: Embedding the entire CV captures the overall profile of the candidate, allowing you to match it against a job posting holistically.

### 2. Entire Job Posting Text (for JobPosting Nodes)
- **What**: The full text of a job posting, including the job description and requirements.
- **Why**: Embedding the entire job posting captures its complete semantic context, enabling comparison with a candidate's CV.

### 3. Skill Names or Descriptions (for Skill Nodes, Optional)
- **What**: The name of each skill (e.g., "Python") or a short description if available.
- **Why**: Embedding skills allows you to capture similarities between them (e.g., "Python" and "R" as data science skills), expanding the candidate pool to include those with related skills.

### Why Not Embed Relationships?
Relationships in Neo4j (e.g., HAS_SKILL) are structural and don't contain text suitable for embedding. Instead, embeddings are stored as properties on nodes, and relationships are used in graph queries to filter or connect entities.

## Step 3: Generate and Store Vector Embeddings

Here's how to create and integrate embeddings into Neo4j:

### How to Generate Embeddings
1. Use a pre-trained text embedding model, such as:
    - **SentenceTransformers**: Open-source library (e.g., all-MiniLM-L6-v2 model).
    - **OpenAI Embeddings API**: For high-quality embeddings.
2. Input the text (e.g., CV or job posting) into the model to get a vector (a list of floats, typically 768 or 1024 dimensions).
3. Ensure consistency by using the same model for all embeddings (CVs, job postings, and skills) so they are comparable.

### How to Store Embeddings in Neo4j
Store the vectors as properties on the respective nodes:
- For **Candidate**: Add a property like `cv_embedding` (e.g., [0.12, -0.45, ...]).
- For **JobPosting**: Add a property like `description_embedding`.
- For **Skill** (optional): Add a property like `embedding`.

Neo4j supports vectors as lists of floats, which can be indexed for efficient similarity searches.

## Step 4: Implement the Hybrid Matching Approach

The hybrid approach involves two phases: filtering with the graph and ranking with embeddings.

### Phase 1: Filter Candidates Using Graph Queries
Use Cypher to find candidates who meet the job's hard requirements. For example:

```cypher
MATCH (j:JobPosting)-[:REQUIRES_SKILL]->(s:Skill)<-[:HAS_SKILL]-(c:Candidate)
WHERE j.id = 'job123'
RETURN c
```

This query retrieves candidates who have at least one skill required by the job posting with ID job123.

### Phase 2: Rank Candidates Using Vector Similarity
Among the filtered candidates, compute the similarity between their `cv_embedding` and the job's `description_embedding`. Use Neo4j's similarity functions (e.g., cosine similarity) or vector indexes.

Example Cypher query:

```cypher
MATCH (j:JobPosting {id: 'job123'})
MATCH (c:Candidate)
WHERE (c)-[:HAS_SKILL]->(:Skill)<-[:REQUIRES_SKILL]-(j)
WITH c, j, gds.similarity.cosine(c.cv_embedding, j.description_embedding) AS similarity
RETURN c, similarity
ORDER BY similarity DESC
LIMIT 10
```

This ranks the filtered candidates by how similar their CVs are to the job posting, returning the top 10.

### Optimize with Vector Indexes
For large datasets, create a vector index on the `cv_embedding` property to speed up similarity searches (available in Neo4j 5.11+):

```cypher
CREATE VECTOR INDEX candidate_embeddings FOR (c:Candidate) ON (c.cv_embedding)
```

Then, use the index to find similar candidates:

```cypher
MATCH (j:JobPosting {id: 'job123'})
CALL db.index.vector.queryNodes('candidate_embeddings', 10, j.description_embedding)
YIELD node AS c, score AS similarity
WHERE (c)-[:HAS_SKILL]->(:Skill)<-[:REQUIRES_SKILL]-(j)
RETURN c, similarity
ORDER BY similarity DESC
```

### Optional: Enhance with Skill Embeddings
To include candidates with similar skills:

```cypher
MATCH (j:JobPosting)-[:REQUIRES_SKILL]->(req_skill:Skill)
MATCH (similar_skill:Skill)
WHERE gds.similarity.cosine(req_skill.embedding, similar_skill.embedding) > 0.8
MATCH (c:Candidate)-[:HAS_SKILL]->(similar_skill)
RETURN c
```

This finds candidates with skills similar to those required (e.g., similarity > 0.8), broadening the match criteria.

## Summary of Entities and Relationships to Embed

**Entities to Embed**:
- CV text → Stored as `cv_embedding` on Candidate nodes.
- Job posting text → Stored as `description_embedding` on JobPosting nodes.
- Skill names/descriptions (optional) → Stored as `embedding` on Skill nodes.

**Relationships**: Not embedded, but used in graph queries to filter candidates (e.g., HAS_SKILL, REQUIRES_SKILL).

## How It Works Together
1. **Filter**: Use graph relationships to narrow down candidates who meet must-have requirements (e.g., specific skills).
2. **Rank**: Use vector embeddings to rank these candidates based on semantic similarity between their CVs and the job posting.
3. **Enhance** (Optional): Use skill embeddings to include candidates with related skills, improving flexibility.

This hybrid approach leverages Neo4j's strengths in structured data querying and vector-based similarity searches, resulting in more accurate and efficient candidate-to-job matching.
