import io
from pathlib import Path

import numpy as np
from scipy import ndimage
from PIL import Image, ImageOps, UnidentifiedImageError


class ImageProcessingError(Exception):
    """Raised when an image cannot be read or does not contain a digit."""


# MNIST pen strokes are about 2-3 pixels thick once the digit is 20 px tall.
TARGET_STROKE = 2.6      # desired stroke thickness (pixels at 28x28 scale)
MAX_STROKE = 3.0         # thicker than this  -> thin the strokes
MIN_STROKE = 2.0         # thinner than this  -> thicken the strokes


def _disk(radius):
    """Circular structuring element with the given integer radius."""
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    return x * x + y * y <= radius * radius


def estimate_stroke_width(digit):
    """
    Average pen thickness (in pixels) of a cropped digit image (0-255 array).
    For a stroke of width w the distance from an ink pixel to the nearest
    background pixel averages about w / 4, so  w ~ 4 * mean(distance).
    """
    mask = digit > 90
    if not mask.any():
        return 1.0
    dist = ndimage.distance_transform_edt(mask)
    return max(1.0, 4.0 * float(np.mean(dist[mask] - 0.5)))


def normalise_stroke_width(digit, scale):
    """
    Make the pen thickness match MNIST after the digit is scaled by `scale`.
    A thick brush on a small drawing would turn into a blob (and a thin pen line
    would vanish), so we erode or dilate the digit BEFORE resizing it.
    """
    width_after = estimate_stroke_width(digit) * scale
    if MIN_STROKE <= width_after <= MAX_STROKE:
        return digit
    radius = int(round(abs(TARGET_STROKE - width_after) / (2.0 * scale)))
    if radius < 1:
        return digit
    footprint = _disk(radius)
    if width_after > MAX_STROKE:
        return ndimage.grey_erosion(digit, footprint=footprint)
    return ndimage.grey_dilation(digit, footprint=footprint)


def load_image(source):
    """
    Open an image from a Streamlit upload, a file object, or a file path.
    Raises ImageProcessingError with a friendly message if anything is wrong.
    """
    try:
        if hasattr(source, "getvalue"):            # Streamlit UploadedFile / BytesIO
            data = source.getvalue()
        elif hasattr(source, "read"):              # any other file object
            data = source.read()
        elif isinstance(source, (str, Path)):      # file path
            with open(source, "rb") as f:
                data = f.read()
        else:
            raise ImageProcessingError("Unsupported input type for image.")
    except OSError as exc:
        raise ImageProcessingError(f"Could not read the file: {exc}") from exc

    if not data:
        raise ImageProcessingError("The uploaded file is empty.")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()                                # force full decode
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ImageProcessingError(
            "This file is not a valid image. Please upload a PNG, JPG or JPEG file."
        )

    try:
        image = ImageOps.exif_transpose(image)      # fix rotated phone photos
    except Exception:
        pass
    return image


def to_grayscale(image):
    """Convert RGB / RGBA / palette / 16-bit / grayscale images to 8-bit gray."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(white, rgba).convert("L")   # transparent -> white
    if image.mode in ("I;16", "I", "F"):
        arr = np.array(image, dtype=np.float32)
        span = arr.max() - arr.min()
        if span == 0:
            return Image.fromarray(np.zeros(arr.shape, dtype=np.uint8))
        return Image.fromarray(((arr - arr.min()) / span * 255).astype(np.uint8))
    return image.convert("L")


def preprocess_image(image):
    """
    Full preprocessing pipeline.

    Returns
    -------
    model_input : np.ndarray, shape (1, 28, 28, 1), float32, range 0-1
    processed   : PIL.Image (28 x 28, mode 'L') - what the CNN actually sees
    """
    gray = to_grayscale(image)
    if min(gray.size) < 8:
        raise ImageProcessingError("The image is too small. Use at least 8 x 8 pixels.")

    arr = np.array(gray, dtype=np.float32)

    # 1. Stretch contrast to the full 0-255 range
    low, high = arr.min(), arr.max()
    if high - low < 25:
        raise ImageProcessingError(
            "The image has almost no contrast - no digit could be found."
        )
    arr = (arr - low) / (high - low) * 255.0

    # 2. MNIST is white-on-black. If the border (background) is bright, invert.
    border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    if np.median(border) > 127:
        arr = 255.0 - arr

    # 3. Remove faint noise / paper texture
    arr[arr < 40] = 0

    # 4. Crop tightly around the digit
    rows, cols = np.where(arr > 90)
    if len(rows) == 0:
        raise ImageProcessingError("No digit was found in the image.")
    digit = arr[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    h, w = digit.shape
    scale = 20.0 / max(w, h)

    # 5. Match MNIST pen thickness, then resize so the longest side is 20 px
    digit = normalise_stroke_width(digit, scale)
    digit_img = Image.fromarray(np.clip(digit, 0, 255).astype(np.uint8))
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    digit_img = digit_img.resize((new_w, new_h), Image.LANCZOS)

    # 6. Paste in the middle of a black 28 x 28 canvas
    canvas = np.zeros((28, 28), dtype=np.float32)
    top, left = (28 - new_h) // 2, (28 - new_w) // 2
    canvas[top:top + new_h, left:left + new_w] = np.array(digit_img, dtype=np.float32)

    # 7. Shift so the centre of mass is at the image centre (as MNIST was made)
    total = canvas.sum()
    if total > 0:
        ys, xs = np.indices(canvas.shape)
        cy, cx = (ys * canvas).sum() / total, (xs * canvas).sum() / total
        shift_y = int(np.clip(round(13.5 - cy), -4, 4))
        shift_x = int(np.clip(round(13.5 - cx), -4, 4))
        canvas = np.roll(canvas, (shift_y, shift_x), axis=(0, 1))

    processed = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))

    # 8. Normalise to 0-1 and reshape for the CNN
    model_input = (np.array(processed, dtype=np.float32) / 255.0).reshape(1, 28, 28, 1)
    return model_input, processed