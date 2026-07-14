"""
utils/image.py
--------------
OpenCV-based phone image condition assessment.
Returns a condition score, label, detected issues, and a price-deduction %.
"""

import numpy as np


def assess_condition(image_bytes: bytes) -> dict:
    """
    Analyse a phone photo and return a condition assessment dict.

    Keys
    ----
    score      : int  — 0–100 condition score
    label      : str  — "Excellent" / "Good" / "Fair" / "Poor"
    issues     : list — human-readable defect descriptions
    condition  : str  — "New" or "Used"  (for model input)
    deduction  : int  — suggested price deduction in percent
    lap_var    : float — Laplacian variance (sharpness proxy)
    brightness : float — mean pixel brightness
    """
    try:
        import cv2

        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return _fallback("Could not decode image.")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, w = gray.shape
        score  = 100
        issues = []

        # 1. Sharpness via Laplacian variance
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < 40:
            score -= 35
            issues.append("Screen appears cracked or heavily scratched (low sharpness)")
        elif lap_var < 120:
            score -= 15
            issues.append("Minor scratches or slight blur detected")

        # 2. Brightness — very dark may indicate screen damage
        mean_bright = float(gray.mean())
        if mean_bright < 40:
            score -= 20
            issues.append("Display is very dark — possible screen damage")
        elif mean_bright < 80:
            score -= 8
            issues.append("Slightly dim — minor display issue possible")

        # 3. Colour-saturation variance — scratches reduce local uniformity
        sat_std = float(hsv[:, :, 1].std())
        if sat_std > 70:
            score -= 10
            issues.append("High colour variance — possible scratches or stains")

        # 4. Edge density — blank/off screen has very few edges
        edges      = cv2.Canny(gray, 50, 150)
        edge_ratio = edges.sum() / (255 * h * w)
        if edge_ratio < 0.005:
            score -= 10
            issues.append("Very few visible features — screen may be blank or off")

        score = int(np.clip(score, 0, 100))

        if score >= 85:
            label, condition, deduction = "Excellent", "New",  0
        elif score >= 65:
            label, condition, deduction = "Good",      "Used", 10
        elif score >= 40:
            label, condition, deduction = "Fair",      "Used", 25
        else:
            label, condition, deduction = "Poor",      "Used", 40

        if not issues:
            issues = ["No visible defects detected"]

        return {
            "score":      score,
            "label":      label,
            "issues":     issues,
            "condition":  condition,
            "deduction":  deduction,
            "lap_var":    round(lap_var, 1),
            "brightness": round(mean_bright, 1),
        }

    except ImportError:
        return _fallback("opencv-python-headless is not installed.")
    except Exception as exc:
        return _fallback(str(exc))


def _fallback(reason: str) -> dict:
    return {
        "score":      75,
        "label":      "Unknown",
        "issues":     [f"Image analysis unavailable: {reason}"],
        "condition":  "Used",
        "deduction":  0,
        "lap_var":    0.0,
        "brightness": 0.0,
    }
