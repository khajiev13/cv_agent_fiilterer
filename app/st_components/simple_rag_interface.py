import streamlit as st
import logging

# Setup logging
logger = logging.getLogger(__name__)

def show_simple_rag_interface():
    """Display a clean and simple RAG chatbot interface"""
    st.title("Resume Database Chatbot")
    
    # Initialize the RAG service
    try:
        from app.services.rag_service import RAGService
    except ImportError as e:
        st.error(f"Error importing RAG service: {e}")
        st.info("Make sure your RAG service implementation is available in app/services/rag_service.py")
        return
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your resume search assistant. Ask me about candidates in our database."}
        ]
    
    # Initialize RAG service once
    if 'rag_service' not in st.session_state:
        try:
            with st.spinner("Connecting to database..."):
                st.session_state.rag_service = RAGService()
        except Exception as e:
            st.error(f"Failed to initialize RAG service: {str(e)}")
            return
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    if prompt := st.chat_input("Ask a question..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Searching database..."):
                try:
                    # Query the RAG service for text response
                    response = st.session_state.rag_service.query(prompt)
                    st.markdown(response)
                    
                    # Store response in session state
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    logger.error(f"Error in RAG query: {str(e)}")
    
    # Show example queries in the sidebar
    st.sidebar.subheader("Example Queries")
    
    examples = [
        "Find candidates with Python experience",
        "Who knows React and has 3+ years of experience?",
        "Find data scientists with machine learning skills",
        "Show me candidates who worked at Google",
        "Who has experience in project management?",
        "Find people with a degree in Computer Science"
    ]
    
    for example in examples:
        if st.sidebar.button(example, key=f"ex_{example[:20]}"):
            # Add example as user message and rerun
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()

def show_advanced_rag_interface():
    """Display a simpler version of the RAG interface with minimal debug tools"""
    show_simple_rag_interface()  # Reuse the same interface
    
    # Add a clear chat button
    if st.sidebar.button("Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat history cleared. How can I help you?"}
        ]
        st.rerun()
