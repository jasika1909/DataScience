"""
preprocess.py
-------------
Data loading, cleaning, and feature engineering pipeline.
Used by both train_model.py (fit) and the app (transform-only).
"""

import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Feature column definitions — single source of truth
NUMERIC_COLS     = ["RAM", "Storage", "Battery", "Camera", "ScreenSize", "PhoneAge"]
CATEGORICAL_COLS = ["Brand", "FiveG", "Condition"]


def load_raw_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop nulls, enforce dtypes, and remove obvious outliers.
    Returns a clean, reset-index DataFrame.
    """
    df = df.dropna().copy()

    # Enforce numeric dtypes
    for col in NUMERIC_COLS + ["Price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()

    # Clip to realistic Indian-market ranges
    df = df[(df["Price"]      >= 3_000) & (df["Price"]      <= 2_00_000)]
    df = df[(df["Battery"]    >= 1_500) & (df["Battery"]    <=  8_000)]
    df = df[(df["ScreenSize"] >=   4.0) & (df["ScreenSize"] <=    8.0)]
    df = df[(df["RAM"]        >=     1) & (df["RAM"]        <=   32)]
    df = df[(df["Storage"]    >=    16) & (df["Storage"]    <= 1024)]

    return df.reset_index(drop=True)


def fit_encoder_scaler(
    df: pd.DataFrame,
) -> tuple:
    """
    Fit a OneHotEncoder on categorical columns and a StandardScaler on the
    combined (numeric + encoded-categorical) feature matrix.

    Returns
    -------
    encoder      : fitted OneHotEncoder
    scaler       : fitted StandardScaler
    X_scaled     : np.ndarray  — scaled feature matrix
    y            : pd.Series   — target (Price)
    feature_names: list[str]   — column names matching X_scaled
    """
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoded_cat = encoder.fit_transform(df[CATEGORICAL_COLS])
    encoded_cat_df = pd.DataFrame(
        encoded_cat,
        columns=encoder.get_feature_names_out(CATEGORICAL_COLS),
        index=df.index,
    )

    numeric_df = df[NUMERIC_COLS].reset_index(drop=True)
    combined   = pd.concat(
        [numeric_df, encoded_cat_df.reset_index(drop=True)], axis=1
    )

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(combined)

    y = df["Price"].reset_index(drop=True)

    return encoder, scaler, X_scaled, y, combined.columns.tolist()
