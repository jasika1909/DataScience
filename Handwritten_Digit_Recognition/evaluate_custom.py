"""
evaluate_custom.py
------------------
Measures how well the model works on YOUR OWN handwriting (drawn on paper and
photographed, or exported from any drawing app). MNIST accuracy does not
guarantee this, so it is the most honest number to report.

Put images in  custom_digits/  in either layout:

    custom_digits/7/anything.png        (folder name = true digit)
    custom_digits/7_001.png             (file name starts with the true digit)

Usage:
    python evaluate_custom.py
    python evaluate_custom.py --folder my_digits
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import config
from utils.preprocessing import ImageProcessingError, load_image

EXTENSIONS = {".png", ".jpg", ".jpeg"}


def collect_images(folder):
    """Return [(path, true_digit)] using the folder name or file-name prefix."""
    items = []
    for path in sorted(Path(folder).rglob("*")):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        label = path.parent.name if path.parent.name.isdigit() else path.name[:1]
        if label.isdigit():
            items.append((path, int(label)))
    return items


def main():
    parser = argparse.ArgumentParser(description="Evaluate the model on your own digits.")
    parser.add_argument("--folder", default=str(config.CUSTOM_DIR))
    args = parser.parse_args()

    items = collect_images(args.folder)
    if not items:
        print(f"No labelled images found in '{args.folder}'. See the notes at the top of this file.")
        sys.exit(1)

    from utils.predictor import load_trained_model, predict_digit
    model = load_trained_model()

    correct, skipped = 0, 0
    per_digit = defaultdict(lambda: [0, 0])          # digit -> [correct, total]
    mistakes = []
    for path, truth in items:
        try:
            result = predict_digit(model, load_image(path))
        except ImageProcessingError as exc:
            print(f"skipped {path.name}: {exc}")
            skipped += 1
            continue
        per_digit[truth][1] += 1
        if result["digit"] == truth:
            per_digit[truth][0] += 1
            correct += 1
        else:
            mistakes.append((path.name, truth, result["digit"], result["confidence"]))

    total = sum(t for _, t in per_digit.values())
    if total == 0:
        print("No image could be processed.")
        sys.exit(1)

    print(f"\nCustom-digit accuracy: {correct}/{total} = {correct / total * 100:.1f}%"
          f"   ({skipped} skipped)\n")
    print("Per digit:")
    for d in sorted(per_digit):
        c, t = per_digit[d]
        print(f"  {d}: {c}/{t} = {c / t * 100:.0f}%")
    if mistakes:
        print("\nMistakes (file, true, predicted, confidence):")
        for name, truth, pred, conf in mistakes:
            print(f"  {name}: true {truth}, predicted {pred} ({conf * 100:.0f}%)")

    config.RESULTS_DIR.mkdir(exist_ok=True)
    out = {
        "accuracy": correct / total, "correct": correct, "total": total, "skipped": skipped,
        "per_digit": {str(d): {"correct": c, "total": t} for d, (c, t) in sorted(per_digit.items())},
        "mistakes": [{"file": n, "true": t, "predicted": p, "confidence": c}
                     for n, t, p, c in mistakes],
    }
    (config.RESULTS_DIR / "custom_eval.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved to {config.RESULTS_DIR / 'custom_eval.json'}")


if __name__ == "__main__":
    main()
