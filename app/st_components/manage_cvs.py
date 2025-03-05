import streamlit as st
import pandas as pd
import time
import json
from datetime import datetime
from services.neo4j_service import Neo4jService
import os
from utils.file_utils import delete_cv_file, CV_DATA_DIR, delete_cv_file



def show_manage_cvs(neo4j_service:Neo4jService):
    st.header("📋 Manage CVs", divider="rainbow")
    
    # Initialize session states
    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False
    
    if 'confirm_delete_all' not in st.session_state:
        st.session_state.confirm_delete_all = False
    
    if 'selected_ids' not in st.session_state:
        st.session_state.selected_ids = []
    
    if 'view_cv_details' not in st.session_state:
        st.session_state.view_cv_details = None
    
    # Fetch CVs from Neo4j
    with st.spinner("Loading CVs..."):
        cvs = []
        if neo4j_service and neo4j_service.is_connected():
            cvs = neo4j_service.get_all_cv_nodes()
    
    if not cvs:
        st.info("No CVs have been uploaded yet.")
        
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
            if st.button("🗑️ Delete All CVs", type="primary", use_container_width=True):
                st.session_state.confirm_delete_all = True
        
        # Handle Delete All confirmation dialog
        if st.session_state.get('confirm_delete_all', False):
            st.warning("⚠️ This action cannot be undone! Are you sure you want to delete ALL CVs in the system?")
            confirm_col1, confirm_col2 = st.columns([1, 1])
            
            with confirm_col1:
                if st.button("✅ Yes, Delete All", type="primary", use_container_width=True):
                    with st.spinner("Deleting all files..."):
                        success = False
                        total_count = len(cvs)
                        
                        # Create a progress bar
                        progress_bar = st.progress(0)
                        
                        # Store file paths before deleting from Neo4j
                        file_paths_to_delete = []
                        for cv in cvs:
                            # Check if file_path exists in the CV node data
                            if 'file_path' in cv and cv['file_path']:
                                file_paths_to_delete.append(cv['file_path'])
                            # If file_path doesn't exist but filename does, construct the path
                            elif 'filename' in cv or 'file_name' in cv:
                                filename = cv.get('filename', cv.get('file_name', ''))
                                if filename:
                                    file_path = os.path.join(CV_DATA_DIR, filename)
                                    file_paths_to_delete.append(file_path)
                        
                        # Delete from Neo4j if connected
                        db_success = False
                        if neo4j_service and neo4j_service.is_connected():
                            db_success = neo4j_service.delete_all_cv_nodes()
                        
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
                            progress = 0.5 + ((i + 1) / len(file_paths_to_delete) * 0.5)
                            progress_bar.progress(progress)
                            time.sleep(0.05)
                        
                        success = db_success and file_success
                        
                        if success:
                            st.toast(f"Successfully deleted all {total_count} CVs from database and {deleted_count} CV files from disk.")
                            st.session_state.confirm_delete_all = False
                            time.sleep(1)
                        else:
                            if not db_success:
                                st.error("Failed to delete CVs from database.")
                            if not file_success:
                                st.error(f"Failed to delete some CV files. Deleted {deleted_count} of {len(file_paths_to_delete)}.")
            
            with confirm_col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_delete_all = False
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📋 All CVs", "📊 Statistics"])
        
        with tab1:
            # Prepare data for display
            df = pd.DataFrame(cvs)
            
            # Ensure columns exist
            for col in ['id', 'filename', 'upload_date', 'processed']:
                if col not in df.columns:
                    if col == 'filename' and 'file_name' in df.columns:
                        df['filename'] = df['file_name']
                    else:
                        df[col] = None
            
            # Rename for display and select relevant columns
            display_df = df[['id', 'filename', 'upload_date', 'processed']].copy()
            display_df.columns = ['ID', 'Filename', 'Upload Date', 'Data Extracted']
            
            # Convert boolean to emoji
            display_df['Data Extracted'] = display_df['Data Extracted'].apply(lambda x: "✅" if x else "❌")
            
            # Add filter options
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                filter_filename = st.text_input("Filter by filename", key="filter_filename")
            
            with filter_col2:
                filter_data_extracted = st.selectbox(
                    "Filter by data extraction status",
                    options=["All", "Extracted", "Not Extracted"],
                    key="filter_data_extracted"
                )
            
            # Apply filters
            filtered_df = display_df.copy()
            if filter_filename:
                filtered_df = filtered_df[filtered_df['Filename'].str.contains(filter_filename, case=False)]
            
            if filter_data_extracted == "Extracted":
                filtered_df = filtered_df[filtered_df['Data Extracted'] == "✅"]
            elif filter_data_extracted == "Not Extracted":
                filtered_df = filtered_df[filtered_df['Data Extracted'] == "❌"]
            
            # Display CV count
            st.caption(f"Showing {len(filtered_df)} of {len(display_df)} CVs")
            
            # Data editor with selection
            edited_df = st.data_editor(
                filtered_df,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", help="CV identifier"),
                    "Filename": st.column_config.TextColumn("Filename", help="Name of the file"),
                    "Upload Date": st.column_config.DatetimeColumn("Upload Date", help="Date when CV was uploaded", format="DD/MM/YYYY HH:mm"),
                    "Data Extracted": st.column_config.TextColumn("Data Extracted", help="Whether data has been extracted")
                },
                use_container_width=True,
                disabled=["ID", "Filename", "Upload Date", "Data Extracted"],
                key="cv_table"
            )
            
            # Create a mapping of ID to filename for safe lookups
            id_to_filename = {}
            for _, row in filtered_df.iterrows():
                id_to_filename[row['ID']] = row['Filename']
            
            # Add a multi-select widget to select rows by ID with safe format function
            selected_ids = st.multiselect(
                "Select CVs to manage:",
                options=filtered_df['ID'].tolist(),
                format_func=lambda x: f"ID: {x} - {id_to_filename.get(x, 'Unknown')}"
            )
            
            # Get the selected rows based on the selected IDs
            if selected_ids:
                selected_rows = filtered_df[filtered_df['ID'].isin(selected_ids)].to_dict('records')
                st.session_state.selected_ids = selected_ids
                
                # Show selected CV details in an expander
                with st.expander("📄 Selected CV Details", expanded=True):
                    for i, row in enumerate(selected_rows):
                        st.markdown(f"**CV #{i+1}: {row['Filename']}**")
                        st.markdown(f"- **ID:** {row['ID']}")
                        st.markdown(f"- **Upload Date:** {row['Upload Date']}")
                        st.markdown(f"- **Data Extraction Status:** {row['Data Extracted']}")
                        
                        # View details button
                        button_key = f"details_{row['ID'] if row['ID'] is not None else f'unknown_{i}'}"
                        if st.button(f"🔍 View Details", key=button_key):
                            st.session_state.view_cv_details = row['ID']
                            st.rerun()
                            
                        if i < len(selected_rows) - 1:
                            st.divider()
                
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button(f"🗑️ Delete Selected ({len(selected_ids)} CVs)", type="primary", use_container_width=True):
                        st.session_state.confirm_delete = True
                
                with col2:
                    if st.session_state.get('confirm_delete', False):
                        st.warning("⚠️ This action cannot be undone! Are you sure you want to delete the selected CVs?")
                        confirm_col1, confirm_col2 = st.columns([1, 1])
                        
                        with confirm_col1:
                            if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
                                with st.spinner("Deleting files..."):
                                    success_count = 0
                                    
                                    # Create a progress bar
                                    progress_bar = st.progress(0)
                                    
                                    for i, cv_id in enumerate(selected_ids):
                                        # Delete from Neo4j if connected
                                        if neo4j_service and neo4j_service.is_connected():
                                            if neo4j_service.delete_cv_node(cv_id):
                                                success_count += 1
                                        
                                        # Update progress
                                        progress = (i + 1) / len(selected_ids)
                                        progress_bar.progress(progress)
                                        time.sleep(0.1)
                                    
                                    if success_count:
                                        st.toast(f"Successfully deleted {success_count} CVs.")
                                        st.session_state.confirm_delete = False
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete the selected CVs.")
                        
                        with confirm_col2:
                            if st.button("❌ Cancel", use_container_width=True):
                                st.session_state.confirm_delete = False
                                st.rerun()
        
        with tab2:
            # Show statistics
            st.subheader("CV Statistics")
            
            # Calculate statistics
            total_cvs = len(df)
            extracted_cvs = len(df[df['processed'] == True]) if 'processed' in df.columns else 0
            not_extracted_cvs = total_cvs - extracted_cvs
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total CVs", total_cvs)
            col2.metric("Processed CVs", extracted_cvs)
            col3.metric("Pending CVs", not_extracted_cvs)
            
            # Add a chart
            if total_cvs > 0:
                st.subheader("Processing Status")
                chart_data = pd.DataFrame({
                    'Status': ['Processed', 'Pending'],
                    'Count': [extracted_cvs, not_extracted_cvs]
                })
                st.bar_chart(
                    chart_data, 
                    x='Status', 
                    y='Count',
                    color='#4776E6'  
                )

        # Handle CV details view
        if st.session_state.view_cv_details:
            cv_id = st.session_state.view_cv_details
            cv_details = next((cv for cv in cvs if cv['id'] == cv_id), None)
            
            if cv_details:
                st.sidebar.subheader(f"📄 CV Details")
                st.sidebar.write(f"**Filename:** {cv_details.get('filename', cv_details.get('file_name', 'Unknown'))}")
                st.sidebar.write(f"**Upload Date:** {cv_details.get('upload_date', 'Unknown')}")
                st.sidebar.write(f"**Processed:** {'Yes' if cv_details.get('processed', False) else 'No'}")
                
                if 'file_path' in cv_details and cv_details['file_path']:
                    st.sidebar.write(f"**File Path:** {cv_details['file_path']}")
                
                # Show extracted data if available
                extraction_data = cv_details.get('extraction_data', {})
                if extraction_data:
                    try:
                        if isinstance(extraction_data, str):
                            extraction_data = json.loads(extraction_data)
                        
                        st.sidebar.subheader("Extracted Data")
                        
                        # Show entities 
                        if "entities" in extraction_data:
                            entities = extraction_data["entities"]
                            
                            # Group entities by label
                            entity_groups = {}
                            for entity in entities:
                                label = entity.get("label", "Unknown")
                                if label not in entity_groups:
                                    entity_groups[label] = []
                                entity_groups[label].append(entity)
                            
                            # Create tabs for different entity types
                            if entity_groups:
                                tabs = st.sidebar.tabs(list(entity_groups.keys()))
                                
                                for i, (label, entities) in enumerate(entity_groups.items()):
                                    with tabs[i]:
                                        for entity in entities:
                                            st.write(f"**ID:** {entity.get('id', 'Unknown')}")
                                            for key, value in entity.items():
                                                if key not in ["id", "label"]:
                                                    st.write(f"**{key.capitalize()}:** {value}")
                                            st.divider()
                    except Exception as e:
                        st.sidebar.error(f"Error parsing extraction data: {e}")
                
                # Close button
                if st.sidebar.button("Close Details"):
                    st.session_state.view_cv_details = None
                    st.rerun()