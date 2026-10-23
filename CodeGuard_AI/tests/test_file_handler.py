"""Tests for upload validation and decoding."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src import file_handler as fh
from src.file_handler import FileValidationError


class FileHandlerTests(unittest.TestCase):
    def test_valid_python_file(self):
        f = fh.load_source_file("a.py", b"x = 1\nprint(x)\n")
        self.assertEqual(f.language, "python")
        self.assertEqual(f.line_count, 2)
        self.assertEqual(f.origin, "upload")

    def test_all_supported_extensions(self):
        for ext, lang in config.LANGUAGE_BY_EXTENSION.items():
            f = fh.load_source_file("file" + ext, b"int x = 1;\n" if lang != "python" else b"x = 1\n")
            self.assertEqual(f.language, lang)

    def test_unsupported_extension(self):
        with self.assertRaises(FileValidationError):
            fh.load_source_file("notes.txt", b"hello")
        with self.assertRaises(FileValidationError):
            fh.load_source_file("noextension", b"hello")

    def test_empty_file_and_whitespace_only(self):
        with self.assertRaises(FileValidationError):
            fh.load_source_file("a.py", b"")
        with self.assertRaises(FileValidationError):
            fh.load_source_file("a.py", b"   \n\n\t\n")

    def test_comment_only_file_rejected(self):
        with self.assertRaises(FileValidationError):
            fh.load_source_file("a.py", b"# nothing here\n# at all\n")
        with self.assertRaises(FileValidationError):
            fh.load_source_file("A.java", b"/* only a comment */\n// another\n")

    def test_binary_rejected(self):
        with self.assertRaises(FileValidationError):
            fh.load_source_file("a.py", b"\x00\x01\x02\x03binary")
        with self.assertRaises(FileValidationError):
            fh.load_source_file("a.c", bytes(range(1, 31)) * 20)

    def test_too_large(self):
        data = b"x = 1\n" * (config.MAX_FILE_SIZE_BYTES // 6 + 10)
        with self.assertRaises(FileValidationError):
            fh.load_source_file("big.py", data)

    def test_too_many_lines(self):
        data = b"x=1\n" * (config.MAX_LINES_PER_FILE + 1)
        with self.assertRaises(FileValidationError) as ctx:
            fh.load_source_file("long.py", data)
        self.assertIn("lines", str(ctx.exception))

    def test_encodings(self):
        utf8 = fh.load_source_file("a.py", "s = 'héllo'\n".encode("utf-8"))
        self.assertIn("héllo", utf8.content)
        bom = fh.load_source_file("a.py", b"\xef\xbb\xbfx = 1\n")
        self.assertEqual(bom.content, "x = 1\n")
        cp = fh.load_source_file("a.py", "s = 'café'\n".encode("cp1252"))
        self.assertIn("café", cp.content)
        u16 = fh.load_source_file("a.py", "x = 1\n".encode("utf-16"))
        self.assertEqual(u16.content.strip(), "x = 1")

    def test_line_endings_normalized(self):
        f = fh.load_source_file("a.py", b"x = 1\r\ny = 2\r\n")
        self.assertNotIn("\r", f.content)
        self.assertEqual(f.line_count, 2)

    def test_filename_sanitized(self):
        self.assertEqual(fh.sanitize_filename("../../evil.py"), "evil.py")
        self.assertEqual(fh.sanitize_filename("C:\\dir\\prog.java"), "prog.java")
        self.assertFalse(fh.sanitize_filename("=cmd().py").startswith("="))
        self.assertFalse(fh.sanitize_filename("-rf.py").startswith("-"))
        self.assertEqual(fh.sanitize_filename(""), "unnamed")
        self.assertLessEqual(len(fh.sanitize_filename("a" * 500 + ".py")), config.MAX_NAME_LENGTH)

    def test_pasted_code(self):
        f = fh.source_from_text("print(1)\nprint(2)\n", "python")
        self.assertEqual(f.origin, "paste")
        self.assertTrue(f.name.endswith(".py"))
        with self.assertRaises(FileValidationError):
            fh.source_from_text("   ", "python")
        with self.assertRaises(FileValidationError):
            fh.source_from_text("x", "cobol")
        with self.assertRaises(FileValidationError):
            fh.source_from_text("x" * (config.MAX_PASTE_CHARS + 1), "python")

    def test_uploaded_code_is_never_executed(self):
        marker = Path(config.BASE_DIR) / "data" / "SHOULD_NOT_EXIST"
        payload = ("import os\nopen(%r, 'w').write('x')\n" % str(marker)).encode()
        fh.load_source_file("evil.py", payload)
        self.assertFalse(marker.exists())

    def test_dedupe_names(self):
        a = fh.source_from_text("x = 1\n", "python", "same.py")
        b = fh.source_from_text("y = 2\n", "python", "same.py")
        names = [f.name for f in fh.dedupe_names([a, b])]
        self.assertEqual(names, ["same.py", "same (2).py"])

    def test_samples_all_load(self):
        for p in config.SAMPLES_DIR.iterdir():
            fh.load_from_path(p)

    def test_missing_path(self):
        with self.assertRaises(FileValidationError):
            fh.load_from_path(Path("does/not/exist.py"))


if __name__ == "__main__":
    unittest.main()
