import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.hiring_trends_model import HiringTrendAnalyzer

@st.cache_data
def get_dashboard_data():
    analyzer = HiringTrendAnalyzer()
    df = analyzer.generate_trend_data(months=24)
    return df, analyzer


def render():
    st.markdown("## 📊 Business Intelligence Dashboard")
    st.markdown("Executive overview combining fraud detection, salary, classification, and hiring trend insights.")

    df, analyzer = get_dashboard_data()

    # ── Sidebar-style filters at top ─────────────────────────────────────
    with st.expander("🔧 Dashboard Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_categories = st.multiselect(
                "Categories", df['category'].unique().tolist(),
                default=df['category'].unique().tolist()
            )
        with col2:
            min_date, max_date = df['date'].min(), df['date'].max()
            date_filter = st.select_slider(
                "Date Range",
                options=sorted(df['month'].unique()),
                value=(sorted(df['month'].unique())[0], sorted(df['month'].unique())[-1])
            )
        with col3:
            view_mode = st.radio("View", ['Summary', 'Detailed'], horizontal=True)

    filtered = df[
        (df['category'].isin(selected_categories)) &
        (df['month'] >= date_filter[0]) & (df['month'] <= date_filter[1])
    ]

    # ── Top KPI Row ───────────────────────────────────────────────────────
    st.markdown("### 🎯 Key Performance Indicators")
    total_postings = filtered['job_postings'].sum()
    avg_salary = filtered['avg_salary'].mean()
    avg_fraud = filtered['fraud_pct'].mean()
    avg_remote = filtered['remote_pct'].mean()
    avg_time_to_fill = filtered['time_to_fill_days'].mean()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""<div class='metric-card'><h3 style='color:#667eea; margin:0;'>{total_postings:,.0f}</h3>
        <p style='color:#999; margin:0; font-size:0.8rem;'>Total Job Postings</p></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class='metric-card'><h3 style='color:#00cc88; margin:0;'>${avg_salary:,.0f}</h3>
        <p style='color:#999; margin:0; font-size:0.8rem;'>Avg Salary</p></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class='metric-card'><h3 style='color:#ff6b6b; margin:0;'>{avg_fraud:.1f}%</h3>
        <p style='color:#999; margin:0; font-size:0.8rem;'>Avg Fraud Rate</p></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class='metric-card'><h3 style='color:#4ecdc4; margin:0;'>{avg_remote:.1f}%</h3>
        <p style='color:#999; margin:0; font-size:0.8rem;'>Remote Jobs</p></div>""", unsafe_allow_html=True)
    with k5:
        st.markdown(f"""<div class='metric-card'><h3 style='color:#feca57; margin:0;'>{avg_time_to_fill:.0f} days</h3>
        <p style='color:#999; margin:0; font-size:0.8rem;'>Avg Time to Fill</p></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Row 1: Volume + Category Mix ────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        monthly_total = filtered.groupby('date')['job_postings'].sum().reset_index()
        fig = px.area(monthly_total, x='date', y='job_postings',
                      title='Total Job Postings Over Time')
        fig.update_traces(line_color='#667eea', fillcolor='rgba(102,126,234,0.2)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#ccc', height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cat_mix = filtered.groupby('category')['job_postings'].sum().reset_index()
        fig2 = px.pie(cat_mix, names='category', values='job_postings',
                     title='Category Mix', hole=0.45)
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc', height=350,
                          showlegend=False)
        fig2.update_traces(textposition='inside', textinfo='percent+label', textfont_size=9)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Salary heatmap + Fraud gauge ─────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        pivot = filtered.pivot_table(index='category', columns='month',
                                     values='avg_salary', aggfunc='mean')
        fig3 = px.imshow(pivot, color_continuous_scale='Viridis', aspect='auto',
                         title='Salary Heatmap (Category × Month)')
        fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc', height=380)
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        latest_fraud = filtered[filtered['date'] == filtered['date'].max()]['fraud_pct'].mean()
        fig4 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=latest_fraud,
            delta={'reference': filtered['fraud_pct'].mean(), 'decreasing': {'color': '#00cc88'}},
            title={'text': "Current Fraud Rate"},
            gauge={'axis': {'range': [0, 25]},
                  'bar': {'color': '#ff6b6b'},
                  'steps': [{'range': [0, 8], 'color': 'rgba(0,204,136,0.13)'},
                           {'range': [8, 15], 'color': 'rgba(255,165,0,0.13)'},
                           {'range': [15, 25], 'color': 'rgba(255,75,75,0.13)'}]}
        ))
        fig4.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ccc', height=380)
        st.plotly_chart(fig4, use_container_width=True)

    # ── Row 3: Detailed view ─────────────────────────────────────────────
    if view_mode == 'Detailed':
        st.markdown("---")
        st.markdown("### 🔬 Detailed Category Breakdown")

        summary_table = filtered.groupby('category').agg(
            total_postings=('job_postings', 'sum'),
            avg_salary=('avg_salary', 'mean'),
            avg_fraud_pct=('fraud_pct', 'mean'),
            avg_remote_pct=('remote_pct', 'mean'),
            avg_time_to_fill=('time_to_fill_days', 'mean')
        ).round(1).sort_values('total_postings', ascending=False)

        st.dataframe(
            summary_table.style.background_gradient(cmap='Blues', subset=['total_postings'])
            .background_gradient(cmap='Greens', subset=['avg_salary']),
            use_container_width=True
        )

        col1, col2 = st.columns(2)
        with col1:
            fig5 = px.scatter(
                filtered.groupby('category').agg(
                    postings=('job_postings', 'sum'), salary=('avg_salary', 'mean'),
                    fraud=('fraud_pct', 'mean')
                ).reset_index(),
                x='postings', y='salary', size='fraud', color='category',
                title='Postings vs Salary (bubble = fraud rate)', text='category'
            )
            fig5.update_traces(textposition='top center', textfont_size=8)
            fig5.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=400, showlegend=False)
            st.plotly_chart(fig5, use_container_width=True)

        with col2:
            time_fill = filtered.groupby('category')['time_to_fill_days'].mean().reset_index()
            fig6 = px.bar(time_fill.sort_values('time_to_fill_days'),
                         x='time_to_fill_days', y='category', orientation='h',
                         title='Avg Time to Fill by Category', color='time_to_fill_days',
                         color_continuous_scale='Reds')
            fig6.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=400, showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col2:
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Dashboard Data (CSV)", csv,
                           "dashboard_export.csv", "text/csv", use_container_width=True)