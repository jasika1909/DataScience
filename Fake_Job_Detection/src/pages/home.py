import streamlit as st
def render():
    st.markdown('<h1 class="main-header">🛡️ TalentGuard AI</h1>', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center; font-size:1.1rem; color:#888;'>"
        "AI-Powered Recruitment Fraud Detection & Talent Intelligence Platform</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # KPI Row
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("🛡️ Jobs Analyzed", "1.2M+", "+12% MoM"),
        ("🚨 Frauds Detected", "23,400+", "+8% MoM"),
        ("🎯 Detection Accuracy", "96.4%", "+0.3%"),
        ("💰 Salary Predictions", "850K+", "+15% MoM"),
        ("📚 Skill Gaps Closed", "42K+", "+20% MoM"),
    ]
    for col, (label, value, delta) in zip([col1, col2, col3, col4, col5], metrics):
        with col:
            st.metric(label=label, value=value, delta=delta)

    st.markdown("---")

    # Module Cards
    st.markdown("### 🔍 Platform Modules")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#ff6b6b22,#ee525222);
             border:1px solid #ff6b6b44; border-radius:12px; padding:1.2rem;'>
            <h4>🚨 Fake Job Detection</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            ML + Deep Learning (BiLSTM) model with 96%+ accuracy.
            Analyzes 40+ signals including NLP features and structural patterns.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style='background:linear-gradient(135deg,#4ecdc422,#2ecc7122);
             border:1px solid #4ecdc444; border-radius:12px; padding:1.2rem; margin-top:1rem;'>
            <h4>💰 Salary Prediction</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            Stacking ensemble (RF + GBM + Ridge) predicts salary ranges
            using 15+ features. Includes confidence intervals.
            </p>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#a29bfe22,#6c5ce722);
             border:1px solid #a29bfe44; border-radius:12px; padding:1.2rem;'>
            <h4>📚 Skill Gap Analysis</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            Compares your skills vs. job requirements with a match score,
            personalized learning paths, and time-to-ready estimates.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style='background:linear-gradient(135deg,#fd79a822,#e8406422);
             border:1px solid #fd79a844; border-radius:12px; padding:1.2rem; margin-top:1rem;'>
            <h4>🏷️ Job Classification</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            NLP-powered multi-class classifier (12 categories) using
            TF-IDF + Logistic Regression. Instant category detection.
            </p>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#ffeaa722,#fdcb6e22);
             border:1px solid #ffeaa744; border-radius:12px; padding:1.2rem;'>
            <h4>📈 Hiring Trend Analytics</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            LSTM-based forecasting for job market demand, salary trends,
            remote work adoption, and fraud pattern evolution.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style='background:linear-gradient(135deg,#55efc422,#00b89422);
             border:1px solid #55efc444; border-radius:12px; padding:1.2rem; margin-top:1rem;'>
            <h4>📊 Business Dashboard</h4>
            <p style='font-size:0.85rem; color:#aaa;'>
            Executive-level BI dashboard with KPIs, interactive charts,
            filters, and exportable reports powered by Plotly.
            </p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Tech Stack
    st.markdown("### 🛠️ Tech Stack")
    st.markdown("""
    | Layer | Technologies |
    |---|---|
    | **Data Processing** | Python, Pandas, NumPy |
    | **NLP** | NLTK, spaCy, TF-IDF, Word Embeddings |
    | **Machine Learning** | Scikit-Learn, XGBoost, SMOTE |
    | **Deep Learning** | TensorFlow, Keras, BiLSTM, CNN |
    | **Visualization** | Matplotlib, Seaborn, Plotly |
    | **BI & Dashboard** | Power BI concepts, Streamlit |
    | **Deployment** | Streamlit Cloud / Docker |
    """)

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center; color:#555; font-size:0.85rem;'>"
        "Built by <strong>Jasika Awasthi</strong> · B.Tech CSE (Data Science & AI) · 2026 · "
        "<a href='https://github.com/jasika1909' style='color:#667eea;'>GitHub</a>"
        "</p>", unsafe_allow_html=True
    )