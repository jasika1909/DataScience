"""
pages/predictor.py
------------------
Full AI appraisal page: specs → XGBoost price prediction → SHAP explanation
→ image condition scan → depreciation preview → PDF download.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import streamlit as st
import joblib

from utils.style  import get_custom_css, stamp_class
from utils.helper import (
    BRANDS, FIVEG, CONDITIONS,
    MODEL_PATH, METRICS_PATH, BASE_DIR,
    load_artifacts, build_feature_frame, transform_features,
    price_category, value_for_money_score, price_range,
    depreciation_forecast,
)
from utils.db    import save_prediction, check_and_trigger_alerts
from utils.shap  import plot_shap_waterfall, plot_feature_importance
from utils.image import assess_condition
from utils.pdf   import generate_report

st.set_page_config(
    page_title="Predictor · Appraisal Desk",
    page_icon="🔮",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.markdown('<div class="eyebrow">WALK-IN APPRAISAL</div>', unsafe_allow_html=True)
st.title("🔮 Phone Predictor")
st.caption("Full AI appraisal — specs in, fair price + explainability + report out.")

# ── Guard: model must exist ────────────────────────────────────────────────────
if not os.path.exists(MODEL_PATH):
    st.error("Model not found. Run `python train_model.py` first.")
    st.stop()

model, scaler, encoder = load_artifacts()

# ── Model metrics banner ───────────────────────────────────────────────────────
if os.path.exists(METRICS_PATH):
    m = joblib.load(METRICS_PATH)
    mc1, mc2, mc3, mc4 = st.columns(4)
    for col, val, lbl in [
        (mc1, f"{m['r2']:.3f}",         "R² Score"),
        (mc2, f"₹{m['mae']:,.0f}",       "Mean Abs Error"),
        (mc3, f"₹{m['rmse']:,.0f}",      "RMSE"),
        (mc4, "XGBoost",                  "Model"),
    ]:
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-val">{val}</div>'
            f'<div class="metric-lbl">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.write("")

# ── Two-column layout ──────────────────────────────────────────────────────────
left, right = st.columns([1, 1.2], gap="large")

with left:
    st.markdown('<div class="ticket">', unsafe_allow_html=True)

    # Section 1 — Identity
    st.markdown('<div class="ticket-label">01 · IDENTITY</div>', unsafe_allow_html=True)
    brand     = st.selectbox("Brand", BRANDS)
    condition = st.radio("Condition", CONDITIONS, horizontal=True)

    # Section 2 — Hardware
    st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">02 · HARDWARE</div>', unsafe_allow_html=True)
    ram     = st.select_slider("RAM (GB)",     [2, 3, 4, 6, 8, 12, 16], value=8)
    storage = st.select_slider("Storage (GB)", [32, 64, 128, 256, 512],  value=128)
    battery = st.slider("Battery (mAh)",        2500, 7000, 5000, 100)
    camera  = st.select_slider("Camera (MP)",   [8, 12, 16, 32, 48, 50, 64, 108, 200], value=48)
    screen  = st.slider("Screen Size (in)",     4.5, 7.5, 6.5, 0.1)
    fiveg   = st.radio("5G Support", FIVEG, horizontal=True)

    # Section 3 — Wear & listing
    st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ticket-label">03 · WEAR & LISTING</div>', unsafe_allow_html=True)
    age          = st.slider("Phone Age (years)", 0.0, 6.0, 1.0, 0.5)
    listed_price = st.number_input(
        "Listed / Asking Price (₹) — optional",
        min_value=0.0, value=0.0, step=500.0,
    )

    # Section 4 — Image scan
    st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ticket-label">04 · IMAGE CONDITION SCAN (OPTIONAL)</div>',
        unsafe_allow_html=True,
    )
    uploaded_img = st.file_uploader(
        "Upload phone photo for AI condition scan",
        type=["jpg", "jpeg", "png", "webp"],
    )
    st.markdown('</div>', unsafe_allow_html=True)

    predict_btn = st.button("Appraise This Phone →", use_container_width=True)

# ── Right column — results ─────────────────────────────────────────────────────
with right:
    if predict_btn:

        # --- Image condition assessment -----------------------------------
        img_result = None
        if uploaded_img:
            img_bytes  = uploaded_img.read()
            img_result = assess_condition(img_bytes)
            ai_cond    = img_result["condition"]

            st.markdown('<div class="ticket">', unsafe_allow_html=True)
            st.markdown(
                '<div class="ticket-label">📷 IMAGE CONDITION SCAN</div>',
                unsafe_allow_html=True,
            )
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                st.image(img_bytes, use_column_width=True)
            with sc2:
                score_color = (
                    "#3FB876" if img_result["score"] >= 75
                    else ("#C9A24B" if img_result["score"] >= 50 else "#E2574C")
                )
                st.markdown(
                    f'<div class="metric-val" style="color:{score_color}">'
                    f'{img_result["score"]}/100</div>'
                    f'<div class="metric-lbl">{img_result["label"]} condition</div>'
                    f'<div style="margin-top:8px;font-size:0.78rem;color:#7D8590">'
                    + "".join(f"• {i}<br>" for i in img_result["issues"])
                    + "</div>",
                    unsafe_allow_html=True,
                )
                if img_result["deduction"] > 0:
                    st.warning(
                        f"Suggested price deduction: {img_result['deduction']}%"
                    )
            st.markdown('</div>', unsafe_allow_html=True)

            # Override user-supplied condition with AI result
            condition = ai_cond

        # --- Prediction ---------------------------------------------------
        df_input            = build_feature_frame(
            brand, ram, storage, battery, camera, screen, fiveg, age, condition
        )
        X_scaled, feat_names = transform_features(df_input, encoder, scaler)
        predicted            = float(model.predict(X_scaled)[0])

        # Apply image deduction if applicable
        if img_result and img_result["deduction"] > 0:
            predicted *= 1 - img_result["deduction"] / 100

        predicted = max(0.0, round(predicted, 2))
        low, high = price_range(predicted)
        vfm       = value_for_money_score(ram, storage, battery, camera, screen, predicted)
        depr      = depreciation_forecast(predicted, age)

        # --- Valuation slip -----------------------------------------------
        st.markdown('<div class="ticket">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">APPRAISED VALUE</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="price-mono">₹{predicted:,.0f}</div>'
            f'<div class="price-sub">range  ₹{low:,.0f} – ₹{high:,.0f}</div>'
            f'<span class="vfm-pill">VALUE FOR MONEY · {vfm} / 100</span>',
            unsafe_allow_html=True,
        )

        verdict    = ""
        suggestion = ""
        category   = "—"

        if listed_price > 0:
            category, suggestion = price_category(predicted, listed_price)
            cls = stamp_class(category)
            st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stamp {cls}">{category.upper()}</div>'
                f'<div class="price-sub" style="margin-top:8px">{suggestion}</div>',
                unsafe_allow_html=True,
            )
            verdict = suggestion

            # Fire any matching price alerts
            triggered = check_and_trigger_alerts(brand, condition, predicted)
            for t in triggered:
                st.success(
                    f"🔔 Price alert triggered!  "
                    f"{t['brand']} ({t['condition']}) ≤ ₹{t['target']:,}"
                )

        # Depreciation mini-preview
        st.markdown('<div class="ticket-perf"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ticket-label">FUTURE VALUE PREVIEW</div>',
            unsafe_allow_html=True,
        )
        d_cols = st.columns(min(4, len(depr)))
        for col, (yr, price) in zip(d_cols, depr[:4]):
            col.markdown(
                f'<div style="text-align:center">'
                f'<div style="font-family:monospace;font-size:0.9rem;color:#C9A24B">'
                f'₹{price:,.0f}</div>'
                f'<div style="font-size:0.65rem;color:#7D8590">+{yr - age:.0f} yr</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # Persist to DB
        save_prediction(
            brand, ram, storage, battery, camera, screen,
            fiveg, age, condition, predicted, listed_price, verdict,
        )

        # --- SHAP explainability ------------------------------------------
        st.markdown(
            '<div class="ticket" style="margin-top:14px">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ticket-label">🔍 EXPLAINABLE AI — WHY THIS PRICE?</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Computing SHAP values…"):
            shap_fig = plot_shap_waterfall(model, X_scaled, feat_names)

        if shap_fig:
            st.pyplot(shap_fig, transparent=True)
        else:
            fi_path = os.path.join(BASE_DIR, "data", "feature_importance.csv")
            if os.path.exists(fi_path):
                import pandas as _pd
                fi_fig = plot_feature_importance(_pd.read_csv(fi_path))
                st.pyplot(fi_fig, transparent=True)
            else:
                st.caption("SHAP unavailable — install the `shap` package.")
        st.markdown('</div>', unsafe_allow_html=True)

        # --- PDF download -------------------------------------------------
        st.markdown(
            '<div class="ticket" style="margin-top:14px">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ticket-label">📄 VALUATION REPORT</div>',
            unsafe_allow_html=True,
        )
        pdf_data = {
            "brand":       brand,
            "ram":         ram,
            "storage":     storage,
            "battery":     battery,
            "camera":      camera,
            "screen":      screen,
            "fiveg":       fiveg,
            "age":         age,
            "condition":   condition,
            "predicted":   predicted,
            "low":         low,
            "high":        high,
            "vfm":         vfm,
            "verdict":     suggestion,
            "category":    category,
            "listed":      listed_price,
            "depreciation": list(depr),
        }
        pdf_bytes = generate_report(pdf_data)
        if pdf_bytes:
            st.download_button(
                label="⬇ Download PDF Valuation Report",
                data=pdf_bytes,
                file_name=f"appraisal_{brand}_{int(predicted)}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.caption("PDF generation unavailable — install `fpdf2` to enable.")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Placeholder before first prediction
        st.markdown('<div class="ticket">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">AWAITING SPECS</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div style="font-family:monospace;font-size:0.85rem;color:#7D8590;line-height:2.2">
            Fill in the specification slip on the left,<br>
            then hit <b style="color:#C9A24B">Appraise This Phone →</b><br><br>
            You'll get:<br>
            ✦ AI-predicted fair market price (XGBoost)<br>
            ✦ Price range (low–high)<br>
            ✦ Value-for-money score<br>
            ✦ Great Deal / Overpriced verdict<br>
            ✦ SHAP explanation (why this price)<br>
            ✦ Image condition scan (optional photo)<br>
            ✦ Depreciation preview<br>
            ✦ PDF valuation report
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
