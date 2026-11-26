"""
Tests for image preprocessing (no TensorFlow needed).
Run from the project folder:   python -m unittest discover tests -v
"""
import io
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.preprocessing import ImageProcessingError, load_image, preprocess_image


def make_digit_image(digit="7", size=300, dark_on_light=True, mode="RGB"):
    """Draw a digit with a font: dark-on-white (paper) or white-on-black (canvas)."""
    bg, fg = ((255, 255, 255), (20, 20, 20)) if dark_on_light else ((0, 0, 0), (255, 255, 255))
    img = Image.new("RGB", (size, size), bg)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size * 0.6))
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((size * 0.3, size * 0.15), digit, fill=fg, font=font)
    return img.convert(mode) if mode != "RGB" else img


class PreprocessingTests(unittest.TestCase):
    def check_output(self, image):
        x, processed = preprocess_image(image)
        self.assertEqual(x.shape, (1, 28, 28, 1))
        self.assertEqual(x.dtype, np.float32)
        self.assertGreaterEqual(x.min(), 0.0)
        self.assertLessEqual(x.max(), 1.0)
        self.assertEqual(processed.size, (28, 28))
        # MNIST style: dark background (corners ~0), bright strokes
        self.assertLess(x[0, :3, :3, 0].mean(), 0.05)
        self.assertGreater(x.max(), 0.8)
        return x

    def test_dark_digit_on_white_is_inverted(self):
        x = self.check_output(make_digit_image(dark_on_light=True))
        self.assertLess(x.mean(), 0.5)

    def test_white_digit_on_black_kept(self):
        self.check_output(make_digit_image(dark_on_light=False))

    def test_both_polarities_give_similar_result(self):
        a, _ = preprocess_image(make_digit_image("3", dark_on_light=True))
        b, _ = preprocess_image(make_digit_image("3", dark_on_light=False))
        self.assertLess(np.abs(a - b).mean(), 0.05)

    def test_color_modes_and_sizes(self):
        for mode in ["RGB", "L", "RGBA", "P", "1"]:
            self.check_output(make_digit_image(mode=mode))
        for size in [32, 100, 600, 1500]:
            self.check_output(make_digit_image(size=size))

    def test_noisy_background(self):
        img = np.array(make_digit_image(dark_on_light=True), dtype=np.int16)
        noise = np.random.default_rng(0).integers(-25, 25, img.shape)
        self.check_output(Image.fromarray(np.clip(img + noise, 0, 255).astype(np.uint8)))

    def test_digit_is_centred(self):
        x, _ = preprocess_image(make_digit_image("1"))
        ys, xs = np.indices((28, 28))
        img = x[0, :, :, 0]
        cy, cx = (ys * img).sum() / img.sum(), (xs * img).sum() / img.sum()
        self.assertAlmostEqual(cy, 13.5, delta=1.5)
        self.assertAlmostEqual(cx, 13.5, delta=1.5)

    def test_blank_image_rejected(self):
        with self.assertRaises(ImageProcessingError):
            preprocess_image(Image.new("RGB", (200, 200), (255, 255, 255)))

    def test_tiny_image_rejected(self):
        with self.assertRaises(ImageProcessingError):
            preprocess_image(Image.new("RGB", (4, 4), (255, 255, 255)))

    def test_load_image_errors(self):
        with self.assertRaises(ImageProcessingError):
            load_image(io.BytesIO(b""))                      # empty file
        with self.assertRaises(ImageProcessingError):
            load_image(io.BytesIO(b"this is not an image"))  # wrong format
        with self.assertRaises(ImageProcessingError):
            load_image("does_not_exist.png")                 # missing file

    def test_load_image_roundtrip(self):
        buf = io.BytesIO()
        make_digit_image().save(buf, format="PNG")
        buf.seek(0)
        self.check_output(load_image(buf))


class TrainHelpersTests(unittest.TestCase):
    def test_plot_functions(self):
        import tempfile
        import pandas as pd
        import train
        with tempfile.TemporaryDirectory() as tmp:
            train.RESULTS_DIR = Path(tmp)
            hist = pd.DataFrame({"accuracy": [.9, .95, .97], "val_accuracy": [.92, .95, .96],
                                 "loss": [.3, .15, .1], "val_loss": [.25, .16, .12]})
            train.save_training_graphs(hist)
            train.save_confusion_matrix(np.eye(10, dtype=int) * 100)
            for name in ["accuracy.png", "loss.png", "confusion_matrix.png"]:
                self.assertTrue((Path(tmp) / name).stat().st_size > 1000, name)


if __name__ == "__main__":
    unittest.main()
