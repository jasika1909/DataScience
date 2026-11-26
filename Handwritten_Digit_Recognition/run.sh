#!/usr/bin/env bash
# One-command launcher for Linux / macOS: venv -> install -> train (if needed) -> app
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "[2/4] Installing requirements..."
python -m pip install -q -r requirements.txt

if [ ! -f "model/digit_model.keras" ]; then
  echo "[3/4] Trained model not found. Training now (a few minutes)..."
  python train.py
else
  echo "[3/4] Trained model found. Skipping training."
fi

echo "[4/4] Starting the Streamlit app..."
python -m streamlit run app.py
