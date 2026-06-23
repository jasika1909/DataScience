import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "encoder.pkl")
DATA_PATH = os.path.join(BASE_DIR, "data", "mobile_data.csv")

BRANDS = ["Samsung", "Apple", "Xiaomi", "OnePlus", "Realme", "Vivo", "Oppo", "Google", "Motorola", "Nothing"]
CONDITIONS = ["New", "Used"]
FIVEG = ["Yes", "No"]

NUMERIC_COLS = ["RAM", "Storage", "Battery", "Camera", "ScreenSize", "PhoneAge"]
CATEGORICAL_COLS = ["Brand", "FiveG", "Condition"]
FEATURE_COLS = NUMERIC_COLS + CATEGORICAL_COLS


def load_artifacts():
    """Load trained model, scaler and encoder from disk."""
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    encoder = joblib.load(ENCODER_PATH)
    return model, scaler, encoder


def build_feature_frame(brand, ram, storage, battery, camera, screen_size,
                         fiveg, phone_age, condition):
    """Build a single-row DataFrame in the exact column order used for training."""
    row = {
        "RAM": ram,
        "Storage": storage,
        "Battery": battery,
        "Camera": camera,
        "ScreenSize": screen_size,
        "PhoneAge": phone_age,
        "Brand": brand,
        "FiveG": fiveg,
        "Condition": condition,
    }
    return pd.DataFrame([row], columns=FEATURE_COLS)


def transform_features(df, encoder, scaler):
    """Apply the same encoding + scaling pipeline used during training."""
    encoded_cat = encoder.transform(df[CATEGORICAL_COLS])
    encoded_cat_df = pd.DataFrame(
        encoded_cat,
        columns=encoder.get_feature_names_out(CATEGORICAL_COLS),
        index=df.index,
    )
    numeric_df = df[NUMERIC_COLS].reset_index(drop=True)
    combined = pd.concat([numeric_df, encoded_cat_df.reset_index(drop=True)], axis=1)
    scaled = scaler.transform(combined)
    return scaled, combined.columns.tolist()


def price_category(predicted_price, listed_price):

    difference_percent = (
        (listed_price - predicted_price)
        / predicted_price
    ) * 100

    if difference_percent <= -70:
        return (
            "Suspicious Listing 🚨",
            "Price is unrealistically low. Verify authenticity before purchasing."
        )

    elif difference_percent <= -20:
        return (
            "Great Deal 🔥",
            f"Listed price is {abs(difference_percent):.1f}% below estimated market value."
        )

    elif difference_percent <= -5:
        return (
            "Good Deal 👍",
            f"Listed price is {abs(difference_percent):.1f}% below estimated market value."
        )

    elif difference_percent < 10:
        return (
            "Fair Price ✅",
            "Listed price is close to estimated market value."
        )

    else:
        return (
            "Overpriced ❌",
            f"Listed price is {difference_percent:.1f}% above estimated market value."
        )

def value_for_money_score(ram, storage, battery, camera, screen_size, price):
    spec_score = (ram * 4) + (storage * 0.3) + (battery / 100) + (camera * 2) + (screen_size * 5)
    raw_score = spec_score / (price / 5000 + 1)   # adjusted divisor for INR scale
    score = min(100, max(0, raw_score))
    return round(score, 1)


def price_range(predicted_price, margin=0.08):
    """Return a (low, high) tuple price range around the predicted price."""
    low = predicted_price * (1 - margin)
    high = predicted_price * (1 + margin)
    return round(low, 2), round(high, 2)