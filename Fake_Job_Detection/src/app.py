import streamlit as st
import pages.home as home
import pages.dashboard as dashboard
import pages.salary_prediction as salary_prediction
import pages.fake_job_detection as fake_job_detection
import pages.hiring_trends as hiring_trends
import pages.skills_gap_analysis as skills_gap_analysis
import pages.job_classification as job_classification
import pages.skills_gap_analysis as skills_gap_analysis


st.set_page_config(
    page_title="AI Recruitment Fraud & Talent Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .sidebar-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
    }
    div[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🛡️ TalentGuard AI")
    st.markdown("---")

    st.markdown('<p class="sidebar-title">🔍 Core Modules</p>', unsafe_allow_html=True)

    page = st.radio(
        "Navigate to:",
        options=[
            "🏠 Home",
            "🚨 Fake Job Detection",
            "💰 Salary Prediction",
            "📚 Skill Gap Analysis",
            "🏷️ Job Classification",
            "📈 Hiring Trend Analytics",
            "📊 Business Dashboard"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**📌 Platform Stats**")
    st.metric("Jobs Analyzed", "1.2M+")
    st.metric("Fraud Detected", "23,400+")
    st.metric("Accuracy", "96.4%")
    st.markdown("---")
    st.caption("Built by Jasika Awasthi | 2026")
    st.caption("B.Tech CSE (Data Science & AI)")

# Page Routing
if page == "🏠 Home":
    home.render()
elif page == "🚨 Fake Job Detection":
    fake_job_detection.render()
elif page == "💰 Salary Prediction":
    salary_prediction.render()
elif page == "📚 Skill Gap Analysis":
    skills_gap_analysis.render()
elif page == "🏷️ Job Classification":
    job_classification.render()
elif page == "📈 Hiring Trend Analytics":
    hiring_trends.render()
elif page == "📊 Business Dashboard":
    dashboard.render()