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

default_workers = min(32, os.cpu_count() * 3)  

# Create a global processor service with desired number of workers
cv_processor = CVProcessorService(max_workers=default_workers)  

# Function to run background processing in a separate thread
def start_background_processing():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cv_processor.start_background_processing())
    loop.close()

def stop_background_processing():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cv_processor.stop_background_processing())
    loop.close()

def show_upload_cv(neo4j_service:Neo4jService):
    st.header("📤 Upload CVs", divider="rainbow")
    
    # Display processing status
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Queue Size", cv_processor.get_queue_size())
    with col2:
        st.metric("Processing Active", "Yes" if cv_processor.is_processing else "No")
    with col3:
        if cv_processor.is_processing:
            if st.button("⏹️ Stop Processing", use_container_width=True):
                stop_background_processing()
                st.success("Processing stopped!")
                st.rerun()
        else:
            if st.button("▶️ Start Processing", use_container_width=True):
                thread = threading.Thread(target=start_background_processing)
                thread.daemon = True
                thread.start()
                st.success("Processing started!")
                time.sleep(0.5)  # Brief pause to let thread initialize
                st.rerun()
    
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
                    
                    #Pass the file name and content to background processor
                    cv_processor.add_cv_to_queue(file_name, unique_file_name, file_path)
                    success_count += 1
                    
                    # Update progress
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    time.sleep(0.1)  # Small delay for visual feedback

                progress_bar.empty()
                
                if success_count == total_files:
                    status.update(label=f"✅ Added {success_count} CV(s) to processing queue!", state="complete")
                    
                    # Ensure background processing is running
                    if not cv_processor.is_processing:
                        st.info("Starting CV processing in the background.")
                        thread = threading.Thread(target=start_background_processing)
                        thread.daemon = True
                        thread.start()
                    
                    st.success(f"CV processing queue: {cv_processor.get_queue_size()} files")
                    st.balloons()
                else:
                    status.update(label=f"Queued {success_count} of {total_files} CV(s)", state="complete")
                
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