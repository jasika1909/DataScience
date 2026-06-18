import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.nlp_models import SkillGapAnalyzer

@st.cache_resource
def get_analyzer():
    return SkillGapAnalyzer()


def render():
    st.markdown("## 📚 Skill Gap Analysis")
    st.markdown("Compare your current skill set against a job's requirements and get a personalized upskilling roadmap.")

    analyzer = get_analyzer()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 👤 Your Skills")
        candidate_skills_input = st.text_area(
            "Enter your skills (comma-separated)",
            value="python, sql, pandas, matplotlib, scikit-learn, power bi",
            height=100
        )

        st.markdown("#### 💼 Target Job")
        job_title = st.text_input("Job Title", value="Senior Data Scientist")
        job_description = st.text_area(
            "Job Description / Requirements",
            height=220,
            value=(
                "We are looking for a Senior Data Scientist with expertise in Python, SQL, "
                "and machine learning frameworks like TensorFlow and PyTorch. Experience with "
                "AWS, Docker, and MLflow for MLOps is required. Knowledge of NLP techniques, "
                "BERT models, and Apache Spark for big data processing is a strong plus. "
                "Familiarity with Tableau or Power BI for stakeholder reporting is preferred."
            )
        )

        analyze_btn = st.button("🔍 Analyze Skill Gap", type="primary", use_container_width=True)

    with col2:
        if analyze_btn:
            candidate_skills = analyzer.parse_candidate_skills(candidate_skills_input)
            result = analyzer.analyze_gap(candidate_skills, job_description, job_title)

            # Match score gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=result['match_score'],
                title={'text': "Skill Match Score", 'font': {'size': 16, 'color': '#ccc'}},
                number={'suffix': '%', 'font': {'size': 30}},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': '#667eea', 'thickness': 0.3},
                    'bgcolor': '#1e1e2e',
                    'steps': [
                        {'range': [0, 40], 'color': 'rgba(255,75,75,0.13)'},
                        {'range': [40, 60], 'color': 'rgba(255,165,0,0.13)'},
                        {'range': [60, 80], 'color': 'rgba(254,202,87,0.13)'},
                        {'range': [80, 100], 'color': 'rgba(0,204,136,0.13)'}
                    ]
                }
            ))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc',
                             height=250, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(
                f"<div style='text-align:center; font-size:1.05rem; font-weight:700; "
                f"padding:0.4rem; border-radius:8px; background:#667eea15;'>"
                f"{result['readiness_label']}</div>", unsafe_allow_html=True
            )
            st.info(result['recommendation'])

        else:
            st.markdown("""
            <div style='border:1px dashed #444; border-radius:12px; padding:3rem;
                 text-align:center; color:#666;'>
                <div style='font-size:2.5rem;'>🎯</div>
                <p>Enter your skills and job details, then click<br><strong>Analyze Skill Gap</strong></p>
            </div>""", unsafe_allow_html=True)

    if analyze_btn:
        st.markdown("---")
        candidate_skills = analyzer.parse_candidate_skills(candidate_skills_input)
        result = analyzer.analyze_gap(candidate_skills, job_description, job_title)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ✅ Matching Skills")
            if result['matching_skills']:
                for skill in result['matching_skills']:
                    st.markdown(
                        f"<span style='background:#00cc8822; color:#00cc88; padding:4px 10px; "
                        f"border-radius:12px; margin:3px; display:inline-block; font-size:0.85rem;'>"
                        f"✓ {skill.title()}</span>", unsafe_allow_html=True
                    )
            else:
                st.warning("No matching skills found.")

        with col2:
            st.markdown("#### ❌ Missing Skills (Priority Order)")
            if result['missing_skills']:
                for skill in result['missing_skills']:
                    st.markdown(
                        f"<span style='background:#ff6b6b22; color:#ff6b6b; padding:4px 10px; "
                        f"border-radius:12px; margin:3px; display:inline-block; font-size:0.85rem;'>"
                        f"✗ {skill.title()}</span>", unsafe_allow_html=True
                    )
            else:
                st.success("No missing skills — full match!")

        st.markdown("---")
        st.markdown("#### 🗺️ Personalized Learning Roadmap")

        if result['learning_paths']:
            for i, (skill, path) in enumerate(result['learning_paths'].items(), 1):
                with st.expander(f"**{i}. {skill.title()}** — {path['level'].title()} level · ⏱️ {path['estimated_time']}"):
                    st.markdown("**Recommended Resources:**")
                    for resource in path['resources']:
                        st.markdown(f"- {resource}")
        else:
            st.success("🎉 You already cover all key required skills for this role!")

        # Skill category breakdown
        if result['required_by_category']:
            st.markdown("---")
            st.markdown("#### 📊 Required Skills by Category")
            cat_data = []
            for cat, skills in result['required_by_category'].items():
                for skill in skills:
                    status = 'Have' if skill in result['matching_skills'] else 'Missing'
                    cat_data.append({'Category': cat, 'Skill': skill, 'Status': status})

            cat_df = pd.DataFrame(cat_data)
            if not cat_df.empty:
                fig = px.bar(
                    cat_df.groupby(['Category', 'Status']).size().reset_index(name='Count'),
                    x='Category', y='Count', color='Status',
                    color_discrete_map={'Have': '#00cc88', 'Missing': '#ff6b6b'},
                    barmode='stack', title='Skills Coverage by Category'
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                 font_color='#ccc', height=350)
                st.plotly_chart(fig, use_container_width=True)

    # Market skill trends section
    st.markdown("---")
    st.markdown("#### 🔥 Trending Skills in the Job Market (2026)")
    trending_skills = pd.DataFrame({
        'Skill': ['LLMs / GenAI', 'Python', 'SQL', 'Cloud (AWS/Azure)', 'MLOps',
                 'Machine Learning', 'Power BI/Tableau', 'Apache Spark', 'Docker/K8s', 'NLP'],
        'Demand Score': [98, 96, 94, 90, 87, 92, 80, 75, 78, 82]
    }).sort_values('Demand Score', ascending=True)

    fig = px.bar(trending_skills, x='Demand Score', y='Skill', orientation='h',
                color='Demand Score', color_continuous_scale='Plasma',
                title='Most In-Demand Skills (Job Postings Frequency Score)')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font_color='#ccc', height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)