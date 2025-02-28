from app.services.neo4j_service import Neo4jService
from services.data_extraction_service import DataExtractionService
import streamlit as st
import pandas as pd
import time
import uuid
import asyncio
import io


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
            
            # Display roles as a data editor without selection_mode
            edited_df = st.data_editor(
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
                key="roles_table"
            )
            
            # Add a selectbox for role selection instead of using data_editor selection
            if len(display_df) > 0:
                st.write("---")
                st.subheader("Select a role to manage")
                
                # Create options for the selectbox with descriptive labels
                role_options = display_df['ID'].tolist()
                role_labels = {row['ID']: f"{row['Job Title']} (ID: {row['ID']})" for _, row in display_df.iterrows()}
                
                selected_role_id = st.selectbox(
                    "Choose a role:",
                    options=role_options,
                    format_func=lambda x: role_labels[x]
                )
                
                # Get the selected role data
                if selected_role_id:
                    selected_role = display_df[display_df['ID'] == selected_role_id].iloc[0].to_dict()
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
                                
                                # Add fields for industry sector and role level
                                col1, col2 = st.columns(2)
                                with col1:
                                    industry_sector = st.text_input(
                                        "Industry Sector",
                                        value=current_role.get('industry_sector', '')
                                    )
                                
                                with col2:
                                    role_level = st.text_input(
                                        "Role Level",
                                        value=current_role.get('role_level', '')
                                    )
                                
                                # Format skills with importance and required status
                                skills_formatted = current_role['required_skills']
                                if 'skills' in current_role and isinstance(current_role['skills'], list):
                                    skills_formatted = ""
                                    for i, skill in enumerate(current_role['skills']):
                                        if skill['name']:  # Only include if name exists
                                            if i > 0:
                                                skills_formatted += ", "
                                            skills_formatted += f"{skill['name']}:{skill.get('importance', 5)}:{str(skill.get('is_required', True)).lower()}"
                                
                                st.subheader("Skills")
                                st.info("For each skill, you can specify importance (1-10) and whether it's required. Format: Skill:importance:required")
                                st.caption("Example: Python:8:true, SQL:5:false")
                                
                                required_skills = st.text_area(
                                    "Required Skills (formatted)",
                                    value=skills_formatted
                                )
                                
                                # Visual skill builder for editing
                                with st.expander("Visual Skill Builder"):
                                    skill_name = st.text_input("Skill Name", key="edit_form_skill_name")
                                    skill_importance = st.slider("Importance", 1, 10, 5, key="edit_form_skill_importance")
                                    skill_required = st.checkbox("Required Skill", True, key="edit_form_skill_required")
                                    
                                    add_skill = st.form_submit_button("Add Skill to List")
                                    if add_skill and skill_name:
                                        new_skill = f"{skill_name}:{skill_importance}:{str(skill_required).lower()}"
                                        if required_skills:
                                            required_skills += f", {new_skill}"
                                        else:
                                            required_skills = new_skill
                                
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
                                                required_skills, location_remote,
                                                industry_sector, role_level
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
        
        # Add file uploader for job description documents
        uploaded_file = st.file_uploader(
            "Upload job description document", 
            type=["pdf", "docx", "txt","doc"],
            help="Upload a job description to auto-fill the form"
        )
        
        # Initialize form fields as session state variables if not already present
        if 'job_form_data' not in st.session_state:
            st.session_state.job_form_data = {
                "job_title": "",
                "degree_requirement": 0,  # Index for selectbox
                "experience_years": 0,
                "field_of_study": "",
                "location_remote": "",
                "industry_sector": "",
                "role_level": "",
                "required_skills": ""
            }
        
        # Process uploaded file if present
        if uploaded_file:
            with st.spinner("Extracting information from job description..."):
                # Read file
                file_bytes = uploaded_file.read()
                file_name = uploaded_file.name
                
                # Handle different file types
                # Find the file handling section around line 269
                # Handle different file types
                text_content = ""
                if file_name.lower().endswith('.txt'):
                    text_content = file_bytes.decode('utf-8')
                elif file_name.lower().endswith('.pdf'):
                    # You'll need pdfplumber or PyPDF2 imported at the top
                    import pdfplumber  # Make sure this is installed
                    try:
                        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                            text_content = "\n".join([page.extract_text() or "" for page in pdf.pages])
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
                elif file_name.lower().endswith('.docx'):
                    # You'll need python-docx imported at the top
                    import docx  # Make sure this is installed
                    try:
                        doc = docx.Document(io.BytesIO(file_bytes))
                        text_content = "\n".join([para.text for para in doc.paragraphs])
                    except Exception as e:
                        st.error(f"Error reading DOCX: {e}")
                elif file_name.lower().endswith('.doc'):
                    # Option 1: Using textract (most versatile)
                    try:
                        import textract
                        # Save file temporarily to process with textract
                        temp_path = f"/tmp/{file_name}"
                        with open(temp_path, "wb") as f:
                            f.write(file_bytes)
                        text_content = textract.process(temp_path).decode('utf-8')
                        import os
                        os.remove(temp_path)  # Clean up temp file
                    except ImportError:
                        st.error("textract package not installed. Please install it using: pip install textract")
                    except Exception as e:
                        st.error(f"Error reading DOC file: {e}")

                if text_content:
                    # Extract information using DataExtractionService
                    extraction_service = DataExtractionService()
                    if extraction_service:
                        # Run the extraction asynchronously
                        extracted_data = asyncio.run(
                            extraction_service.extract_job_posting_information_for_form(text_content)
                        )
                        if extracted_data:
                            # Update form data in session state - access properties directly, not as a dictionary
                            st.session_state.job_form_data = {
                                "job_title": extracted_data.job_title,
                                "degree_requirement": ["Any", "Bachelor's", "Master's", "PhD"].index(
                                    extracted_data.degree_requirement
                                ),
                                "experience_years": extracted_data.experience_years,
                                "field_of_study": extracted_data.field_of_study,
                                "location_remote": extracted_data.location_remote,
                                "industry_sector": extracted_data.industry_sector,
                                "role_level": extracted_data.role_level,
                                "required_skills": extracted_data.required_skills
                            }
                            st.success("Form auto-filled from job description! Please review and adjust as needed.")
                        
                        else:
                            st.warning("Couldn't extract information from the document. Please fill the form manually.")
                    else:
                        st.error("Extraction service not available. Please initialize the service.")
        
        with st.form("add_role_form"):
            job_title = st.text_input(
                "Job Title*", 
                placeholder="e.g. Software Engineer",
                value=st.session_state.job_form_data.get("job_title", "")
            )
            
            col1, col2 = st.columns(2)
            with col1:
                degree_requirement = st.selectbox(
                    "Degree Requirement", 
                    ["Any", "Bachelor's", "Master's", "PhD"],
                    index=st.session_state.job_form_data.get("degree_requirement", 0),
                    help="Minimum education requirement"
                )
                
                experience_years = st.number_input(
                    "Years of Experience", 
                    min_value=0, 
                    value=st.session_state.job_form_data.get("experience_years", 0),
                    help="Minimum years of experience required"
                )
            
            with col2:
                field_of_study = st.text_input(
                    "Field of Study",
                    placeholder="e.g. Computer Science, Engineering",
                    value=st.session_state.job_form_data.get("field_of_study", ""),
                    help="Comma separated for multiple fields"
                )
                
                location_remote = st.text_input(
                    "Location/Remote",
                    placeholder="e.g. New York / Remote",
                    value=st.session_state.job_form_data.get("location_remote", ""),
                    help="Job location or remote policy"
                )
            
            # Add new fields for industry sector and role level
            col1, col2 = st.columns(2)
            with col1:
                industry_sector = st.text_input(
                    "Industry Sector",
                    placeholder="e.g. Technology, Finance",
                    value=st.session_state.job_form_data.get("industry_sector", ""),
                    help="Industry the role belongs to"
                )
            
            with col2:
                role_level = st.text_input(
                    "Role Level",
                    placeholder="e.g. Junior, Senior, Manager",
                    value=st.session_state.job_form_data.get("role_level", ""),
                    help="Seniority level of the role"
                )
            
            # Improved skill input section with importance and required flags
            st.subheader("Skills")
            st.info("For each skill, you can specify importance (1-10) and whether it's required. Format: Skill:importance:required")
            st.caption("Example: Python:8:true, SQL:5:false")
            
            required_skills = st.text_area(
                "Required Skills",
                placeholder="e.g. Python:8:true, SQL:5:false, JavaScript:7:true",
                value=st.session_state.job_form_data.get("required_skills", ""),
                help="Format: Skill:importance:required"
            )
            
            # Add a visual skill builder as an alternative
            with st.expander("Visual Skill Builder"):
                skill_name = st.text_input("Skill Name", key="add_form_skill_name")
                skill_importance = st.slider("Importance", 1, 10, 5, key="add_form_skill_importance")
                skill_required = st.checkbox("Required Skill", True, key="add_form_skill_required")
                
                add_skill = st.form_submit_button("Add Skill to List")
                if add_skill and skill_name:
                    new_skill = f"{skill_name}:{skill_importance}:{str(skill_required).lower()}"
                    if required_skills:
                        required_skills += f", {new_skill}"
                    else:
                        required_skills = new_skill
            
            # Clear auto-filled data after submission
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
                            experience_years, required_skills, location_remote,
                            industry_sector, role_level
                        )
                        if success:
                            # Clear form data on successful submission
                            st.session_state.job_form_data = {
                                "job_title": "",
                                "degree_requirement": 0,
                                "experience_years": 0,
                                "field_of_study": "",
                                "location_remote": "",
                                "industry_sector": "",
                                "role_level": "",
                                "required_skills": ""
                            }
                            st.toast("✅ Role added successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to add the role")