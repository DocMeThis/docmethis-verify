# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for the Verify candidate distribution boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from docmethis_extract_python.static_extraction.models import ClassRecord, FunctionRecord, ModuleRecord

import docmethis_verify
from docmethis_verify.docstring.models import GeneratedDocstring
from docmethis_verify.models.contracts import VerificationRequest
from docmethis_verify.verification.format_validator import section_canonical_probable, validate_docstring_format
from docmethis_verify.verification.raises_verification import verify_raises_ghosts, verify_raises_missing
from docmethis_verify.verification.structural import (
    check_missing_parameters,
    verify_order_parameters,
    verify_parameters_ghosts,
)
from docmethis_verify.verification.types_verification import verify_type_return_missing, verify_types_parameters_missing
from docmethis_verify.verification.verifier import verify
from docmethis_verify.verification.vocabulary_verification import verify_vocabulary_forbidden

PACKAGE_ROOT = Path(docmethis_verify.__file__).resolve().parent
EXPECTED_ROOT_EXPORTS = {
    "FormatWarning",
    "FormatWarningSpan",
    "VerificationRequest",
    "VerificationResponse",
    "PatchGranularity",
    "VerificationError",
    "VerificationErrorType",
    "ReturnAnnotationKind",
    "classify_return_annotation",
}


def test_root_exports_are_frozen() -> None:
    """The candidate exposes only the documented Verify root exports."""
    assert set(docmethis_verify.__all__) == EXPECTED_ROOT_EXPORTS
    assert all(hasattr(docmethis_verify, name) for name in EXPECTED_ROOT_EXPORTS)


def test_supported_verifiers_are_available() -> None:
    """The Verify functions listed in the R2 manifest remain importable."""
    assert all(
        callable(function)
        for function in (
            check_missing_parameters,
            verify_order_parameters,
            verify_parameters_ghosts,
            verify_type_return_missing,
            verify_types_parameters_missing,
            verify_raises_ghosts,
            verify_raises_missing,
            verify_vocabulary_forbidden,
            section_canonical_probable,
            validate_docstring_format,
            verify,
        )
    )


def test_return_annotation_classifier_is_available() -> None:
    """The shared return annotation classifier is available to downstream tools."""
    assert docmethis_verify.classify_return_annotation("typing.NoReturn") is docmethis_verify.ReturnAnnotationKind.UNKNOWN


def test_extract_models_are_used_by_request_contract() -> None:
    """Verify requests use the installed Extract model classes, not copies."""
    assert FunctionRecord.__module__.startswith("docmethis_extract_python.")
    assert ClassRecord.__module__.startswith("docmethis_extract_python.")
    assert VerificationRequest.__annotations__["generated_docstring"] is GeneratedDocstring


def test_request_accepts_optional_extract_module_context() -> None:
    """Callers can supply M1 import facts without changing existing request construction."""
    module = ModuleRecord(file_path=PACKAGE_ROOT / "example.py", module_name="example")
    generated = GeneratedDocstring(summary="Example.")
    assert VerificationRequest(function_record=module, generated_docstring=generated).module_record is None
    request = VerificationRequest(function_record=module, generated_docstring=generated, module_record=module)
    assert request.module_record is module


def test_source_has_no_private_or_historical_imports() -> None:
    """The candidate source does not import the monorepo or private namespaces."""
    forbidden_prefixes = ("docmethis.", "docmethis_gateway", "gateway")

    for source_path in PACKAGE_ROOT.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported_names = [node.module or ""]
            else:
                continue

            assert not any(name.startswith(forbidden_prefixes) for name in imported_names), source_path
