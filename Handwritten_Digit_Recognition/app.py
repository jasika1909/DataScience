import json
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from PIL import Image

import config
from config import (AMBIGUOUS_MARGIN, LEGACY_ARCHITECTURE, LOW_CONFIDENCE, MODEL_PATH,
                    RESULTS_DIR, SIDEBAR_CAPTION)
from utils.custom_samples import save_sample
from utils.preprocessing import ImageProcessingError, load_image
from utils.predictor import (
    DependencyError, ModelLoadError, ModelNotFoundError, PredictionError,
    load_trained_model, predict_digit,
)

BASE_DIR = config.BASE_DIR

st.set_page_config(page_title="Handwritten Digit Recognition", page_icon="🔢", layout="wide")

st.markdown(
    """
    <style>
    .main-title {font-size: 2.2rem; font-weight: 700; color: #1f4e79; margin-bottom: 0;}
    .sub-title {color: #5a6672; font-size: 1.05rem; margin-bottom: 1rem;}
    .digit-card {background: #eef4fb; border: 2px solid #1f77b4; border-radius: 14px;
                 padding: 18px; text-align: center;}
    .digit-card .label {color: #5a6672; font-size: 0.95rem;}
    .digit-card .digit {font-size: 4.5rem; font-weight: 800; color: #1f4e79; line-height: 1.1;}
    .digit-card .conf {font-size: 1.3rem; font-weight: 600; color: #2e7d32;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Model loading (cached: the model is loaded once, never retrained)
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading trained model...")
def _load_model(path_str, mtime):
    # `mtime` is part of the cache key: retraining (even from a terminal while the
    # app is open) changes the file's timestamp, so the new model is picked up.
    return load_trained_model(path_str)


def get_model():
    mtime = MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else 0.0
    return _load_model(str(MODEL_PATH), mtime)


def show_train_option():
    """Shown when the model file is missing: lets the user train from the UI."""
    st.code("python train.py", language="bash")
    st.caption("Run the command above in the project folder, or train from here:")
    if st.button("Train model now (takes a few minutes)"):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        with st.spinner("Training the CNN on MNIST... please wait."):
            proc = subprocess.run(
                [sys.executable, str(BASE_DIR / "train.py")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(BASE_DIR), env=env,
            )
        if proc.returncode == 0:
            _load_model.clear()
            st.success("Training finished. Reloading the app...")
            st.rerun()
        else:
            st.error("Training failed. Details:")
            st.code((proc.stdout + "\n" + proc.stderr)[-3000:])


def require_model():
    """Return the loaded model, or show a helpful message and return None."""
    try:
        return get_model()
    except ModelNotFoundError as exc:
        st.error(str(exc))
        show_train_option()
    except (DependencyError, ModelLoadError) as exc:
        st.error(str(exc))
    return None


# ----------------------------------------------------------------------------
# Shared display helpers
# ----------------------------------------------------------------------------
def probability_chart(probs, predicted):
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    colors = ["#1f77b4" if i == predicted else "#c7d3e0" for i in range(10)]
    bars = ax.bar(range(10), probs * 100, color=colors)
    for bar, p in zip(bars, probs * 100):
        if p >= 1:
            ax.text(bar.get_x() + bar.get_width() / 2, p + 1.5, f"{p:.1f}",
                    ha="center", fontsize=8)
    ax.set_xticks(range(10))
    ax.set_xlabel("Digit")
    ax.set_ylabel("Probability (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Probability Distribution (digits 0-9)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def show_result(result):
    """Predicted digit, confidence, processed image and all 10 probabilities."""
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.markdown("**Preprocessed input (28×28)**")
        st.image(result["processed_image"].resize((168, 168), Image.NEAREST), width=168)
        st.caption("This is exactly what the CNN sees.")
    with c2:
        st.markdown(
            f"""<div class="digit-card"><div class="label">Predicted Digit</div>
            <div class="digit">{result['digit']}</div>
            <div class="conf">{result['confidence'] * 100:.2f}% confidence</div></div>""",
            unsafe_allow_html=True,
        )
        runner_digit, runner_prob = result["top"][1]
        st.caption(f"Runner-up: **{runner_digit}** ({runner_prob * 100:.1f}%)")
        if result["confidence"] < LOW_CONFIDENCE:
            st.warning("Low confidence - try a clearer, thicker, single digit.")
        elif result["margin"] < AMBIGUOUS_MARGIN:
            st.warning(f"The model is torn between {result['digit']} and {runner_digit}. "
                       "Try drawing the digit more clearly.")
    with c3:
        fig = probability_chart(result["probabilities"], result["digit"])
        st.pyplot(fig)
        plt.close(fig)

    table = pd.DataFrame({
        "Digit": list(range(10)),
        "Probability (%)": (result["probabilities"] * 100).round(2),
    })
    with st.expander("Show probability table for all digits"):
        st.dataframe(table, hide_index=True, use_container_width=True)


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home():
    st.markdown('<p class="main-title">🔢 Handwritten Digit Recognition</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Using Convolutional Neural Networks (CNN) trained on the MNIST dataset</p>',
                unsafe_allow_html=True)

    st.markdown("### Project Description")
    st.write(
        "This project recognises handwritten digits (0-9) from images. A Convolutional Neural "
        "Network is trained on 60,000 MNIST images and the saved model is used here to give real "
        "predictions for images you upload or digits you draw."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Objective")
        st.markdown(
            "- Build a CNN that classifies digits 0-9 with high accuracy\n"
            "- Evaluate it using accuracy, loss, confusion matrix and classification report\n"
            "- Provide an easy web interface for real-time prediction"
        )
        st.markdown("### Technologies Used")
        st.markdown(
            "- **Python** - programming language\n"
            "- **TensorFlow / Keras** - building and training the CNN\n"
            "- **NumPy & Pandas** - numerical and tabular data handling\n"
            "- **Matplotlib** - graphs and charts\n"
            "- **Scikit-learn** - classification report and confusion matrix\n"
            "- **Pillow** - image loading and processing\n"
            "- **Streamlit** - web application"
        )
    with right:
        st.markdown("### How the System Works")
        st.markdown(
            "1. **Input** - upload an image or draw a digit on the canvas\n"
            "2. **Preprocessing** - grayscale → invert if background is light → crop the digit → "
            "resize to 20×20 → centre in 28×28 → normalise to 0-1\n"
            "3. **CNN** - convolution and pooling layers extract features, dense layers classify\n"
            "4. **Softmax output** - 10 probabilities (one per digit)\n"
            "5. **Result** - the highest probability is the predicted digit; its value is the confidence"
        )
        st.markdown("### Model Architecture")
        arch_file = RESULTS_DIR / "architecture.txt"
        arch = arch_file.read_text(encoding="utf-8") if arch_file.exists() else LEGACY_ARCHITECTURE
        st.code(arch, language="text")
    st.info("Use the sidebar to open **Digit Prediction**, **Draw Digit** or **Model Performance**.")


def page_prediction():
    st.header("📤 Digit Prediction")
    st.caption("Upload an image of ONE handwritten digit (PNG / JPG / JPEG). "
               "Dark digit on a plain light background (or the reverse) works best.")
    model = require_model()
    if model is None:
        return

    file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
    if file is None:
        st.info("Upload an image to get a prediction. Sample images are in `assets/sample_images/`.")
        return

    try:
        image = load_image(file)
    except ImageProcessingError as exc:
        st.error(str(exc))
        return

    left, right = st.columns([1, 3])
    with left:
        st.markdown("**Uploaded image**")
        st.image(image, width=220)
        st.caption(f"Size: {image.size[0]}×{image.size[1]} | Mode: {image.mode}")
    with right:
        try:
            show_result(predict_digit(model, image))
        except ImageProcessingError as exc:
            st.warning(str(exc))
        except PredictionError as exc:
            st.error(str(exc))


def page_draw():
    st.header("✏️ Draw Digit")
    st.caption("Draw one digit with your mouse: Drawing → Preprocessing → CNN → Prediction → Confidence")
    model = require_model()
    if model is None:
        return

    try:
        from streamlit_drawable_canvas import st_canvas
    except ImportError:
        st.error("The drawing canvas package is missing. Run:  "
                 "python -m pip install streamlit-drawable-canvas==0.9.3")
        st.info("You can still use the **Digit Prediction** page to upload images.")
        return

    brush = st.slider("Brush size", 8, 28, 14, help="8-18 works best. Very thick brushes merge strokes.")
    left, right = st.columns([1, 3])
    with left:
        canvas = st_canvas(
            fill_color="#000000",
            stroke_width=brush,
            stroke_color="#FFFFFF",        # white digit on black, like MNIST
            background_color="#000000",
            height=320, width=320,
            drawing_mode="freedraw",
            key="digit_canvas",
        )
        st.caption("Draw BIG (fill most of the canvas) and use the 🗑 icon below it to clear.")

    with right:
        data = canvas.image_data
        if data is None or data[:, :, :3].max() < 50:
            st.info("Draw a digit on the canvas - the prediction appears here.")
            return
        image = Image.fromarray(data[:, :, :3].astype("uint8"))
        try:
            show_result(predict_digit(model, image))
        except ImageProcessingError as exc:
            st.warning(str(exc))
            return
        except PredictionError as exc:
            st.error(str(exc))
            return

        with st.expander("Wrong prediction? Save this drawing with the correct digit"):
            st.caption("Saved to custom_digits/. Later run  python evaluate_custom.py  to see "
                       "which digits the model gets wrong on YOUR handwriting.")
            true_digit = st.selectbox("Correct digit", list(range(10)), key="true_digit")
            if st.button("Save drawing"):
                try:
                    st.success(f"Saved: {save_sample(image, int(true_digit))}")
                except (OSError, ValueError) as exc:
                    st.error(f"Could not save the drawing: {exc}")


def page_performance():
    st.header("📊 Model Performance")
    metrics_file = RESULTS_DIR / "metrics.json"
    if not metrics_file.exists():
        st.warning("No evaluation results found yet. Run  `python train.py`  first.")
        return
    try:
        with open(metrics_file, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, json.JSONDecodeError):
        st.error("results/metrics.json is unreadable. Run  `python train.py`  again.")
        return

    if m.get("model_version", 1) < config.MODEL_VERSION:
        st.info("These results belong to the original (version 1) model. "
                "Run  `python train.py`  to train the improved model and refresh this page.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test Accuracy", f"{m['test_accuracy'] * 100:.2f}%")
    c2.metric("Test Loss", f"{m['test_loss']:.4f}")
    c3.metric("Epochs Trained", m["epochs_trained"])
    c4.metric("Parameters", f"{m['total_parameters']:,}")
    st.caption(f"Final training accuracy: {m['final_train_accuracy'] * 100:.2f}% | "
               f"Final validation accuracy: {m['final_val_accuracy'] * 100:.2f}%")

    def show_image(name, caption):
        path = RESULTS_DIR / name
        if path.exists():
            try:
                st.image(str(path), caption=caption, use_container_width=True)
            except TypeError:       # older Streamlit versions use another name
                st.image(str(path), caption=caption, use_column_width=True)
        else:
            st.warning(f"{name} is missing. Run  python train.py  again.")

    st.markdown("#### Training & Validation Graphs")
    g1, g2 = st.columns(2)
    with g1:
        show_image("accuracy.png", "Training accuracy vs validation accuracy")
    with g2:
        show_image("loss.png", "Training loss vs validation loss")

    st.markdown("#### Confusion Matrix and Classification Report")
    g3, g4 = st.columns(2)
    with g3:
        show_image("confusion_matrix.png", "Confusion matrix on the test set")
    with g4:
        report_path = RESULTS_DIR / "classification_report.csv"
        if report_path.exists():
            report = pd.read_csv(report_path, index_col=0).round(4)
            if "support" in report.columns:
                report["support"] = report["support"].astype(int)
            st.dataframe(report, use_container_width=True, height=440)
            st.caption("Precision, recall and F1-score for each digit (0-9).")
        else:
            st.warning("classification_report.csv is missing. Run  python train.py  again.")

    confused_path = RESULTS_DIR / "most_confused.csv"
    if confused_path.exists():
        with st.expander("Most confused digit pairs"):
            st.dataframe(pd.read_csv(confused_path), hide_index=True, use_container_width=True)

    custom_path = RESULTS_DIR / "custom_eval.json"
    if custom_path.exists():
        try:
            ce = json.loads(custom_path.read_text(encoding="utf-8"))
            st.markdown("#### Accuracy on your own handwriting")
            st.metric("Custom-digit accuracy", f"{ce['accuracy'] * 100:.1f}%",
                      help=f"{ce['correct']} of {ce['total']} images")
        except (OSError, ValueError, KeyError):
            pass

    history_path = RESULTS_DIR / "history.csv"
    if history_path.exists():
        with st.expander("Epoch-by-epoch training history"):
            hist = pd.read_csv(history_path)
            hist.insert(0, "epoch", range(1, len(hist) + 1))
            st.dataframe(hist.round(4), hide_index=True, use_container_width=True)


# ----------------------------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------------------------
st.sidebar.title("🔢 Digit Recognition")
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Digit Prediction", "Draw Digit", "Model Performance"],
)
st.sidebar.markdown("---")
st.sidebar.caption(SIDEBAR_CAPTION)
st.sidebar.caption("Model: CNN (Keras) | Dataset: MNIST")
if MODEL_PATH.exists():
    st.sidebar.success("Trained model found")
else:
    st.sidebar.warning("Model not trained yet")

if page == "Home":
    page_home()
elif page == "Digit Prediction":
    page_prediction()
elif page == "Draw Digit":
    page_draw()
else:
    page_performance()