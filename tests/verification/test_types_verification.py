# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for type verifiers."""

from pathlib import Path

import pytest
from docmethis_extract_python.api import NormalReturnStatus, extract_module_record
from docmethis_extract_python.static_extraction.models import (
    Confidence,
    FunctionRecord,
    MethodType,
    Provenance,
    ResolvedTypes,
    TypeInfo,
    Visibility,
)

from docmethis_verify.docstring.models import (
    DocstringParameter,
    DocstringReturn,
    GeneratedDocstring,
)
from docmethis_verify.models.contracts import VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.verification.types_verification import (
    verify_type_return_missing,
    verify_types_parameters_missing,
)
from docmethis_verify.verification.verifier import verify

_PATH = Path("tests/mock/example.py")


def _type_info(type_str: str, confidence: Confidence) -> TypeInfo:
    return TypeInfo(type_str=type_str, confidence=confidence, provenance=Provenance.ANNOTATION)


def _function_record(
    types_dict: dict[str, tuple[str, Confidence]] | None,
    return_type: TypeInfo | None = None,
) -> FunctionRecord:
    types: ResolvedTypes | None = None
    if types_dict is not None:
        parameter_types = {name: _type_info(type_str, confidence) for name, (type_str, confidence) in types_dict.items()}
        types = ResolvedTypes(parameters=parameter_types, return_type=return_type)
    elif return_type is not None:
        types = ResolvedTypes(parameters={}, return_type=return_type)

    return FunctionRecord(
        qualified_name="module.function",
        file_path=_PATH,
        line_start=1,
        line_end=5,
        col_start=0,
        col_end=0,
        method_kind=MethodType.FUNCTION,
        is_async=False,
        visibility=Visibility.PUBLIC,
        parent_class=None,
        parent_module="module",
        existing_docstring=None,
        signature_confidence=Confidence.ABSENT,
        signature=None,
        types=types,
    )


def _generated_docstring(params: list[tuple[str, str | None]]) -> GeneratedDocstring:
    parameters = tuple(
        DocstringParameter(name=name, description=f"Description of {name}", annotation=annotation) for name, annotation in params
    )
    return GeneratedDocstring(summary="Summary", parameters=parameters, returns=None)


def _generated_docstring_with_returns(return_annotation: str | None) -> GeneratedDocstring:
    returns = DocstringReturn(description="Return value.", annotation=return_annotation)
    return GeneratedDocstring(summary="Summary", parameters=(), returns=returns)


def _request(
    types_dict: dict[str, tuple[str, Confidence]] | None,
    params: list[tuple[str, str | None]],
) -> VerificationRequest:
    return VerificationRequest(
        function_record=_function_record(types_dict),
        generated_docstring=_generated_docstring(params),
    )


# ---------------------------------------------------------------------------
# verify_types_parameters_missing
# ---------------------------------------------------------------------------


class TestVerifyTypesParametersMissing:
    """Unit tests for verify_types_parameters_missing()."""

    def test_explicit_type_is_not_documented(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.EXPLICIT)}, [("x", None)]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_TYPE_MISSING
        assert "x" in errors[0].detail
        assert "int" in errors[0].detail

    def test_explicit_type_is_documented(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.EXPLICIT)}, [("x", "int")]))
        assert errors == []

    def test_confidence_inferred_high_ignore(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.INFERRED_HIGH)}, [("x", None)]))
        assert errors == []

    def test_confidence_inferred_low_ignore(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.INFERRED_LOW)}, [("x", None)]))
        assert errors == []

    def test_confidence_absent_ignore(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.ABSENT)}, [("x", None)]))
        assert errors == []

    def test_parameter_absent_from_m1_dict(self):
        errors = verify_types_parameters_missing(_request({}, [("x", None)]))
        assert errors == []

    def test_none_types_returns_empty_list(self):
        errors = verify_types_parameters_missing(_request(None, [("x", None)]))
        assert errors == []

    def test_multiple_parameters_have_missing_types(self):
        errors = verify_types_parameters_missing(
            _request(
                {"x": ("int", Confidence.EXPLICIT), "y": ("str", Confidence.EXPLICIT)},
                [("x", None), ("y", None)],
            )
        )
        assert len(errors) == 2
        assert all(error.error_type is VerificationErrorType.PARAMETER_TYPE_MISSING for error in errors)

    def test_explicit_and_inferred_types_are_mixed(self):
        errors = verify_types_parameters_missing(
            _request(
                {"x": ("int", Confidence.EXPLICIT), "y": ("str", Confidence.INFERRED_HIGH)},
                [("x", None), ("y", None)],
            )
        )
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_TYPE_MISSING
        assert "x" in errors[0].detail


class TestVerifyTypeReturnMissing:
    """Unit tests for verify_type_return_missing()."""

    def test_explicit_return_type_is_not_documented(self):
        return_type = _type_info("int", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        errors = verify_type_return_missing(request)
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.RETURNS_TYPE_MISSING
        assert "int" in errors[0].detail

    def test_explicit_return_type_is_documented(self):
        return_type = _type_info("int", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns("int"),
        )
        errors = verify_type_return_missing(request)
        assert errors == []

    def test_confidence_inferred_ignore(self):
        return_type = _type_info("int", Confidence.INFERRED_HIGH)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        errors = verify_type_return_missing(request)
        assert errors == []

    def test_m1_return_is_none(self):
        request = VerificationRequest(
            function_record=_function_record({}, return_type=None),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        errors = verify_type_return_missing(request)
        assert errors == []

    def test_types_none(self):
        request = VerificationRequest(
            function_record=_function_record(None),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        errors = verify_type_return_missing(request)
        assert errors == []

    def test_returns_absent_not_required(self):
        return_type = _type_info("int", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring([]),
        )
        errors = verify_type_return_missing(request)
        assert errors == []


# ---------------------------------------------------------------------------
# verify orchestrator
# ---------------------------------------------------------------------------


class TestVerifyTypesIntegration:
    """Integration tests through the orchestrator."""

    def test_missing_parameter_type_is_detected(self):
        response = verify(_request({"x": ("int", Confidence.EXPLICIT)}, [("x", None)]))
        assert not response.is_valid
        assert VerificationErrorType.PARAMETER_TYPE_MISSING in {error.error_type for error in response.errors}

    def test_missing_return_type_is_detected(self):
        return_type = _type_info("int", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        response = verify(request)
        assert not response.is_valid
        assert VerificationErrorType.RETURNS_TYPE_MISSING in {error.error_type for error in response.errors}

    def test_valid_case_has_no_errors(self):
        return_type = _type_info("int", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({"x": ("str", Confidence.EXPLICIT)}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns("int"),
        )
        response = verify(request)
        assert response.is_valid


# ---------------------------------------------------------------------------
# Enriched fields (iteration 3.7)
# ---------------------------------------------------------------------------


class TestVerifyTypesEnrichedFields:
    """Verify that parameter_name, observed, and expected are populated."""

    def test_parameter_type_missing_enriched_fields(self):
        errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.EXPLICIT)}, [("x", None)]))
        assert len(errors) == 1
        error = errors[0]
        assert error.parameter_name == "x"
        assert error.expected == "int"
        assert error.observed is None

    def test_returns_type_missing_enriched_fields(self):
        return_type = _type_info("str", Confidence.EXPLICIT)
        request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        errors = verify_type_return_missing(request)
        assert len(errors) == 1
        error = errors[0]
        assert error.expected == "str"
        assert error.observed is None
        assert error.parameter_name is None


class TestTypeGranularitiesPreserved:
    """Verify that iteration 3.9 preserves existing type diagnostics."""

    def test_type_diagnostics_remain_spans(self):
        parameter_errors = verify_types_parameters_missing(_request({"x": ("int", Confidence.EXPLICIT)}, [("x", None)]))
        return_type = _type_info("str", Confidence.EXPLICIT)
        return_request = VerificationRequest(
            function_record=_function_record({}, return_type=return_type),
            generated_docstring=_generated_docstring_with_returns(None),
        )
        return_errors = verify_type_return_missing(return_request)

        assert [(error.error_type, error.granularity, error.dmt_code) for error in parameter_errors + return_errors] == [
            (VerificationErrorType.PARAMETER_TYPE_MISSING, PatchGranularity.SPAN, "DMT-2120"),
            (VerificationErrorType.RETURNS_TYPE_MISSING, PatchGranularity.SPAN, "DMT-3010"),
        ]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (NormalReturnStatus.PROVEN_ABSENT, False),
        (NormalReturnStatus.POSSIBLE, True),
        (NormalReturnStatus.UNKNOWN, True),
    ],
)
def test_dmt3010_applicability_uses_the_normal_return_fact(status: NormalReturnStatus, expected: bool) -> None:
    """Verify itself suppresses the type request only for a proven absence."""
    function = _function_record({}, return_type=_type_info("int", Confidence.EXPLICIT))
    function.normal_return_status = status
    request = VerificationRequest(function_record=function, generated_docstring=_generated_docstring_with_returns(None))
    assert bool(verify_type_return_missing(request)) is expected
    assert ("DMT-3010" in {error.dmt_code for error in verify(request).errors}) is expected


@pytest.mark.parametrize(
    ("imports", "annotation", "include_module", "expected"),
    [
        ("", "None", False, False),
        ("from types import NoneType as Nil", "Nil", True, False),
        ("from typing import NoReturn as Exit", "Exit", True, False),
        ("import typing_extensions as te", "te.Never", True, False),
        ("from typing import NoReturn as Exit", "Exit", False, True),
        ("from application import NoReturn as Exit", "Exit", True, True),
        ("from typing import NoReturn as Exit\nfrom application import Exit", "Exit", True, True),
        ("", "int | None", True, True),
    ],
    ids=["none", "none-alias", "no-return-alias", "qualified-never", "missing-context", "unknown-alias", "conflict", "nullable"],
)
def test_dmt3010_resolves_no_value_annotations_without_guessing_aliases(
    tmp_path: Path,
    imports: str,
    annotation: str,
    include_module: bool,
    expected: bool,
) -> None:
    """Import context controls resolution, not a consumer-specific diagnostic filter."""
    path = tmp_path / "module.py"
    path.write_text(f"{imports}\n\ndef f() -> {annotation}:\n    pass\n", encoding="utf-8")
    module = extract_module_record(path, "module", is_stub=False, is_test=False, file_hash="test")
    assert module is not None
    request = VerificationRequest(
        function_record=module.functions[0],
        generated_docstring=_generated_docstring_with_returns(None),
        module_record=module if include_module else None,
    )
    assert bool(verify_type_return_missing(request)) is expected
    assert ("DMT-3010" in {error.dmt_code for error in verify(request).errors}) is expected
