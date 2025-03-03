import streamlit as st
import os
import base64
import time
from app.services.rag_service import RAGCandidateService

def get_cv_file_path(cv_filename):
    """Get the full path to a CV file in the data/cvs directory"""
    cv_dir = os.path.join("data", "cvs")
    return os.path.join(cv_dir, cv_filename)

def display_pdf(file_path):
    """Display a PDF file in Streamlit"""
    # Opening file and encoding
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # Embedding PDF in HTML
    pdf_display = f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>
    """
    
    # Displaying the PDF
    st.markdown(pdf_display, unsafe_allow_html=True)

def show_rag_interface(neo4j_service=None):
    """
    Display the RAG interface for candidate search
    
    Args:
        neo4j_service: Neo4jService instance (optional)
    """
    st.header("🔍 AI Candidate Search", divider="rainbow")
    
    # Initialize or get the RAG service from session state
    if 'rag_service' not in st.session_state:
        # If neo4j_service is provided, use its credentials
        if neo4j_service:
            uri = neo4j_service.uri
            username = neo4j_service.username
            password = neo4j_service.password
        else:
            # Try to get from session state
            if 'neo4j_service' in st.session_state:
                uri = st.session_state.neo4j_service.uri
                username = st.session_state.neo4j_service.username
                password = st.session_state.neo4j_service.password
            else:
                st.error("Database connection is required. Please connect to Neo4j first.")
                return
                
        # Get OpenAI API key from environment or prompt user
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            openai_api_key = st.text_input(
                "Enter your OpenAI API key:", 
                type="password",
                help="Your key will be used only for this session and not stored."
            )
            if not openai_api_key:
                st.info("Please enter your OpenAI API key to proceed.")
                return
        
        # Initialize the RAG service
        st.session_state.rag_service = RAGCandidateService(
            neo4j_uri=uri,
            neo4j_username=username,
            neo4j_password=password,
            openai_api_key=openai_api_key
        )
        
    # Query input interface
    st.markdown("""
    ### Ask about candidates
    Ask questions about candidate skills, experience, or qualifications. For example:
    - "List the most experienced and skilled candidates in Smart TV"
    - "Find candidates with management experience in tech companies"
    - "Show me candidates with Python and SQL skills"
    """)
    
    query = st.text_input("Enter your question:", key="rag_query")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        search_button = st.button("🔍 Search", use_container_width=True)
    with col2:
        example_query = st.selectbox(
            "Or try an example query:",
            [
                "",
                "List the most experienced and skilled candidates in Smart TV",
                "Find candidates with at least 3 years of Python experience",
                "Show me candidates with management experience",
                "Find candidates with a Master's degree in Computer Science"
            ]
        )
    
    # Use either the manual query or the example
    if example_query and not query:
        query = example_query
    
    # Process query when button is clicked
    if search_button and query:
        with st.spinner("Searching for candidates..."):
            # Query candidates using the RAG service
            candidates = st.session_state.rag_service.query_candidates(query)
            
        if candidates:
            st.success(f"Found {len(candidates)} matching candidates")
            
            # Display results in a table
            for i, candidate in enumerate(candidates):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"### {candidate['name']}")
                        st.caption(f"{candidate.get('role', 'Professional')}")
                    
                    with col2:
                        st.markdown(f"**Experience:** {candidate.get('years_experience', 'N/A')} years")
                    
                    with col3:
                        # Create a button with the CV filename
                        if st.button(f"View CV", key=f"view_{i}"):
                            # Store in session state which CV to view
                            st.session_state.view_cv = candidate['cv_file_name']
                            st.rerun()
                            
                    # Additional details section
                    st.caption(f"CV Filename: {candidate['cv_file_name']}")
                    st.markdown("---")
        else:
            st.info("No matching candidates found. Try a different query.")
    
    # Display selected CV if any
    if 'view_cv' in st.session_state and st.session_state.view_cv:
        st.markdown("---")
        st.header(f"Viewing: {st.session_state.view_cv}")
        
        # Get the CV file path
        cv_path = get_cv_file_path(st.session_state.view_cv)
        
        # Check if file exists
        if os.path.exists(cv_path):
            # If it's a PDF, display it
            if cv_path.lower().endswith('.pdf'):
                display_pdf(cv_path)
            else:
                # For non-PDF files, just provide download link
                with open(cv_path, "rb") as file:
                    st.download_button(
                        label="Download CV",
                        data=file,
                        file_name=st.session_state.view_cv,
                        mime="application/octet-stream"
                    )
        else:
            st.error(f"CV file not found: {cv_path}")
        
        # Add button to go back to search results
        if st.button("← Back to search results"):
            st.session_state.view_cv = None
            st.rerun()
