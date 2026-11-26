"""
utils/custom_samples.py
-----------------------
Saves drawings the model got wrong (or right) together with the TRUE digit, in the
layout that evaluate_custom.py reads:   custom_digits/<digit>/draw_<timestamp>.png
"""
import time
from pathlib import Path

from config import CUSTOM_DIR


def save_sample(image, digit, folder=CUSTOM_DIR):
    """Save a PIL image under <folder>/<digit>/ and return the file path."""
    if not isinstance(digit, int) or isinstance(digit, bool) or not 0 <= digit <= 9:
        raise ValueError("digit must be an integer from 0 to 9")
    target = Path(folder) / str(digit)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"draw_{int(time.time() * 1000)}.png"
    image.convert("RGB").save(path)
    return path
