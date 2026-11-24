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


    def test_docling_adapter_converts_in_memory_stream_and_preserves_markdown(self):
        import sys
        from types import ModuleType, SimpleNamespace

        base = ModuleType("docling.datamodel.base_models")
        base.InputFormat = SimpleNamespace(PDF="pdf")
        base.DocumentStream = lambda name, stream: SimpleNamespace(name=name, stream=stream)
        pipeline = ModuleType("docling.datamodel.pipeline_options")
        pipeline.PdfPipelineOptions = lambda **kwargs: SimpleNamespace(**kwargs)
        pipeline.TesseractCliOcrOptions = lambda **kwargs: SimpleNamespace(**kwargs)
        converter_module = ModuleType("docling.document_converter")

        class FakeConverter:
            def __init__(self, format_options):
                self.format_options = format_options

            def convert(self, source, **kwargs):
                self.source = source
                document = SimpleNamespace(
                    pages={1: object(), 2: object()},
                    export_to_markdown=lambda: "# Kết quả\\n| Hb | 13 |",
                )
                return SimpleNamespace(
                    document=document,
                    status=SimpleNamespace(value="success"),
                    errors=[],
                )

        converter_module.DocumentConverter = FakeConverter
        converter_module.PdfFormatOption = lambda **kwargs: kwargs
        modules = {
            "docling": ModuleType("docling"),
            "docling.datamodel": ModuleType("docling.datamodel"),
            "docling.datamodel.base_models": base,
            "docling.datamodel.pipeline_options": pipeline,
            "docling.document_converter": converter_module,
        }
        with patch.dict(sys.modules, modules):
            result = extract_document_with_docling("record.pdf", b"%PDF-test")

        self.assertIn("| Hb | 13 |", result.text)
        self.assertEqual(result.page_count, 2)
        self.assertEqual(result.status, "success")

    def test_healthcare_document_pipeline_uses_docling_only_when_enabled(self):
        import sys
        from types import SimpleNamespace
        import healthcare_documents

        parsed = SimpleNamespace(text="# Hồ sơ\\n| Hb | 13 |", page_count=1, warnings=())
        with patch.dict("os.environ", {"YTEMO_DOCUMENT_ENGINE": "docling"}):
            with patch.dict(sys.modules, {
                "document_ai_adapter": SimpleNamespace(
                    extract_document_with_docling=lambda filename, data: parsed
                )
            }):
                result = healthcare_documents.extract_medical_document(
                    "record.pdf", b"%PDF-test"
                )

        self.assertEqual(result.extraction_status, "docling_extracted")
        self.assertIn("| Hb | 13 |", result.text)
        self.assertFalse(result.persisted)

    def test_empty_and_oversized_payloads_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            extract_document_with_docling("record.pdf", b"")
        with self.assertRaisesRegex(ValueError, "10 MB"):
            extract_document_with_docling("record.pdf", b"x" * (10 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
