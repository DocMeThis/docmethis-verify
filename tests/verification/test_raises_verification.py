# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for Raises section verifiers."""

from pathlib import Path

from docmethis_extract_python.static_extraction.models import (
    Confidence,
    ExceptBlock,
    ExceptionRecord,
    FunctionRecord,
    MethodType,
    Provenance,
    Visibility,
)

from docmethis_verify.docstring.models import (
    DocstringRaise,
    GeneratedDocstring,
)
from docmethis_verify.models.contracts import VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.verification.raises_verification import (
    verify_raises_ghosts,
    verify_raises_missing,
)
from docmethis_verify.verification.verifier import verify

_PATH = Path("tests/mock/example.py")


def _exception_record(name: str) -> ExceptionRecord:
    return ExceptionRecord(exception_type=name, message=None, raise_line=3)


def _function_record(exception_names: list[str] | None) -> FunctionRecord:
    exceptions = [_exception_record(name) for name in exception_names] if exception_names is not None else None
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
        exceptions=exceptions,
    )


def _generated_docstring(raises: list[str]) -> GeneratedDocstring:
    documented_raises = tuple(DocstringRaise(exception=name, description=f"Raised if {name}.") for name in raises)
    return GeneratedDocstring(summary="Summary", parameters=(), raises=documented_raises, returns=None)


def _request(exception_names: list[str] | None, raise_names: list[str]) -> VerificationRequest:
    return VerificationRequest(
        function_record=_function_record(exception_names),
        generated_docstring=_generated_docstring(raise_names),
    )


# ---------------------------------------------------------------------------
# verify_raises_ghosts
# ---------------------------------------------------------------------------


class TestVerifyRaisesGhosts:
    """Unit tests for verify_raises_ghosts()."""

    def test_none_exceptions_return_empty_list(self):
        errors = verify_raises_ghosts(_request(None, ["ValueError"]))
        assert errors == []

    def test_single_ghost_exception(self):
        errors = verify_raises_ghosts(_request([], ["ValueError"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.RAISES_GHOST
        assert "ValueError" in errors[0].detail

    def test_exception_present_in_m1_has_no_error(self):
        errors = verify_raises_ghosts(_request(["ValueError"], ["ValueError"]))
        assert errors == []

    def test_multiple_ghosts(self):
        errors = verify_raises_ghosts(_request([], ["ValueError", "TypeError"]))
        assert len(errors) == 2
        assert all(error.error_type is VerificationErrorType.RAISES_GHOST for error in errors)

    def test_duplicate_documented_entries_are_deduplicated(self):
        errors = verify_raises_ghosts(_request([], ["ValueError", "builtins.ValueError", "valueerror"]))

        assert [(error.observed, error.dmt_code) for error in errors] == [("ValueError", "DMT-4002")]

    def test_mix_present_and_ghost(self):
        errors = verify_raises_ghosts(_request(["ValueError"], ["ValueError", "TypeError"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.RAISES_GHOST
        assert "TypeError" in errors[0].detail

    def test_module_qualification_is_normalized(self):
        errors = verify_raises_ghosts(_request(["builtins.ValueError"], ["ValueError"]))
        assert errors == []

    def test_case_is_normalized(self):
        errors = verify_raises_ghosts(_request(["ValueError"], ["valueerror"]))
        assert errors == []

    def test_empty_m2_has_no_error(self):
        errors = verify_raises_ghosts(_request(["ValueError"], []))
        assert errors == []


# ---------------------------------------------------------------------------
# verify_raises_missing
# ---------------------------------------------------------------------------


class TestVerifyRaisesMissing:
    """Unit tests for verify_raises_missing()."""

    def test_none_exceptions_returns_empty_list(self):
        errors = verify_raises_missing(_request(None, []))
        assert errors == []

    def test_single_missing_exception(self):
        errors = verify_raises_missing(_request(["ValueError"], []))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.RAISES_MISSING
        assert "ValueError" in errors[0].detail

    def test_documented_exception_has_no_error(self):
        errors = verify_raises_missing(_request(["ValueError"], ["ValueError"]))
        assert errors == []

    def test_multiple_missing_exceptions(self):
        errors = verify_raises_missing(_request(["ValueError", "TypeError"], []))
        assert len(errors) == 2
        assert all(error.error_type is VerificationErrorType.RAISES_MISSING for error in errors)

    def test_duplicate_m1_occurrences_are_deduplicated(self):
        errors = verify_raises_missing(_request(["ValueError", "builtins.ValueError", "valueerror"], []))

        assert [(error.expected, error.provenance, error.dmt_code) for error in errors] == [("ValueError", "local", "DMT-4001")]

    def test_local_observation_takes_precedence_over_propagation(self):
        request = _request(["ValueError", "builtins.ValueError"], [])
        assert request.function_record.exceptions is not None
        request.function_record.exceptions[0].provenance = Provenance.CALLGRAPH_PROPAGATION

        errors = verify_raises_missing(request)

        assert [(error.expected, error.provenance) for error in errors] == [("builtins.ValueError", "local")]

    def test_mix_documented_and_missing(self):
        errors = verify_raises_missing(_request(["ValueError", "TypeError"], ["ValueError"]))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.RAISES_MISSING
        assert "TypeError" in errors[0].detail

    def test_module_qualification_is_normalized(self):
        errors = verify_raises_missing(_request(["ValueError"], ["builtins.ValueError"]))
        assert errors == []

    def test_case_is_normalized(self):
        errors = verify_raises_missing(_request(["ValueError"], ["valueerror"]))
        assert errors == []

    def test_empty_m1_has_no_error(self):
        errors = verify_raises_missing(_request([], ["ValueError"]))
        assert errors == []

    def test_locally_caught_exception_is_not_exposed(self):
        function = _function_record(["ValueError"])
        function.except_blocks = [ExceptBlock(caught_types=["ValueError"], is_reraised=False, is_swallowed=True, line=4)]
        request = VerificationRequest(function_record=function, generated_docstring=_generated_docstring([]))

        assert verify_raises_missing(request) == []


# ---------------------------------------------------------------------------
# Entry granularity (iteration 3.9, phase 2)
# ---------------------------------------------------------------------------


class TestEntryGranularityRaises:
    """Verify individual targeting of Raises diagnostics."""

    def test_ghost_raises_are_distinct_entries(self):
        errors = verify_raises_ghosts(_request([], ["ValueError", "TypeError"]))

        assert [
            (error.granularity, error.expected, error.observed, error.parameter_name, error.dmt_code) for error in errors
        ] == [
            (PatchGranularity.ENTRY, None, "ValueError", None, "DMT-4002"),
            (PatchGranularity.ENTRY, None, "TypeError", None, "DMT-4002"),
        ]

    def test_missing_raises_preserve_provenance_and_granularity(self):
        request = _request(["builtins.ValueError", "ValueError"], [])
        assert request.function_record.exceptions is not None
        request.function_record.exceptions[1].provenance = Provenance.CALLGRAPH_PROPAGATION

        errors = verify_raises_missing(request)

        assert [(error.granularity, error.expected, error.observed, error.provenance, error.dmt_code) for error in errors] == [
            (PatchGranularity.ENTRY, "builtins.ValueError", None, "local", "DMT-4001"),
        ]

    def test_verify_preserves_raises_targeting(self):
        response = verify(_request(["TypeError"], ["ValueError"]))
        granularities = {error.error_type: error.granularity for error in response.errors}

        assert granularities == {
            VerificationErrorType.RAISES_GHOST: PatchGranularity.ENTRY,
            VerificationErrorType.RAISES_MISSING: PatchGranularity.ENTRY,
        }


# ---------------------------------------------------------------------------
# verify orchestrator
# ---------------------------------------------------------------------------


class TestVerifyRaisesIntegration:
    """Integration tests through the orchestrator."""

    def test_ghost_raise_is_detected(self):
        response = verify(_request([], ["ValueError"]))
        assert not response.is_valid
        assert VerificationErrorType.RAISES_GHOST in {error.error_type for error in response.errors}

    def test_missing_raise_is_detected(self):
        response = verify(_request(["ValueError"], []))
        assert not response.is_valid
        assert VerificationErrorType.RAISES_MISSING in {error.error_type for error in response.errors}

    def test_valid_case_has_no_errors(self):
        response = verify(_request(["ValueError"], ["ValueError"]))
        assert response.is_valid


# ---------------------------------------------------------------------------
# Enriched fields (iteration 3.7)
# ---------------------------------------------------------------------------


class TestVerifyRaisesEnrichedFields:
    """Verify that observed and expected are populated."""

    def test_raises_ghost_enriched_fields(self):
        errors = verify_raises_ghosts(_request([], ["ValueError"]))
        assert len(errors) == 1
        error = errors[0]
        assert error.observed == "ValueError"
        assert error.expected is None
        assert error.parameter_name is None

    def test_raises_missing_enriched_fields(self):
        errors = verify_raises_missing(_request(["TypeError"], []))
        assert len(errors) == 1
        error = errors[0]
        assert error.expected == "TypeError"
        assert error.observed is None
        assert error.parameter_name is None

    def test_raises_missing_deduplicates_m1_provenance(self):
        request = _request(["builtins.ValueError", "ValueError"], [])
        assert request.function_record.exceptions is not None
        request.function_record.exceptions[1].provenance = Provenance.CALLGRAPH_PROPAGATION

        errors = verify_raises_missing(request)

        assert [(error.expected, error.provenance) for error in errors] == [
            ("builtins.ValueError", "local"),
        ]
