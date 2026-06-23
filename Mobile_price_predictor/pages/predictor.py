import os
import joblib
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from utils.helper import (
    BRANDS, FIVEG, CONDITIONS, MODEL_PATH,
    build_feature_frame, transform_features, load_artifacts,
    price_category, value_for_money_score, price_range
)

st.set_page_config(page_title="Predictor - Mobile Price Predictor", page_icon="🔮", layout="wide")

st.title("🔮 Mobile Price Predictor")
st.caption("Get an instant fair-price estimate and a Buy / Avoid / Good Deal verdict.")

if not os.path.exists(MODEL_PATH):
    st.error("Model not trained yet. Run `python train_model.py` first.")
    st.stop()

model, scaler, encoder = load_artifacts()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
metrics_path = os.path.join(BASE_DIR, "metrics.pkl")
if os.path.exists(metrics_path):
    metrics = joblib.load(metrics_path)
    c1, c2, c3 = st.columns(3)
    c1.metric("Model Accuracy (R²)", f"{metrics['r2']:.3f}")
    c2.metric("Average Error", f"₹{metrics['mae']:.2f}")
    c3.metric("Prediction Stability", f"₹{metrics['rmse']:.2f}")
    st.markdown("---")

with st.form("predictor_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        brand = st.selectbox("Brand", BRANDS)
        ram = st.selectbox("RAM (GB)", [2, 3, 4, 6, 8, 12, 16], index=4)
        storage = st.selectbox("Storage (GB)", [32, 64, 128, 256, 512], index=2)
    with col2:
        battery = st.number_input("Battery (mAh)", 2500, 7000, 5000, step=100)
        camera = st.selectbox("Camera (MP)", [8, 12, 16, 32, 48, 50, 64, 108, 200], index=5)
        screen_size = st.number_input("Screen Size (inches)", 4.5, 7.5, 6.5, step=0.1)
    with col3:
        fiveg = st.selectbox("5G Support", FIVEG)
        phone_age = st.number_input("Phone Age (years)", 0.0, 6.0, 1.0, step=0.5)
        condition = st.selectbox("Condition", CONDITIONS)

    listed_price = st.number_input("Listed / Asking Price (₹) — optional", min_value=0.0, value=0.0, step=500.0)
    submitted = st.form_submit_button("Predict Now 🚀")

if submitted:
    df_input = build_feature_frame(
        brand, ram, storage, battery, camera, screen_size,
        fiveg, phone_age, condition
    )
    X_scaled, _ = transform_features(df_input, encoder, scaler)
    predicted_price = model.predict(X_scaled)[0]
    low, high = price_range(predicted_price)
    vfm = value_for_money_score(ram, storage, battery, camera, screen_size, predicted_price)

    st.success(f"### Estimated Fair Price: ₹{predicted_price:,.2f}")
    st.info(f"**Expected Price Range:** ₹{low:,.0f} – ₹{high:,.0f}")
    st.write(f"**Value for Money Score:** {vfm}/100")

    if listed_price > 0:
        category, suggestion = price_category(predicted_price, listed_price)
        st.markdown("---")
        st.subheader("Verdict")
        colA, colB = st.columns(2)
        colA.metric("Price Category", category)
        colB.metric("Recommendation", suggestion)

        if "Suspicious" in category:
            st.warning(
                "🚨 This listing is suspiciously cheap. Verify authenticity before purchase."
            )

        elif "Great Deal" in category:
            st.success(
                "🔥 This phone is priced significantly below estimated market value."
            )

        elif "Overpriced" in category:
            st.error(
                "❌ This phone is priced above estimated market value."
            )

        else:
            st.info(
                "👍 This price is close to market value."
            )
    else:
        st.warning("Enter a listed price above to get a Buy / Avoid / Good Deal verdict.")