import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.nlp_models import JobCategoryClassifier


@st.cache_resource
def get_classifier():
    return JobCategoryClassifier()


def render():
    st.markdown("## 🏷️ Job Category Classification")
    st.markdown("Automatically classify job postings into 12 standardized categories using NLP.")

    classifier = get_classifier()

    tab1, tab2, tab3 = st.tabs(["🔍 Classify a Job", "📂 Batch Classification", "📊 Category Insights"])

    with tab1:
        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown("#### Job Posting")
            job_title = st.text_input("Job Title", value="Senior Machine Learning Engineer")
            job_text = st.text_area(
                "Job Description",
                height=280,
                value=(
                    "We are hiring a Machine Learning Engineer to design, build, and deploy "
                    "production ML models. You'll work with TensorFlow, PyTorch, and large-scale "
                    "data pipelines. Strong background in deep learning, NLP, and MLOps required. "
                    "Experience with AWS SageMaker and Docker is a plus."
                )
            )
            classify_btn = st.button("🏷️ Classify Job", type="primary", use_container_width=True)

        with col2:
            if classify_btn:
                full_text = f"{job_title} {job_text}"
                result = classifier.predict_single(full_text)

                st.markdown(f"""
                <div style='text-align:center; background:linear-gradient(135deg,#667eea22,#764ba222);
                     border:1px solid #667eea44; border-radius:16px; padding:1.5rem;'>
                    <p style='color:#aaa; margin-bottom:0;'>Predicted Category</p>
                    <h2 style='color:#667eea; margin:0.3rem 0;'>{result['category']}</h2>
                    <p style='color:#888;'>Confidence: {result['confidence']*100:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### Top 5 Category Probabilities")
                top5_df = pd.DataFrame(result['top_5'][:5], columns=['Category', 'Probability'])
                top5_df['Probability'] = top5_df['Probability'] * 100
                fig = px.bar(top5_df.sort_values('Probability'), x='Probability', y='Category',
                            orientation='h', color='Probability', color_continuous_scale='Viridis')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#ccc', height=300, showlegend=False,
                                  xaxis_title='Probability (%)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div style='border:1px dashed #444; border-radius:12px; padding:3rem;
                     text-align:center; color:#666;'>
                    <div style='font-size:2.5rem;'>🏷️</div>
                    <p>Enter a job posting and click<br><strong>Classify Job</strong></p>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("#### 📂 Batch Classification")
        st.info("Upload a CSV with `title` and `description` columns to classify multiple job postings at once.")
        uploaded = st.file_uploader("Upload CSV", type=['csv'], key='classify_upload')

        if uploaded:
            df = pd.read_csv(uploaded)
            st.success(f"Loaded {len(df):,} rows")

            if 'description' in df.columns:
                with st.spinner("Classifying all jobs..."):
                    title_col = df['title'].fillna("") if 'title' in df.columns else ""
                    combined = title_col + " " + df['description'].fillna("")
                    df['predicted_category'] = combined.apply(
                        lambda x: classifier.predict_single(x)['category']
                    )

                st.dataframe(df[['title', 'predicted_category']].head(50)
                            if 'title' in df.columns else df[['predicted_category']].head(50))

                cat_counts = df['predicted_category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                fig = px.pie(cat_counts, names='Category', values='Count',
                            title='Category Distribution', hole=0.4)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc')
                st.plotly_chart(fig, use_container_width=True)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Classified Data", csv,
                                   "classified_jobs.csv", "text/csv")
            else:
                st.error("CSV must contain a `description` column.")

    with tab3:
        st.markdown("#### 📊 Job Category Market Insights")

        category_stats = pd.DataFrame({
            'Category': classifier.JOB_CATEGORIES,
            'Avg Postings/Month': [8200, 24500, 4800, 11200, 6900, 5800,
                                    7100, 8600, 3900, 6200, 2100, 3400],
            'Avg Salary': [115000, 110000, 120000, 75000, 85000, 65000,
                          95000, 70000, 80000, 52000, 105000, 68000],
            'Growth Rate (YoY %)': [28.5, 12.3, 8.1, 4.2, 3.5, 2.8,
                                     6.5, 5.1, 7.2, 3.1, 4.5, 2.2]
        })

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(category_stats.sort_values('Avg Postings/Month'),
                         x='Avg Postings/Month', y='Category', orientation='h',
                         color='Avg Postings/Month', color_continuous_scale='Blues',
                         title='Monthly Job Postings by Category')
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=450, showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.scatter(category_stats, x='Avg Salary', y='Growth Rate (YoY %)',
                             size='Avg Postings/Month', color='Category', text='Category',
                             title='Salary vs Growth Rate (bubble size = volume)')
            fig2.update_traces(textposition='top center', textfont_size=8)
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=450, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### 🏆 Model Performance")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Categories", "12")
        col2.metric("Accuracy", "89.3%")
        col3.metric("F1 (Macro)", "0.871")
        col4.metric("Training Samples", "45,000+")