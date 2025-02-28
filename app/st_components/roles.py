from app.services.neo4j_service import Neo4jService
import streamlit as st
import pandas as pd
import time
import uuid

def show_roles(neo4j_service=None):
    st.header("🧩 Manage Roles", divider="rainbow")
    
    # Use session state Neo4j service if none is provided
    if neo4j_service is None:
        neo4j_service = st.session_state.neo4j_service
    
    # Check connection status
    if not neo4j_service.is_connected():
        st.error("Database connection is required to manage roles.")
        if st.button("Try reconnecting"):
            connection_success = neo4j_service.connect()
            if connection_success:
                st.success("Connection established")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Connection failed. Please check your database settings.")
        return
    
    # Initialize session states
    if 'edit_role_id' not in st.session_state:
        st.session_state.edit_role_id = None
    
    if 'delete_role_id' not in st.session_state:
        st.session_state.delete_role_id = None
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["View Roles", "Add Role"])
    
    with tab1:
        # Display existing roles
        st.subheader("Existing Roles")
        
        # Get all roles from Neo4j
        with st.spinner("Loading roles..."):
            roles = neo4j_service.get_all_roles()
        
        if not roles:
            st.info("No roles have been added yet.")
            
            # Add a helper message
            st.markdown("""
            <div style="text-align: center; padding: 20px; margin: 20px 0; border-radius: 10px;">
                <h3>No Roles Found</h3>
                <p>Add your first job role to start matching candidates</p>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            # Convert to DataFrame for display
            df = pd.DataFrame(roles)
            df = df[['id', 'job_title', 'degree_requirement', 'experience_years', 'required_skills', 'location_remote']]
            df.columns = ['ID', 'Job Title', 'Degree', 'Experience (years)', 'Skills', 'Location']
            
            # Add search functionality
            search_query = st.text_input("🔍 Search roles", placeholder="Enter job title or skills")
            
            if search_query:
                filtered_df = df[
                    df['Job Title'].str.contains(search_query, case=False) | 
                    df['Skills'].str.contains(search_query, case=False)
                ]
                st.caption(f"Found {len(filtered_df)} matching roles")
                display_df = filtered_df
            else:
                display_df = df
            
            # Display roles as a data editor
            selection = st.data_editor(
                display_df,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", help="Role identifier"),
                    "Job Title": st.column_config.TextColumn("Job Title", help="Title of the job role"),
                    "Degree": st.column_config.TextColumn("Degree", help="Required education level"),
                    "Experience (years)": st.column_config.NumberColumn("Experience (years)", help="Required years of experience"),
                    "Skills": st.column_config.TextColumn("Skills", help="Required skills for the role", width="large"),
                    "Location": st.column_config.TextColumn("Location", help="Job location or remote policy")
                },
                use_container_width=True,
                disabled=df.columns.tolist(),
                selection_mode="single",
                key="roles_table"
            )
            
            # Handle role selection for edit/delete
            selected_rows = selection.get("selected_rows", [])
            if selected_rows:
                selected_role = selected_rows[0]
                role_id = selected_role['ID']
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit Role", use_container_width=True):
                        st.session_state.edit_role_id = role_id
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Delete Role", use_container_width=True):
                        st.session_state.delete_role_id = role_id
                        st.rerun()
                
                # Handle delete confirmation
                if st.session_state.delete_role_id == role_id:
                    st.warning("⚠️ Are you sure you want to delete this role?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Delete", key="confirm_delete", use_container_width=True):
                            with st.spinner("Deleting role..."):
                                success = neo4j_service.delete_role(role_id)
                                if success:
                                    st.session_state.delete_role_id = None
                                    st.toast("Role deleted successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to delete the role")
                    
                    with col2:
                        if st.button("❌ Cancel", key="cancel_delete", use_container_width=True):
                            st.session_state.delete_role_id = None
                            st.rerun()
                
                # Handle edit form
                if st.session_state.edit_role_id == role_id:
                    # Get current role data
                    current_role = next((r for r in roles if r['id'] == role_id), None)
                    if current_role:
                        st.subheader("Edit Role")
                        with st.form(key="edit_role_form"):
                            job_title = st.text_input(
                                "Job Title*", 
                                value=current_role['job_title']
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                degree_requirement = st.selectbox(
                                    "Degree Requirement", 
                                    ["Any", "Bachelor's", "Master's", "PhD"],
                                    index=["Any", "Bachelor's", "Master's", "PhD"].index(current_role['degree_requirement'])
                                )
                                
                                experience_years = st.number_input(
                                    "Years of Experience", 
                                    min_value=0, 
                                    value=int(current_role['experience_years'])
                                )
                            
                            with col2:
                                field_of_study = st.text_input(
                                    "Field of Study",
                                    value=current_role['field_of_study']
                                )
                                
                                location_remote = st.text_input(
                                    "Location/Remote",
                                    value=current_role['location_remote']
                                )
                            
                            required_skills = st.text_area(
                                "Required Skills (comma separated)",
                                value=current_role['required_skills']
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                submit = st.form_submit_button("💾 Update Role", use_container_width=True)
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state.edit_role_id = None
                                    st.rerun()
                            
                            if submit:
                                if not job_title:
                                    st.error("Job Title is required")
                                else:
                                    with st.spinner("Updating role..."):
                                        success = neo4j_service.update_role(
                                            role_id, job_title, degree_requirement, 
                                            field_of_study, experience_years, 
                                            required_skills, location_remote
                                        )
                                        if success:
                                            st.session_state.edit_role_id = None
                                            st.toast("Role updated successfully!")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("Failed to update the role")
    
    with tab2:
        # Form to add a new role with improved layout
        st.subheader("Add New Role")
        with st.form("add_role_form"):
            job_title = st.text_input("Job Title*", placeholder="e.g. Software Engineer")
            
            col1, col2 = st.columns(2)
            with col1:
                degree_requirement = st.selectbox(
                    "Degree Requirement", 
                    ["Any", "Bachelor's", "Master's", "PhD"],
                    help="Minimum education requirement"
                )
                
                experience_years = st.number_input(
                    "Years of Experience", 
                    min_value=0, 
                    value=0,
                    help="Minimum years of experience required"
                )
            
            with col2:
                field_of_study = st.text_input(
                    "Field of Study",
                    placeholder="e.g. Computer Science, Engineering",
                    help="Comma separated for multiple fields"
                )
                
                location_remote = st.text_input(
                    "Location/Remote",
                    placeholder="e.g. New York / Remote",
                    help="Job location or remote policy"
                )
            
            required_skills = st.text_area(
                "Required Skills",
                placeholder="e.g. Python, Java, Machine Learning",
                help="Comma separated for multiple skills"
            )
            
            submitted = st.form_submit_button("➕ Add Role", use_container_width=True)
            
            if submitted:
                if not job_title:
                    st.error("Job Title is required")
                else:
                    with st.spinner("Adding role..."):
                        # Generate a unique ID for the new role
                        role_id = str(uuid.uuid4())
                        success = neo4j_service.add_role(
                            role_id, job_title, degree_requirement, field_of_study,
                            experience_years, required_skills, location_remote
                        )
                        if success:
                            st.toast("✅ Role added successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to add the role")