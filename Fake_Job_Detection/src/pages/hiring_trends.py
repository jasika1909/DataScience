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


@st.cache_resource
def get_analyzer():
    return HiringTrendAnalyzer()


@st.cache_data
def get_trend_data():
    analyzer = HiringTrendAnalyzer()
    return analyzer.generate_trend_data(months=36)


def render():
    st.markdown("## 📈 Hiring Trend Analytics")
    st.markdown("Market intelligence on job posting volume, salary trends, remote work adoption, and fraud patterns.")

    analyzer = get_analyzer()
    df = get_trend_data()

    # Filters
    col1, col2 = st.columns([2, 1])
    with col1:
        categories = st.multiselect(
            "Filter Categories", options=df['category'].unique().tolist(),
            default=['Data Science & AI', 'Software Engineering', 'Product Management']
        )
    with col2:
        date_range = st.selectbox("Time Range", ['Last 12 months', 'Last 24 months', 'All time (36 mo)'])

    months_map = {'Last 12 months': 12, 'Last 24 months': 24, 'All time (36 mo)': 36}
    n_months = months_map[date_range]
    recent_dates = sorted(df['date'].unique())[-n_months:]
    filtered_df = df[(df['category'].isin(categories)) & (df['date'].isin(recent_dates))]

    if filtered_df.empty:
        st.warning("Select at least one category to view trends.")
        return

    # Summary metrics
    summary = analyzer.market_summary(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Latest Month Postings", summary['total_postings_latest'],
              f"{summary['mom_change_pct']}% MoM")
    c2.metric("Avg Fraud Rate", f"{summary['avg_fraud_pct']}%")
    c3.metric("Avg Remote %", f"{summary['avg_remote_pct']}%")
    c4.metric("Top Category", summary['top_category'])
    c5.metric("Avg Salary", f"${summary['avg_salary_overall']:,.0f}")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Demand Trends", "💰 Salary Trends", "🏠 Remote Work",
        "🚨 Fraud Patterns", "🔮 Forecasting"
    ])

    with tab1:
        st.markdown("#### Job Posting Volume Over Time")
        fig = px.line(filtered_df, x='date', y='job_postings', color='category',
                     title='Monthly Job Postings by Category', markers=True)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#ccc', height=420)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏆 Top Growing Categories")
            growth_df = analyzer.top_growing_categories(df, n=8)
            growth_df = growth_df[growth_df['category'].isin(categories) | True]
            fig2 = px.bar(growth_df, x='avg_mom_growth', y='category', orientation='h',
                         color='avg_mom_growth', color_continuous_scale='RdYlGn',
                         title='Average MoM Growth Rate (%)')
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=350, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.markdown("#### 📅 Seasonal Pattern (Avg by Month)")
            df_temp = df.copy()
            df_temp['month_num'] = pd.to_datetime(df_temp['date']).dt.month
            seasonal = df_temp.groupby('month_num')['job_postings'].mean().reset_index()
            month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            seasonal['month_name'] = seasonal['month_num'].apply(lambda x: month_names[x-1])
            fig3 = px.bar(seasonal, x='month_name', y='job_postings',
                         title='Average Hiring Activity by Month',
                         color='job_postings', color_continuous_scale='Blues')
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#ccc', height=350, showlegend=False,
                              xaxis_title='', yaxis_title='Avg Postings')
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.markdown("#### 💰 Salary Trends Over Time")
        fig = px.line(filtered_df, x='date', y='avg_salary', color='category',
                     title='Average Salary Trend by Category', markers=True)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#ccc', height=420)
        st.plotly_chart(fig, use_container_width=True)

        latest = filtered_df[filtered_df['date'] == filtered_df['date'].max()]
        fig2 = px.bar(latest.sort_values('avg_salary'), x='avg_salary', y='category',
                     orientation='h', title='Current Avg Salary by Category',
                     color='avg_salary', color_continuous_scale='Greens')
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#ccc', height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("#### 🏠 Remote Work Adoption Trend")
        remote_trend = analyzer.remote_work_trend(df)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=remote_trend['date'], y=remote_trend['avg_remote_pct'],
                                 mode='lines+markers', name='Remote %',
                                 line=dict(color='#4ecdc4', width=3),
                                 fill='tozeroy', fillcolor='rgba(78,205,196,0.1)'))
        fig.update_layout(
            title='Remote Work Adoption Over Time (% of Postings)',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#ccc', height=420, yaxis_title='Remote %'
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        col1.metric("Current Remote Adoption", f"{remote_trend['avg_remote_pct'].iloc[-1]:.1f}%")
        col2.metric("Change Since 2022", f"+{remote_trend['avg_remote_pct'].iloc[-1] - remote_trend['avg_remote_pct'].iloc[0]:.1f} pp")

    with tab4:
        st.markdown("#### 🚨 Fraud Pattern Trends")
        fraud_trend = analyzer.fraud_trend_analysis(df)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=fraud_trend['date'], y=fraud_trend['avg_fraud_pct'],
                                 mode='lines+markers', name='Fraud Rate %',
                                 line=dict(color='#ff6b6b', width=3)), secondary_y=False)
        fig.add_trace(go.Bar(x=fraud_trend['date'], y=fraud_trend['estimated_fraud_jobs'],
                             name='Estimated Fraud Jobs', opacity=0.3,
                             marker_color='#ff6b6b'), secondary_y=True)
        fig.update_layout(
            title='Fraud Rate & Estimated Fraudulent Job Count Over Time',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#ccc', height=420
        )
        fig.update_yaxes(title_text="Fraud Rate (%)", secondary_y=False)
        fig.update_yaxes(title_text="Est. Fraud Job Count", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        st.success(
            f"📉 Fraud detection improvements have reduced average fraud rate from "
            f"{fraud_trend['avg_fraud_pct'].iloc[0]:.1f}% to {fraud_trend['avg_fraud_pct'].iloc[-1]:.1f}% "
            f"over the observed period."
        )

    with tab5:
        st.markdown("#### 🔮 LSTM-Based Demand Forecasting")
        forecast_category = st.selectbox("Select category to forecast",
                                         df['category'].unique().tolist())
        n_months_forecast = st.slider("Months to forecast", 3, 12, 6)

        if st.button("🔮 Generate Forecast", type="primary"):
            with st.spinner("Training LSTM model and generating forecast..."):
                result = analyzer.forecast(df, forecast_category, n_months=n_months_forecast)

            hist_dates = pd.to_datetime(df[df['category'] == forecast_category]['date'])
            future_dates = pd.date_range(
                start=hist_dates.max() + pd.Timedelta(days=30),
                periods=n_months_forecast, freq='30D'
            )

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_dates, y=result['historical'],
                                     mode='lines', name='Historical', line=dict(color='#667eea')))
            fig.add_trace(go.Scatter(x=future_dates, y=result['forecast'],
                                     mode='lines+markers', name='Forecast',
                                     line=dict(color='#ff6b6b', dash='dash')))
            fig.update_layout(
                title=f'{forecast_category} — Job Posting Forecast ({result["method"]})',
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#ccc', height=420
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Forecast Method", result['method'])
            col2.metric("Trend Direction", result['trend'].title())
            col3.metric("Projected Growth", f"{result['growth_pct']}%")