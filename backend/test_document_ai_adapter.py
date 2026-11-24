import sys
from types import SimpleNamespace

import pytest

from document_ai_adapter import extract_document_with_docling


def test_docling_adapter_fails_with_actionable_message_when_not_installed(monkeypatch):
    # Simulate an environment without the optional dependency.
    for name in list(sys.modules):
        if name == "docling" or name.startswith("docling."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    import builtins
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "docling" or name.startswith("docling."):
            raise ImportError("optional dependency unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(RuntimeError, match="requirements-document-ai.txt"):
        extract_document_with_docling("record.pdf", b"%PDF-test")


def test_docling_adapter_rejects_empty_and_oversized_payloads():
    with pytest.raises(ValueError, match="empty"):
        extract_document_with_docling("record.pdf", b"")
    with pytest.raises(ValueError, match="10 MB"):
        extract_document_with_docling("record.pdf", b"x" * (10 * 1024 * 1024 + 1))
