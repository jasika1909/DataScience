"""
Tests for utils/predictor.py and evaluate_custom.py.
They use a fake model, so TensorFlow is NOT needed.
Run from the project folder:   python -m unittest discover tests -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
import evaluate_custom
from utils import predictor
from utils.preprocessing import ImageProcessingError
from tests.test_preprocessing import make_digit_image


class FakeModel:
    """Always answers with a fixed probability vector."""
    def __init__(self, probs):
        self.probs = np.array(probs, dtype=np.float32)

    def predict(self, x, verbose=0):
        assert x.shape == (1, 28, 28, 1)
        return self.probs.reshape(1, 10)


class BrokenModel:
    def predict(self, x, verbose=0):
        raise RuntimeError("boom")


def one_hot(digit, p=0.9):
    probs = np.full(10, (1 - p) / 9)
    probs[digit] = p
    return probs


class PredictorTests(unittest.TestCase):
    def test_predict_digit_result_fields(self):
        probs = one_hot(7)
        res = predictor.predict_digit(FakeModel(probs), make_digit_image("7"))
        self.assertEqual(res["digit"], 7)
        self.assertAlmostEqual(res["confidence"], 0.9, places=5)
        self.assertEqual(len(res["top"]), 3)
        self.assertEqual(res["top"][0][0], 7)
        self.assertGreater(res["margin"], 0.8)
        self.assertEqual(res["processed_image"].size, (28, 28))

    def test_margin_is_small_when_two_digits_compete(self):
        probs = np.full(10, 0.0125)
        probs[4], probs[9] = 0.45, 0.43
        res = predictor.predict_digit(FakeModel(probs), make_digit_image("4"))
        self.assertEqual(res["digit"], 4)
        self.assertEqual(res["top"][1][0], 9)
        self.assertLess(res["margin"], config.AMBIGUOUS_MARGIN)

    def test_top_predictions_order(self):
        top = predictor.top_predictions(np.array([0.1, 0.5, 0.2, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02]))
        self.assertEqual([d for d, _ in top], [1, 2, 0])

    def test_model_failure_is_wrapped(self):
        with self.assertRaises(predictor.PredictionError):
            predictor.predict_digit(BrokenModel(), make_digit_image("2"))

    def test_bad_image_propagates(self):
        with self.assertRaises(ImageProcessingError):
            predictor.predict_digit(FakeModel(one_hot(1)), Image.new("RGB", (100, 100), "white"))

    def test_missing_model_file(self):
        with self.assertRaises(predictor.ModelNotFoundError):
            predictor.load_trained_model("no_such_model.keras")

    def test_unreadable_model_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.keras"
            bad.write_bytes(b"not a model")
            with self.assertRaises((predictor.ModelLoadError, predictor.DependencyError)):
                predictor.load_trained_model(bad)


class BrokenTensorFlowTests(unittest.TestCase):
    def test_broken_tensorflow_import_gives_readable_error(self):
        """A TensorFlow that is installed but crashes on import must not produce a traceback."""
        import types
        from unittest import mock

        class Broken(types.ModuleType):
            def __getattr__(self, name):
                raise RuntimeError("DLL load failed: blocked by Application Control policy")

        with tempfile.TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "m.keras"
            model_file.write_bytes(b"x")
            with mock.patch.dict(sys.modules, {"tensorflow": Broken("tensorflow")}):
                with self.assertRaises(predictor.DependencyError) as ctx:
                    predictor.load_trained_model(model_file)
        self.assertIn("could not start", str(ctx.exception))


class SaveSampleTests(unittest.TestCase):
    def test_saved_drawing_is_found_by_evaluator(self):
        from utils.custom_samples import save_sample
        with tempfile.TemporaryDirectory() as tmp:
            path = save_sample(make_digit_image("6"), 6, folder=tmp)
            self.assertTrue(path.exists())
            self.assertEqual([(p.name, d) for p, d in evaluate_custom.collect_images(tmp)],
                             [(path.name, 6)])

    def test_rejects_bad_digit(self):
        from utils.custom_samples import save_sample
        with tempfile.TemporaryDirectory() as tmp:
            for bad in (10, -1, "3", True):
                with self.assertRaises(ValueError):
                    save_sample(make_digit_image("6"), bad, folder=tmp)


class CustomEvalTests(unittest.TestCase):
    def test_collect_images_both_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "3").mkdir()
            make_digit_image("3").save(tmp / "3" / "a.png")
            make_digit_image("5").save(tmp / "5_001.png")
            (tmp / "notes.txt").write_text("ignore me")
            make_digit_image("8").save(tmp / "unlabelled.png")      # no digit prefix -> ignored
            items = {(p.name, d) for p, d in evaluate_custom.collect_images(tmp)}
            self.assertEqual(items, {("a.png", 3), ("5_001.png", 5)})


@unittest.skipUnless((config.MODEL_PATH).exists(), "no trained model file")
class SavedModelSmokeTest(unittest.TestCase):
    """Runs only where TensorFlow is installed: the shipped model must read the sample images."""
    def test_mnist_samples(self):
        try:
            model = predictor.load_trained_model()
        except predictor.DependencyError:
            self.skipTest("TensorFlow not installed")
        wrong = []
        for d in range(10):
            img = Image.open(config.SAMPLES_DIR / f"mnist_digit_{d}.png")
            if predictor.predict_digit(model, img)["digit"] != d:
                wrong.append(d)
        self.assertLessEqual(len(wrong), 1, f"misread digits: {wrong}")


if __name__ == "__main__":
    unittest.main()
