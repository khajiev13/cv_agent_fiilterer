import streamlit as st
import pandas as pd
import time
import json
from datetime import datetime
from services.neo4j_service import Neo4jService
import os
from utils.file_utils import delete_cv_file, CV_DATA_DIR


def show_manage_cvs(neo4j_service:Neo4jService):
    st.header("📋 Manage Candidates", divider="rainbow")
    
    # Initialize session states
    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False
    
    if 'confirm_delete_all' not in st.session_state:
        st.session_state.confirm_delete_all = False
    
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = []
    
    if 'view_candidate_details' not in st.session_state:
        st.session_state.view_candidate_details = None
    
    if 'delete_candidate_id' not in st.session_state:
        st.session_state.delete_candidate_id = None
        
    # Fetch candidates from Neo4j
    with st.spinner("Loading candidates..."):
        candidates = []
        if neo4j_service and neo4j_service.is_connected():
            candidates = neo4j_service.get_all_candidates()
    
    if not candidates:
        st.info("No candidates have been added to the database yet.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Go to Upload Page", use_container_width=True):
                st.session_state.current_page = "Upload CVs"
                st.rerun()
    else:
        # Create header with action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col3:
            if st.button("🗑️ Delete All Candidates", type="primary", use_container_width=True):
                st.session_state.confirm_delete_all = True
        
        # Handle Delete All confirmation dialog
        if st.session_state.get('confirm_delete_all', False):
            st.warning("⚠️ This action cannot be undone! Are you sure you want to delete ALL candidates in the system?")
            confirm_col1, confirm_col2 = st.columns([1, 1])
            
            with confirm_col1:
                if st.button("✅ Yes, Delete All", type="primary", use_container_width=True):
                    with st.spinner("Deleting all candidates..."):
                        success = False
                        total_count = len(candidates)
                        
                        # Create a progress bar
                        progress_bar = st.progress(0)
                        
                        # Delete from Neo4j if connected
                        file_paths_to_delete = []
                        db_success = False
                        
                        if neo4j_service and neo4j_service.is_connected():
                            file_paths_to_delete, db_success = neo4j_service.delete_all_candidates()
                        
                        # Delete physical files
                        file_success = True
                        deleted_count = 0
                        
                        for i, file_path in enumerate(file_paths_to_delete):
                            # Delete the file
                            if delete_cv_file(file_path):
                                deleted_count += 1
                            else:
                                file_success = False
                            
                            # Update progress (weight Neo4j deletion as half the job)
                            progress = 0.5 + ((i + 1) / len(file_paths_to_delete) * 0.5) if file_paths_to_delete else 1.0
                            progress_bar.progress(progress)
                            time.sleep(0.05)
                        
                        success = db_success and file_success
                        
                        if success:
                            st.toast(f"Successfully deleted all {total_count} candidates from database and {deleted_count} CV files from disk.")
                            st.session_state.confirm_delete_all = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            if not db_success:
                                st.error("Failed to delete candidates from database.")
                            if not file_success:
                                st.error(f"Failed to delete some CV files. Deleted {deleted_count} of {len(file_paths_to_delete)}.")
            
            with confirm_col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_delete_all = False
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["👥 All Candidates", "📊 Statistics"])
        
        with tab1:
            # Prepare data for display
            df = pd.DataFrame(candidates)
            
            # Ensure all necessary columns exist
            for col in ['id', 'name', 'job_title', 'upload_date', 'has_skills', 'has_experience', 'has_education', 'file_path']:
                if col not in df.columns:
                    df[col] = None
            
            # Rename for display and select relevant columns
            display_df = df[['id', 'name', 'job_title', 'upload_date', 'has_skills', 'has_experience', 'has_education']].copy()
            display_df.columns = ['ID', 'Name', 'Job Title', 'Upload Date', 'Has Skills', 'Has Experience', 'Has Education']
            
            # Convert booleans to emojis
            for col in ['Has Skills', 'Has Experience', 'Has Education']:
                display_df[col] = display_df[col].apply(lambda x: "✅" if x else "❌")
            
            # Add filter options
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                filter_name = st.text_input("Filter by name", key="filter_name")
            
            with filter_col2:
                filter_job_title = st.text_input("Filter by job title", key="filter_job_title")
            
            # Apply filters
            filtered_df = display_df.copy()
            if filter_name:
                filtered_df = filtered_df[filtered_df['Name'].str.contains(filter_name, case=False, na=False)]
            
            if filter_job_title:
                filtered_df = filtered_df[filtered_df['Job Title'].str.contains(filter_job_title, case=False, na=False)]
            
            # Display candidate count
            st.caption(f"Showing {len(filtered_df)} of {len(display_df)} candidates")
            
            # Add Action column for individual deletion
            filtered_df['Action'] = [f"{id}" for id in filtered_df['ID']]
            
            # Data editor with selection
            edited_df = st.data_editor(
                filtered_df,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", help="Candidate identifier"),
                    "Name": st.column_config.TextColumn("Name", help="Candidate name"),
                    "Job Title": st.column_config.TextColumn("Job Title", help="Current job title"),
                    "Upload Date": st.column_config.DatetimeColumn("Upload Date", help="Date when candidate was added", format="DD/MM/YYYY HH:mm"),
                    "Has Skills": st.column_config.TextColumn("Skills", help="Has skill data"),
                    "Has Experience": st.column_config.TextColumn("Experience", help="Has experience data"),
                    "Has Education": st.column_config.TextColumn("Education", help="Has education data"),
                    "Action": st.column_config.CheckboxColumn("Select", help="Select for action")
                },
                use_container_width=True,
                disabled=["ID", "Name", "Job Title", "Upload Date", "Has Skills", "Has Experience", "Has Education"],
                key="candidates_table"
            )
            
            # Process the checkboxes and extract IDs of selected candidates
            selected_ids = edited_df.loc[edited_df['Action'] == True, 'ID'].tolist()
            st.session_state.selected_ids = selected_ids
            
            # Individual row delete buttons
            for i, row in filtered_df.iterrows():
                col1, col2, col3 = st.columns([10, 1, 1])
                with col2:
                    if st.button("🔍", key=f"view_{row['ID']}"):
                        st.session_state.view_candidate_details = row['ID']
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"delete_{row['ID']}"):
                        st.session_state.delete_candidate_id = row['ID']
                        st.rerun()
            
            # Handle individual candidate deletion
            if st.session_state.delete_candidate_id:
                candidate_id = st.session_state.delete_candidate_id
                st.warning(f"⚠️ Are you sure you want to delete this candidate? This action cannot be undone.")
                
                confirm_col1, confirm_col2 = st.columns([1, 1])
                with confirm_col1:
                    if st.button("✅ Yes, Delete", type="primary", key=f"confirm_delete_{candidate_id}", use_container_width=True):
                        with st.spinner("Deleting candidate..."):
                            # Get file path and delete from Neo4j
                            file_path, db_success = neo4j_service.delete_candidate(candidate_id)
                            
                            # Delete CV file if file path exists
                            file_success = True
                            if file_path and os.path.exists(file_path):
                                file_success = delete_cv_file(file_path)
                            
                            if db_success:
                                st.toast(f"Successfully deleted candidate {candidate_id}")
                                st.session_state.delete_candidate_id = None
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to delete candidate from database.")
                
                with confirm_col2:
                    if st.button("❌ Cancel", key=f"cancel_delete_{candidate_id}", use_container_width=True):
                        st.session_state.delete_candidate_id = None
                        st.rerun()
            
            # Batch deletion section - only show if candidates are selected
            if selected_ids:
                st.divider()
                st.subheader(f"Selected Candidates: {len(selected_ids)}")
                
                # Show list of selected candidates
                selected_names = filtered_df[filtered_df['ID'].isin(selected_ids)][['Name', 'Job Title']].values.tolist()
                for name, job_title in selected_names:
                    st.write(f"• {name}: {job_title}")
                
                if st.button(f"🗑️ Delete {len(selected_ids)} Selected Candidates", type="primary"):
                    st.session_state.confirm_delete = True
                
                # Confirmation for batch deletion
                if st.session_state.confirm_delete:
                    st.warning("⚠️ This will delete all selected candidates and their CV files. This action cannot be undone!")
                    confirm_col1, confirm_col2 = st.columns([1, 1])
                    
                    with confirm_col1:
                        if st.button("✅ Yes, Delete Selected", type="primary", use_container_width=True):
                            with st.spinner("Deleting selected candidates..."):
                                success_count = 0
                                file_success_count = 0
                                
                                # Create a progress bar
                                progress_bar = st.progress(0)
                                
                                for i, candidate_id in enumerate(selected_ids):
                                    # Delete from Neo4j
                                    file_path, db_success = neo4j_service.delete_candidate(candidate_id)
                                    
                                    if db_success:
                                        success_count += 1
                                        
                                        # Delete CV file
                                        if file_path and os.path.exists(file_path):
                                            if delete_cv_file(file_path):
                                                file_success_count += 1
                                    
                                    # Update progress
                                    progress = (i + 1) / len(selected_ids)
                                    progress_bar.progress(progress)
                                    time.sleep(0.1)
                                
                                if success_count > 0:
                                    st.toast(f"Successfully deleted {success_count} candidates and {file_success_count} CV files.")
                                    st.session_state.confirm_delete = False
                                    st.session_state.selected_ids = []
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to delete the selected candidates.")
                    
                    with confirm_col2:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()
        
        with tab2:
            # Show statistics
            st.subheader("Candidate Statistics")
            
            # Calculate statistics
            total_candidates = len(df)
            candidates_with_skills = len(df[df['has_skills'] == True]) if 'has_skills' in df.columns else 0
            candidates_with_experience = len(df[df['has_experience'] == True]) if 'has_experience' in df.columns else 0
            candidates_with_education = len(df[df['has_education'] == True]) if 'has_education' in df.columns else 0
            
            # Display metrics
            col1, col2 = st.columns(2)
            col1.metric("Total Candidates", total_candidates)
            col2.metric("With Skills", candidates_with_skills)
            col3, col4 = st.columns(2)
            col3.metric("With Experience", candidates_with_experience)
            col4.metric("With Education", candidates_with_education)
            
            # Add charts
            if total_candidates > 0:
                # Skills chart
                st.subheader("Candidate Information Completeness")
                chart_data = pd.DataFrame({
                    'Category': ['With Skills', 'With Experience', 'With Education'],
                    'Count': [candidates_with_skills, candidates_with_experience, candidates_with_education]
                })
                st.bar_chart(
                    chart_data, 
                    x='Category', 
                    y='Count',
                    color='#4776E6'  
                )

        # Handle candidate details view
        if st.session_state.view_candidate_details:
            candidate_id = st.session_state.view_candidate_details
            # Find the candidate in our DataFrame
            candidate = df[df['id'] == candidate_id].iloc[0].to_dict() if any(df['id'] == candidate_id) else None
            
            if candidate:
                st.sidebar.header(f"Candidate Details")
                st.sidebar.write(f"**Name:** {candidate.get('name', 'Unknown')}")
                st.sidebar.write(f"**Job Title:** {candidate.get('job_title', 'Unknown')}")
                st.sidebar.write(f"**Added On:** {candidate.get('upload_date', 'Unknown')}")
                
                # Show file path if available
                if candidate.get('file_path'):
                    st.sidebar.write(f"**CV File:** {os.path.basename(candidate['file_path'])}")
                
                # Add buttons to view CV or close details
                col1, col2 = st.sidebar.columns(2)
                
                with col1:
                    if st.button("View CV", use_container_width=True):
                        # Add functionality to view CV file
                        st.sidebar.info("CV viewer not implemented yet")
                
                with col2:
                    if st.button("Close Details", use_container_width=True):
                        st.session_state.view_candidate_details = None
                        st.rerun()