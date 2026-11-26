"""
config.py
---------
Single place for paths and settings shared by train.py, evaluate_custom.py,
utils/predictor.py and app.py.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"
RESULTS_DIR = BASE_DIR / "results"
SAMPLES_DIR = BASE_DIR / "assets" / "sample_images"
CUSTOM_DIR = BASE_DIR / "custom_digits"
MODEL_PATH = MODEL_DIR / "digit_model.keras"

SEED = 42
DEFAULT_EPOCHS = 25
DEFAULT_BATCH_SIZE = 128

# Bumped whenever the architecture in train.py changes. results/metrics.json
# stores it so the app can tell when the saved results belong to an older model.
MODEL_VERSION = 2

# App settings
LOW_CONFIDENCE = 0.60      # below this the app asks for a clearer drawing
AMBIGUOUS_MARGIN = 0.25    # top-1 minus top-2 probability below this = "torn" prediction
SIDEBAR_CAPTION = "B.Tech CSE (Data Science & AI)"

LEGACY_ARCHITECTURE = (
    "Input (28,28,1)\n"
    "→ Conv2D(32, 3x3, ReLU) → MaxPooling(2x2)\n"
    "→ Conv2D(64, 3x3, ReLU) → MaxPooling(2x2)\n"
    "→ Flatten → Dropout(0.5)\n"
    "→ Dense(128, ReLU) → Dense(10, Softmax)"
)
