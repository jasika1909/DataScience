# Handwritten Digit Recognition (CNN + Streamlit)

Recognises handwritten digits 0-9 from an uploaded image or a digit drawn on a canvas.
A convolutional neural network is trained on MNIST (60,000 images) and served through a Streamlit web app.

## Quick start

Requires **Python 3.9 - 3.12** (TensorFlow 2.16/2.17 does not support 3.13 yet).

| OS | Command |
|----|---------|
| Windows | double-click `run.bat` |
| Linux / macOS | `./run.sh` |
| Manual | `pip install -r requirements.txt` → `python train.py` → `streamlit run app.py` |

The launchers install the requirements, train the model only if `model/digit_model.keras` is missing, then start the app.

## Project layout

```
app.py                 Streamlit app (Home, Digit Prediction, Draw Digit, Model Performance)
train.py               Trains and evaluates the CNN, writes model/ and results/
evaluate_custom.py     Measures accuracy on YOUR OWN digits (custom_digits/)
config.py              Paths and settings shared by every script
utils/preprocessing.py Image -> 28x28 MNIST-style input (invert, crop, stroke-width fix, centre)
utils/predictor.py     Model loading and prediction (top-3 probabilities, margin)
tests/                 Unit tests (no TensorFlow needed except one optional smoke test)
```

## Model (version 2)

Augmentation (rotation / shift / zoom) → 2 × [Conv-BN-ReLU ×2 → MaxPool → Dropout(0.25)] with 32 and 64 filters
→ Flatten → Dense(128) → Dropout(0.4) → Dense(10, softmax).

Training uses early stopping (patience 5) and `ReduceLROnPlateau`, up to 25 epochs.
`python train.py --epochs 40 --seed 7` changes the defaults.

> **Note:** `model/digit_model.keras` and the numbers in `results/` that ship with this folder come from the
> original version-1 model (98.84 % test accuracy, 8 epochs). Run `python train.py` once to train the
> version-2 model; the app's Model Performance page shows a notice until you do.

## Testing on your own handwriting

MNIST accuracy does not guarantee accuracy on your drawings. To measure it, save digits as images:

```
custom_digits/7/photo1.png        # folder name = true digit
custom_digits/7_002.png           # or a file name that starts with the digit
```

then run `python evaluate_custom.py`. It prints per-digit accuracy and every mistake, and the result
appears on the Model Performance page.

## Troubleshooting

**`RuntimeError ... DLL load failed ... An Application Control policy has blocked this file`**
(shown when the app opens Digit Prediction, in `_pywrap_analyzer_wrapper`)

This is a Windows security setting, not a bug in the project. Smart App Control (Windows 11) or a
college / company Application Control policy is blocking a DLL inside the TensorFlow package.
Try, in this order:

1. **Use Python 3.12, not 3.13 / 3.14**, in a new virtual environment, so that the pinned
   TensorFlow 2.16 / 2.17 from `requirements.txt` is installed:
   `py -3.12 -m venv .venv` → `.venv\Scripts\activate` → `pip install -r requirements.txt`.
   (Python 3.14 pulls a much newer TensorFlow that this project was not written for.)
2. On your **own PC**: Windows Security → App & browser control → Smart App Control settings →
   Off. (Turning it off cannot be undone without resetting Windows.)
3. On a **managed PC** (college lab, company laptop) the policy cannot be changed by you.
   Run the project on another computer, in WSL2 (Ubuntu), or in Google Colab.

## Tests

```
python -m unittest discover tests -v
```

## Tips for good predictions

* One digit per image, drawn large, with a plain background.
* The app shows the 28×28 image the CNN really sees, plus the runner-up digit; if the model is torn
  between two digits it tells you.

## Ideas for future work

* Multi-digit recognition (segment connected components, predict each).
* Fine-tune on your own handwriting collected through the Draw page.
* Export to TensorFlow Lite / ONNX for mobile or browser use.
