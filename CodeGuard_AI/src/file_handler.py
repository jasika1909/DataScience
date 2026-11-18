"""Safe loading and validation of uploaded, pasted and sample source code.

Uploaded content is only ever decoded to text. It is never imported, compiled
or executed, and it is not sent anywhere.
"""
from __future__ import annotations

import codecs
import hashlib
import io
import os
import re
import zipfile
from pathlib import Path

import config
from src.code_normalizer import tokenize
from src.models import SourceFile


class FileValidationError(ValueError):
    """Raised with a user-friendly message when a file cannot be used."""


def detect_language(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return config.LANGUAGE_BY_EXTENSION.get(ext)


def sanitize_filename(name: str) -> str:
    """Reduce a user-supplied name to a safe display name (no paths)."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    name = re.sub(r"[^\w.\- +()\[\]]", "_", name)
    name = name.lstrip("=+-@. ")          # avoid CSV-formula / hidden-file names
    if len(name) > config.MAX_NAME_LENGTH:
        stem, ext = os.path.splitext(name)
        name = stem[: config.MAX_NAME_LENGTH - len(ext)] + ext
    return name or "unnamed"


def decode_bytes(data: bytes) -> tuple[str, str]:
    """Decode bytes to text. Returns (text, encoding_used)."""
    if data.startswith(codecs.BOM_UTF8):
        text, enc = data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    elif data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        text, enc = data.decode("utf-16", errors="replace"), "utf-16"
    else:
        if b"\x00" in data:
            raise FileValidationError(
                "This looks like a binary file, not source code."
            )
        try:
            text, enc = data.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            text, enc = data.decode("cp1252", errors="replace"), "cp1252"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text:
        bad = sum(1 for c in text if ord(c) < 32 and c not in "\n\t\f")
        if bad / len(text) > 0.02:
            raise FileValidationError(
                "This file contains too many control characters to be source code."
            )
    return text, enc


def count_lines(text: str) -> int:
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return len(parts)


def _build(name: str, language: str, text: str, size: int, origin: str) -> SourceFile:
    if not text.strip():
        raise FileValidationError(f"'{name}' is empty.")
    lines = count_lines(text)
    if lines > config.MAX_LINES_PER_FILE:
        raise FileValidationError(
            f"'{name}' has {lines:,} lines; the limit is "
            f"{config.MAX_LINES_PER_FILE:,} lines per file."
        )
    if not tokenize(text, language):
        raise FileValidationError(
            f"'{name}' contains only whitespace or comments, so there is "
            "nothing to compare."
        )
    return SourceFile(
        name=name,
        language=language,
        content=text,
        size_bytes=size,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        line_count=lines,
        origin=origin,
    )


def load_source_file(name: str, data: bytes, origin: str = "upload") -> SourceFile:
    """Validate raw bytes and return a SourceFile (raises FileValidationError)."""
    safe = sanitize_filename(name)
    ext = Path(safe).suffix.lower()
    language = config.LANGUAGE_BY_EXTENSION.get(ext)
    if language is None:
        supported = ", ".join(config.SUPPORTED_EXTENSIONS)
        raise FileValidationError(
            f"'{safe}' has an unsupported extension. Supported: {supported}."
        )
    if len(data) == 0:
        raise FileValidationError(f"'{safe}' is empty.")
    if len(data) > config.MAX_FILE_SIZE_BYTES:
        mb = config.MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise FileValidationError(
            f"'{safe}' is {len(data) / 1024:,.0f} KB; the limit is {mb:g} MB."
        )
    text, _ = decode_bytes(data)
    return _build(safe, language, text, len(data), origin)


def source_from_text(text: str, language: str, name: str | None = None,
                     origin: str = "paste") -> SourceFile:
    """Create a SourceFile from pasted code."""
    if language not in config.LANGUAGE_LABELS:
        raise FileValidationError(f"Unsupported language: {language}.")
    if text is None or not text.strip():
        raise FileValidationError("The pasted code is empty.")
    if len(text) > config.MAX_PASTE_CHARS:
        raise FileValidationError(
            f"Pasted code is too long (limit {config.MAX_PASTE_CHARS:,} characters)."
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in text:
        raise FileValidationError("Pasted text contains null characters.")
    ext = config.DEFAULT_EXTENSION[language]
    safe = sanitize_filename(name) if name else f"snippet{ext}"
    if not safe.lower().endswith(tuple(config.LANGUAGE_BY_EXTENSION)):
        safe += ext
    return _build(safe, language, text, len(text.encode("utf-8")), origin)


def load_from_path(path: Path, origin: str = "sample") -> SourceFile:
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FileValidationError(f"Cannot read '{path.name}': {exc.strerror}") from exc
    return load_source_file(path.name, data, origin)


def dedupe_names(files: list[SourceFile]) -> list[SourceFile]:
    """Give files with colliding names a numeric suffix, e.g. 'a (2).py'."""
    from dataclasses import replace

    seen: dict[str, int] = {}
    result = []
    for f in files:
        key = f.name.lower()
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count == 1:
            result.append(f)
        else:
            stem, ext = os.path.splitext(f.name)
            result.append(replace(f, name=f"{stem} ({count}){ext}"))
    return result


def load_zip(name: str, data: bytes):
    """Read supported source files from a ZIP archive (in memory only).

    Returns (sources, errors, skipped). Nothing is extracted to disk, paths are
    flattened into the file name (``student1/main.py`` -> ``student1__main.py``),
    and entry-count, size and compression-ratio limits guard against ZIP bombs.
    """
    safe = sanitize_filename(name)
    if len(data) > config.MAX_ZIP_TOTAL_BYTES:
        raise FileValidationError(f"'{safe}' is larger than the ZIP limit.")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise FileValidationError(f"'{safe}' is not a valid ZIP archive (it may be corrupted).")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = [i for i in zf.infolist() if not i.is_dir()]
    except (zipfile.BadZipFile, OSError, NotImplementedError) as exc:
        raise FileValidationError(f"'{safe}' could not be read as a ZIP archive: {exc}") from exc
    if len(infos) > config.MAX_ZIP_ENTRIES:
        raise FileValidationError(
            f"'{safe}' contains {len(infos)} files; the limit is {config.MAX_ZIP_ENTRIES}.")
    if sum(i.file_size for i in infos) > config.MAX_ZIP_TOTAL_BYTES:
        raise FileValidationError(f"'{safe}' expands to more than the allowed size.")
    sources, errors, skipped = [], [], 0
    for info in infos:
        parts = [p for p in info.filename.replace("\\", "/").split("/") if p]
        if (not parts or parts[0] == "__MACOSX" or any(p.startswith(".") for p in parts)
                or detect_language(parts[-1]) is None):
            skipped += 1
            continue
        if info.flag_bits & 0x1:
            errors.append(f"'{info.filename}' is password protected and was skipped.")
            continue
        if info.compress_size and info.file_size / info.compress_size > config.MAX_ZIP_RATIO:
            errors.append(f"'{info.filename}' has a suspicious compression ratio and was skipped.")
            continue
        label = "__".join(sanitize_filename(p) for p in parts)
        try:
            with zf.open(info) as handle:
                raw = handle.read(config.MAX_FILE_SIZE_BYTES + 1)
            sources.append(load_source_file(label, raw))
        except FileValidationError as exc:
            errors.append(str(exc))
        except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
            errors.append(f"'{info.filename}' is corrupted or unreadable: {exc}")
    return sources, errors, skipped
