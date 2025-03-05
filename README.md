# Resume Search Assistant

A RAG (Retrieval-Augmented Generation) application for searching through candidate resumes using natural language queries.

## Features

- 💬 Conversational interface to search for candidates
- 📄 View candidate resumes directly in the application
- 🔍 Find candidates by skills, experience, education, and more
- 🧠 Powered by LLMs and Neo4j graph database

## Getting Started

1. Make sure your environment variables are set up in the `.env` file:

```
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

2. Run the application:

```bash
streamlit run app.py
```

3. Access the application at `http://localhost:8501`

## Application Modes

- **Simple Mode**: Clean, user-friendly interface focused on searching
- **Advanced Mode**: Includes debugging tools and direct database querying

To access advanced mode, use the URL parameter: `http://localhost:8501/?mode=advanced`

## Folder Structure

```
resume_agent/
├── app/
│   ├── services/
│   │   └── rag_service.py     # RAG implementation using LangChain
│   └── st_components/
│       └── simple_rag_interface.py  # Streamlit UI components
├── data/
│   └── cvs/                   # Resume documents (PDF, DOCX, TXT)
├── app.py                     # Main Streamlit application
├── .env                       # Environment variables
└── README.md                  # Documentation
```

## Development

The application uses the following technologies:

- **Streamlit** for the web interface
- **LangChain** for RAG pipeline implementation
- **Neo4j** for storing and querying the knowledge graph
- **Azure OpenAI** for language model capabilities
