"""
train.py
--------
Trains a CNN on the MNIST dataset (downloaded automatically), evaluates it and
saves everything the Streamlit app needs.

Usage:
    python train.py                 # normal training (max 25 epochs, early stopping)
    python train.py --epochs 5      # quicker run
    python train.py --seed 7        # different random seed

Creates:
    model/digit_model.keras
    results/accuracy.png, loss.png, confusion_matrix.png
    results/metrics.json, history.csv, classification_report.csv
    results/most_confused.csv, results/architecture.txt
    assets/sample_images/mnist_digit_0.png ... mnist_digit_9.png
"""
import argparse
import json
import sys

import matplotlib
matplotlib.use("Agg")                      # draw plots without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Avoid Unicode errors when the console is not UTF-8 (older Windows terminals)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
from config import MODEL_DIR, MODEL_PATH, RESULTS_DIR, SAMPLES_DIR, SEED


# ----------------------------------------------------------------------------
# 1. Data
# ----------------------------------------------------------------------------
def load_and_preprocess():
    """Download/load MNIST, normalise pixels to 0-1, reshape to (N, 28, 28, 1)."""
    from tensorflow import keras

    print("Loading MNIST dataset (downloaded automatically on first run)...")
    (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
    print(f"Training images: {x_train.shape} | Test images: {x_test.shape}")

    x_train = (x_train.astype("float32") / 255.0).reshape(-1, 28, 28, 1)
    x_test = (x_test.astype("float32") / 255.0).reshape(-1, 28, 28, 1)
    return x_train, y_train, x_test, y_test


def save_sample_images(x_test, y_test):
    """Save one real MNIST test image per digit, handy for testing uploads."""
    from PIL import Image

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for digit in range(10):
        idx = int(np.where(y_test == digit)[0][0])
        img = (x_test[idx].reshape(28, 28) * 255).astype("uint8")
        Image.fromarray(img).resize((280, 280), Image.NEAREST).save(
            SAMPLES_DIR / f"mnist_digit_{digit}.png"
        )


# ----------------------------------------------------------------------------
# 2. Model
# ----------------------------------------------------------------------------
def build_model():
    """
    CNN: light augmentation -> 2 x (Conv-BN-ReLU, Conv-BN-ReLU, Pool, Dropout)
    -> dense classifier. BatchNorm + a learning-rate schedule let it train
    faster and reach higher accuracy than the original two-layer CNN.
    """
    from tensorflow import keras
    from tensorflow.keras import layers

    def conv_bn(filters):
        return [
            layers.Conv2D(filters, (3, 3), padding="same", use_bias=False),
            layers.BatchNormalization(),
            layers.Activation("relu"),
        ]

    model = keras.Sequential([
        layers.Input(shape=(28, 28, 1)),

        # Data augmentation (only active during training). It makes the model
        # more robust to slightly shifted / rotated hand-drawn digits.
        layers.RandomRotation(0.08, fill_mode="constant"),
        layers.RandomTranslation(0.08, 0.08, fill_mode="constant"),
        layers.RandomZoom(0.1, fill_mode="constant"),

        *conv_bn(32), *conv_bn(32),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        *conv_bn(64), *conv_bn(64),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        layers.Flatten(),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.4),                          # reduces overfitting
        layers.Dense(10, activation="softmax"),       # probabilities for 0-9
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def architecture_text(model):
    """Plain-text layer list (skips augmentation layers) shown in the app."""
    lines = ["Input (28,28,1)"]
    for layer in model.layers:
        name = layer.__class__.__name__
        if name.startswith("Random"):
            continue
        if name == "Conv2D":
            lines.append(f"→ Conv2D({layer.filters}, 3x3, same)")
        elif name == "BatchNormalization":
            lines.append("   BatchNorm")
        elif name == "Activation":
            lines.append("   ReLU")
        elif name == "MaxPooling2D":
            lines.append("→ MaxPooling(2x2)")
        elif name == "Dropout":
            lines.append(f"   Dropout({layer.rate})")
        elif name == "Flatten":
            lines.append("→ Flatten")
        elif name == "Dense":
            act = layer.activation.__name__.capitalize()
            lines.append(f"→ Dense({layer.units}, {act})")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 3. Result plots
# ----------------------------------------------------------------------------
def _plot_curve(history_df, train_col, val_col, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    epochs = range(1, len(history_df) + 1)
    ax.plot(epochs, history_df[train_col], marker="o", label=f"Training {ylabel.lower()}")
    ax.plot(epochs, history_df[val_col], marker="s", label=f"Validation {ylabel.lower()}")
    ax.set_title(title)
    ax.set_xlabel("Epoch")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / filename, dpi=120)
    plt.close(fig)


def save_training_graphs(history_df):
    _plot_curve(history_df, "accuracy", "val_accuracy",
                "Training vs Validation Accuracy", "Accuracy", "accuracy.png")
    _plot_curve(history_df, "loss", "val_loss",
                "Training vs Validation Loss", "Loss", "loss.png")


def save_confusion_matrix(cm):
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, ax=ax)
    ax.set_title("Confusion Matrix (10,000 test images)")
    ax.set_xlabel("Predicted digit")
    ax.set_ylabel("Actual digit")
    ax.set_xticks(range(10))
    ax.set_yticks(range(10))
    threshold = cm.max() / 2
    for i in range(10):
        for j in range(10):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=8,
                    color="white" if cm[i, j] > threshold else "black")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=120)
    plt.close(fig)


def most_confused_pairs(cm, top=10):
    """Return the digit pairs the model mixes up most often."""
    rows = [
        {"actual": i, "predicted": j, "count": int(cm[i, j])}
        for i in range(10) for j in range(10) if i != j and cm[i, j] > 0
    ]
    return pd.DataFrame(rows).sort_values("count", ascending=False).head(top)


# ----------------------------------------------------------------------------
# 4. Main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Train the MNIST digit CNN.")
    parser.add_argument("--epochs", type=int, default=config.DEFAULT_EPOCHS,
                        help=f"maximum epochs (default {config.DEFAULT_EPOCHS})")
    parser.add_argument("--batch-size", type=int, default=config.DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=SEED, help="random seed (default 42)")
    args = parser.parse_args()

    try:
        import tensorflow as tf
        from sklearn.metrics import classification_report, confusion_matrix
        from tensorflow import keras
    except ImportError as exc:
        print(f"\nERROR: a required package is missing ({exc}).")
        print("Fix:  python -m pip install -r requirements.txt")
        sys.exit(1)

    MODEL_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    np.random.seed(args.seed)
    tf.random.set_seed(args.seed)

    try:
        x_train, y_train, x_test, y_test = load_and_preprocess()
    except Exception as exc:
        print(f"\nERROR: could not load the MNIST dataset ({exc}).")
        print("Check your internet connection (needed only once to download MNIST).")
        sys.exit(1)

    save_sample_images(x_test, y_test)

    model = build_model()
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=5, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5, verbose=1),
    ]
    print("\nTraining started...")
    history = model.fit(
        x_train, y_train,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=0.1,          # 10% of training data used for validation
        callbacks=callbacks,
        verbose=2,
    )

    # ---- Evaluation on the unseen test set ----
    test_loss, test_acc = model.evaluate(x_test, y_test, verbose=0)
    print(f"\nTest Accuracy: {test_acc * 100:.2f}%   Test Loss: {test_loss:.4f}")

    y_pred = np.argmax(model.predict(x_test, verbose=0), axis=1)
    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred, digits=4))
    report = classification_report(y_test, y_pred, digits=4, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)

    # ---- Save model + results ----
    model.save(MODEL_PATH)

    history_df = pd.DataFrame(history.history)
    history_df.to_csv(RESULTS_DIR / "history.csv", index=False)
    pd.DataFrame(report).transpose().to_csv(RESULTS_DIR / "classification_report.csv")
    save_training_graphs(history_df)
    save_confusion_matrix(cm)
    most_confused_pairs(cm).to_csv(RESULTS_DIR / "most_confused.csv", index=False)
    (RESULTS_DIR / "architecture.txt").write_text(architecture_text(model), encoding="utf-8")

    metrics = {
        "test_accuracy": float(test_acc),
        "test_loss": float(test_loss),
        "final_train_accuracy": float(history_df["accuracy"].iloc[-1]),
        "final_val_accuracy": float(history_df["val_accuracy"].iloc[-1]),
        "epochs_trained": int(len(history_df)),
        "total_parameters": int(model.count_params()),
        "model_version": config.MODEL_VERSION,
        "seed": args.seed,
        "tensorflow_version": tf.__version__,
    }
    with open(RESULTS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nModel saved to : {MODEL_PATH}")
    print(f"Results saved to: {RESULTS_DIR}")
    print("\nMost confused digit pairs:\n")
    print(most_confused_pairs(cm, top=5).to_string(index=False))
    print("\nTraining complete. Now run:  streamlit run app.py")
    print("Tip: measure real-world accuracy with  python evaluate_custom.py")


if __name__ == "__main__":
    main()
