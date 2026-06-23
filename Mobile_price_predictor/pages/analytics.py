import os
import pandas as pd
import numpy as np
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt

from utils.helper import DATA_PATH, NUMERIC_COLS

st.set_page_config(page_title="Analytics - Mobile Price Predictor", page_icon="📊", layout="wide")

st.title("📊 Mobile Market Analytics Dashboard")

if not os.path.exists(DATA_PATH):
    st.error("Dataset not found. Please run `python train_model.py` first.")
    st.stop()

df = pd.read_csv(DATA_PATH)

st.subheader("Dataset Preview")
st.dataframe(df.head(20), use_container_width=True)

st.markdown("---")
st.subheader("💰 Price Distribution")
fig1, ax1 = plt.subplots(figsize=(8, 4))
sns.histplot(df["Price"], bins=40, kde=True, color="#4C72B0", ax=ax1)
ax1.set_title("Distribution of Phone Prices")
st.pyplot(fig1)

st.markdown("---")
st.subheader("🏷️ Brand vs Average Price")
brand_avg = df.groupby("Brand")["Price"].mean().sort_values(ascending=False)
fig2, ax2 = plt.subplots(figsize=(8, 4))
sns.barplot(x=brand_avg.index, y=brand_avg.values, palette="viridis", ax=ax2)
ax2.set_ylabel("Average Price")
ax2.set_xlabel("Brand")
plt.xticks(rotation=45)
st.pyplot(fig2)

st.markdown("---")
st.subheader("📦 Price by Condition (New vs Used)")
fig3, ax3 = plt.subplots(figsize=(8, 4))
sns.boxplot(data=df, x="Condition", y="Price", ax=ax3, palette="Set2")
st.pyplot(fig3)

st.markdown("---")
st.subheader("🔗 Correlation Heatmap (Numeric Features)")
numeric_df = df[NUMERIC_COLS + ["Price"]]
fig4, ax4 = plt.subplots(figsize=(7, 5))
sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", fmt=".2f", ax=ax4)
st.pyplot(fig4)

st.markdown("---")
st.subheader("📡 5G vs Non-5G Price Comparison")
fig5, ax5 = plt.subplots(figsize=(6, 4))
sns.violinplot(data=df, x="FiveG", y="Price", ax=ax5, palette="pastel")
st.pyplot(fig5)

st.markdown("---")
st.subheader("📈 Summary Statistics")
st.dataframe(df.describe(), use_container_width=True)
st.caption("Predictions are generated using a machine learning model trained on synthetic market data and should be considered estimates rather than exact market prices.")