"""
utils/shap.py
-------------
SHAP-based explainability helpers for the XGBoost model.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Core SHAP computation
# ---------------------------------------------------------------------------
def get_shap_values(model, X_scaled: np.ndarray, feature_names: list):
    """
    Compute SHAP values using TreeExplainer.

    Returns
    -------
    (shap_values, base_value) on success, (None, None) on failure.
    """
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_scaled)
        base_val  = explainer.expected_value
        if isinstance(base_val, (list, np.ndarray)):
            base_val = float(base_val[0])
        return shap_vals, float(base_val)
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Waterfall chart (single prediction)
# ---------------------------------------------------------------------------
def plot_shap_waterfall(
    model,
    X_scaled: np.ndarray,
    feature_names: list,
    max_display: int = 12,
):
    """
    Return a matplotlib Figure showing a waterfall-style SHAP explanation
    for the first (only) row in X_scaled.
    Returns None if SHAP computation fails.
    """
    shap_vals, base_val = get_shap_values(model, X_scaled, feature_names)
    if shap_vals is None:
        return None

    vals = shap_vals[0]   # single row

    # Sort by absolute impact, take top N
    pairs = sorted(
        zip(feature_names, vals),
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:max_display]

    # Human-readable labels
    def _label(raw: str) -> str:
        return (
            raw.replace("Brand_",     "Brand:")
               .replace("Condition_", "Cond:")
               .replace("FiveG_",     "5G:")
        )

    labels = [_label(p[0]) for p in pairs]
    values = [p[1]         for p in pairs]
    colors = ["#3FB876" if v >= 0 else "#E2574C" for v in values]

    fig, ax = plt.subplots(figsize=(7, max(3, len(labels) * 0.45)))
    fig.patch.set_facecolor("#161B22")
    ax.set_facecolor("#161B22")

    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.65)

    # Value annotations on each bar
    max_abs = max(abs(v) for v in values) if values else 1
    for bar, val in zip(bars, values[::-1]):
        sign   = "+" if val >= 0 else ""
        offset = max_abs * 0.02
        ax.text(
            bar.get_width() + (offset if val >= 0 else -offset),
            bar.get_y() + bar.get_height() / 2,
            f"{sign}₹{val:,.0f}",
            va="center",
            ha="left" if val >= 0 else "right",
            fontsize=8,
            color="#E6EDF3",
            fontfamily="monospace",
        )

    ax.axvline(0, color="#7D8590", linewidth=0.8, linestyle="--")
    ax.set_xlabel("SHAP contribution (₹)", color="#7D8590", fontsize=9)
    ax.tick_params(colors="#7D8590", labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(
        f"Why this price?  |  Base: ₹{base_val:,.0f}",
        color="#C9A24B", fontsize=9, pad=10,
    )

    pos_patch = mpatches.Patch(color="#3FB876", label="Increases price")
    neg_patch = mpatches.Patch(color="#E2574C", label="Decreases price")
    ax.legend(
        handles=[pos_patch, neg_patch],
        loc="lower right", fontsize=8,
        framealpha=0, labelcolor="#7D8590",
    )

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Global feature importance bar chart
# ---------------------------------------------------------------------------
def plot_feature_importance(fi_df, top_n: int = 10):
    """Bar chart of global feature importance from the saved CSV."""
    fi = fi_df.head(top_n).copy()
    fi["feature"] = (
        fi["feature"]
        .str.replace("Brand_",     "Brand:")
        .str.replace("Condition_", "Cond:")
        .str.replace("FiveG_",     "5G:")
    )

    labels = fi["feature"].tolist()
    values = fi["importance"].values

    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor("#161B22")
    ax.set_facecolor("#161B22")
    ax.barh(labels[::-1], values[::-1], color="#C9A24B", height=0.65)
    ax.set_xlabel("Importance", color="#7D8590", fontsize=9)
    ax.tick_params(colors="#7D8590", labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Global Feature Importance (XGBoost)", color="#C9A24B", fontsize=9)
    plt.tight_layout()
    return fig
