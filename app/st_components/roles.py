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
    
    if 'required_experiences' not in st.session_state:
        st.session_state.required_experiences = [{"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0}]
    
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
        st.info("No roles found in the database. Create one using the 'Add Role' tab.")
        return
    
    # Create a search bar for filtering roles
    search_query = st.text_input("🔍 Search roles by title, skills, or industry", placeholder="e.g. developer, python, finance...")
    
    # Filter roles if search query is provided
    if search_query:
        search_terms = search_query.lower().split()
        filtered_roles = []
        
        for role in roles:
            # Search in various fields
            searchable_text = " ".join([
                str(role.get("job_title", "")), 
                str(role.get("industry_sector", "")),
                str(role.get("keywords", "")),
                " ".join([skill.get("name", "") for skill in role.get("skills", []) if isinstance(skill, dict)])
            ]).lower()
            
            if any(term in searchable_text for term in search_terms):
                filtered_roles.append(role)
        
        roles = filtered_roles
    
    # Display a message if no roles match the search
    if search_query and not roles:
        st.warning(f"No roles found matching '{search_query}'")
        return
    
    # Display roles count
    st.write(f"Displaying {len(roles)} roles")
    
    # Create a modern data table with expandable details
    for i, role in enumerate(roles):
        with st.container():
            # Create a card-like appearance with a border
            with st.expander(f"**{role.get('job_title', 'Untitled Role')}**", expanded=False):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                # Main information column
                with col1:
                    # Basic role information
                    st.markdown(f"**ID**: `{role.get('id', 'N/A')}`")
                    st.markdown(f"**Required Experience**: {role.get('experience_years', 0)} years")
                    
                    # Display the degree requirement with an appropriate icon
                    degree = role.get('degree_requirement', 'any')
                    degree_icon = {
                        "any": "📜", 
                        "bachelor": "🎓", 
                        "master": "🎓🎓", 
                        "phd": "🎓🎓🎓"
                    }.get(degree, "📜")
                    st.markdown(f"**Degree**: {degree_icon} {degree.capitalize()}")
                    
                    # Display location info with optional remote badge
                    location_text = role.get('location', 'Not specified')
                    remote = role.get('remote_option')
                    if remote and remote.lower() == 'true':
                        st.markdown(f"**Location**: {location_text} 🌐 *Remote available*")
                    else:
                        st.markdown(f"**Location**: {location_text}")
                    
                    # Industry and role level
                    st.markdown(f"**Industry**: {role.get('industry_sector', 'Not specified')}")
                    st.markdown(f"**Level**: {role.get('role_level', 'Not specified')}")
                
                # Skills and fields column
                with col2:
                    # Display required skills with colored badges
                    st.markdown("**Required Skills:**")
                    
                    if 'skills' in role and role['skills']:
                        skills_html = []
                        
                        for skill in role['skills']:
                            if isinstance(skill, dict) and 'name' in skill:
                                importance = skill.get('importance', 'normal')
                                color = "#f63366" if importance == "required" else "#ff9f36" if importance == "preferred" else "#09ab3b"
                                min_years = f"{skill.get('minimum_years', 0)}+ yrs" if skill.get('minimum_years', 0) > 0 else ""
                                
                                skill_badge = f"""
                                <span style="background-color:{color};
                                             color:white;
                                             padding:2px 6px;
                                             margin:2px;
                                             border-radius:10px;
                                             font-size:0.8em;
                                             display:inline-block;">
                                    {skill['name']} {min_years}
                                </span>
                                """
                                skills_html.append(skill_badge)
                        
                        st.markdown(''.join(skills_html), unsafe_allow_html=True)
                    else:
                        st.text("No skills specified")
                    
                    # Fields of study
                    st.markdown("**Fields of Study:**")
                    if 'fields_of_study' in role and role['fields_of_study']:
                        fields_html = []
                        
                        for field in role['fields_of_study']:
                            if isinstance(field, dict) and 'name' in field:
                                importance = field.get('importance', 'normal')
                                color = "#1e3d59" if importance == "required" else "#457b9d" if importance == "preferred" else "#77abb7"
                                
                                field_badge = f"""
                                <span style="background-color:{color};
                                             color:white;
                                             padding:2px 6px;
                                             margin:2px;
                                             border-radius:10px;
                                             font-size:0.8em;
                                             display:inline-block;">
                                    {field['name']}
                                </span>
                                """
                                fields_html.append(field_badge)
                        
                        st.markdown(''.join(fields_html), unsafe_allow_html=True)
                    else:
                        st.text("No fields specified")
                    
                    # Display required experiences
                    st.markdown("**Required Experiences:**")
                    if 'required_experiences' in role and role['required_experiences']:
                        experiences_html = []
                        
                        for experience in role['required_experiences']:
                            if isinstance(experience, dict) and 'role' in experience:
                                importance = experience.get('importance', 'normal')
                                color = "#6a0dad" if importance == "required" else "#9370db" if importance == "preferred" else "#b19cd9"
                                years = f"{experience.get('minimum_years', 0)}+ yrs" if experience.get('minimum_years', 0) > 0 else ""
                                
                                exp_badge = f"""
                                <span style="background-color:{color};
                                             color:white;
                                             padding:2px 6px;
                                             margin:2px;
                                             border-radius:10px;
                                             font-size:0.8em;
                                             display:inline-block;">
                                    {experience['role']} {years}
                                </span>
                                """
                                experiences_html.append(exp_badge)
                        
                        st.markdown(''.join(experiences_html), unsafe_allow_html=True)
                    else:
                        st.text("No specific experience requirements")
                
                # Action buttons column
                with col3:
                    # Edit button
                    if st.button("✏️ Edit", key=f"edit_{role['id']}_{i}", use_container_width=True):
                        st.session_state.edit_role_id = role['id']
                        # Prepare form with existing data
                        prepare_edit_form(role)
                        # Switch to Add Role tab
                        st.rerun()
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{role['id']}_{i}", use_container_width=True):
                        st.session_state.delete_role_id = role['id']
                        st.rerun()
                
                # Show creation/update timestamp
                created_at = role.get('created_at', 'Unknown')
                updated_at = role.get('updated_at')
                
                if updated_at:
                    st.caption(f"Last updated: {updated_at}")
                else:
                    st.caption(f"Created: {created_at}")
            
            # Add some spacing between cards
            st.write("")
    
    # Handle role deletion with confirmation dialog
    if st.session_state.delete_role_id:
        st.warning(f"Are you sure you want to delete this role? This action cannot be undone.")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Yes, delete role", type="primary", use_container_width=True):
                success = neo4j_service.delete_role(st.session_state.delete_role_id)
                if success:
                    st.success(f"Role deleted successfully!")
                    st.session_state.delete_role_id = None
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to delete role")
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.delete_role_id = None
                st.rerun()

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
    
    # Extract required experiences
    experiences = []
    if 'required_experiences' in role and isinstance(role['required_experiences'], list):
        experiences = [
            {
                "role": exp.get('role', ''),
                "alternative_roles": exp.get('alternative_roles', ''),
                "importance": exp.get('importance', 'required'),
                "minimum_years": exp.get('minimum_years', 0)
            }
            for exp in role['required_experiences'] if isinstance(exp, dict) and 'role' in exp
        ]
    
    st.session_state.required_experiences = experiences if experiences else [{"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0}]
    
    # Set other form fields
    for key in ['job_title', 'alternative_titles', 'degree_requirement', 'total_experience_years', 
                'location_city', 'industry_sector', 'role_level', 'keywords']:
        if key in role:
            st.session_state[key] = role[key]
    
    # Boolean field handling
    if 'remote_option' in role:
        st.session_state.remote_option = role['remote_option'] == 'true' if isinstance(role['remote_option'], str) else bool(role['remote_option'])


def add_role_form(neo4j_service):
    """Form for adding a new role or editing an existing one"""
    data_extraction_service = DataExtractionService()
    
    # Initialize location_city in session state if not present
    if 'location_city' not in st.session_state:
        st.session_state.location_city = ""
    
    # Initialize required_experiences in session state if not present
    if 'required_experiences' not in st.session_state:
        st.session_state.required_experiences = [{"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0}]
        
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
                        required_experiences = []
                        
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
                        
                        # Process required experiences
                        if hasattr(job_data, 'required_experiences') and job_data.required_experiences:
                            for experience in job_data.required_experiences:
                                required_experiences.append({
                                    "role": experience.role,
                                    "alternative_roles": experience.alternative_roles,
                                    "importance": experience.importance,
                                    "minimum_years": experience.minimum_years
                                })
                        
                        # Update session state with extracted data
                        st.session_state.job_title = job_data.job_title
                        st.session_state.alternative_titles = job_data.alternative_titles
                        st.session_state.degree_requirement = job_data.degree_requirement
                        st.session_state.fields_of_study = fields_of_study if fields_of_study else [{"name": "", "alternative_fields": "", "importance": "required"}]
                        st.session_state.total_experience_years = job_data.total_experience_years
                        st.session_state.required_skills = required_skills if required_skills else [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]
                        st.session_state.required_experiences = required_experiences if required_experiences else [{"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0}]
                        st.session_state.location_city = job_data.location_city
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
    
    # Dynamic controls for Experience Requirements - OUTSIDE the form
    st.subheader("Experience Requirements")
    
    # Button to add more experience requirements - OUTSIDE form
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Add Experience Requirement"):
            st.session_state.required_experiences.append({"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0})
            st.rerun()
    
    # Button to remove experiences - OUTSIDE form
    for i, exp in enumerate(st.session_state.required_experiences):
        if i > 0:  # Don't allow removing the first experience
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"Remove Experience #{i+1}", key=f"remove_exp_{i}"):
                    st.session_state.required_experiences.pop(i)
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
        
        # Experience Requirements - dynamic form inputs (no buttons)
        st.subheader("Experience Requirements Details")
        
        # Display experience inputs
        for i, exp in enumerate(st.session_state.required_experiences):
            st.markdown(f"**Experience Requirement {i+1}**")
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.session_state.required_experiences[i]["role"] = st.text_input(
                    "Role/Position", value=exp["role"], key=f"exp_role_{i}")
            
            with col2:
                st.session_state.required_experiences[i]["alternative_roles"] = st.text_input(
                    "Alternative Roles", value=exp["alternative_roles"], key=f"exp_alt_{i}")
            
            col3, col4 = st.columns([1, 1])
            with col3:
                importance_options = ["required", "preferred", "nice-to-have"]
                st.session_state.required_experiences[i]["importance"] = st.selectbox(
                    "Importance", importance_options,
                    index=importance_options.index(exp["importance"]) if exp["importance"] in importance_options else 0,
                    key=f"exp_importance_{i}")
            
            with col4:
                st.session_state.required_experiences[i]["minimum_years"] = st.number_input(
                    "Minimum Years", min_value=0, value=exp["minimum_years"], key=f"exp_years_{i}")
            
            st.markdown("---")
        
        # Location and other info
        st.subheader("Additional Information")
        
        # Removed the location field
        location_city = st.text_input("City", key="location_city",
                                   help="The city where the job is located")
        
        # Add remaining fields
        col1, col2 = st.columns([1, 1])
        with col1:
            remote_option = st.checkbox("Remote Work Available", key="remote_option",
                                    help="Check if this position allows remote work")
        
        industry_sector = st.text_input("Industry Sector", key="industry_sector",
                                    help="The industry this role belongs to (e.g., healthcare, tech, finance)")
        
        role_level = st.text_input("Role Level", key="role_level",
                                help="Seniority level (e.g., junior, senior, manager)")
        
        keywords = st.text_area("Keywords (comma-separated)", key="keywords",
                             help="Additional keywords for improved matching with candidates")

        # Submit button - THIS IS THE CRITICAL PART THAT WAS MISSING
        submit_label = "Update Role" if st.session_state.edit_role_id else "Create Role"
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
        
        # Handle form submission
        if submitted:
            # Define action variable BEFORE any operation that might fail
            action = "update" if st.session_state.edit_role_id else "create"
            
            # Generate a unique ID for new roles or use existing ID for edits
            role_id = st.session_state.edit_role_id if st.session_state.edit_role_id else f"role_{uuid.uuid4().hex[:8]}"
            
            # Filter out empty fields
            fields_of_study_filtered = [
                field for field in st.session_state.fields_of_study 
                if field["name"].strip()
            ]
            
            required_skills_filtered = [
                skill for skill in st.session_state.required_skills 
                if skill["name"].strip()
            ]
            
            required_experiences_filtered = [
                exp for exp in st.session_state.required_experiences 
                if exp["role"].strip()
            ]
            
            # Call Neo4j service to add/update role
            success = neo4j_service.add_role(
                role_id=role_id,
                job_title=job_title,
                alternative_titles=alternative_titles,
                degree_requirement=degree_requirement,
                fields_of_study=fields_of_study_filtered,
                total_experience_years=total_experience_years,
                required_skills=required_skills_filtered,
                required_experiences=required_experiences_filtered,
                location_city=location_city,
                remote_option=remote_option,
                industry_sector=industry_sector,
                role_level=role_level,
                keywords=keywords
            )
            
            if success:
                past_tense_action = "updated" if st.session_state.edit_role_id else "created"
                st.success(f"Role {past_tense_action} successfully!")
                
                # Clear edit state and form fields
                st.session_state.edit_role_id = None
                st.session_state.fields_of_study = [{"name": "", "alternative_fields": "", "importance": "required"}]
                st.session_state.required_skills = [{"name": "", "alternative_names": "", "importance": "required", "minimum_years": 0}]
                st.session_state.required_experiences = [{"role": "", "alternative_roles": "", "importance": "required", "minimum_years": 0}]
                
                # Delay for the success message to be seen
                time.sleep(1)
                
                # Rerun to refresh the page
                st.rerun()
            else:
                st.error(f"Failed to {action} role. Please try again.")