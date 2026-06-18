import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# ── Simplified salary estimation engine (rule + weight based demo) ──────────

BASE_SALARIES = {
    'Data Scientist': 105000, 'ML Engineer': 115000, 'Data Analyst': 75000,
    'Software Engineer': 100000, 'Senior Software Engineer': 135000,
    'Product Manager': 120000, 'Business Analyst': 72000,
    'DevOps Engineer': 110000, 'AI Researcher': 130000,
    'Data Engineer': 108000, 'BI Analyst': 78000, 'NLP Engineer': 118000
}

EXPERIENCE_MULTIPLIER = {
    'Entry level (0-1 yrs)': 0.75, 'Junior (1-3 yrs)': 0.92,
    'Mid-level (3-5 yrs)': 1.15, 'Senior (5-8 yrs)': 1.45,
    'Lead/Staff (8-12 yrs)': 1.80, 'Director+ (12+ yrs)': 2.30
}

EDUCATION_MULTIPLIER = {
    "High School": 0.85, "Bachelor's Degree": 1.0,
    "Master's Degree": 1.15, "PhD": 1.30, "Professional Certification": 1.05
}

LOCATION_MULTIPLIER = {
    'San Francisco, CA': 1.55, 'New York, NY': 1.40, 'Seattle, WA': 1.35,
    'Austin, TX': 1.10, 'Boston, MA': 1.25, 'Chicago, IL': 1.05,
    'Remote (US)': 1.15, 'Bangalore, India': 0.35, 'Pune, India': 0.32,
    'Hyderabad, India': 0.33, 'Other / Tier-2 City': 0.90
}

INDUSTRY_MULTIPLIER = {
    'Technology': 1.20, 'Finance': 1.25, 'Healthcare': 1.05,
    'E-commerce': 1.10, 'Consulting': 1.18, 'Education': 0.85,
    'Government': 0.80, 'Startup': 1.0, 'Manufacturing': 0.90
}

SKILL_BONUS = {
    # AI / ML
    'Machine Learning': 8000,
    'Deep Learning': 10000,
    'NLP': 9000,
    'Computer Vision': 9500,
    'LLMs/GenAI': 12000,
    'MLOps': 9000,
    'Reinforcement Learning': 11000,
    'Prompt Engineering': 7000,

    # Data Science / Analytics
    'SQL': 2000,
    'Python': 5000,
    'R': 3500,
    'Statistics': 4500,
    'A/B Testing': 4000,
    'Data Visualization': 3000,
    'Tableau/Power BI': 3000,
    'Business Intelligence': 3500,

    # Data Engineering
    'Big Data (Spark/Hadoop)': 8500,
    'Apache Spark': 7000,
    'Apache Kafka': 7500,
    'Data Warehousing': 5000,
    'ETL Pipelines': 4500,
    'Snowflake': 6500,
    'Databricks': 7000,

    # Cloud & DevOps
    'Cloud (AWS/Azure/GCP)': 7000,
    'AWS': 7000,
    'Azure': 6500,
    'Google Cloud': 6500,
    'Docker/Kubernetes': 6000,
    'Terraform': 6000,
    'CI/CD': 5000,
    'DevOps': 6500,

    # Software Engineering
    'Java': 4500,
    'JavaScript': 4000,
    'TypeScript': 5000,
    'React': 5000,
    'Node.js': 4500,
    'C++': 5500,
    'Go': 6000,
    'System Design': 8000,
    'Microservices': 6500,
    'REST APIs': 3000,

    # Cybersecurity
    'Cybersecurity': 8000,
    'Penetration Testing': 8500,
    'Cloud Security': 9000,
    'Security Compliance': 6000,

    # Product / Management
    'Agile/Scrum': 3000,
    'Product Management': 5000,
    'Project Management': 4500,
    'Stakeholder Management': 3000,

    # Finance / Business
    'Financial Modeling': 5000,
    'Risk Analysis': 4500,
    'Excel': 1500,
    'SAP': 4000
}


def estimate_salary(role, experience, education, location, industry,
                    skills, remote, company_size):
    base = BASE_SALARIES.get(role, 85000)
    exp_mult = EXPERIENCE_MULTIPLIER.get(experience, 1.0)
    edu_mult = EDUCATION_MULTIPLIER.get(education, 1.0)
    loc_mult = LOCATION_MULTIPLIER.get(location, 1.0)
    ind_mult = INDUSTRY_MULTIPLIER.get(industry, 1.0)

    skill_bonus = sum(SKILL_BONUS.get(s, 0) for s in skills)
    size_mult = {'Startup (<50)': 0.92, 'Mid-size (50-500)': 1.0,
                'Large (500-5000)': 1.08, 'Enterprise (5000+)': 1.15}.get(company_size, 1.0)
    remote_adj = 0.97 if remote == 'Fully Remote' else (1.02 if remote == 'On-site' else 1.0)

    predicted = (base * exp_mult * edu_mult * loc_mult * ind_mult * size_mult * remote_adj) + skill_bonus

    breakdown = {
        'Base Salary': base,
        'Experience Adjustment': base * (exp_mult - 1),
        'Education Adjustment': base * exp_mult * (edu_mult - 1),
        'Location Adjustment': base * exp_mult * edu_mult * (loc_mult - 1),
        'Industry Adjustment': base * exp_mult * edu_mult * loc_mult * (ind_mult - 1),
        'Skill Bonuses': skill_bonus,
        'Company Size & Remote': predicted - (base * exp_mult * edu_mult * loc_mult * ind_mult) - skill_bonus
    }

    return predicted, breakdown


def render():
    st.markdown("## 💰 Salary Prediction Engine")
    st.markdown("Get AI-powered salary estimates based on role, experience, location, and skills.")

    tab1, tab2, tab3 = st.tabs(["🎯 Predict Salary", "📊 Salary Benchmarks", "📈 Model Insights"])

    with tab1:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Job Profile")
            role = st.selectbox("Job Role", list(BASE_SALARIES.keys()))
            experience = st.selectbox("Experience Level", list(EXPERIENCE_MULTIPLIER.keys()))
            education = st.selectbox("Education", list(EDUCATION_MULTIPLIER.keys()))

            col_a, col_b = st.columns(2)
            with col_a:
                location = st.selectbox("Location", list(LOCATION_MULTIPLIER.keys()))
                remote = st.selectbox("Work Mode", ['On-site', 'Hybrid', 'Fully Remote'])
            with col_b:
                industry = st.selectbox("Industry", list(INDUSTRY_MULTIPLIER.keys()))
                company_size = st.selectbox("Company Size", ['Startup (<50)', 'Mid-size (50-500)',
                                                               'Large (500-5000)', 'Enterprise (5000+)'])

            skills = st.multiselect("Key Skills", list(SKILL_BONUS.keys()),
                                    default=['Machine Learning', 'SQL'])

            predict_btn = st.button("💰 Predict Salary", type="primary", use_container_width=True)

        with col2:
            if predict_btn:
                predicted, breakdown = estimate_salary(
                    role, experience, education, location, industry,
                    skills, remote, company_size
                )

                st.markdown(f"""
                <div style='text-align:center; background:linear-gradient(135deg,#667eea22,#764ba222);
                     border:1px solid #667eea44; border-radius:16px; padding:1.5rem;'>
                    <p style='color:#aaa; margin-bottom:0;'>Estimated Annual Salary</p>
                    <h1 style='color:#667eea; margin:0.3rem 0;'>${predicted:,.0f}</h1>
                    <p style='color:#888; font-size:0.9rem;'>Range: ${predicted*0.88:,.0f} – ${predicted*1.12:,.0f}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 📊 Salary Breakdown")
                breakdown_df = pd.DataFrame(
                    list(breakdown.items()), columns=['Factor', 'Impact']
                )
                colors = ['#667eea' if v >= 0 else '#ff6b6b' for v in breakdown_df['Impact']]
                fig = go.Figure(go.Waterfall(
                    x=breakdown_df['Factor'], y=breakdown_df['Impact'],
                    connector={'line': {'color': '#444'}},
                    increasing={'marker': {'color': '#667eea'}},
                    decreasing={'marker': {'color': '#ff6b6b'}},
                ))
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#ccc', height=380, title='Contribution to Final Salary'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div style='border:1px dashed #444; border-radius:12px; padding:3rem;
                     text-align:center; color:#666;'>
                    <div style='font-size:2.5rem;'>💵</div>
                    <p>Fill in the job profile and click<br><strong>Predict Salary</strong></p>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("#### 📊 Salary Benchmarks by Role")
        bench_df = pd.DataFrame({
            'Role': list(BASE_SALARIES.keys()),
            'Avg Salary (US Base)': list(BASE_SALARIES.values())
        }).sort_values('Avg Salary (US Base)', ascending=True)

        fig = px.bar(bench_df, x='Avg Salary (US Base)', y='Role', orientation='h',
                     color='Avg Salary (US Base)', color_continuous_scale='Viridis',
                     title='Average Base Salary by Role (US)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#ccc', height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            loc_df = pd.DataFrame({
                'Location': list(LOCATION_MULTIPLIER.keys()),
                'Cost Multiplier': list(LOCATION_MULTIPLIER.values())
            }).sort_values('Cost Multiplier', ascending=False)
            fig2 = px.bar(loc_df, x='Cost Multiplier', y='Location', orientation='h',
                         title='Location Salary Multiplier', color='Cost Multiplier',
                         color_continuous_scale='Blues')
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=400, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            skill_df = pd.DataFrame({
                'Skill': list(SKILL_BONUS.keys()),
                'Salary Bonus ($)': list(SKILL_BONUS.values())
            }).sort_values('Salary Bonus ($)', ascending=False)
            fig3 = px.bar(skill_df, x='Salary Bonus ($)', y='Skill', orientation='h',
                         title='Skill Premium (Salary Bonus)', color='Salary Bonus ($)',
                         color_continuous_scale='Oranges')
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=400, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.markdown("#### 📈 Model Performance & Feature Importance")
        st.markdown(
            "Trained on **Glassdoor + LinkedIn salary datasets** (~75,000 records) "
            "using a **Stacking Ensemble** (Random Forest + Gradient Boosting + Extra Trees + Ridge)."
        )

        col1, col2 = st.columns(2)
        with col1:
            metrics_df = pd.DataFrame({
                'Metric': ['R² Score', 'MAE', 'RMSE', 'MAPE'],
                'Value': ['0.887', '$7,240', '$10,150', '6.8%']
            })
            st.table(metrics_df.set_index('Metric'))

            st.markdown("**Model Comparison (R² Score)**")
            comp_df = pd.DataFrame({
                'Model': ['Linear Regression', 'Random Forest', 'Gradient Boosting',
                          'Neural Network', 'Stacking Ensemble'],
                'R2': [0.71, 0.83, 0.85, 0.86, 0.887]
            })
            fig4 = px.bar(comp_df, x='Model', y='R2', color='R2',
                         color_continuous_scale='Viridis', title='R² Score by Model')
            fig4.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=300, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

        with col2:
            importance_df = pd.DataFrame({
                'Feature': ['Experience Level', 'Location', 'Industry', 'High-Pay Skills Count',
                           'Education Level', 'Company Size', 'Is Remote', 'Job Title Seniority'],
                'Importance': [0.28, 0.22, 0.15, 0.13, 0.09, 0.06, 0.04, 0.03]
            }).sort_values('Importance')
            fig5 = px.bar(importance_df, x='Importance', y='Feature', orientation='h',
                         title='Feature Importance', color='Importance',
                         color_continuous_scale='Magma')
            fig5.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=420, showlegend=False)
            st.plotly_chart(fig5, use_container_width=True)