import streamlit as st
import pandas as pd
import time
from services.neo4j_service import Neo4jService
import logging


# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def show_home(neo4j_service):

    st.title("Welcome to Resume Agent")
    
    # Main description
    st.markdown("""
    Resume Agent is a powerful tool for managing and analyzing CVs. It uses AI to extract structured data from resumes,
    allowing for efficient candidate matching to job roles based on skills, experience, and qualifications.
    """)
    
    # Feature cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### 📤 Upload CVs")
        st.write("Upload CV files in PDF or DOCX format for processing.")
        st.write("The system will extract key information and store it in a structured format.")
    
    with col2:
        st.info("### 🧩 Define Roles")
        st.write("Create job role definitions with specific requirements.")
        st.write("Specify required skills, education, experience and more.")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.success("### 🔍 Find Matches")
        st.write("Match candidates to roles based on their qualifications.")
        st.write("Score candidates automatically based on how well they meet the role requirements.")
    
    with col4:
        st.success("### 📊 View Analytics")
        st.write("Get insights into your candidate pool and skill availability.")
        st.write("Visualize data to make better hiring decisions.")
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Upload CVs", use_container_width=True):
            st.session_state.current_page = "Upload CVs"
            st.rerun()
    
    with col2:
        if st.button("📋 Manage CVs", use_container_width=True):
            st.session_state.current_page = "Manage CVs"
            st.rerun()
    
    with col3:
        if st.button("🧩 Manage Roles", use_container_width=True):
            st.session_state.current_page = "Roles"
            st.rerun()
            
    # System status
    st.subheader("System Status")
    
    # Modified system status metrics without database reference
    status_cols = st.columns(3)
    # Modified system status metrics without database reference
    status_cols = st.columns(3)
    logger.info(f"Connection: {neo4j_service.is_connected()}")
    with status_cols[0]:
        st.metric(label="Neo4j Status", value="Connected" if neo4j_service.is_connected() else "Not Connected")
    with status_cols[1]:
        st.metric(label="OpenAI Status", value="Ready")
