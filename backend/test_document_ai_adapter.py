import builtins
import unittest
from unittest.mock import patch

from document_ai_adapter import extract_document_with_docling


class DoclingAdapterTests(unittest.TestCase):
    def test_missing_optional_dependency_has_actionable_error(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "docling" or name.startswith("docling."):
                raise ImportError("optional dependency unavailable")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "requirements-document-ai.txt"):
                extract_document_with_docling("record.pdf", b"%PDF-test")

    def test_empty_and_oversized_payloads_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            extract_document_with_docling("record.pdf", b"")
        with self.assertRaisesRegex(ValueError, "10 MB"):
            extract_document_with_docling("record.pdf", b"x" * (10 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
