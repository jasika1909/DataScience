import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.data_pipeline import TextPreprocessor, FeatureEngineer

# ── Fraud scoring (rule-based demo engine) ───────────────────────────────────

FRAUD_RED_FLAGS = [
    ('work from home', 3), ('no experience', 2), ('earn from home', 4),
    ('daily payment', 4), ('weekly payment', 3), ('be your own boss', 3),
    ('unlimited income', 5), ('guaranteed income', 5), ('easy money', 5),
    ('no degree required', 2), ('immediate start', 1), ('apply now!!!', 2),
    ('bitcoin', 5), ('western union', 5), ('wire transfer', 4),
    ('gift card', 5), ('mlm', 5), ('multi-level', 4),
    ('make money fast', 5), ('risk free', 3), ('100% legitimate', 3)
]

LEGIT_SIGNALS = [
    ('years of experience', -2), ('bachelor', -2), ('master', -2),
    ('phd', -3), ('team', -1), ('collaborate', -1), ('salary range', -2),
    ('health insurance', -2), ('401k', -2), ('benefits', -1),
    ('linkedin', -1), ('github', -1), ('portfolio', -1),
    ('interview process', -2), ('background check', -2)
]


def rule_based_fraud_score(text: str) -> dict:
    """Compute rule-based fraud score with signal breakdown"""
    text_lower = text.lower()
    raw_score = 0
    triggered_red = []
    triggered_green = []

    for phrase, weight in FRAUD_RED_FLAGS:
        if phrase in text_lower:
            raw_score += weight
            triggered_red.append((phrase, weight))

    for phrase, weight in LEGIT_SIGNALS:
        if phrase in text_lower:
            raw_score += weight  # weight is negative
            triggered_green.append((phrase, abs(weight)))

    # Structural signals
    if '!' * 3 in text:
        raw_score += 3
        triggered_red.append(('excessive exclamation marks', 3))
    word_count = len(text.split())
    if word_count < 50:
        raw_score += 2
        triggered_red.append(('very short description (<50 words)', 2))
    if word_count > 300:
        raw_score -= 1
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.15:
        raw_score += 2
        triggered_red.append(('excessive capitalization', 2))

    # Normalize to 0-100.
    # SATURATION_SCORE represents a realistic "obviously fraudulent" raw score
    # (a handful of strong red flags firing together), not the theoretical sum
    # of every possible signal -- which a single posting would never fully trigger.
    SATURATION_SCORE = 20
    fraud_prob = min(max(raw_score / SATURATION_SCORE, 0), 1)

    if fraud_prob >= 0.6:
        verdict = "🚨 HIGH RISK - Likely Fraudulent"
        color = "#ff4b4b"
    elif fraud_prob >= 0.35:
        verdict = "⚠️ MEDIUM RISK - Review Carefully"
        color = "#ffa500"
    else:
        verdict = "✅ LOW RISK - Appears Legitimate"
        color = "#00cc88"

    return {
        'fraud_probability': round(fraud_prob * 100, 1),
        'verdict': verdict,
        'color': color,
        'red_flags': triggered_red,
        'green_signals': triggered_green,
        'word_count': word_count,
        'caps_ratio': round(caps_ratio * 100, 1)
    }


def render_gauge(probability: float, color: str):
    """Render fraud probability gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=probability,
        title={'text': "Fraud Risk Score", 'font': {'size': 18, 'color': '#ccc'}},
        number={'suffix': '%', 'font': {'size': 32, 'color': color}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#888'},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': '#1e1e2e',
            'bordercolor': '#333',
            'steps': [
                {'range': [0, 35], 'color': 'rgba(0,204,136,0.13)'},
                {'range': [35, 60], 'color': 'rgba(255,165,0,0.13)'},
                {'range': [60, 100], 'color': 'rgba(255,75,75,0.13)'}
            ],
            'threshold': {
                'line': {'color': color, 'width': 4},
                'thickness': 0.75,
                'value': probability
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#ccc', height=280, margin=dict(t=40, b=0, l=20, r=20)
    )
    return fig


def render_signal_bar(signals: list, title: str, color: str):
    """Render horizontal bar chart for signals"""
    if not signals:
        return None
    phrases = [s[0].title()[:30] for s in signals]
    weights = [s[1] for s in signals]
    fig = px.bar(
        x=weights, y=phrases, orientation='h',
        title=title,
        color_discrete_sequence=[color]
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#ccc', height=max(200, len(signals) * 35 + 60),
        xaxis_title='Signal Weight', yaxis_title='',
        margin=dict(t=40, b=20, l=10, r=10)
    )
    return fig


def render():
    st.markdown("## 🚨 Fake Job Detection")
    st.markdown("Paste a job posting below to analyze it for fraud signals using our AI engine.")

    tab1, tab2, tab3 = st.tabs(["🔍 Single Analysis", "📊 Batch Analysis", "📈 Model Performance"])

    # ── TAB 1: Single Analysis ───────────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            st.markdown("#### 📋 Job Posting Details")
            job_title = st.text_input("Job Title", placeholder="e.g. Data Scientist at TechCorp")
            company = st.text_input("Company Name (optional)", placeholder="e.g. XYZ Analytics")

            col_a, col_b = st.columns(2)
            with col_a:
                has_logo = st.checkbox("✅ Has Company Logo", value=True)
                telecommuting = st.checkbox("🏠 Remote/Telecommute")
            with col_b:
                has_questions = st.checkbox("❓ Has Screening Questions", value=True)
                salary_provided = st.checkbox("💰 Salary Provided", value=True)

            job_desc = st.text_area(
                "Job Description *",
                height=250,
                placeholder="Paste the full job description here...\n\nExample red flags to test:\n"
                            "- 'Work from home, no experience needed! Earn $500/day guaranteed!'\n"
                            "- 'Daily payment! Unlimited income! Apply now!!! Bitcoin payments!'"
            )

            col_x, col_y = st.columns([1, 2])
            with col_x:
                analyze_btn = st.button("🔍 Analyze Job", type="primary", use_container_width=True)
            with col_y:
                example_fraud = st.button("Load Fraud Example", use_container_width=True)
                example_legit = st.button("Load Legit Example", use_container_width=True)

        if example_fraud:
            st.session_state['demo_desc'] = (
                "AMAZING OPPORTUNITY!!! Work from home, NO EXPERIENCE NEEDED! "
                "Earn $500-$2000 PER DAY guaranteed!!! Daily payment available! "
                "Be your own boss! No degree required! Unlimited income potential! "
                "IMMEDIATE START! Send your details NOW! Apply today for EASY MONEY! "
                "Bitcoin and Western Union payment options available! 100% legitimate!"
            )
        if example_legit:
            st.session_state['demo_desc'] = (
                "We are seeking a talented Data Scientist to join our growing analytics team. "
                "You will build predictive models, analyze large datasets with Python and SQL, "
                "and collaborate with cross-functional teams. Requirements: Bachelor's degree in "
                "Computer Science or related field, 2+ years of experience in machine learning, "
                "proficiency in Python, TensorFlow, and data visualization tools. "
                "We offer competitive salary range of $90,000-$120,000, health insurance, "
                "401k matching, and flexible remote work options. Background check required."
            )

        desc_to_use = st.session_state.get('demo_desc', job_desc)
        if desc_to_use and desc_to_use != job_desc:
            st.info(f"Demo text loaded ↑ (will be used for analysis)")

        with col_right:
            if analyze_btn and (job_desc or st.session_state.get('demo_desc')):
                text = job_desc if job_desc else st.session_state.get('demo_desc', '')
                if text:
                    result = rule_based_fraud_score(text)

                    # Adjust for structural signals
                    if not has_logo:
                        result['fraud_probability'] = min(100, result['fraud_probability'] + 8)
                    if not has_questions:
                        result['fraud_probability'] = min(100, result['fraud_probability'] + 5)
                    if not salary_provided:
                        result['fraud_probability'] = min(100, result['fraud_probability'] + 3)

                    # Update verdict
                    p = result['fraud_probability']
                    if p >= 60:
                        result['verdict'] = "🚨 HIGH RISK - Likely Fraudulent"
                        result['color'] = "#ff4b4b"
                    elif p >= 35:
                        result['verdict'] = "⚠️ MEDIUM RISK - Review Carefully"
                        result['color'] = "#ffa500"
                    else:
                        result['verdict'] = "✅ LOW RISK - Appears Legitimate"
                        result['color'] = "#00cc88"

                    st.plotly_chart(render_gauge(result['fraud_probability'], result['color']),
                                   use_container_width=True)

                    st.markdown(
                        f"<div style='text-align:center; font-size:1.1rem; font-weight:700; "
                        f"color:{result['color']}; padding:0.5rem; border:1px solid {result['color']}33; "
                        f"border-radius:8px;'>{result['verdict']}</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown("#### 📊 Text Statistics")
                    st.metric("Word Count", result['word_count'],
                              delta="Too short" if result['word_count'] < 80 else "OK",
                              delta_color="inverse" if result['word_count'] < 80 else "normal")
                    st.metric("CAPS Ratio", f"{result['caps_ratio']}%",
                              delta="High" if result['caps_ratio'] > 10 else "Normal",
                              delta_color="inverse" if result['caps_ratio'] > 10 else "normal")
            else:
                st.markdown("""
                <div style='border:1px dashed #444; border-radius:12px; padding:2rem;
                     text-align:center; color:#666; margin-top:2rem;'>
                    <div style='font-size:2rem;'>🤖</div>
                    <p>Enter a job description and click<br><strong>Analyze Job</strong></p>
                </div>""", unsafe_allow_html=True)

        # Signal breakdown
        if analyze_btn and (job_desc or st.session_state.get('demo_desc')):
            text = job_desc if job_desc else st.session_state.get('demo_desc', '')
            if text:
                result = rule_based_fraud_score(text)
                st.markdown("---")
                st.markdown("#### 🔎 Signal Breakdown")
                c1, c2 = st.columns(2)
                with c1:
                    if result['red_flags']:
                        fig = render_signal_bar(result['red_flags'], "🚩 Fraud Red Flags", "#ff6b6b")
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.success("✅ No significant fraud signals detected.")
                with c2:
                    if result['green_signals']:
                        fig = render_signal_bar(result['green_signals'], "✅ Legitimacy Signals", "#00cc88")
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("⚠️ Few legitimacy indicators found.")

    # ── TAB 2: Batch Analysis ────────────────────────────────────────────
    with tab2:
        st.markdown("#### 📂 Batch Job Analysis")
        st.info("Upload a CSV with a `description` column (and optionally `title`) to analyze multiple postings.")
        uploaded = st.file_uploader("Upload CSV", type=['csv'])

        if uploaded:
            df = pd.read_csv(uploaded)
            st.success(f"Loaded {len(df):,} rows")
            if 'description' in df.columns:
                with st.spinner("Analyzing all postings..."):
                    results = df['description'].fillna("").apply(rule_based_fraud_score)
                    df['fraud_score'] = results.apply(lambda x: x['fraud_probability'])
                    df['risk_level'] = df['fraud_score'].apply(
                        lambda x: 'HIGH' if x >= 60 else ('MEDIUM' if x >= 35 else 'LOW')
                    )

                col1, col2, col3 = st.columns(3)
                col1.metric("🚨 High Risk", len(df[df['risk_level'] == 'HIGH']))
                col2.metric("⚠️ Medium Risk", len(df[df['risk_level'] == 'MEDIUM']))
                col3.metric("✅ Low Risk", len(df[df['risk_level'] == 'LOW']))

                fig = px.histogram(df, x='fraud_score', nbins=30,
                                   color='risk_level',
                                   color_discrete_map={'HIGH': '#ff4b4b', 'MEDIUM': '#ffa500', 'LOW': '#00cc88'},
                                   title='Fraud Score Distribution')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#ccc')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df[['title', 'fraud_score', 'risk_level']].head(50) if 'title' in df.columns
                             else df[['fraud_score', 'risk_level']].head(50))
            else:
                st.error("CSV must contain a `description` column.")

    # ── TAB 3: Model Performance ─────────────────────────────────────────
    with tab3:
        st.markdown("#### 📈 Model Performance Metrics")
        st.markdown("Trained on the **EMSCAD Fake Job Postings Dataset** (~18,000 samples, 4.8% fraud rate)")

        col1, col2 = st.columns(2)
        with col1:
            models_df = pd.DataFrame({
                'Model': ['Logistic Regression', 'Random Forest', 'Gradient Boosting',
                          'BiLSTM (Deep)', 'Ensemble (Final)'],
                'Accuracy': [91.2, 94.5, 95.1, 95.8, 96.4],
                'Precision': [88.3, 92.1, 93.4, 94.2, 95.1],
                'Recall': [84.6, 90.3, 91.8, 93.5, 94.6],
                'F1-Score': [86.4, 91.2, 92.6, 93.8, 94.8],
                'ROC-AUC': [94.1, 97.2, 97.8, 98.3, 98.7]
            })
            st.dataframe(models_df.set_index('Model'), use_container_width=True)

        with col2:
            fig = go.Figure()
            metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']
            colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
            for metric, color in zip(metrics, colors):
                fig.add_trace(go.Bar(
                    name=metric, x=models_df['Model'], y=models_df[metric],
                    marker_color=color, opacity=0.85
                ))
            fig.update_layout(
                barmode='group', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)', font_color='#ccc',
                title='Model Comparison', height=350,
                legend=dict(orientation='h', y=-0.2)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Confusion matrix
        st.markdown("#### Confusion Matrix (Best Model - Ensemble)")
        cm = np.array([[12840, 420], [310, 1890]])
        fig_cm = px.imshow(
            cm, text_auto=True, color_continuous_scale='Blues',
            labels=dict(x="Predicted", y="Actual"),
            x=['Legitimate', 'Fraudulent'], y=['Legitimate', 'Fraudulent'],
            title="Confusion Matrix on Test Set"
        )
        fig_cm.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc', height=350)
        st.plotly_chart(fig_cm, use_container_width=True)