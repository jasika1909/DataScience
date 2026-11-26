"""
utils/predictor.py
------------------
Loads the saved CNN and predicts digits from user images.
TensorFlow is imported only when the model is loaded, so a missing
dependency can be reported with a clear message instead of a crash.
"""
import sys
from pathlib import Path

import numpy as np

from config import MODEL_PATH
from utils.preprocessing import preprocess_image


class ModelNotFoundError(Exception):
    """The trained model file does not exist yet."""


class DependencyError(Exception):
    """TensorFlow is not installed."""


class ModelLoadError(Exception):
    """The model file exists but could not be loaded."""


class PredictionError(Exception):
    """The model failed while predicting."""


def load_trained_model(path=MODEL_PATH):
    """Load the saved Keras model from disk (no retraining)."""
    path = Path(path)
    if not path.exists():
        raise ModelNotFoundError(
            "Trained model not found. Run  python train.py  first "
            "(or use the Train button below)."
        )
    try:
        from tensorflow import keras
    except ImportError as exc:
        raise DependencyError(
            "TensorFlow is not installed. Run:  python -m pip install -r requirements.txt"
        ) from exc
    except Exception as exc:
        # TensorFlow is installed but fails while importing (for example a blocked DLL
        # on Windows, or an unsupported Python version). Show a readable message
        # instead of a long traceback.
        raise DependencyError(
            "TensorFlow is installed but could not start "
            f"(Python {sys.version_info.major}.{sys.version_info.minor}). "
            "Use Python 3.9 - 3.12 in a fresh virtual environment with "
            "'python -m pip install -r requirements.txt'. If Windows reports that an "
            "'Application Control policy has blocked this file', see the Troubleshooting "
            f"section of the README. Original error: {str(exc)[-300:]}"
        ) from exc
    try:
        return keras.models.load_model(path, compile=False)
    except Exception as exc:
        raise ModelLoadError(
            f"The model file could not be loaded ({exc}). "
            "Delete the files in the model folder and run  python train.py  again."
        ) from exc


def top_predictions(probs, k=3):
    """Return the k most likely digits as [(digit, probability), ...], best first."""
    order = np.argsort(probs)[::-1][:k]
    return [(int(i), float(probs[i])) for i in order]


def predict_digit(model, image):
    """
    Preprocess a PIL image and predict with the CNN.
    ImageProcessingError from preprocessing is allowed to propagate.
    """
    x, processed = preprocess_image(image)
    try:
        probs = np.asarray(model.predict(x, verbose=0))[0]
    except Exception as exc:
        raise PredictionError(f"Prediction failed: {exc}") from exc
    top = top_predictions(probs)
    return {
        "digit": top[0][0],
        "confidence": top[0][1],
        "probabilities": probs,
        "top": top,
        "margin": top[0][1] - top[1][1],     # small margin = model is torn between two digits
        "processed_image": processed,
    }
