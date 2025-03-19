import streamlit as st
from app.utils.file_utils import save_uploaded_file
import time
import uuid
import os
from datetime import datetime
from services.neo4j_service import Neo4jService
from services.background_processor import CVProcessorService
import threading

# Calculate default workers
default_workers = min(32, (os.cpu_count() or 4) * 3)  

def show_upload_cv(neo4j_service: Neo4jService):
    # Initialize CV processor
    if 'cv_processor' not in st.session_state:
        processor = CVProcessorService()
        processor.start()
        st.session_state.cv_processor = processor
    
    cv_processor = st.session_state.cv_processor
    
    # Add a way to properly shut down the processor when the app ends
    # Check if shutdown_registered exists AND is False
    if not st.session_state.get("shutdown_registered", False):
        # Register this in session state so we only do it once
        def _on_session_end():
            if hasattr(cv_processor, 'shutdown'):
                cv_processor.shutdown()
        
        st.session_state.on_session_end = _on_session_end
        st.session_state.shutdown_registered = True
    
    st.header("📤 Upload CVs", divider="rainbow")
    
    # Display processing status with refresh button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Queue Size", cv_processor.get_queue_size())
    with col2:
        st.metric("Processing Active", "Yes" if cv_processor.is_processing else "No")
    with col3:
        if st.button("🔄 Refresh Status"):
            st.rerun()
            
    # Add control buttons for the processor
    col1, col2 = st.columns(2)
    with col1:
        if cv_processor.is_processing:
            if st.button("⏹️ Stop Processor"):
                cv_processor.shutdown()
                st.success("Processor shutting down...")
                time.sleep(0.5)
                st.rerun()
                
    # File uploader section (existing code)
    with st.container():
        uploaded_files = st.file_uploader(
            "Choose CV files", 
            accept_multiple_files=True, 
            type=["pdf", "docx", "doc"],
            help="Supported formats: PDF, DOCX, DOC"
        )
    
    # Rest of your existing upload code remains the same
    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected for upload")
        
        file_details_expander = st.expander("View file details", expanded=False)
        with file_details_expander:
            for i, uploaded_file in enumerate(uploaded_files):
                st.text(f"{i+1}. {uploaded_file.name} - {round(uploaded_file.size/1024, 2)} KB")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            # Disable the upload button if processor isn't running
            upload_button = st.button(
                "📤 Upload Selected CVs", 
                use_container_width=True, 
                type="primary",
                disabled=not cv_processor.is_processing
            )
            
        # UNCHANGED: Keep the initialization and UI section the same

        # Change the upload_button handler to immediately process CVs
        if upload_button:
            with st.status("Processing files...", expanded=True) as status:
                queued_count = 0
                processed_count = 0
                total_files = len(uploaded_files)
                
                progress_bar = st.progress(0)
                
                # Step 1: Queue all files first
                for i, uploaded_file in enumerate(uploaded_files):
                    st.write(f"Queueing: {uploaded_file.name}")
                    
                    # Generate a unique ID and create unique filename
                    unique_id = str(uuid.uuid4())
                    file_extension = os.path.splitext(uploaded_file.name)[1]
                    unique_file_name = f"{unique_id}{file_extension}"
                    
                    # Save the file with unique filename
                    file_name, file_path = save_uploaded_file(uploaded_file, unique_file_name)
                    
                    # Pass the file name and content to background processor
                    cv_processor.add_cv_to_queue(file_name, unique_file_name, file_path)
                    queued_count += 1
                    
                    # Update progress for queueing phase (50% of total progress)
                    progress = ((i + 1) / total_files) * 0.5
                    progress_bar.progress(progress)
                    time.sleep(0.05)  # Small delay for visual feedback

                st.write(f"Added {queued_count} CV(s) to processing queue")
                
                # Step 2: Process all files immediately
                st.write("Processing files... (this may take time)")
                status.update(label="Processing CV files...", state="running")
                
                # Process all CVs at once
                processed_count = cv_processor.process_all_cvs()
                
                # Update progress to 100%
                progress_bar.progress(1.0)
                time.sleep(0.5)  # Brief pause for UX
                progress_bar.empty()
                
                # Show final status
                if processed_count == total_files:
                    status.update(label=f"✅ Successfully processed {processed_count} CV(s)!", state="complete")
                    st.success(f"All {processed_count} CV(s) were processed and added to the database")
                else:
                    status.update(label=f"⚠️ Processed {processed_count} of {total_files} CV(s)", state="error")
                    st.warning(f"Some files failed to process. Check logs for details.")
                
                # Check if any files remain in the queue
                remaining = cv_processor.get_queue_size()
                if remaining > 0:
                    st.warning(f"{remaining} files remain in the queue")
    else:
        st.info("Drag and drop CV files here or click to browse")
