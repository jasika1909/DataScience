"""
train_model.py
--------------
Generates synthetic Indian-market mobile phone data, trains an XGBoost
regressor, and saves model artifacts to disk.

Run:  python train_model.py
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib

from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import load_raw_data, clean_data, fit_encoder_scaler
from utils.helper import (
    DATA_PATH, MODEL_PATH, SCALER_PATH, ENCODER_PATH, METRICS_PATH,
    BRANDS, CONDITIONS, FIVEG,
)

np.random.seed(42)

# ---------------------------------------------------------------------------
# Brand-level market anchors (₹) — entry-level floor for each brand.
# The formula stacks spec premiums on top of this base.
# Apple/Google/Samsung command a large brand premium vs Xiaomi/Realme.
# ---------------------------------------------------------------------------
BRAND_BASE = {
    "Apple":    70000,   # iPhone SE / base iPhone 15 (India pricing)
    "Samsung":  22000,   # Galaxy A-series mid entry
    "Google":   50000,   # Pixel 6a base (India)
    "OnePlus":  22000,   # OnePlus Nord base
    "Nothing":  20000,   # Phone 1 base
    "Xiaomi":    8000,   # Redmi entry
    "Realme":    7000,   # Realme entry
    "Vivo":      9500,   # Vivo Y-series entry
    "Oppo":      9500,   # Oppo A-series entry
    "Motorola":  8500,   # Moto G base
}

# RAM tier premiums — scaled to real Indian upgrade costs
RAM_PREMIUM     = {2: 0, 3: 800, 4: 2000, 6: 4500, 8: 7500, 12: 12000, 16: 18000}
STORAGE_PREMIUM = {32: 0, 64: 1200, 128: 3000, 256: 6000, 512: 11000}


def generate_synthetic_dataset(n: int = 5000) -> pd.DataFrame:
    """
    Build a realistic synthetic dataset for Indian smartphone pricing.

    Pricing formula (all in ₹):
        price  = brand_base
                + ram_premium
                + storage_premium
                + battery_bonus        (every 100 mAh above 3 000 → +₹60)
                + camera_bonus         (log-scaled so 200 MP isn't crazy)
                + screen_bonus         (₹800 per 0.1 in above 5 in)
                + fiveg_premium        (+₹4 000 for 5G)
                − age_depreciation     (brand_rate % per year, compounded)
                − used_discount        (30 % off for Used)
                + noise                (±8 %)

    Ranges are clipped to ₹4 000 – ₹2 00 000 before saving.
    """

    # Per-brand annual depreciation rates
    depr_rate = {
        "Apple": 0.13, "Samsung": 0.18, "Google": 0.17, "OnePlus": 0.20,
        "Nothing": 0.22, "Motorola": 0.22, "Xiaomi": 0.24,
        "Realme": 0.25, "Vivo": 0.24, "Oppo": 0.24,
    }

    ram_choices     = [2, 3, 4, 6, 8, 12, 16]
    storage_choices = [32, 64, 128, 256, 512]
    camera_choices  = [8, 12, 16, 32, 48, 50, 64, 108, 200]

    rows = []
    for _ in range(n):
        brand     = np.random.choice(BRANDS)
        ram       = int(np.random.choice(ram_choices))
        storage   = int(np.random.choice(storage_choices))
        battery   = int(np.random.randint(3000, 6500))
        camera    = int(np.random.choice(camera_choices))
        screen    = round(float(np.random.uniform(5.0, 7.2)), 1)
        fiveg     = str(np.random.choice(FIVEG, p=[0.60, 0.40]))
        age       = round(float(np.random.uniform(0.0, 5.0)), 1)
        condition = str(np.random.choice(CONDITIONS, p=[0.55, 0.45]))

        # --- build price ---
        price = float(BRAND_BASE[brand])
        price += RAM_PREMIUM.get(ram, 0)
        price += STORAGE_PREMIUM.get(storage, 0)
        price += (battery - 3000) * 0.5           # mAh bonus
        price += np.log1p(camera) * 1200           # log-scaled camera premium
        price += max(0, (screen - 5.0)) * 3000    # screen premium
        price += 3000 if fiveg == "Yes" else 0

        # Brand-level ecosystem/OS premium (Apple and Google carry extra premium
        # in India beyond raw specs — iOS ecosystem, software support, etc.)
        if brand == "Apple":
            price *= 1.35
        elif brand == "Google":
            price *= 1.10
        elif brand == "Samsung":
            price *= 1.10

        # Depreciation — compounded per year of age
        rate   = depr_rate.get(brand, 0.20)
        price *= (1 - rate) ** age

        # Used discount
        if condition == "Used":
            price *= 0.72

        # ±8 % market noise
        price *= np.random.uniform(0.92, 1.08)

        # Clip to realistic bounds
        price = float(np.clip(round(price, 2), 4000, 200000))

        rows.append({
            "Brand":      brand,
            "Model":      f"{brand}-{np.random.randint(100, 999)}",
            "RAM":        ram,
            "Storage":    storage,
            "Battery":    battery,
            "Camera":     camera,
            "ScreenSize": screen,
            "FiveG":      fiveg,
            "PhoneAge":   age,
            "Condition":  condition,
            "Price":      price,
        })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"[dataset] {len(df):,} rows → {DATA_PATH}")
    return df


def train() -> None:
    # --- data ---
    if not os.path.exists(DATA_PATH):
        print("[dataset] Generating synthetic dataset …")
        generate_synthetic_dataset()

    df = load_raw_data(DATA_PATH)
    df = clean_data(df)
    print(f"[dataset] {len(df):,} clean rows loaded.")

    encoder, scaler, X, y, feature_names = fit_encoder_scaler(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    # --- XGBoost ---
    model = XGBRegressor(
        n_estimators=600,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.80,
        colsample_bytree=0.80,
        reg_alpha=10,
        reg_lambda=20,
        min_child_weight=5,
        random_state=42,
        tree_method="hist",        # fast histogram method
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    preds = model.predict(X_test)
    r2   = float(r2_score(y_test, preds))
    mae  = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))

    print("\n===== Model Evaluation =====")
    print(f"R²   : {r2:.4f}")
    print(f"MAE  : ₹{mae:,.0f}")
    print(f"RMSE : ₹{rmse:,.0f}")

    # --- save artifacts ---
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model,   MODEL_PATH)
    joblib.dump(scaler,  SCALER_PATH)
    joblib.dump(encoder, ENCODER_PATH)

    metrics = {"r2": r2, "mae": mae, "rmse": rmse}
    joblib.dump(metrics, METRICS_PATH)

    # global feature importance
    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    fi_path = os.path.join(os.path.dirname(DATA_PATH), "feature_importance.csv")
    importance_df.to_csv(fi_path, index=False)

    print(f"\n[artifacts] model  → {MODEL_PATH}")
    print(f"[artifacts] scaler → {SCALER_PATH}")
    print(f"[artifacts] encoder→ {ENCODER_PATH}")
    print(f"[artifacts] metrics→ {METRICS_PATH}")
    print(f"[artifacts] fi_csv → {fi_path}")
    print("\nDone. ✓")


if __name__ == "__main__":
    train()
