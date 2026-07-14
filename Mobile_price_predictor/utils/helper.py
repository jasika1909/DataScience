"""
utils/helper.py
---------------
Path constants, artifact loaders, feature-building helpers, and
business-logic utilities shared across all pages.
"""

import os
import joblib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH   = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH  = os.path.join(BASE_DIR, "scaler.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "encoder.pkl")
METRICS_PATH = os.path.join(BASE_DIR, "metrics.pkl")
DATA_PATH    = os.path.join(BASE_DIR, "data", "mobile_data.csv")

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
BRANDS     = ["Samsung", "Apple", "Xiaomi", "OnePlus", "Realme",
              "Vivo", "Oppo", "Google", "Motorola", "Nothing"]
CONDITIONS = ["New", "Used"]
FIVEG      = ["Yes", "No"]

NUMERIC_COLS     = ["RAM", "Storage", "Battery", "Camera", "ScreenSize", "PhoneAge"]
CATEGORICAL_COLS = ["Brand", "FiveG", "Condition"]
FEATURE_COLS     = NUMERIC_COLS + CATEGORICAL_COLS


# ---------------------------------------------------------------------------
# Artifact I/O
# ---------------------------------------------------------------------------
def load_artifacts():
    """Load and return (model, scaler, encoder) from disk."""
    model   = joblib.load(MODEL_PATH)
    scaler  = joblib.load(SCALER_PATH)
    encoder = joblib.load(ENCODER_PATH)
    return model, scaler, encoder


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def build_feature_frame(
    brand: str,
    ram: int,
    storage: int,
    battery: int,
    camera: int,
    screen_size: float,
    fiveg: str,
    phone_age: float,
    condition: str,
) -> pd.DataFrame:
    """Return a single-row DataFrame in the exact column order used for training."""
    row = {
        "RAM":        ram,
        "Storage":    storage,
        "Battery":    battery,
        "Camera":     camera,
        "ScreenSize": screen_size,
        "PhoneAge":   phone_age,
        "Brand":      brand,
        "FiveG":      fiveg,
        "Condition":  condition,
    }
    return pd.DataFrame([row], columns=FEATURE_COLS)


def transform_features(
    df: pd.DataFrame,
    encoder,
    scaler,
) -> tuple:
    """
    Apply the same encoding + scaling pipeline used during training.

    Returns
    -------
    scaled       : np.ndarray
    feature_names: list[str]
    """
    encoded_cat = encoder.transform(df[CATEGORICAL_COLS])
    encoded_cat_df = pd.DataFrame(
        encoded_cat,
        columns=encoder.get_feature_names_out(CATEGORICAL_COLS),
        index=df.index,
    )
    numeric_df = df[NUMERIC_COLS].reset_index(drop=True)
    combined   = pd.concat(
        [numeric_df, encoded_cat_df.reset_index(drop=True)], axis=1
    )
    scaled = scaler.transform(combined)
    return scaled, combined.columns.tolist()


# ---------------------------------------------------------------------------
# Business logic helpers
# ---------------------------------------------------------------------------
def price_category(predicted_price: float, listed_price: float) -> tuple:
    """
    Compare a listed/asking price against the model's estimate and return
    a (category_label, description) tuple.
    """
    if predicted_price <= 0:
        return ("Fair Price ✅", "Could not compute difference.")

    diff_pct = (listed_price - predicted_price) / predicted_price * 100

    if diff_pct <= -70:
        return (
            "Suspicious Listing 🚨",
            "Price is unrealistically low — verify authenticity before purchasing.",
        )
    if diff_pct <= -20:
        return (
            "Great Deal 🔥",
            f"Listed price is {abs(diff_pct):.1f}% below estimated market value.",
        )
    if diff_pct <= -5:
        return (
            "Good Deal 👍",
            f"Listed price is {abs(diff_pct):.1f}% below estimated market value.",
        )
    if diff_pct < 10:
        return (
            "Fair Price ✅",
            "Listed price is close to estimated market value.",
        )
    return (
        "Overpriced ❌",
        f"Listed price is {diff_pct:.1f}% above estimated market value.",
    )


def value_for_money_score(
    ram: int,
    storage: int,
    battery: int,
    camera: int,
    screen_size: float,
    price: float,
) -> float:
    """
    Returns a 0–100 score reflecting how many specs you get per rupee.
    Higher is better.
    """
    if price <= 0:
        return 0.0
    spec_score = (
        ram * 4
        + storage * 0.3
        + battery / 100
        + camera * 2
        + screen_size * 5
    )
    # Normalise against price (₹5 000 unit scale)
    raw = spec_score / (price / 5_000 + 1)
    return round(float(np.clip(raw, 0, 100)), 1)


def price_range(predicted_price: float, margin: float = 0.08) -> tuple:
    """Return a (low, high) confidence range around the predicted price."""
    low  = predicted_price * (1 - margin)
    high = predicted_price * (1 + margin)
    return round(low, 2), round(high, 2)


def depreciation_forecast(
    base_price: float,
    current_age: float,
    years_ahead: int = 5,
    annual_rate: float = 0.20,
) -> list:
    """
    Return a list of (age, estimated_price) tuples covering the next
    `years_ahead` years from `current_age`.

    The floor is 8 % of the original base price (residual value).
    """
    floor  = base_price * 0.08
    points = []
    for y in range(years_ahead + 1):
        age   = round(current_age + y, 1)
        value = base_price * ((1 - annual_rate) ** y)
        points.append((age, round(max(value, floor), 2)))
    return points
