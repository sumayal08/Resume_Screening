import streamlit as st
import pymongo
from datetime import datetime
import base64
from pymongo.errors import ServerSelectionTimeoutError
from pymongo import MongoClient
#MONGO_URI =  st.secrets.get("MONGO_URI", "mongodb://localhost:27017/")
#client = pymongo.MongoClient(MONGO_URI,serverSelectionTimeoutMS=5000)
# MongoDB connection
#client = pymongo.MongoClient("mongodb://localhost:27017/")
client = MongoClient(st.secrets["mongodb"]["MONGO_URI"])
db = client["resume_db"]
hr_collection = db["hr_requirements"]
resumes_collection = db["resumes"]

# Custom CSS for improved styling
st.markdown("""
<style>
    /* Main Application Styling */
    .stApp {
    background: #f5faf7;
    background-image: radial-gradient(#e0ede6 1px, transparent 0);
    background-size: 20px 20px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
 
    
    /* Header Styling */
    .dashboard-header {
        background-color: #2c3e50;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .dashboard-header h1 {
        margin: 0;
        color: white;
        font-size: 28px;
        font-weight: 600;
    }
    
    /* Card Styling */
    .section-card {
        background-color: white;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        border: 1px solid #eaecef;
    }
    
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #3498db;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        height: 100%;
    }
    
    .metric-card-success {
        border-left: 5px solid #2ecc71;
    }
    
    .metric-card-warning {
        border-left: 5px solid #f39c12;
    }
    
    /* Candidate Cards */
    .candidate-card {
        background-color: white;
        border-radius: 10px;
        padding: 24px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #eaecef;
    }
    
    .candidate-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 15px;
        border-bottom: 1px solid #eaecef;
    }
    
    /* Buttons */
    .primary-button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    
    .primary-button:hover {
        background-color: #2980b9;
    }
    
    .stButton>button {
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 500;
        background-color: #3498db;
        color: white;
        border: none;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #2980b9;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Progress Bars */
    .stProgress>div>div>div>div {
        background-color: #3498db !important;
    }
    
    /* Score and Tags */
    .score-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }
    
    .score-badge-high {
        background-color: #e3fcef;
        color: #1b8a59;
    }
    
    .score-badge-medium {
        background-color: #fff8e6;
        color: #b7791f;
    }
    
    .score-badge-low {
        background-color: #fee2e2;
        color: #b91c1c;
    }
    
    .skill-tag {
        display: inline-block;
        background-color: #e9f2fe;
        color: #2779bd;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        margin-right: 5px;
        margin-bottom: 5px;
        font-weight: 500;
    }
    
    /* Section Headers */
    .section-header {
        color: #2c3e50;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid #eaecef;
    }
    
    /* Form Elements */
    .stSelectbox>div>div {
        border-radius: 6px !important;
    }
    
    .stTextArea>div>div {
        border-radius: 6px !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #2c3e50;
        background-color: #f8fafc;
        border-radius: 6px;
    }
    
    /* Data Tables */
    .dataframe {
        border-radius: 10px !important;
        overflow: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# Position options
POSITION_OPTIONS = [
    "AI Engineer", "AI Researcher", "AR/VR Developer", "Blockchain Developer",
    "Business Analyst", "Cloud Architect", "Cloud Engineer", "Content Writer",
    "Cybersecurity Analyst", "Data Analyst",
    "Data Architect", "Data Engineer", "Data Scientist", "Database Administrator",
    "DevOps Engineer", "Digital Marketing Specialist", "E-commerce Specialist",
    "Full Stack Developer", "Game Developer", "Graphic Designer",
    "Human Resources Specialist", "IT Support Specialist", "Machine Learning Engineer",
    "Mobile App Developer", "Network Engineer", "Product Manager", "Project Manager",
    "QA Engineer", "Robotics Engineer", "Software Developer", "Software Engineer",
    "System Administrator", "UI Designer", "UI Engineer",  "UX Designer"
]

# Initialize current requirements if none exist
if hr_collection.count_documents({"is_active": True}) == 0:
    hr_collection.insert_one({
        "position": "Data Scientist",
        "job_description": "We are seeking a Data Scientist...",
        "created_at": datetime.now(),
        "is_active": True
    })

# Page header
st.markdown("""
<div class="dashboard-header">
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
        <circle cx="9" cy="7" r="4"></circle>
        <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
    <h1>HR Recruitment Dashboard</h1>
</div>
""", unsafe_allow_html=True)

# Dashboard summary cards
col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
with col_metrics1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total Resumes", resumes_collection.count_documents({}))
    st.markdown('</div>', unsafe_allow_html=True)
with col_metrics2:
    st.markdown('<div class="metric-card metric-card-success">', unsafe_allow_html=True)
    st.metric("Suitable Candidates", resumes_collection.count_documents({"is_suitable": True}))
    st.markdown('</div>', unsafe_allow_html=True)
with col_metrics3:
    st.markdown('<div class="metric-card metric-card-warning">', unsafe_allow_html=True)
    st.metric("Positions", len(resumes_collection.distinct("position")))
    st.markdown('</div>', unsafe_allow_html=True)

# HR Requirements Section
with st.container():
    #st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h3 class="section-header">🎯 Set Job Requirements</h3>', unsafe_allow_html=True)
    with st.form("HR form"):
        #current_req = hr_collection.find_one({"is_active": True})
        #default_position = current_req["position"] if current_req else POSITION_OPTIONS[0]
        #default_desc = current_req["job_description"] if current_req else ""
        
        position = st.selectbox(
            "Position",
            options=POSITION_OPTIONS,
            index=0 
        )
        
        job_description = st.text_area(
            "Job Description",
            value="",  # Empty by default
            height=200,
            placeholder="Enter the job responsibilities, requirements, and qualifications..."
        )
        
        submitted = st.form_submit_button("Save Requirements", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if submitted:
    try:
        hr_collection.update_many(
            {"is_active": True},
            {"$set": {"is_active": False}}
        )
        
        hr_collection.insert_one({
            "position": position.strip().lower(),
            "job_description": job_description,
            "created_at": datetime.now(),
            "is_active": True
        })
        st.success("✅ Requirements saved successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Get current requirement
current_req = hr_collection.find_one({"is_active": True})
if current_req:
    st.markdown(f"""
    <div style="background-color: #ebf5fe; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #2779bd;">📢 Currently Hiring For: {current_req['position'].upper()}</h4>
        <button id="view-details" onclick="this.nextElementSibling.style.display='block';this.style.display='none';" 
                style="background: none; border: none; color: #3498db; cursor: pointer; padding: 0; font-weight: 500;">
            View Job Details
        </button>
        <div style="display: none; margin-top: 10px; padding: 15px; background-color: white; border-radius: 6px;">
            {current_req.get('job_description', 'No additional details').replace('\n', '<br>')}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Candidate search button with better styling
if st.button("🔍 Find Suitable Candidates", type="primary", use_container_width=True):
    if current_req:
        query = {
            "position": current_req["position"], 
            "is_suitable": True, 
            "llm_score": {"$exists": True}
        }

        suitable_resumes = list(resumes_collection.find(query).sort("llm_score", pymongo.DESCENDING))

        if suitable_resumes:
            #st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(f'<h3 class="section-header">🏆 Top Candidates for {current_req["position"].title()}</h3>', unsafe_allow_html=True)
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Total Candidates", len(suitable_resumes))
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                avg_score = sum(resume.get('llm_score', 0) for resume in suitable_resumes) / len(suitable_resumes)
                st.metric("Average Match Score", f"{avg_score:.1f}/100")
                st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                top_score = max(resume.get('llm_score', 0) for resume in suitable_resumes)
                st.metric("Top Match Score", f"{top_score}/100")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Candidate table
            table_data = []
            for resume in suitable_resumes:
                score = resume.get('llm_score', 0)
                score_class = "high" if score >= 80 else "medium" if score >= 60 else "low"
                
                table_data.append({
                    "Rank": len(table_data)+1,
                    "Name": resume.get('name', 'N/A'),
                    "Score": score,
                    "Email": resume.get('email', 'N/A'),
                    "Phone": resume.get('phone', 'N/A'),
                    "Education": resume.get('education', 'N/A').split('\n')[0][:50] + "..." if resume.get('education') else 'N/A',
                    "Key Skills": resume.get('skills', 'N/A'),
                    "Score_Display": f"{score}/100",
                    "_id": str(resume.get('_id', ''))
                })
            
            st.markdown('<div style="background-color: white; padding: 2px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">', unsafe_allow_html=True)
            st.dataframe(
                data=table_data,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", width="small"),
                    "Name": st.column_config.TextColumn("Candidate", width="medium"),
                    "Score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=100, format="%d"),
                    "Score_Display": st.column_config.Column("Score", width="small"),
                    "Email": st.column_config.TextColumn("Email", width="large"),
                    "Phone": st.column_config.TextColumn("Phone", width="small"),
                    "Education": st.column_config.TextColumn("Education", width="large"),
                    "Key Skills": st.column_config.TextColumn("Skills", width="large"),
                    "_id": None
                },
                hide_index=True,
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Candidate detailed profiles
            st.markdown('<h3 class="section-header" style="margin-top: 3px;">👤 Candidate Profiles</h3>', unsafe_allow_html=True)
            
            for resume in suitable_resumes:
                score = resume.get('llm_score', 0)
                score_class = "high" if score >= 80 else "medium" if score >= 60 else "low"
                
                with st.expander(f"{resume.get('name', 'N/A')} - {score}/100"):
                    #st.markdown('<div class="candidate-card">', unsafe_allow_html=True)
                    
                    # Candidate header
                    st.markdown(f"""
                    <div class="candidate-header">
                        <div>
                            <h3 style="margin:0; font-size: 20px;">{resume.get('name', 'N/A')}</h3>
                            <p style="margin:5px 0 0 0; color: #64748b;">{resume.get('experience', 'N/A').split('\n')[0][:50]}</p>
                        </div>
                        <span class='score-badge score-badge-{score_class}'>{score}/100</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Profile content in two columns
                    col_left, col_right = st.columns([2, 1])
                    
                    with col_left:
                        # Contact Information
                        st.markdown('<p style="color: #64748b; font-weight: 600; margin-bottom: 5px;">CONTACT INFORMATION</p>', unsafe_allow_html=True)
                        col_contact1, col_contact2 = st.columns(2)
                        with col_contact1:
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2">
                                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                                    <polyline points="22,6 12,13 2,6"></polyline>
                                </svg>
                                {resume.get('email', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_contact2:
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2">
                                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                                </svg>
                                {resume.get('phone', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Experience
                        st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">WORK EXPERIENCE</p>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px;">
                            {resume.get('experience', 'N/A').replace('\n', '<br>')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Education
                        st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">EDUCATION</p>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px;">
                            {resume.get('education', 'N/A').replace('\n', '<br>')}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_right:
                        # Download Button
                        st.download_button(
                            "Download Resume",
                            data=resume["resume"],
                            file_name=f"{resume['name']}_resume.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        # Skills
                        st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">SKILLS</p>', unsafe_allow_html=True)
                        
                        # Display skills as tags
                        skills = resume.get('skills', 'N/A').split(', ')
                        skills_html = ''
                        for skill in skills:
                            if skill and skill != 'N/A':
                                skills_html += f'<span class="skill-tag">{skill}</span>'
                        
                        st.markdown(f"""
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px;">
                            {skills_html if skills_html else 'No skills listed'}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Score Breakdown - FIXED TO ENSURE VALUES ARE BETWEEN 0 AND 1
                        if 'score_breakdown' in resume:
                            st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">SCORE BREAKDOWN</p>', unsafe_allow_html=True)
                            st.markdown('<div style="background-color: #f8fafc; padding: 15px; border-radius: 8px;">', unsafe_allow_html=True)
                            
                            for category, points in resume.get('score_breakdown', {}).items():
                                # Define max points for each category
                                max_points = 30 if category == 'skill_match' else 25 if category == 'experience' else 20 if category == 'achievements' else 15 if category == 'education' else 10
                                
                                # Ensure the progress value is between 0 and 1
                                progress_value = min(1.0, max(0.0, float(points) / float(max_points)))
                                
                                # Display the progress bar with normalized value
                                st.progress(progress_value)
                                
                                st.markdown(f"""
                                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                    <span style="text-transform: capitalize;">{category.replace('_', ' ')}</span>
                                    <span style="font-weight: 600;">{points}/{max_points}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    # AI Assessment
                    st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">AI ASSESSMENT</p>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        {resume.get('summary', 'No summary available').replace('\n', '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Flags if any
                    if 'flags' in resume and resume['flags']:
                        flags = resume['flags']
                        if isinstance(flags, list) and flags:
                            st.markdown('<p style="color: #64748b; font-weight: 600; margin: 20px 0 5px 0;">CAUTION FLAGS</p>', unsafe_allow_html=True)
                            flags_html = ''
                            for flag in flags:
                                flags_html += f'<span style="display: inline-block; background-color: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 20px; font-size: 12px; margin-right: 5px; margin-bottom: 5px;">{flag}</span>'
                            
                            st.markdown(f"""
                            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px;">
                                {flags_html}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ No suitable candidates found for this position")
    else:
        st.warning("⚠️ Please set HR requirements first")

# Add some helpful footer information
st.markdown("""
<div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; margin-top: 30px; text-align: center;">
    <p style="margin: 0; color: #64748b;">💡 For best results, provide detailed job descriptions with clear responsibilities and requirements.</p>
</div>
""", unsafe_allow_html=True)