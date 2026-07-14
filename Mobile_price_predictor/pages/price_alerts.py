"""
pages/price_alerts.py
---------------------
Set a target price — get flagged when a prediction hits it.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.style  import get_custom_css
from utils.helper import BRANDS, CONDITIONS
from utils.db     import add_alert, get_alerts, delete_alert

st.set_page_config(
    page_title="Price Alerts",
    page_icon="🔔",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.markdown('<div class="eyebrow">WATCHLIST</div>', unsafe_allow_html=True)
st.title("🔔 Price Alerts")
st.caption(
    "Set a target price — we'll flag it every time a prediction falls at or "
    "below your threshold."
)

# ── Add alert ─────────────────────────────────────────────────────────────────
st.markdown('<div class="ticket">', unsafe_allow_html=True)
st.markdown('<div class="ticket-label">NEW ALERT</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    a_brand     = st.selectbox("Brand",       BRANDS,     key="a_brand")
with c2:
    a_condition = st.selectbox("Condition",   CONDITIONS, key="a_cond")
with c3:
    a_ram       = st.selectbox("Min RAM (GB)", [2, 3, 4, 6, 8, 12, 16], index=3, key="a_ram")
with c4:
    a_storage   = st.selectbox(
        "Min Storage (GB)", [32, 64, 128, 256, 512], index=2, key="a_stor"
    )

a_target = st.number_input(
    "Target Price — alert when predicted ≤ this (₹)",
    min_value=1_000, max_value=250_000, value=20_000, step=500,
)

if st.button("➕ Add Alert", use_container_width=True):
    add_alert(a_brand, a_ram, a_storage, a_condition, a_target)
    st.success(
        f"Alert set: {a_brand} ({a_condition}) · "
        f"{a_ram}GB RAM · {a_storage}GB · ≤ ₹{a_target:,}"
    )
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ── Active alerts ─────────────────────────────────────────────────────────────
st.markdown('<div class="ticket" style="margin-top:14px">', unsafe_allow_html=True)
st.markdown('<div class="ticket-label">ACTIVE ALERTS</div>', unsafe_allow_html=True)

alerts_df = get_alerts()

if alerts_df.empty:
    st.markdown(
        '<div class="price-sub">No alerts set yet. Add one above.</div>',
        unsafe_allow_html=True,
    )
else:
    active = alerts_df[alerts_df["triggered"] == 0]
    fired  = alerts_df[alerts_df["triggered"] == 1]

    if not active.empty:
        st.markdown("**Watching:**")
        for _, row in active.iterrows():
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(
                    f'<div class="alert-row">'
                    f'<span>🔔 <b>{row["brand"]}</b> · {row["condition"]} · '
                    f'{row["ram"]}GB RAM · {row["storage"]}GB</span>'
                    f'<span style="color:#C9A24B">≤ ₹{row["target"]:,.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_b:
                if st.button("✕", key=f"del_{row['id']}"):
                    delete_alert(int(row["id"]))
                    st.rerun()
    else:
        st.markdown(
            '<div class="price-sub">No active alerts.</div>',
            unsafe_allow_html=True,
        )

    if not fired.empty:
        st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
        st.markdown("**Triggered:**")
        for _, row in fired.iterrows():
            st.markdown(
                f'<div class="alert-row" style="opacity:0.5">'
                f'<span>✅ <b>{row["brand"]}</b> · {row["condition"]} · '
                f'{row["ram"]}GB RAM</span>'
                f'<span style="color:#3FB876">₹{row["target"]:,.0f} — HIT</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown('</div>', unsafe_allow_html=True)

# ── How it works ──────────────────────────────────────────────────────────────
st.markdown('<div class="ticket" style="margin-top:14px">', unsafe_allow_html=True)
st.markdown('<div class="ticket-label">HOW IT WORKS</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div style="font-family:monospace;font-size:0.82rem;color:#7D8590;line-height:2">
    1. Set a brand, condition, minimum specs, and your target price.<br>
    2. Go to the <b style="color:#C9A24B">Predictor</b> page and run a valuation.<br>
    3. If the predicted price falls at or below your target, the alert fires.<br>
    4. Use this as your buy signal — if the model says the phone is worth your target
       or less, it may be a deal worth acting on.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)
