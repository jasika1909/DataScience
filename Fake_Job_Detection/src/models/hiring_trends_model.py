import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter

from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HiringTrendAnalyzer:
    """
    Analyzes hiring trends over time:
    - Demand forecasting per job category
    - Skill trend tracking
    - Remote work adoption trends
    - Salary trend analysis
    - Fraud pattern trends
    """

    def __init__(self):
        self.scaler = MinMaxScaler()
        self.lstm_models = {}
        self.trend_data = {}

    # ── Synthetic trend data generator ──────────────────────────────────

    def generate_trend_data(self, months: int = 36) -> pd.DataFrame:
        """
        Generate realistic synthetic monthly hiring trend data.
        Based on real-world patterns from 2022–2025.
        """
        np.random.seed(42)
        start = datetime(2022, 1, 1)
        dates = [start + timedelta(days=30 * i) for i in range(months)]

        categories = [
            'Data Science & AI', 'Software Engineering', 'Product Management',
            'Marketing & Sales', 'Finance & Accounting', 'Human Resources',
            'Operations', 'Design & Creative'
        ]

        # Seasonal multipliers (hiring peaks in Jan, Sep; slow in summer)
        def seasonal(month: int) -> float:
            seasonal_factors = {1: 1.15, 2: 1.05, 3: 1.08, 4: 1.02,
                                 5: 0.98, 6: 0.90, 7: 0.85, 8: 0.88,
                                 9: 1.12, 10: 1.05, 11: 0.92, 12: 0.80}
            return seasonal_factors.get(month, 1.0)

        # Growth trends per category
        trends = {
            'Data Science & AI': 1.025,       # 2.5% monthly growth
            'Software Engineering': 1.015,
            'Product Management': 1.010,
            'Marketing & Sales': 1.005,
            'Finance & Accounting': 1.003,
            'Human Resources': 1.002,
            'Operations': 1.001,
            'Design & Creative': 1.008
        }

        # Base monthly posting counts
        base_counts = {
            'Data Science & AI': 8000,
            'Software Engineering': 25000,
            'Product Management': 5000,
            'Marketing & Sales': 12000,
            'Finance & Accounting': 7000,
            'Human Resources': 6000,
            'Operations': 9000,
            'Design & Creative': 4000
        }

        records = []
        for i, date in enumerate(dates):
            for cat in categories:
                base = base_counts[cat]
                growth = trends[cat] ** i
                season = seasonal(date.month)
                noise = np.random.normal(1.0, 0.05)

                # COVID dip in early 2022, AI boom in 2023
                if cat == 'Data Science & AI' and date.year == 2023:
                    growth *= 1.3  # ChatGPT effect

                postings = int(base * growth * season * noise)
                avg_salary = self._base_salary(cat) * (1 + 0.003 * i) * np.random.normal(1, 0.02)
                remote_pct = min(80, 30 + 0.5 * i + np.random.normal(0, 2))

                records.append({
                    'date': date,
                    'month': date.strftime('%Y-%m'),
                    'year': date.year,
                    'quarter': f"Q{(date.month - 1) // 3 + 1} {date.year}",
                    'category': cat,
                    'job_postings': postings,
                    'avg_salary': round(avg_salary, 0),
                    'remote_pct': round(remote_pct, 1),
                    'fraud_pct': round(max(2, 15 - 0.2 * i + np.random.normal(0, 1)), 1),
                    'avg_experience_required': round(np.random.uniform(1.5, 5.5), 1),
                    'time_to_fill_days': int(np.random.normal(28, 8))
                })

        df = pd.DataFrame(records)
        logger.info(f"Generated trend data: {df.shape}")
        return df

    def _base_salary(self, category: str) -> float:
        salaries = {
            'Data Science & AI': 115000, 'Software Engineering': 110000,
            'Product Management': 120000, 'Marketing & Sales': 75000,
            'Finance & Accounting': 85000, 'Human Resources': 65000,
            'Operations': 70000, 'Design & Creative': 80000
        }
        return salaries.get(category, 80000)

    # ── Trend metrics ────────────────────────────────────────────────────

    def compute_growth_rates(self, df: pd.DataFrame,
                              value_col: str = 'job_postings') -> pd.DataFrame:
        """Compute MoM and YoY growth rates"""
        df = df.sort_values(['category', 'date']).copy()
        df['mom_growth'] = df.groupby('category')[value_col].pct_change() * 100
        df['yoy_growth'] = df.groupby('category')[value_col].pct_change(12) * 100
        df['rolling_3m_avg'] = df.groupby('category')[value_col].transform(
            lambda x: x.rolling(3, min_periods=1).mean()
        )
        df['rolling_6m_avg'] = df.groupby('category')[value_col].transform(
            lambda x: x.rolling(6, min_periods=1).mean()
        )
        return df

    def detect_trends(self, df: pd.DataFrame,
                       category: str = 'Data Science & AI') -> Dict:
        """Linear trend detection for a category"""
        cat_df = df[df['category'] == category].sort_values('date')
        X = np.arange(len(cat_df)).reshape(-1, 1)
        y = cat_df['job_postings'].values

        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]
        r2 = model.score(X, y)

        direction = 'Growing 📈' if slope > 50 else 'Declining 📉' if slope < -50 else 'Stable ➡️'

        return {
            'category': category,
            'trend_direction': direction,
            'monthly_slope': round(slope, 1),
            'r2_fit': round(r2, 3),
            'avg_postings': round(y.mean(), 0),
            'latest_postings': int(y[-1]),
            'peak_postings': int(y.max()),
            'peak_month': cat_df.iloc[y.argmax()]['month']
        }

    def top_growing_categories(self, df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        """Rank categories by growth rate"""
        df = self.compute_growth_rates(df)
        latest = df.sort_values('date').groupby('category').tail(3)
        growth_summary = latest.groupby('category').agg(
            avg_mom_growth=('mom_growth', 'mean'),
            latest_postings=('job_postings', 'last'),
            avg_salary=('avg_salary', 'mean')
        ).reset_index().sort_values('avg_mom_growth', ascending=False).head(n)
        return growth_summary

    def remote_work_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze remote work adoption over time"""
        monthly = df.groupby('month').agg(
            avg_remote_pct=('remote_pct', 'mean'),
            total_postings=('job_postings', 'sum')
        ).reset_index()
        monthly['date'] = pd.to_datetime(monthly['month'])
        return monthly.sort_values('date')

    def salary_trend_by_category(self, df: pd.DataFrame) -> pd.DataFrame:
        """Salary trends over time per category"""
        return df.groupby(['month', 'category']).agg(
            avg_salary=('avg_salary', 'mean')
        ).reset_index().sort_values('month')

    def fraud_trend_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Track fraud percentage over time"""
        monthly = df.groupby('month').agg(
            avg_fraud_pct=('fraud_pct', 'mean'),
            total_postings=('job_postings', 'sum')
        ).reset_index()
        monthly['date'] = pd.to_datetime(monthly['month'])
        monthly['estimated_fraud_jobs'] = (
            monthly['total_postings'] * monthly['avg_fraud_pct'] / 100
        ).astype(int)
        return monthly.sort_values('date')

    # ── LSTM Forecasting ─────────────────────────────────────────────────

    def build_lstm_forecaster(self, sequence_length: int = 12) -> Sequential:
        """Build LSTM model for time-series forecasting"""
        model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(sequence_length, 1)),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model

    def prepare_sequences(self, series: np.ndarray,
                           seq_len: int = 12) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare input/output sequences for LSTM"""
        X, y = [], []
        for i in range(len(series) - seq_len):
            X.append(series[i:i + seq_len])
            y.append(series[i + seq_len])
        return np.array(X), np.array(y)

    def forecast(self, df: pd.DataFrame, category: str,
                 n_months: int = 6, seq_len: int = 12) -> Dict:
        """
        Forecast job postings for next n_months using LSTM.
        Falls back to linear trend if insufficient data.
        """
        cat_df = df[df['category'] == category].sort_values('date')
        series = cat_df['job_postings'].values.astype(float)

        if len(series) < seq_len + 5:
            logger.warning(f"Not enough data for LSTM forecast of {category}. Using linear.")
            return self._linear_forecast(series, category, n_months)

        # Scale
        scaler = MinMaxScaler()
        series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()

        # Prepare sequences
        X, y_seq = self.prepare_sequences(series_scaled, seq_len)
        X = X.reshape(X.shape[0], X.shape[1], 1)

        # Train
        model = self.build_lstm_forecaster(seq_len)
        callbacks = [EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)]

        train_size = int(len(X) * 0.8)
        model.fit(
            X[:train_size], y_seq[:train_size],
            validation_data=(X[train_size:], y_seq[train_size:]),
            epochs=50, batch_size=8, verbose=0,
            callbacks=callbacks
        )

        # Forecast
        last_seq = series_scaled[-seq_len:].reshape(1, seq_len, 1)
        predictions_scaled = []
        for _ in range(n_months):
            pred = model.predict(last_seq, verbose=0)[0, 0]
            predictions_scaled.append(pred)
            last_seq = np.roll(last_seq, -1, axis=1)
            last_seq[0, -1, 0] = pred

        predictions = scaler.inverse_transform(
            np.array(predictions_scaled).reshape(-1, 1)
        ).flatten()
        predictions = np.maximum(predictions, 0)

        # Future dates
        last_date = cat_df['date'].max()
        future_dates = [last_date + timedelta(days=30 * (i + 1)) for i in range(n_months)]

        return {
            'category': category,
            'historical': series.tolist(),
            'historical_dates': cat_df['date'].tolist(),
            'forecast': predictions.tolist(),
            'forecast_dates': future_dates,
            'method': 'LSTM',
            'trend': 'growing' if predictions[-1] > predictions[0] else 'declining',
            'growth_pct': round((predictions[-1] / predictions[0] - 1) * 100, 1)
        }

    def _linear_forecast(self, series: np.ndarray, category: str,
                          n_months: int) -> Dict:
        """Simple linear regression forecast fallback"""
        X = np.arange(len(series)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, series)
        future_X = np.arange(len(series), len(series) + n_months).reshape(-1, 1)
        predictions = np.maximum(model.predict(future_X), 0)
        return {
            'category': category,
            'historical': series.tolist(),
            'forecast': predictions.tolist(),
            'method': 'Linear Regression',
            'trend': 'growing' if model.coef_[0] > 0 else 'declining',
            'growth_pct': round((predictions[-1] / max(series[-1], 1) - 1) * 100, 1)
        }

    def market_summary(self, df: pd.DataFrame) -> Dict:
        """High-level market summary stats"""
        latest_month = df['month'].max()
        latest = df[df['month'] == latest_month]
        prev_month = df[df['month'] == df['month'].unique()[-2]] if len(df['month'].unique()) > 1 else latest

        total_postings = latest['job_postings'].sum()
        prev_total = prev_month['job_postings'].sum()

        return {
            'total_postings_latest': f"{total_postings:,}",
            'mom_change_pct': round((total_postings / max(prev_total, 1) - 1) * 100, 1),
            'avg_fraud_pct': round(latest['fraud_pct'].mean(), 1),
            'avg_remote_pct': round(latest['remote_pct'].mean(), 1),
            'top_category': latest.loc[latest['job_postings'].idxmax(), 'category'],
            'avg_salary_overall': round(latest['avg_salary'].mean(), 0),
            'latest_month': latest_month
        }