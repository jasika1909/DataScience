import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import joblib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.helper import (
    BRANDS, FIVEG, CONDITIONS, DATA_PATH, MODEL_PATH,
    build_feature_frame, transform_features, load_artifacts,
    price_category, value_for_money_score, price_range
)

st.set_page_config(
    page_title="Smart Mobile Price Predictor",
    page_icon="📱",
    layout="wide"
)
st.markdown("""
<style>

.stApp{
    background: linear-gradient(
        135deg,
        #0F172A 0%,
        #1E293B 50%,
        #334155 100%
    );
}

h1,h2,h3,label,p{
    color:white !important;
}

.block-container{
    padding-top:1rem;
    padding-bottom:2rem;
}

[data-testid="stMetric"]{
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(255,255,255,0.1);
    padding:15px;
    border-radius:18px;
}

.stButton>button{
    width:100%;
    height:55px;
    border-radius:14px;
    border:none;
    background:linear-gradient(90deg,#2563EB,#06B6D4);
    color:white;
    font-weight:bold;
    font-size:18px;
}

.stButton>button:hover{
    transform:scale(1.02);
}

[data-testid="stSidebar"]{
    background:#0B1120;
}

.glass-card{
    background:rgba(255,255,255,0.05);
    padding:20px;
    border-radius:20px;
    border:1px solid rgba(255,255,255,0.08);
}

.hero{
    text-align:center;
    padding:20px;
}

.hero h1{
    font-size:56px;
    color:#60A5FA;
}

.hero p{
    font-size:18px;
    color:#CBD5E1;
}

</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_artifacts_exist():
    return os.path.exists(MODEL_PATH)


def main():
    st.markdown("""
        <div class="hero">
        <h1>📱 Smart Mobile Price Predictor</h1>
        <p>
        AI Powered Mobile Valuation & Deal Intelligence Platform
        </p>
        </div>
        """, unsafe_allow_html=True)

    if not check_artifacts_exist():
        st.warning(
            "Model artifacts not found. Please run `python train_model.py` first "
            "to generate the dataset and train the model."
        )
        st.stop()

    model, scaler, encoder = load_artifacts()

# ======================
# Sidebar
# ======================

    with st.sidebar:
        st.title("📱 Mobile AI")
        st.markdown("---")
        st.markdown("""
        ### Features
        ✅ AI Price Prediction
        ✅ Value Score
        ✅ Deal Analyzer
        ✅ Market Insights
        ✅ Feature Importance
        """)
        st.markdown("---")
        st.info("Built using Machine Learning + Streamlit")
    # ======================
    # Feature Cards
    # ======================
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.info("🤖 AI Prediction")

    with c2:
        st.info("💰 Deal Analysis")

    with c3:
        st.info("📈 Market Trends")

    with c4:
        st.info("⚡ Smart Valuation")

    # ======================
    # Main Layout
    # ======================
    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Enter Phone Specifications")
        brand = st.selectbox("Brand", BRANDS)
        ram = st.select_slider("RAM (GB)", options=[2, 3, 4, 6, 8, 12, 16], value=8)
        storage = st.select_slider("Storage (GB)", options=[32, 64, 128, 256, 512], value=128)
        battery = st.slider("Battery (mAh)", 2500, 7000, 5000, step=100)
        camera = st.select_slider("Camera (MP)", options=[8, 12, 16, 32, 48, 50, 64, 108, 200], value=48)
        screen_size = st.slider("Screen Size (inches)", 4.5, 7.5, 6.5, step=0.1)
        fiveg = st.radio("5G Support", FIVEG, horizontal=True)
        phone_age = st.slider("Phone Age (years)", 0.0, 6.0, 1.0, step=0.5)
        condition = st.radio("Condition", CONDITIONS, horizontal=True)
        listed_price = st.number_input(
        "Listed / Asking Price (optional, to compare) ₹", min_value=0.0, value=0.0, step=500.0
        )
        predict_btn = st.button("🔮 Predict Price", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        if predict_btn:
            df_input = build_feature_frame(
                brand, ram, storage, battery, camera, screen_size,
                fiveg, phone_age, condition
            )
            X_scaled, _ = transform_features(df_input, encoder, scaler)
            predicted_price = model.predict(X_scaled)[0]
            low, high = price_range(predicted_price)

            st.subheader("📊 Prediction Results")      
            vfm = value_for_money_score(ram, storage, battery, camera, screen_size, predicted_price)
            metric1,metric2,metric3 = st.columns(3)
            metric1.metric(
                "Estimated Price",
                f"₹{predicted_price:,.0f}"
            )
            metric2.metric(
                "Expected Range",
                f"₹{low:,.0f} - ₹{high:,.0f}"
            )
            metric3.metric(
                "Value Score",
                f"{vfm}/100"
            )

            
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=vfm,
                title={"text":"Value For Money Score"},
                gauge={
                    "axis":{"range":[0,100]},
                    "steps":[
                        {"range":[0,40],"color":"#EF4444"},
                        {"range":[40,70],"color":"#F59E0B"},
                        {"range":[70,100],"color":"#22C55E"}
                    ]
                }
            ))

            st.plotly_chart(
                gauge,
                use_container_width=True
            )

            if listed_price > 0:
                category, suggestion = price_category(predicted_price, listed_price)
                st.markdown("---")
                st.subheader("🏷️ Price Verdict")
                c1, c2 = st.columns(2)
                if category.lower().startswith("great"):
                    color="#22C55E"

                elif category.lower().startswith("fair"):
                    color="#F59E0B"

                else:
                    color="#EF4444"

                st.markdown(
                f"""
                <div style="
                background:{color};
                padding:20px;
                border-radius:20px;
                text-align:center;
                color:white;
                margin-top:15px;
                ">

                <h2>{category}</h2>

                <p>{suggestion}</p>

                </div>
                """,
                unsafe_allow_html=True
                )
            if listed_price > 0:
                if "Great Deal" in category:
                    st.success(
                        "🔥 This phone is priced significantly below estimated market value."
                    )

                elif "Overpriced" in category:
                    st.error(
                        "❌ This phone is priced above estimated market value."
                    )

                else:
                    st.info(
                        "👍 This price is fair for the given specifications."
                    )
            else:
                st.info("Enter a listed price on the left to get a Buy/Avoid/Good-Deal verdict.")

            st.markdown("---")
            fi_path = os.path.join(
                BASE_DIR,
                "data",
                "feature_importance.csv"
            )
            if os.path.exists(fi_path):
                fi_df = pd.read_csv(fi_path).head(10)
                fig = px.bar(
                    fi_df,
                    x="importance",
                    y="feature",
                    orientation="h",
                    title="Top Features Driving Price"
                )

                fig.update_layout(
                    height=500,
                    template="plotly_dark"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )
        else:
            st.subheader("📈 Dataset Price Distribution")
            df = pd.read_csv(DATA_PATH)
            if os.path.exists(DATA_PATH):
                fig = px.histogram(
                df,
                x="Price",
                nbins=40,
                title="Mobile Price Distribution"
            )

            fig.update_layout(
                template="plotly_dark",
                height=500
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )
            st.write("👈 Fill in the specs and click **Predict Price** to see results.")

    st.markdown("---")
    st.caption("Use the sidebar to navigate to **Analytics** and **Predictor** pages for deeper insights.")
    st.caption("Built by Jasika Awasthi")
    


if __name__ == "__main__":
    main()