# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for structural verifiers."""

from pathlib import Path

import pytest
from docmethis_extract_python.static_extraction.models import (
    MISSING_VALUE,
    Confidence,
    FunctionRecord,
    MethodType,
    Parameter,
    ParameterType,
    Signature,
    Visibility,
)

from docmethis_verify.docstring.models import (
    DocstringParameter,
    GeneratedDocstring,
)
from docmethis_verify.models.contracts import VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.verification.structural import (
    check_missing_parameters,
    verify_order_parameters,
    verify_parameters_ghosts,
)
from docmethis_verify.verification.verifier import verify

_PATH = Path("tests/mock/example.py")


def _parameter(name: str) -> Parameter:
    return Parameter(
        name=name,
        annotation_raw=MISSING_VALUE,
        default_value=MISSING_VALUE,
        kind=ParameterType.POSITIONAL_OR_KEYWORD,
    )


def _signature(names: list[str]) -> Signature:
    return Signature(
        parameters=[_parameter(name) for name in names],
        return_annotation=MISSING_VALUE,
        decorators=[],
    )


def _function_record(
    m1_names: list[str] | None = None,
    *,
    method_kind: MethodType = MethodType.FUNCTION,
) -> FunctionRecord:
    sig = _signature(m1_names) if m1_names is not None else None
    return FunctionRecord(
        qualified_name="module.function",
        file_path=_PATH,
        line_start=1,
        line_end=5,
        col_start=0,
        col_end=0,
        method_kind=method_kind,
        is_async=False,
        visibility=Visibility.PUBLIC,
        parent_class="Class" if method_kind is not MethodType.FUNCTION else None,
        parent_module="module",
        existing_docstring=None,
        signature_confidence=Confidence.EXPLICIT if m1_names is not None else Confidence.ABSENT,
        signature=sig,
    )


def _generated_docstring(m2_names: list[str]) -> GeneratedDocstring:
    parameters = tuple(DocstringParameter(name=name, description=f"Description of {name}") for name in m2_names)
    return GeneratedDocstring(summary="Summary", parameters=parameters, returns=None)


def _request(
    m1_names: list[str] | None,
    m2_names: list[str],
    *,
    method_kind: MethodType = MethodType.FUNCTION,
) -> VerificationRequest:
    return VerificationRequest(
        function_record=_function_record(m1_names, method_kind=method_kind),
        generated_docstring=_generated_docstring(m2_names),
    )


# ---------------------------------------------------------------------------
# check_missing_parameters
# ---------------------------------------------------------------------------


class TestCheckMissingParameters:
    """Unit tests for check_missing_parameters()."""

    def test_single_missing_parameter(self):
        errors = check_missing_parameters(_request(["x"], []))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_MISSING
        assert "x" in errors[0].detail

    def test_multiple_missing_parameters(self):
        errors = check_missing_parameters(_request(["x", "y", "z"], ["z"]))
        details = {error.detail for error in errors}
        assert len(errors) == 2
        assert all(error.error_type is VerificationErrorType.PARAMETER_MISSING for error in errors)
        assert any("x" in detail for detail in details)
        assert any("y" in detail for detail in details)

    def test_duplicate_m1_occurrences_are_deduplicated(self):
        errors = check_missing_parameters(_request(["x", "x"], []))

        assert [(error.parameter_name, error.expected) for error in errors] == [("x", "x")]

    @pytest.mark.parametrize(
        ("method_kind", "receiver"),
        [
            (MethodType.INSTANCE_METHOD, "self"),
            (MethodType.PROPERTY, "self"),
            (MethodType.CLASS_METHOD, "cls"),
        ],
    )
    def test_canonical_implicit_receiver_is_excluded(self, method_kind: MethodType, receiver: str):
        errors = check_missing_parameters(_request([receiver, "x"], ["x"], method_kind=method_kind))
        assert errors == []

    @pytest.mark.parametrize(
        ("method_kind", "receiver"),
        [
            (MethodType.FUNCTION, "self"),
            (MethodType.FUNCTION, "cls"),
            (MethodType.STATIC_METHOD, "self"),
            (MethodType.STATIC_METHOD, "cls"),
            (MethodType.CLASS_METHOD, "self"),
            (MethodType.INSTANCE_METHOD, "cls"),
        ],
    )
    def test_non_implicit_receiver_name_remains_documentable(self, method_kind: MethodType, receiver: str):
        errors = check_missing_parameters(_request([receiver, "x"], ["x"], method_kind=method_kind))

        assert [(error.parameter_name, error.dmt_code) for error in errors] == [(receiver, "DMT-2001")]

    def test_none_signature_returns_empty_list(self):
        errors = check_missing_parameters(_request(None, []))
        assert errors == []

    def test_valid_case_has_no_errors(self):
        errors = check_missing_parameters(_request(["a", "b"], ["a", "b"]))
        assert errors == []


# ---------------------------------------------------------------------------
# verify_parameters_ghosts
# ---------------------------------------------------------------------------


class TestVerifyParametersGhosts:
    """Unit tests for verify_parameters_ghosts()."""

    def test_single_ghost(self):
        errors = verify_parameters_ghosts(_request([], ["ghost"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_GHOST
        assert "ghost" in errors[0].detail

    def test_multiple_ghosts(self):
        errors = verify_parameters_ghosts(_request(["x"], ["x", "g1", "g2"]))
        details = {error.detail for error in errors}
        assert len(errors) == 2
        assert all(error.error_type is VerificationErrorType.PARAMETER_GHOST for error in errors)
        assert any("g1" in detail for detail in details)
        assert any("g2" in detail for detail in details)

    def test_duplicate_documented_entries_are_deduplicated(self):
        errors = verify_parameters_ghosts(_request([], ["ghost", "ghost"]))

        assert [(error.parameter_name, error.observed) for error in errors] == [("ghost", "ghost")]

    def test_mix_missing_and_ghost(self):
        # M1 has "a", M2 has "b": a is missing elsewhere, b is a ghost.
        errors = verify_parameters_ghosts(_request(["a"], ["b"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_GHOST
        assert "b" in errors[0].detail

    def test_none_signature_returns_empty_list(self):
        errors = verify_parameters_ghosts(_request(None, ["ghost"]))
        assert errors == []

    def test_valid_case_has_no_errors(self):
        errors = verify_parameters_ghosts(_request(["a", "b"], ["a", "b"]))
        assert errors == []


# ---------------------------------------------------------------------------
# Entry granularity (iteration 3.9, phase 1)
# ---------------------------------------------------------------------------


class TestEntryGranularityParameters:
    """Verify individual targeting of Parameters diagnostics."""

    def test_missing_parameters_are_distinct_entries(self):
        errors = check_missing_parameters(_request(["x", "y"], []))

        assert [
            (error.granularity, error.parameter_name, error.expected, error.observed, error.dmt_code) for error in errors
        ] == [
            (PatchGranularity.ENTRY, "x", "x", None, "DMT-2001"),
            (PatchGranularity.ENTRY, "y", "y", None, "DMT-2001"),
        ]

    def test_ghost_parameters_are_distinct_entries(self):
        errors = verify_parameters_ghosts(_request([], ["x", "y"]))

        assert [
            (error.granularity, error.parameter_name, error.expected, error.observed, error.dmt_code) for error in errors
        ] == [
            (PatchGranularity.ENTRY, "x", None, "x", "DMT-2002"),
            (PatchGranularity.ENTRY, "y", None, "y", "DMT-2002"),
        ]

    def test_parameter_order_remains_a_section(self):
        errors = verify_order_parameters(_request(["x", "y"], ["y", "x"]))

        assert len(errors) == 1
        assert errors[0].granularity is PatchGranularity.SECTION

    def test_verify_preserves_parameter_targeting(self):
        response = verify(_request(["x", "y"], ["y", "ghost"]))
        granularities = {error.error_type: error.granularity for error in response.errors}

        assert granularities == {
            VerificationErrorType.PARAMETER_MISSING: PatchGranularity.ENTRY,
            VerificationErrorType.PARAMETER_GHOST: PatchGranularity.ENTRY,
        }


# ---------------------------------------------------------------------------
# verify_order_parameters
# ---------------------------------------------------------------------------


class TestVerifyOrderParameters:
    """Unit tests for verify_order_parameters()."""

    def test_order_inverted_two_parameters(self):
        errors = verify_order_parameters(_request(["a", "b"], ["b", "a"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_ORDER_WRONG

    def test_order_inverted_three_parameters(self):
        errors = verify_order_parameters(_request(["a", "b", "c"], ["c", "b", "a"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_ORDER_WRONG

    def test_correct_order_has_no_errors(self):
        errors = verify_order_parameters(_request(["a", "b", "c"], ["a", "b", "c"]))
        assert errors == []

    def test_one_common_parameter_has_no_order_error(self):
        # One common item is insufficient to verify order.
        errors = verify_order_parameters(_request(["a", "b"], ["a", "ghost"]))
        assert errors == []

    def test_order_uses_intersection_with_missing_and_ghosts(self):
        # M1: [a, b, c], M2: [c, ghost, a] -> common names are ordered [a, c] and [c, a].
        errors = verify_order_parameters(_request(["a", "b", "c"], ["c", "ghost", "a"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.PARAMETER_ORDER_WRONG

    def test_none_signature_returns_empty_list(self):
        errors = verify_order_parameters(_request(None, ["a", "b"]))
        assert errors == []

    def test_no_common_parameters_has_no_order_error(self):
        errors = verify_order_parameters(_request(["a"], ["b"]))
        assert errors == []


# ---------------------------------------------------------------------------
# verify orchestrator
# ---------------------------------------------------------------------------


class TestVerify:
    """Tests for the verify() orchestrator."""

    def test_valid_case_has_no_errors(self):
        response = verify(_request(["a", "b"], ["a", "b"]))
        assert response.is_valid is True

    def test_missing_parameter_is_detected(self):
        response = verify(_request(["a", "b"], ["a"]))
        assert not response.is_valid
        types = {error.error_type for error in response.errors}
        assert VerificationErrorType.PARAMETER_MISSING in types

    def test_ghost_parameter_is_detected(self):
        response = verify(_request(["a"], ["a", "ghost"]))
        assert not response.is_valid
        types = {error.error_type for error in response.errors}
        assert VerificationErrorType.PARAMETER_GHOST in types

    def test_incorrect_order_is_detected(self):
        response = verify(_request(["a", "b"], ["b", "a"]))
        assert not response.is_valid
        types = {error.error_type for error in response.errors}
        assert VerificationErrorType.PARAMETER_ORDER_WRONG in types

    def test_missing_ghost_and_order_checks_run_together(self):
        # M1: [a, b], M2: [b, ghost] -> a is missing and ghost is extra.
        response = verify(_request(["a", "b"], ["b", "ghost"]))
        types = {error.error_type for error in response.errors}
        assert VerificationErrorType.PARAMETER_MISSING in types
        assert VerificationErrorType.PARAMETER_GHOST in types


# ---------------------------------------------------------------------------
# Enriched fields (iteration 3.7)
# ---------------------------------------------------------------------------


class TestVerifyEnrichedFields:
    """Verify that parameter_name, observed, and expected are populated."""

    def test_parameter_missing_enriched_fields(self):
        errors = check_missing_parameters(_request(["x"], []))
        assert len(errors) == 1
        error = errors[0]
        assert error.parameter_name == "x"
        assert error.expected == "x"
        assert error.observed is None

    def test_parameter_ghost_enriched_fields(self):
        errors = verify_parameters_ghosts(_request([], ["ghost"]))
        assert len(errors) == 1
        error = errors[0]
        assert error.parameter_name == "ghost"
        assert error.observed == "ghost"
        assert error.expected is None

    def test_parameter_order_wrong_enriched_fields(self):
        errors = verify_order_parameters(_request(["a", "b"], ["b", "a"]))
        assert len(errors) == 1
        error = errors[0]
        assert error.expected == "a, b"
        assert error.observed == "b, a"
        assert error.parameter_name is None
