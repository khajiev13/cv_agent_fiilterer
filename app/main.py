import streamlit as st
from app.st_components.home import show_home
from app.st_components.upload_cv import show_upload_cv
from app.st_components.manage_cvs import show_manage_cvs
from app.st_components.roles import show_roles
# Import the RAG interface
from app.st_components.simple_rag_interface import show_simple_rag_interface, show_advanced_rag_interface
# Import your database and neo4j services
from app.services.neo4j_service import Neo4jService

def main():
    # Set page config
    st.set_page_config(
        page_title="Resume Agent",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize Neo4j service in session state (only once)
    if "neo4j_service" not in st.session_state:
        st.session_state.neo4j_service = Neo4jService()
        connection_success = st.session_state.neo4j_service.connect()
        st.session_state.neo4j_connected = connection_success
    
    # Add connection indicator in sidebar
    if st.session_state.get("neo4j_connected", False):
        st.sidebar.success("✅ Database Connected")
    else:
        st.sidebar.error("Database Disconnected", icon="❌")
        if st.sidebar.button("🔄 Reconnect"):
            st.session_state.neo4j_service = Neo4jService()
            st.session_state.neo4j_connected = st.session_state.neo4j_service.connect()
            st.rerun()

    # Initialize session state for navigation
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Home"

    # Sidebar navigation
    st.sidebar.title("Resume Agent")
    
    # Navigation buttons
    if st.sidebar.button("🏠 Home"):
        st.session_state.current_page = "Home"
        st.rerun()
        
    if st.sidebar.button("📤 Upload CVs"):
        st.session_state.current_page = "Upload CVs"
        st.rerun()
        
    if st.sidebar.button("📋 Manage CVs"):
        st.session_state.current_page = "Manage CVs"
        st.rerun()
        
    if st.sidebar.button("🧩 Roles"):
        st.session_state.current_page = "Roles"
        st.rerun()
        
    # Add new button for AI Search & Chat
    if st.sidebar.button("🤖 AI Search & Chat"):
        st.session_state.current_page = "AI Search & Chat"
        st.rerun()
        
    # Debug mode option for the RAG interface
    if st.session_state.current_page == "AI Search & Chat":
        st.session_state.debug_mode = st.sidebar.checkbox("Enable Debug Mode", value=False)
    
    # Display the selected page
    if st.session_state.current_page == "Home":
        show_home(st.session_state.neo4j_service)
    elif st.session_state.current_page == "Upload CVs":
        show_upload_cv(st.session_state.neo4j_service)
    elif st.session_state.current_page == "Manage CVs":
        show_manage_cvs(st.session_state.neo4j_service)
    elif st.session_state.current_page == "Roles":
        show_roles(st.session_state.neo4j_service)
    elif st.session_state.current_page == "AI Search & Chat":
        # Choose which version of the RAG interface to show based on debug mode
        if st.session_state.get("debug_mode", False):
            show_advanced_rag_interface()
        else:
            show_simple_rag_interface()

if __name__ == "__main__":
    main()