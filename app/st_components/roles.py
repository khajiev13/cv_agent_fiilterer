import asyncio
import uuid
import time
import streamlit as st
import pandas as pd
from app.services.data_extraction_service import DataExtractionService
from app.utils.file_utils import extract_text_from_uploaded_file


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
        
    if 'fields_of_study' not in st.session_state:
        st.session_state.fields_of_study = [{"name": "", "alternative_fields": "", "importance": "required"}]
        
    if 'required_skills' not in st.session_state:
        st.session_state.required_skills = [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["View Roles", "Add Role"])
    
    # Tab 1: View Roles
    with tab1:
        display_roles_table(neo4j_service)
    
    # Tab 2: Add Role
    with tab2:
        add_role_form(neo4j_service)


def display_roles_table(neo4j_service):
    """Display existing roles in a table with options to edit or delete"""
    
    # Get all roles from Neo4j
    roles = neo4j_service.get_all_roles()
    
    if not roles:
        st.info("No roles found in the database.")
        return
    
    # Convert to DataFrame for better display
    roles_df = pd.json_normalize(roles)
    
    # Select columns for display
    display_columns = ["id", "job_title", "degree_requirement", "field_of_study", 
                      "experience_years", "required_skills", "location", 
                      "remote_option", "role_level"]
    
    # Filter columns that exist in the DataFrame
    display_columns = [col for col in display_columns if col in roles_df.columns]
    
    # Create role table with action buttons
    st.subheader("Existing Roles")
    
    with st.container():
        # Using expanders for each role for a cleaner UI
        for role in roles:
            with st.expander(f"📋 {role.get('job_title', 'Untitled Role')}"):
                # Two-column layout for role details
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**ID:** {role.get('id', 'N/A')}")
                    st.markdown(f"**Title:** {role.get('job_title', 'N/A')}")
                    st.markdown(f"**Degree:** {role.get('degree_requirement', 'Any')}")
                    st.markdown(f"**Field of Study:** {role.get('field_of_study', 'N/A')}")
                    st.markdown(f"**Experience:** {role.get('experience_years', 0)} years")
                    st.markdown(f"**Location:** {role.get('location', 'N/A')}")
                    st.markdown(f"**Remote:** {'Yes' if role.get('remote_option') == 'true' else 'No'}")
                    st.markdown(f"**Industry:** {role.get('industry_sector', 'N/A')}")
                    st.markdown(f"**Level:** {role.get('role_level', 'N/A')}")
                    
                    # Skills section
                    if 'skills' in role and role['skills']:
                        st.markdown("**Skills:**")
                        for skill in role['skills']:
                            if isinstance(skill, dict) and 'name' in skill:
                                importance = skill.get('importance', 'normal')
                                emoji = "🔴" if importance == "required" else "🟠" if importance == "preferred" else "🟢"
                                st.markdown(f"{emoji} {skill['name']}")
                
                with col2:
                    # Action buttons
                    if st.button("Edit", key=f"edit_{role['id']}"):
                        st.session_state.edit_role_id = role['id']
                        # Prepare form with existing data
                        prepare_edit_form(role)
                        # Switch to Add Role tab
                        st.rerun()
                    
                    if st.button("Delete", key=f"delete_{role['id']}"):
                        st.session_state.delete_role_id = role['id']
                        
    # Handle role deletion with confirmation
    if st.session_state.delete_role_id:
        if st.button(f"Confirm deletion of role {st.session_state.delete_role_id}"):
            success = neo4j_service.delete_role(st.session_state.delete_role_id)
            if success:
                st.success(f"Role {st.session_state.delete_role_id} deleted successfully!")
                st.session_state.delete_role_id = None
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to delete role")


def prepare_edit_form(role):
    """Prepare the form for editing with existing role data"""
    # Extract fields of study
    fields = []
    if 'fields_of_study' in role and isinstance(role['fields_of_study'], list):
        fields = role['fields_of_study']
    elif 'field_of_study' in role and role['field_of_study']:
        # Legacy format - convert to new format
        fields = [{
            "name": role['field_of_study'],
            "alternative_fields": "",
            "importance": "required"
        }]
    
    st.session_state.fields_of_study = fields if fields else [{"name": "", "alternative_fields": "", "importance": "required"}]
    
    # Extract required skills
    skills = []
    if 'skills' in role and isinstance(role['skills'], list):
        skills = [
            {
                "name": skill.get('name', ''),
                "alternative_names": "",
                "importance": skill.get('importance', 'required'),
                "minimum_years": 0
            }
            for skill in role['skills'] if isinstance(skill, dict) and 'name' in skill
        ]
    
    st.session_state.required_skills = skills if skills else [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]
    
    # Set other form fields
    for key in ['job_title', 'alternative_titles', 'degree_requirement', 'total_experience_years', 
                'location', 'industry_sector', 'role_level', 'keywords']:
        if key in role:
            st.session_state[key] = role[key]
    
    # Boolean field handling
    if 'remote_option' in role:
        st.session_state.remote_option = role['remote_option'] == 'true' if isinstance(role['remote_option'], str) else bool(role['remote_option'])


def add_role_form(neo4j_service):
    """Form for adding a new role or editing an existing one"""
    data_extraction_service = DataExtractionService()
    
    st.subheader("Role Details")
    
    # File uploader for job posting - outside the form
    st.markdown("#### Upload Job Description (Optional)")
    st.markdown("_Upload a job posting file to automatically extract role information_")
    
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])
    
    if uploaded_file:
        if st.button("Extract Job Data"):
            with st.spinner("Extracting data from job posting..."):
                # Extract text from the uploaded file
                text_content = asyncio.run(extract_text_from_uploaded_file(uploaded_file))
                
                if text_content:
                    # Extract job data from the text
                    job_data = asyncio.run(data_extraction_service.extract_job_posting_information_for_form(text_content))
                    
                    if job_data:
                        st.success("Data extracted successfully! Form pre-filled with extracted information.")
                        
                        # Initialize lists for fields of study and skills
                        fields_of_study = []
                        required_skills = []
                        
                        # Process fields of study
                        if hasattr(job_data, 'fields_of_study') and job_data.fields_of_study:
                            for field in job_data.fields_of_study:
                                fields_of_study.append({
                                    "name": field.name,
                                    "alternative_fields": field.alternative_fields,
                                    "importance": field.importance
                                })
                        
                        # Process required skills
                        if hasattr(job_data, 'required_skills') and job_data.required_skills:
                            for skill in job_data.required_skills:
                                required_skills.append({
                                    "name": skill.name,
                                    "alternative_names": skill.alternative_names,
                                    "importance": skill.importance,
                                    "minimum_years": skill.minimum_years
                                })
                        
                        # Update session state with extracted data
                        st.session_state.job_title = job_data.job_title
                        st.session_state.alternative_titles = job_data.alternative_titles
                        st.session_state.degree_requirement = job_data.degree_requirement
                        st.session_state.fields_of_study = fields_of_study if fields_of_study else [{"name": "", "alternative_fields": "", "importance": "required"}]
                        st.session_state.total_experience_years = job_data.total_experience_years
                        st.session_state.required_skills = required_skills if required_skills else [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]
                        st.session_state.location = job_data.location
                        st.session_state.remote_option = job_data.remote_option
                        st.session_state.industry_sector = job_data.industry_sector
                        st.session_state.role_level = job_data.role_level
                        st.session_state.keywords = job_data.keywords
                        
                        # Rerun to display updated form
                        st.rerun()
                    else:
                        st.error("Failed to extract job data. Please fill the form manually.")
                else:
                    st.error("Failed to extract text from the file. Please try another file or fill the form manually.")
    
    # Dynamic controls for Fields of Study - OUTSIDE the form
    st.subheader("Fields of Study")
    
    # Button to add more fields - OUTSIDE form
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Add Field of Study"):
            st.session_state.fields_of_study.append({"name": "", "alternative_fields": "", "importance": "required"})
            st.rerun()
    
    # Button to remove fields - OUTSIDE form
    for i, field in enumerate(st.session_state.fields_of_study):
        if i > 0:  # Don't allow removing the first field
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"Remove Field #{i+1}", key=f"remove_field_{i}"):
                    st.session_state.fields_of_study.pop(i)
                    st.rerun()
    
    # Dynamic controls for Skills - OUTSIDE the form
    st.subheader("Required Skills")
    
    # Button to add more skills - OUTSIDE form
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Add Skill"):
            st.session_state.required_skills.append({"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0})
            st.rerun()
    
    # Button to remove skills - OUTSIDE form
    for i, skill in enumerate(st.session_state.required_skills):
        if i > 0:  # Don't allow removing the first skill
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"Remove Skill #{i+1}", key=f"remove_skill_{i}"):
                    st.session_state.required_skills.pop(i)
                    st.rerun()
    
    # Now create the actual form - with NO buttons inside except submit
    with st.form("role_form"):
        # Basic role information
        job_title = st.text_input("Job Title", key="job_title", 
                                help="The main title of the position")
        
        alternative_titles = st.text_input("Alternative Titles (comma-separated)", key="alternative_titles", 
                                        help="Similar job titles separated by commas")
        
        # Education requirements
        col1, col2 = st.columns([1, 1])
        with col1:
            degree_requirement = st.selectbox("Minimum Degree Requirement", 
                                            ["any", "bachelor", "master", "phd"],
                                            key="degree_requirement")
        with col2:
            total_experience_years = st.number_input("Experience Required (Years)", 
                                                  min_value=0, value=0, key="total_experience_years")
        
        # Fields of Study - dynamic form inputs (no buttons)
        st.subheader("Fields of Study Details")
        
        # Display field inputs
        for i, field in enumerate(st.session_state.fields_of_study):
            st.markdown(f"**Field of Study {i+1}**")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.session_state.fields_of_study[i]["name"] = st.text_input(
                    "Field Name", value=field["name"], key=f"field_name_{i}")
            
            with col2:
                st.session_state.fields_of_study[i]["alternative_fields"] = st.text_input(
                    "Alternative Fields", value=field["alternative_fields"], key=f"field_alt_{i}")
            
            with col3:
                importance_options = ["required", "preferred", "nice-to-have"]
                st.session_state.fields_of_study[i]["importance"] = st.selectbox(
                    "Importance", importance_options, 
                    index=importance_options.index(field["importance"]) if field["importance"] in importance_options else 0,
                    key=f"field_importance_{i}")
            
            st.markdown("---")
        
        # Skills requirements - dynamic form inputs (no buttons)
        st.subheader("Skills Details")
        
        # Display skill inputs
        for i, skill in enumerate(st.session_state.required_skills):
            st.markdown(f"**Skill {i+1}**")
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.session_state.required_skills[i]["name"] = st.text_input(
                    "Skill Name", value=skill["name"], key=f"skill_name_{i}")
            
            with col2:
                st.session_state.required_skills[i]["alternative_names"] = st.text_input(
                    "Alternative Names", value=skill["alternative_names"], key=f"skill_alt_{i}")
            
            col3, col4 = st.columns([1, 1])
            with col3:
                importance_options = ["required", "preferred", "nice-to-have"]
                st.session_state.required_skills[i]["importance"] = st.selectbox(
                    "Importance", importance_options,
                    index=importance_options.index(skill["importance"]) if skill["importance"] in importance_options else 0,
                    key=f"skill_importance_{i}")
            
            with col4:
                st.session_state.required_skills[i]["minimum_years"] = st.number_input(
                    "Minimum Years", min_value=0, value=skill["minimum_years"], key=f"skill_years_{i}")
            
            st.markdown("---")
        
        # Location and other info
        st.subheader("Additional Information")
        
        location = st.text_input("Location", key="location", 
                              help="The physical location of the job")
        
        remote_option = st.checkbox("Remote Work Option", key="remote_option",
                                 help="Check if the role can be performed remotely")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            industry_sector = st.text_input("Industry Sector", key="industry_sector",
                                         help="The industry this role belongs to")
        
        with col2:
            role_level = st.text_input("Role Level", key="role_level",
                                    help="Seniority level (e.g., junior, senior)")
        
        keywords = st.text_input("Additional Keywords (comma-separated)", key="keywords",
                              help="Other relevant keywords for matching candidates")
        
        # Submit button - the only button inside the form
        submit_text = "Update Role" if st.session_state.edit_role_id else "Add Role"
        submit = st.form_submit_button(submit_text)
        
        if submit:
            # Validate form
            validation_errors = []
            if not job_title:
                validation_errors.append("Job title is required")
            
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                # Process fields of study - remove empty entries
                fields_of_study = [f for f in st.session_state.fields_of_study 
                                 if f["name"].strip()]
                
                # Process required skills - remove empty entries
                required_skills = [s for s in st.session_state.required_skills 
                                 if s["name"].strip()]
                
                # Generate a unique ID if adding a new role
                role_id = st.session_state.edit_role_id if st.session_state.edit_role_id else f"posting_{uuid.uuid4().hex[:8]}"
                
                # Save to Neo4j
                try:
                    success = neo4j_service.add_role(
                        role_id=role_id,
                        job_title=job_title,
                        alternative_titles=st.session_state.alternative_titles,
                        degree_requirement=degree_requirement,
                        fields_of_study=fields_of_study,
                        total_experience_years=total_experience_years,
                        required_skills=required_skills,
                        location=location,
                        remote_option=remote_option,
                        industry_sector=industry_sector,
                        role_level=role_level,
                        keywords=keywords
                    )
                    if success:
                        st.success("Role updated successfully!")
                        # Consider resetting the form or redirecting
                    else:
                        st.error("Failed to update role - database operation unsuccessful")
                except Exception as e:
                    st.error(f"Error updating role: {str(e)}")


def reset_form_fields():
    """Reset the form fields to default values"""
    for key in st.session_state.keys():
        if key in ['job_title', 'alternative_titles', 'location', 'industry_sector', 'role_level', 'keywords']:
            st.session_state[key] = ""
        elif key == 'total_experience_years':
            st.session_state[key] = 0
        elif key == 'degree_requirement':
            st.session_state[key] = "any"
        elif key == 'remote_option':
            st.session_state[key] = False
    
    st.session_state.fields_of_study = [{"name": "", "alternative_fields": "", "importance": "required"}]
    st.session_state.required_skills = [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]