import os
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

from preprocess import load_raw_data, clean_data, fit_encoder_scaler
from utils.helper import (
    DATA_PATH, MODEL_PATH, SCALER_PATH, ENCODER_PATH,
    BRANDS, CONDITIONS, FIVEG
)

np.random.seed(42)


def generate_synthetic_dataset(n=4000):
    brand_base_price = {
        "Apple": 70000,
        "Samsung": 45000,
        "Google": 50000,
        "OnePlus": 35000,
        "Nothing": 30000,
        "Xiaomi": 22000,
        "Realme": 18000,
        "Vivo": 22000,
        "Oppo": 22000,
        "Motorola": 20000
    }

    rows = []
    for i in range(n):
        brand = np.random.choice(BRANDS)
        ram = np.random.choice([2, 3, 4, 6, 8, 12, 16])
        storage = np.random.choice([32, 64, 128, 256, 512])
        battery = np.random.randint(3000, 6500)
        camera = np.random.choice([8, 12, 16, 32, 48, 50, 64, 108, 200])
        screen_size = round(np.random.uniform(5.0, 7.2), 1)
        fiveg = np.random.choice(FIVEG, p=[0.65, 0.35])
        phone_age = round(np.random.uniform(0, 5), 1)
        condition = np.random.choice(CONDITIONS, p=[0.55, 0.45])

        base = brand_base_price[brand]
        price = (
            base
            + ram * 2500
            + storage * 80
            + (battery - 3000) * 3
            + camera * 120
            + screen_size * 1200
            + (5000 if fiveg == "Yes" else 0)
        )

        # depreciation for age & used condition
        price *= (1 - 0.12 * phone_age)
        if condition == "Used":
            price *= 0.70

        # noise
        price *= np.random.uniform(0.90, 1.10)
        price = max(40, round(price, 2))

        rows.append({
            "Brand": brand,
            "Model": f"{brand}-{np.random.randint(100,999)}",
            "RAM": ram,
            "Storage": storage,
            "Battery": battery,
            "Camera": camera,
            "ScreenSize": screen_size,
            "FiveG": fiveg,
            "PhoneAge": phone_age,
            "Condition": condition,
            "Price": price,
        })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"Synthetic dataset generated at {DATA_PATH} ({len(df)} rows)")
    return df


def train():
    if not os.path.exists(DATA_PATH):
        generate_synthetic_dataset()

    df = load_raw_data(DATA_PATH)
    df = clean_data(df)

    encoder, scaler, X, y, feature_names = fit_encoder_scaler(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))

    print("===== Model Evaluation =====")
    print(f"R2 Score : {r2:.4f}")
    print(f"MAE      : {mae:.2f}")
    print(f"RMSE     : {rmse:.2f}")

    # Save artifacts
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(encoder, ENCODER_PATH)

    # Save metrics + feature importance for the app to display
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    importance_df.to_csv(
        os.path.join(os.path.dirname(DATA_PATH), "feature_importance.csv"),
        index=False
    )

    metrics = {"r2": r2, "mae": mae, "rmse": rmse}
    joblib.dump(metrics, os.path.join(os.path.dirname(MODEL_PATH), "metrics.pkl"))

    print("Model, scaler, and encoder saved successfully.")


if __name__ == "__main__":
    train()