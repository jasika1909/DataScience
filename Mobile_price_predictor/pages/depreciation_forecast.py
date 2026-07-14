"""
pages/depreciation_forecast.py
-------------------------------
Brand-specific depreciation curve with multi-brand comparison.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from utils.style  import get_custom_css
from utils.helper import (
    BRANDS, FIVEG, CONDITIONS, MODEL_PATH,
    load_artifacts, build_feature_frame, transform_features, price_range,
)

st.set_page_config(
    page_title="Depreciation Forecast",
    page_icon="📉",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.markdown('<div class="eyebrow">FUTURE VALUE PROJECTIONS</div>', unsafe_allow_html=True)
st.title("📉 Depreciation Forecast")
st.caption("See how your phone's value is expected to decay over the next 5 years.")

# Brand-specific annual depreciation rates (empirical approximations)
BRAND_DEPR = {
    "Apple":    0.13,
    "Samsung":  0.18,
    "Google":   0.17,
    "OnePlus":  0.20,
    "Nothing":  0.22,
    "Motorola": 0.22,
    "Xiaomi":   0.24,
    "Realme":   0.25,
    "Vivo":     0.24,
    "Oppo":     0.24,
}
COMP_COLORS = ["#58A6FF", "#3FB876", "#E2574C", "#A78BFA", "#F97316"]

# ── Guard: model must exist ────────────────────────────────────────────────────
if not os.path.exists(MODEL_PATH):
    st.warning("Model not found. Run `python train_model.py` first.")
    st.stop()

model, scaler, encoder = load_artifacts()

# ── Input panel ───────────────────────────────────────────────────────────────
st.markdown('<div class="ticket">', unsafe_allow_html=True)
st.markdown('<div class="ticket-label">PHONE SPECS</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    brand     = st.selectbox("Brand", BRANDS)
    condition = st.radio("Condition", CONDITIONS, horizontal=True)
with c2:
    ram     = st.selectbox("RAM (GB)",     [2, 3, 4, 6, 8, 12, 16], index=4)
    storage = st.selectbox("Storage (GB)", [32, 64, 128, 256, 512],   index=2)
with c3:
    battery = st.slider("Battery (mAh)", 2500, 7000, 5000, 100)
    camera  = st.selectbox("Camera (MP)", [8, 12, 16, 32, 48, 50, 64, 108, 200], index=5)
with c4:
    screen = st.slider("Screen (in)", 4.5, 7.5, 6.5, 0.1)
    fiveg  = st.radio("5G", FIVEG, horizontal=True)

current_age = st.slider("Current phone age (years)", 0.0, 5.0, 0.0, 0.5)
compare_brands = st.multiselect(
    "Compare with other brands",
    [b for b in BRANDS if b != brand],
    default=[],
)

forecast_btn = st.button("📈 Generate Forecast", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Forecast ──────────────────────────────────────────────────────────────────
if forecast_btn:
    def _predict_at_age(age_val: float) -> float:
        df_row = build_feature_frame(
            brand, ram, storage, battery, camera, screen, fiveg, age_val, condition
        )
        X, _ = transform_features(df_row, encoder, scaler)
        return max(0.0, float(model.predict(X)[0]))

    base_price = _predict_at_age(current_age)
    low, high  = price_range(base_price)

    rate  = BRAND_DEPR.get(brand, 0.20)
    years = np.arange(0, 5.5, 0.5)
    prices = [base_price * ((1 - rate) ** y) for y in years]
    ages   = current_age + years

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = go.Figure()

    # Main brand curve
    fig.add_trace(go.Scatter(
        x=ages, y=prices,
        mode="lines+markers",
        name=brand,
        line=dict(color="#C9A24B", width=3),
        marker=dict(size=6, color="#C9A24B"),
        hovertemplate="Age: %{x:.1f} yr<br>Value: ₹%{y:,.0f}<extra></extra>",
    ))

    # Confidence band (±8 %)
    fig.add_trace(go.Scatter(
        x=np.concatenate([ages, ages[::-1]]),
        y=[p * 1.08 for p in prices] + [p * 0.92 for p in prices][::-1],
        fill="toself",
        fillcolor="rgba(201,162,75,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Comparison brands
    for i, cbrand in enumerate(compare_brands):
        crate   = BRAND_DEPR.get(cbrand, 0.20)
        cprices = [base_price * ((1 - crate) ** y) for y in years]
        fig.add_trace(go.Scatter(
            x=ages, y=cprices,
            mode="lines",
            name=cbrand,
            line=dict(color=COMP_COLORS[i % len(COMP_COLORS)], width=2, dash="dot"),
            hovertemplate="Age: %{x:.1f} yr<br>Value: ₹%{y:,.0f}<extra></extra>",
        ))

    # Current-age marker
    fig.add_vline(
        x=current_age, line_dash="dash",
        line_color="#7D8590",
        annotation_text="Now",
        annotation_font_color="#7D8590",
    )

    fig.update_layout(
        paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
        font=dict(color="#E6EDF3", family="Inter"),
        xaxis=dict(title="Phone Age (years)", gridcolor="#21262D", color="#7D8590"),
        yaxis=dict(
            title="Estimated Value (₹)", gridcolor="#21262D",
            color="#7D8590", tickformat=",.0f",
        ),
        legend=dict(bgcolor="#161B22", bordercolor="#30363D", borderwidth=1),
        hovermode="x unified",
        margin=dict(t=30, b=40, l=60, r=20),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Value milestones ──────────────────────────────────────────────────────
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">VALUE MILESTONES</div>', unsafe_allow_html=True)

    milestones = [0, 1, 2, 3, 5]
    m_cols = st.columns(len(milestones))
    for col, y in zip(m_cols, milestones):
        p        = base_price * ((1 - rate) ** y)
        loss_pct = (1 - p / base_price) * 100
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-val">₹{p:,.0f}</div>'
            f'<div class="metric-lbl">+{current_age + y:.0f} yr age</div>'
            f'<div style="font-size:0.68rem;color:#E2574C;margin-top:4px;">'
            f'{"—" if y == 0 else f"−{loss_pct:.0f}% lost"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Sell-window analysis ──────────────────────────────────────────────────
    st.markdown('<div class="ticket" style="margin-top:14px">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">SELL WINDOW ANALYSIS</div>', unsafe_allow_html=True)

    drop_yr1 = base_price - base_price * (1 - rate) ** 1
    drop_yr2 = base_price * (1 - rate) ** 1 - base_price * (1 - rate) ** 2

    if current_age < 1:
        sell_tip = "within the next 6 months"
    elif current_age >= 2:
        sell_tip = "soon — value is declining fast"
    else:
        sell_tip = "in the next 3–6 months"

    st.markdown(
        "<div style=\"font-family:monospace;font-size:0.85rem;color:#E6EDF3;line-height:2\">"
        f"💡 <b style=\"color:#C9A24B\">{brand}</b> phones lose ~"
        f"<b style=\"color:#E2574C\">{rate * 100:.0f}%</b> of value per year.<br>"
        f"📅 You will lose ~<b style=\"color:#E2574C\">Rs.{drop_yr1:,.0f}</b> in the first year, "
        f"then ~<b style=\"color:#E2574C\">Rs.{drop_yr2:,.0f}</b> in year two.<br>"
        f"🏷️ <b>Best sell window:</b> {sell_tip}"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info(
        "Configure the phone specs above and click **Generate Forecast** "
        "to see the depreciation curve."
    )
