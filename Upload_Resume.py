import tempfile
import joblib
import pickle
import streamlit as st
from pathlib import Path
import pymongo
from datetime import datetime
import PyPDF2
import docx2txt
import json
import google.generativeai as genai
import random
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
client = MongoClient(st.secrets["mongodb"]["MONGO_URI"])

db = client["resume_db"]
hr_collection = db["hr_requirements"]
resumes_collection = db["resumes"]

# Load ML model components
cv = pickle.load(open('cv.pickle', 'rb'))
model = joblib.load('RFC.joblib')
with open('role_mapping.pickle', 'rb') as f:
    role_mapping = pickle.load(f)

# Configure Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel('gemini-1.5-flash-001')

# Custom CSS
st.markdown("""
<style>
    .stApp {
    background: #f5faf7;
    background-image: radial-gradient(#e0ede6 1px, transparent 0);
    background-size: 20px 20px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main-container {
        background-color: white;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 30px;
        border: 1px solid #f0f0f0;
    }
    
    .header {
        display: flex;
        align-items: center;
        margin-bottom: 25px;
        border-bottom: 1px solid #f0f0f0;
        padding-bottom: 15px;
    }
    
    .header-logo {
        margin-right: 15px;
        color: #4361ee;
    }
    
    .job-banner {
        background: linear-gradient(135deg, #4361ee15, #4361ee05);
        border-left: 4px solid #4361ee;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 25px;
    }
    
    .job-title {
        font-weight: 600;
        color: #4361ee;
        margin: 0;
    }
    
    .score-container {
        text-align: center;
        margin: 30px 0;
    }
    
    .score-circle {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: conic-gradient(#4361ee var(--percentage), #f0f0f0 0);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 15px auto;
        position: relative;
    }
    
    .score-circle::before {
        content: '';
        position: absolute;
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: white;
    }
    
    .score-value {
        position: relative;
        font-size: 28px;
        font-weight: 700;
        color: #2d3748;
    }
    
    .analysis-section {
        background-color: #f9fafb;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
    }
    
    .analysis-header {
        font-weight: 600;
        margin-bottom: 15px;
        color: #2d3748;
        font-size: 18px;
    }
    
    .breakdown-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .breakdown-label {
        color: #4a5568;
    }
    
    .breakdown-value {
        font-weight: 500;
    }
    
    .summary-box {
        background-color: #ebf5ff;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        border-left: 4px solid #4361ee;
    }
    
    .flag-box {
        background-color: #fff5f5;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        border-left: 4px solid #e53e3e;
    }
    
    .stButton > button {
        background-color: #4361ee;
        color: white;
        border-radius: 8px;
        padding: 10px 25px;
        font-weight: 500;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #3a56d4;
        box-shadow: 0 4px 8px rgba(67, 97, 238, 0.2);
    }
    
    .stForm > div > div > div > div > div > .stButton > button {
        background-color: #4361ee;
        width: 100%;
    }
    
    /* File uploader */
    .css-1aehpvj {
        color: #4361ee !important;
    }
    
    /* Success message */
    .stSuccess {
        background-color: #d9f99d;
        color: #3f6212;
        border: none;
    }
    
    /* Error message */
    .stError {
        background-color: #fee2e2;
        color: #b91c1c;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

def extract_text_from_file(file_path, file_type):
    if file_type == "text/plain":
        with open(file_path, 'r') as f:
            return f.read()
    elif file_type == "application/pdf":
        text = ""
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text()
        return text
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx2txt.process(file_path)
    return ""

def analyze_with_gemini(resume_text, position, job_description):
    prompt = f"""
ROLE: You are an unbiased resume screener for {position}. Follow these rules:

1. SCORING (100 points total):
   - Skill Match (30): Exact and adjacent skills. Deduct 5 if missing a 'Required Skill'.
   - Experience (25): Years + relevance. 1 year = 3 points (max 25).
   - Education (15): Degree (PhD=15, Master=12, Bachelor=8, Bootcamp=7). No school name bias.
   - Achievements (20): Quantifiable impact (e.g., "Improved accuracy by 20%" = +5).
   - Technical Depth (10): Complexity (e.g., "Built distributed system" = +10).

2. ANTI-BIAS RULES:
   - IGNORE: Name, gender, age, ethnicity, university.
   - PENALIZE: Resumes mentioning demographic details for fairness.
   - FOCUS: Skills, results, and role fit only.

3. EXAMPLES:
   - "5 YOE at startups" = "5 YOE at [Redacted]" (same score).
   - "Harvard CS grad" = "CS grad" (no bonus for Ivy League).

4. FRAUD CHECKS:
   - Flag impossible claims (e.g., "10 YOE in a 5-year-old tech").
   - Detect keyword stuffing (e.g., "Python Python Python" with no projects).

JOB DESCRIPTION: {job_description}

RESUME TO SCORE:
{resume_text[:8000]}

OUTPUT FORMAT (JSON):
{{
    "name": "Full Name from resume"",
    "email": "Only if professional",
    "phone": "Only if provided",
    "education": "Degree + field (no school names)",
    "experience": "Years + role (no company names)",
    "skills": "Comma-separated list",
    "score": 0-100,
    "score_breakdown": {{
        "skill_match": 0-30,
        "experience": 0-25,
        "education": 0-15,
        "achievements": 0-20,
        "technical_depth": 0-10
    }},
    "summary": "Strengths: ... Weaknesses: ... [Redacted demographics if mentioned]",
    "flags": ["Inconsistency", "Keyword stuffing", etc.] 
}}
"""

    try:
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean JSON response
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1]

        analysis = json.loads(response_text)

        # Normalize score with small variation
        raw_score = float(analysis['score'])
        normalized_score = raw_score + random.uniform(-1.5, 1.5)
        analysis['score'] = max(0, min(100, round(normalized_score, 1)))

        # Ensure required fields exist
        required_fields = ["name", "email", "phone", "education", 
                         "experience", "skills", "score", "summary"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = "N/A"

        return analysis

    except json.JSONDecodeError:
        st.error("❌ Failed to parse Gemini response. Retrying with simplified prompt...")
        return {
            "name": "Parse Error",
            "score": 0,
            "summary": "Analysis failed - invalid format"
        }
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")
        return {
            "name": "Analysis Error",
            "score": 0,
            "summary": "Processing failed"
        }

# Streamlit UI
st.markdown("""
<div class="header">
    <div class="header-logo">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 7h-3a2 2 0 0 0-2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7"></path>
            <path d="M16 3h4v4"></path><line x1="17" y1="7" x2="7" y2="17"></line>
        </svg>
    </div>
    <h1>ResuMatch</h1>
</div>
""", unsafe_allow_html=True)

hr_req = hr_collection.find_one({"is_active": True})

if hr_req:
    st.markdown(f"""
    <div class="job-banner">
        <h2 class="job-title">📢 Now Hiring: {hr_req['position'].upper()}</h2>
        <p>Submit your resume below to apply for this position</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("View Complete Job Details"):
        st.write(hr_req.get('job_description', 'No additional details'))
else:
    st.warning("⚠️ No active job positions available at this time")
    st.stop()

#st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown("### Submit Your Application")

with st.form("upload_form"):
    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Full Name*")
    
    
    uploaded_file = st.file_uploader("Upload Resume* (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    submitted = st.form_submit_button("Submit Application")

#st.markdown('</div>', unsafe_allow_html=True)

if submitted and uploaded_file:
    if not all([full_name, uploaded_file]):
        st.error("Please fill in all required fields")
        st.stop()
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file_path = Path(tmp_file.name)
        file_path.write_bytes(uploaded_file.getvalue())
        text = extract_text_from_file(file_path, uploaded_file.type)
        
        # ML Prediction
        X = cv.transform([text])
        pred = model.predict(X)
        predicted_category = role_mapping.get(pred[0], "a related role") if pred else "a related role"

        is_suitable = predicted_category.lower() == hr_req["position"].lower()
        
        #st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.markdown("### Assessment Results")
        
        # Initial classification
        if is_suitable:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                
            </div>
            """, unsafe_allow_html=True)
            st.write(f"Your profile appears to be more aligned with: {predicted_category}")
        else:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                <h2 style="color: #ef4444; margin-top: 10px;">Your resume may better match a different role</h2>
                <p>We recommend you explore other opportunities that align more closely with your skills.</p>
</div>
""", unsafe_allow_html=True)
            st.write(f"Your profile appears to be more aligned with: {predicted_category}")

        # Store in DB
        with open(file_path, "rb") as f:
            resume_binary = f.read()
        
        resume_data = {
            "name": full_name,
            "resume": resume_binary,
            "position": hr_req["position"],
            "predicted_role": predicted_category,
            "is_suitable": is_suitable,
            "processed_at": datetime.now()
        }

        # Gemini Analysis for suitable candidates
        if is_suitable:
            with st.spinner("Analyzing your resume in detail..."):
                analysis = analyze_with_gemini(text, hr_req["position"], hr_req["job_description"])
                
                # Show results
                score = analysis['score']
                
                # Create score circle with dynamic percentage
                st.markdown(f"""
                <div class="score-container">
                    <div class="score-circle" style="--percentage: {score}%">
                        <div class="score-value">{score}%</div>
                    </div>
                    <p>Match Score</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Score breakdown
                st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
                st.markdown('<div class="analysis-header">Score Breakdown</div>', unsafe_allow_html=True)
                
                for category, points in analysis.get("score_breakdown", {}).items():
                    max_points = {"skill_match": 30, "experience": 25, "education": 15, 
                                 "achievements": 20, "technical_depth": 10}.get(category, 0)
                    
                    st.markdown(f"""
                    <div class="breakdown-item">
                        <div class="breakdown-label">{category.replace('_', ' ').title()}</div>
                        <div class="breakdown-value">{points}/{max_points}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Flags if any
                if "flags" in analysis and analysis["flags"]:
                    st.markdown(f"""
                    <div class="flag-box">
                        <strong>⚠️ Areas for Improvement:</strong> {', '.join(analysis["flags"])}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Summary
                st.markdown(f"""
                <div class="summary-box">
                    <strong>Analysis Summary:</strong><br>
                    {analysis.get("summary", "No summary available")}
                </div>
                """, unsafe_allow_html=True)
                
                # Update DB with analysis
                resume_data.update({
                    "email": analysis.get("email", ""),
                    "phone": analysis.get("phone", ""),
                    "llm_score": analysis["score"],
                    "score_breakdown": analysis.get("score_breakdown", {}),
                    **{k: v for k, v in analysis.items() if k not in ["score", "score_breakdown"]}
                })
        
        resumes_collection.insert_one(resume_data)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #f0fdf4; border-radius: 8px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <h3 style="color: #10b981; margin-top: 10px;">Application Submitted Successfully!</h3>
            <p>Thank you for your interest. Our HR team will review your application and contact you if there's a match.</p>
        </div>
        """, unsafe_allow_html=True)