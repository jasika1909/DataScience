import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_COLS = ["RAM", "Storage", "Battery", "Camera", "ScreenSize", "PhoneAge"]
CATEGORICAL_COLS = ["Brand", "FiveG", "Condition"]


def load_raw_data(path):
    df = pd.read_csv(path)
    return df


def clean_data(df):
    """Basic cleaning: drop nulls, fix dtypes, remove obvious outliers."""
    df = df.dropna().copy()

    df["RAM"] = df["RAM"].astype(float)
    df["Storage"] = df["Storage"].astype(float)
    df["Battery"] = df["Battery"].astype(float)
    df["Camera"] = df["Camera"].astype(float)
    df["ScreenSize"] = df["ScreenSize"].astype(float)
    df["PhoneAge"] = df["PhoneAge"].astype(float)
    df["Price"] = df["Price"].astype(float)

    # remove unrealistic outliers
    df = df[(df["Price"] > 3000) & (df["Price"] < 250000)]
    df = df[(df["Battery"] > 1000) & (df["Battery"] < 8000)]
    df = df[(df["ScreenSize"] > 4) & (df["ScreenSize"] < 8)]

    return df.reset_index(drop=True)


def fit_encoder_scaler(df):
    """
    Fit a OneHotEncoder on categorical columns and a StandardScaler
    on the combined numeric + encoded-categorical feature matrix.
    Returns: encoder, scaler, X (scaled np array), y (target series), feature_names
    """
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoded_cat = encoder.fit_transform(df[CATEGORICAL_COLS])
    encoded_cat_df = pd.DataFrame(
        encoded_cat,
        columns=encoder.get_feature_names_out(CATEGORICAL_COLS),
        index=df.index,
    )

    numeric_df = df[NUMERIC_COLS].reset_index(drop=True)
    combined = pd.concat([numeric_df, encoded_cat_df.reset_index(drop=True)], axis=1)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(combined)

    y = df["Price"].reset_index(drop=True)

    return encoder, scaler, X_scaled, y, combined.columns.tolist()