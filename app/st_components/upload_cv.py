import streamlit as st
from app.utils.file_utils import save_uploaded_file
import time
import uuid
import os
import asyncio
from datetime import datetime
from services.neo4j_service import Neo4jService
from services.background_processor import CVProcessorService
import threading


# Create a global processor service
cv_processor = CVProcessorService()

# Function to run background processing in a separate thread
def start_background_processing():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cv_processor.start_background_processing())
    loop.close()
def show_upload_cv(neo4j_service:Neo4jService):
    st.header("📤 Upload CVs", divider="rainbow")
    
    with st.container():
        
        uploaded_files = st.file_uploader(
            "Choose CV files", 
            accept_multiple_files=True, 
            type=["pdf", "docx", "doc"],
            help="Supported formats: PDF, DOCX, DOC"
        )
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected for upload")
        
        file_details_expander = st.expander("View file details", expanded=False)
        with file_details_expander:
            for i, uploaded_file in enumerate(uploaded_files):
                st.text(f"{i+1}. {uploaded_file.name} - {round(uploaded_file.size/1024, 2)} KB")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            upload_button = st.button("📤 Upload Selected CVs", use_container_width=True, type="primary")
            
        if upload_button:
            with st.status("Uploading files...", expanded=True) as status:
                success_count = 0
                total_files = len(uploaded_files)
                
                progress_bar = st.progress(0)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    st.write(f"Processing: {uploaded_file.name}")
                    
                    # Generate a unique ID and create unique filename
                    unique_id = str(uuid.uuid4())
                    file_extension = os.path.splitext(uploaded_file.name)[1]
                    unique_file_name = f"{unique_id}{file_extension}"
                    
                    # Save the file with unique filename
                    file_name, file_path = save_uploaded_file(uploaded_file, unique_file_name)
                    
                    # Create Neo4j CV node with extracted=false
                    success = neo4j_service.insert_cv_node(file_name=file_name)
                    
                    if success:
                        success_count += 1
                    
                    # Update progress
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    time.sleep(0.2)  # Small delay for visual feedback

                progress_bar.empty()
                
                if success_count == total_files:
                    status.update(label=f"✅ Successfully uploaded {success_count} CV(s)!", state="complete")
                    
                    # Start background processing in a separate thread
                    thread = threading.Thread(target=start_background_processing)
                    thread.daemon = True
                    thread.start()
                    
                    st.info("CV processing has started in the background.")
                    st.balloons()
                else:
                    status.update(label=f"Uploaded {success_count} of {total_files} CV(s)", state="complete")
                
                # Reset the file uploader after successful upload
                st.session_state.clear_file_uploader = True
    else:
        st.info("Drag and drop CV files here or click to browse")

    # Show extraction status
    if st.button("Check Extraction Status"):
        unextracted = neo4j_service.get_unextracted_cvs()
        if unextracted:
            st.warning(f"There are {len(unextracted)} CVs still being processed.")
        else:
            st.success("All CVs have been processed!")