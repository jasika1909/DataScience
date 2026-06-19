import numpy as np
import pandas as pd
import logging
from typing import Dict
from datetime import datetime, timedelta

from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HiringTrendAnalyzer:
    """
    Analyzes hiring trends over time:
    - Demand forecasting per job category
    - Remote work adoption trends
    - Salary trend analysis
    - Fraud pattern trends
    """

    def __init__(self):
        self.scaler = MinMaxScaler()
        self.trend_data = {}

    def generate_trend_data(self, months: int = 36) -> pd.DataFrame:
        np.random.seed(42)

        start = datetime(2022, 1, 1)
        dates = [start + timedelta(days=30 * i) for i in range(months)]

        categories = [
            "Data Science & AI",
            "Software Engineering",
            "Product Management",
            "Marketing & Sales",
            "Finance & Accounting",
            "Human Resources",
            "Operations",
            "Design & Creative",
        ]

        def seasonal(month):
            seasonal_factors = {
                1: 1.15,
                2: 1.05,
                3: 1.08,
                4: 1.02,
                5: 0.98,
                6: 0.90,
                7: 0.85,
                8: 0.88,
                9: 1.12,
                10: 1.05,
                11: 0.92,
                12: 0.80,
            }
            return seasonal_factors.get(month, 1.0)

        trends = {
            "Data Science & AI": 1.025,
            "Software Engineering": 1.015,
            "Product Management": 1.010,
            "Marketing & Sales": 1.005,
            "Finance & Accounting": 1.003,
            "Human Resources": 1.002,
            "Operations": 1.001,
            "Design & Creative": 1.008,
        }

        base_counts = {
            "Data Science & AI": 8000,
            "Software Engineering": 25000,
            "Product Management": 5000,
            "Marketing & Sales": 12000,
            "Finance & Accounting": 7000,
            "Human Resources": 6000,
            "Operations": 9000,
            "Design & Creative": 4000,
        }

        records = []

        for i, date in enumerate(dates):
            for cat in categories:
                base = base_counts[cat]
                growth = trends[cat] ** i
                season = seasonal(date.month)
                noise = np.random.normal(1.0, 0.05)

                if cat == "Data Science & AI" and date.year == 2023:
                    growth *= 1.3

                postings = int(base * growth * season * noise)

                avg_salary = (
                    self._base_salary(cat)
                    * (1 + 0.003 * i)
                    * np.random.normal(1, 0.02)
                )

                remote_pct = min(
                    80,
                    30 + 0.5 * i + np.random.normal(0, 2),
                )

                records.append(
                    {
                        "date": date,
                        "month": date.strftime("%Y-%m"),
                        "year": date.year,
                        "quarter": f"Q{(date.month - 1) // 3 + 1} {date.year}",
                        "category": cat,
                        "job_postings": postings,
                        "avg_salary": round(avg_salary, 0),
                        "remote_pct": round(remote_pct, 1),
                        "fraud_pct": round(
                            max(2, 15 - 0.2 * i + np.random.normal(0, 1)),
                            1,
                        ),
                        "avg_experience_required": round(
                            np.random.uniform(1.5, 5.5), 1
                        ),
                        "time_to_fill_days": int(
                            max(1, np.random.normal(28, 8))
                        ),
                    }
                )

        return pd.DataFrame(records)

    def _base_salary(self, category: str) -> float:
        salaries = {
            "Data Science & AI": 115000,
            "Software Engineering": 110000,
            "Product Management": 120000,
            "Marketing & Sales": 75000,
            "Finance & Accounting": 85000,
            "Human Resources": 65000,
            "Operations": 70000,
            "Design & Creative": 80000,
        }

        return salaries.get(category, 80000)

    def compute_growth_rates(
        self,
        df: pd.DataFrame,
        value_col: str = "job_postings",
    ) -> pd.DataFrame:

        df = df.sort_values(["category", "date"]).copy()

        df["mom_growth"] = (
            df.groupby("category")[value_col].pct_change() * 100
        )

        df["yoy_growth"] = (
            df.groupby("category")[value_col].pct_change(12) * 100
        )

        return df

    def top_growing_categories(
        self,
        df: pd.DataFrame,
        n: int = 5,
    ) -> pd.DataFrame:

        df = self.compute_growth_rates(df)

        latest = (
            df.sort_values("date")
            .groupby("category")
            .tail(3)
        )

        return (
            latest.groupby("category")
            .agg(
                avg_mom_growth=("mom_growth", "mean"),
                latest_postings=("job_postings", "last"),
                avg_salary=("avg_salary", "mean"),
            )
            .reset_index()
            .sort_values(
                "avg_mom_growth",
                ascending=False,
            )
            .head(n)
        )

    def remote_work_trend(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        monthly = (
            df.groupby("month")
            .agg(
                avg_remote_pct=("remote_pct", "mean"),
                total_postings=("job_postings", "sum"),
            )
            .reset_index()
        )

        monthly["date"] = pd.to_datetime(monthly["month"])

        return monthly.sort_values("date")

    def fraud_trend_analysis(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        monthly = (
            df.groupby("month")
            .agg(
                avg_fraud_pct=("fraud_pct", "mean"),
                total_postings=("job_postings", "sum"),
            )
            .reset_index()
        )

        monthly["date"] = pd.to_datetime(monthly["month"])

        monthly["estimated_fraud_jobs"] = (
            monthly["total_postings"]
            * monthly["avg_fraud_pct"]
            / 100
        ).astype(int)

        return monthly.sort_values("date")

    def forecast(
        self,
        df: pd.DataFrame,
        category: str,
        n_months: int = 6,
    ) -> Dict:

        cat_df = (
            df[df["category"] == category]
            .sort_values("date")
        )

        series = cat_df["job_postings"].values.astype(float)

        return self._linear_forecast(
            series,
            category,
            n_months,
        )

    def _linear_forecast(
        self,
        series,
        category,
        n_months,
    ) -> Dict:

        X = np.arange(len(series)).reshape(-1, 1)

        model = LinearRegression()
        model.fit(X, series)

        future_X = np.arange(
            len(series),
            len(series) + n_months,
        ).reshape(-1, 1)

        predictions = np.maximum(
            model.predict(future_X),
            0,
        )

        return {
            "category": category,
            "historical": series.tolist(),
            "forecast": predictions.tolist(),
            "method": "Linear Regression",
            "trend": (
                "growing"
                if model.coef_[0] > 0
                else "declining"
            ),
            "growth_pct": round(
                (
                    predictions[-1]
                    / max(series[-1], 1)
                    - 1
                )
                * 100,
                1,
            ),
        }

    def market_summary(
        self,
        df: pd.DataFrame,
    ) -> Dict:

        months = sorted(df["month"].unique())
        latest_month = months[-1]

        latest = df[df["month"] == latest_month]

        if len(months) > 1:
            prev_month = df[df["month"] == months[-2]]
        else:
            prev_month = latest

        total_postings = latest["job_postings"].sum()
        prev_total = prev_month["job_postings"].sum()

        return {
            "total_postings_latest": f"{total_postings:,}",
            "mom_change_pct": round(
                (
                    total_postings
                    / max(prev_total, 1)
                    - 1
                )
                * 100,
                1,
            ),
            "avg_fraud_pct": round(
                latest["fraud_pct"].mean(),
                1,
            ),
            "avg_remote_pct": round(
                latest["remote_pct"].mean(),
                1,
            ),
            "top_category": latest.loc[
                latest["job_postings"].idxmax(),
                "category",
            ],
            "avg_salary_overall": round(
                latest["avg_salary"].mean(),
                0,
            ),
            "latest_month": latest_month,
        }


if __name__ == "__main__":
    analyzer = HiringTrendAnalyzer()

    df = analyzer.generate_trend_data()

    print("\nMarket Summary:")
    print(analyzer.market_summary(df))

    print("\nTop Growing Categories:")
    print(analyzer.top_growing_categories(df))

    print("\nForecast:")
    print(
        analyzer.forecast(
            df,
            "Data Science & AI",
            n_months=6,
        )
    )
