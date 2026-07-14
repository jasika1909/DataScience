"""
app.py
------
Landing page / home screen for The Appraisal Desk.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.style  import get_custom_css
from utils.helper import DATA_PATH, MODEL_PATH, SCALER_PATH, ENCODER_PATH, BASE_DIR

st.set_page_config(
    page_title="The Appraisal Desk",
    page_icon="📱",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="eyebrow">AI-POWERED MOBILE VALUATION & DEAL INTELLIGENCE</div>',
    unsafe_allow_html=True,
)
st.markdown("# The Appraisal Desk")
st.markdown(
    "**Smart price prediction for new & used phones — with explainability, "
    "negotiation AI, and deal intelligence.**"
)
st.write("")

# ── Feature grid ──────────────────────────────────────────────────────────────
FEATURES = [
    ("🔮", "AI Price Prediction",
     "XGBoost model trained on 5,000 synthetic Indian-market listings"),
    ("📷", "Image Condition Scan",
     "Upload a photo — OpenCV analyses sharpness, brightness & scratches"),
    ("💡", "Explainable AI (SHAP)",
     "Waterfall chart shows exactly why the model priced it this way"),
    ("📊", "Interactive Analytics",
     "Plotly EDA — price distribution, brand comparison, correlation heatmap"),
    ("🤝", "Negotiation Assistant",
     "Gemini AI writes your counter-offer script and spots red flags"),
    ("📉", "Depreciation Forecast",
     "See your phone's value 1–5 years from now with brand-specific decay"),
    ("📄", "PDF Valuation Report",
     "Download a professional appraisal slip with all details"),
    ("🔔", "Price Alerts",
     "Set a target price — get flagged when a prediction hits it"),
    ("🗄️", "Prediction History",
     "Every appraisal saved to SQLite — browse your full history"),
]

rows = [FEATURES[i:i+3] for i in range(0, len(FEATURES), 3)]
for row in rows:
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, row):
        col.markdown(
            f'<div class="ticket" style="min-height:110px">'
            f'<div style="font-size:1.6rem">{icon}</div>'
            f'<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
            f'color:#E6EDF3;margin:4px 0 6px">{title}</div>'
            f'<div style="font-size:0.8rem;color:#7D8590;line-height:1.5">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.write("")

# ── System status + dataset snapshot ─────────────────────────────────────────
status_col, chart_col = st.columns([1, 2], gap="large")

with status_col:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">SYSTEM STATUS</div>', unsafe_allow_html=True)

    checks = [
        ("Model (XGBoost)", os.path.exists(MODEL_PATH)),
        ("Scaler",          os.path.exists(SCALER_PATH)),
        ("Encoder",         os.path.exists(ENCODER_PATH)),
        ("Dataset",         os.path.exists(DATA_PATH)),
    ]
    all_ok = all(ok for _, ok in checks)
    for label, ok in checks:
        icon  = "✅" if ok else "❌"
        color = "#3FB876" if ok else "#E2574C"
        st.markdown(
            f'<div style="font-family:monospace;font-size:0.82rem;'
            f'color:{color};margin:4px 0">{icon} {label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
    if not all_ok:
        st.markdown(
            '<div class="price-sub" style="color:#E2574C">'
            'Run: python train_model.py</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="price-sub" style="color:#3FB876">All systems ready</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">TECH STACK</div>', unsafe_allow_html=True)
    tags = [
        "XGBoost", "SHAP", "OpenCV", "Gemini AI",
        "SQLite", "fpdf2", "Plotly", "Streamlit", "Scikit-learn",
    ]
    st.markdown(
        " ".join(f'<span class="feature-tag">{t}</span>' for t in tags),
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with chart_col:
    if os.path.exists(DATA_PATH):
        st.markdown('<div class="ticket">', unsafe_allow_html=True)
        st.markdown(
            '<div class="ticket-label">DATASET SNAPSHOT</div>',
            unsafe_allow_html=True,
        )
        df  = pd.read_csv(DATA_PATH)
        fig = px.histogram(
            df, x="Price", color="Brand",
            nbins=50, barmode="overlay", opacity=0.75,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
            font=dict(color="#E6EDF3"),
            margin=dict(t=10, b=30, l=30, r=10),
            xaxis=dict(title="Price (₹)", gridcolor="#21262D", color="#7D8590"),
            yaxis=dict(title="Count",     gridcolor="#21262D", color="#7D8590"),
            legend=dict(
                bgcolor="#161B22", font=dict(size=9),
                bordercolor="#30363D", borderwidth=1,
            ),
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            f'<div class="price-sub">'
            f'{len(df):,} synthetic Indian-market listings · '
            f'{df["Brand"].nunique()} brands · '
            f'₹{df.Price.min():,.0f} – ₹{df.Price.max():,.0f}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

st.write("")
st.caption(
    "👈 Use the sidebar to navigate to Predictor, Analytics, "
    "Negotiation Assistant, Depreciation Forecast, and Price Alerts."
)
