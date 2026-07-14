"""
pages/analytics.py
------------------
EDA, dataset insights, global feature importance, and prediction history.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.style  import get_custom_css
from utils.helper import DATA_PATH, BASE_DIR
from utils.db     import get_history

# Shared Plotly dark theme
DARK = dict(
    paper_bgcolor="#0D1117",
    plot_bgcolor="#0D1117",
    font=dict(color="#E6EDF3", family="Inter"),
    margin=dict(t=40, b=40, l=40, r=20),
)

st.set_page_config(
    page_title="Analytics · The Ledger",
    page_icon="📊",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.markdown('<div class="eyebrow">MARKET INTELLIGENCE</div>', unsafe_allow_html=True)
st.title("📊 Analytics Ledger")
st.caption("EDA, dataset insights, and your personal prediction history.")

if not os.path.exists(DATA_PATH):
    st.error("Dataset not found. Run `python train_model.py` first.")
    st.stop()

df = pd.read_csv(DATA_PATH)

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    brands_sel  = st.multiselect(
        "Brands",
        sorted(df["Brand"].unique()),
        default=sorted(df["Brand"].unique()),
    )
    conds_sel   = st.multiselect("Condition", ["New", "Used"], default=["New", "Used"])
    price_rng   = st.slider(
        "Price range (₹)",
        int(df.Price.min()), int(df.Price.max()),
        (int(df.Price.min()), int(df.Price.max())),
        1000,
    )

filtered = df[
    df["Brand"].isin(brands_sel)
    & df["Condition"].isin(conds_sel)
    & df["Price"].between(*price_rng)
]
st.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** records")
st.write("")

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
kpis = [
    ("Avg Price",    f"₹{filtered.Price.mean():,.0f}"),
    ("Median Price", f"₹{filtered.Price.median():,.0f}"),
    ("Min Price",    f"₹{filtered.Price.min():,.0f}"),
    ("Max Price",    f"₹{filtered.Price.max():,.0f}"),
    ("Records",      f"{len(filtered):,}"),
]
for col, (lbl, val) in zip([k1, k2, k3, k4, k5], kpis):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-val" style="font-size:1.2rem">{val}</div>'
        f'<div class="metric-lbl">{lbl}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
st.write("")

# ── Row 1: Price distribution + Brand avg price ───────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">PRICE DISTRIBUTION</div>', unsafe_allow_html=True)
    fig = px.histogram(
        filtered, x="Price", nbins=50, color="Condition",
        color_discrete_map={"New": "#C9A24B", "Used": "#58A6FF"},
        barmode="overlay", opacity=0.8,
    )
    fig.update_layout(**DARK, xaxis_title="Price (₹)", yaxis_title="Count",
                      legend=dict(bgcolor="#161B22", bordercolor="#30363D", borderwidth=1))
    fig.update_xaxes(gridcolor="#21262D")
    fig.update_yaxes(gridcolor="#21262D")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">BRAND VS AVERAGE PRICE</div>', unsafe_allow_html=True)
    brand_avg = (
        filtered.groupby("Brand")["Price"]
        .mean()
        .sort_values(ascending=True)
        .reset_index()
    )
    fig2 = px.bar(
        brand_avg, x="Price", y="Brand", orientation="h",
        color="Price", color_continuous_scale=["#21262D", "#C9A24B"],
    )
    fig2.update_layout(
        **DARK,
        xaxis_title="Avg Price (₹)", yaxis_title="",
        coloraxis_showscale=False, height=380,
    )
    fig2.update_xaxes(gridcolor="#21262D")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 2: New vs Used box + 5G violin ────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">NEW VS USED PRICE SPREAD</div>', unsafe_allow_html=True)
    fig3 = px.box(
        filtered, x="Brand", y="Price", color="Condition",
        color_discrete_map={"New": "#C9A24B", "Used": "#58A6FF"},
    )
    fig3.update_layout(
        **DARK,
        xaxis_title="", yaxis_title="Price (₹)",
        legend=dict(bgcolor="#161B22"),
        xaxis=dict(tickangle=-30, gridcolor="#21262D"),
        yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">5G PREMIUM ANALYSIS</div>', unsafe_allow_html=True)
    fig4 = px.violin(
        filtered, x="FiveG", y="Price", color="FiveG",
        color_discrete_map={"Yes": "#3FB876", "No": "#E2574C"},
        box=True, points=False,
    )
    fig4.update_layout(
        **DARK,
        xaxis_title="5G Support", yaxis_title="Price (₹)",
        showlegend=False,
        yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 3: Correlation heatmap + RAM vs Price scatter ─────────────────────────
c5, c6 = st.columns(2)

with c5:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">CORRELATION HEATMAP</div>', unsafe_allow_html=True)
    num_cols = ["RAM", "Storage", "Battery", "Camera", "ScreenSize", "PhoneAge", "Price"]
    corr = filtered[num_cols].corr()
    fig5 = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns,
        colorscale=[[0, "#E2574C"], [0.5, "#21262D"], [1, "#3FB876"]],
        zmin=-1, zmax=1,
        text=corr.values.round(2), texttemplate="%{text}",
        hovertemplate="%{x} / %{y}: %{z:.2f}<extra></extra>",
    ))
    fig5.update_layout(**DARK, height=380)
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c6:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ticket-label">RAM × STORAGE VS PRICE (SCATTER)</div>',
        unsafe_allow_html=True,
    )
    fig6 = px.scatter(
        filtered, x="RAM", y="Price", color="Brand", size="Storage",
        hover_data=["Condition", "Camera"],
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig6.update_layout(
        **DARK,
        xaxis_title="RAM (GB)", yaxis_title="Price (₹)",
        legend=dict(
            bgcolor="#161B22", bordercolor="#30363D",
            borderwidth=1, font=dict(size=9),
        ),
        xaxis=dict(gridcolor="#21262D"),
        yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 4: Global feature importance ──────────────────────────────────────────
fi_path = os.path.join(BASE_DIR, "data", "feature_importance.csv")
if os.path.exists(fi_path):
    st.markdown('<div class="ticket">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ticket-label">GLOBAL FEATURE IMPORTANCE (XGBoost)</div>',
        unsafe_allow_html=True,
    )
    fi_df = pd.read_csv(fi_path).head(15)
    fi_df["feature"] = (
        fi_df["feature"]
        .str.replace("Brand_",     "Brand:")
        .str.replace("Condition_", "Cond:")
        .str.replace("FiveG_",     "5G:")
    )
    fig7 = px.bar(
        fi_df, x="importance", y="feature", orientation="h",
        color="importance", color_continuous_scale=["#21262D", "#C9A24B"],
    )
    fig7.update_layout(
        **DARK,
        xaxis_title="Importance", yaxis_title="",
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig7, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 5: Prediction history ─────────────────────────────────────────────────
st.markdown('<div class="ticket">', unsafe_allow_html=True)
st.markdown(
    '<div class="ticket-label">YOUR PREDICTION HISTORY</div>',
    unsafe_allow_html=True,
)
hist = get_history(50)
if hist.empty:
    st.markdown(
        '<div class="price-sub">No predictions yet — use the Predictor page to get started.</div>',
        unsafe_allow_html=True,
    )
else:
    hist["predicted"] = hist["predicted"].map(lambda x: f"₹{x:,.0f}")
    hist["listed"]    = hist["listed"].map(lambda x: f"₹{x:,.0f}" if x > 0 else "—")
    display_cols      = ["ts", "brand", "condition", "ram", "storage", "predicted", "listed", "verdict"]
    available         = [c for c in display_cols if c in hist.columns]
    st.dataframe(
        hist[available].rename(columns={
            "ts": "Time", "brand": "Brand", "condition": "Condition",
            "ram": "RAM", "storage": "Storage",
            "predicted": "Predicted", "listed": "Listed", "verdict": "Verdict",
        }),
        use_container_width=True,
        hide_index=True,
    )
st.markdown('</div>', unsafe_allow_html=True)
