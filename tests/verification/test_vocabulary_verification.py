# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for forbidden vocabulary verification."""

from pathlib import Path

from docmethis_extract_python.static_extraction.models import (
    Confidence,
    FunctionRecord,
    MethodType,
    Visibility,
)

from docmethis_verify.docstring.models import (
    DocstringAttribute,
    DocstringParameter,
    DocstringRaise,
    DocstringReturn,
    GeneratedDocstring,
)
from docmethis_verify.models.contracts import VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.verification.verifier import verify
from docmethis_verify.verification.vocabulary_verification import verify_vocabulary_forbidden

_PATH = Path("tests/mock/example.py")
_FORBIDDEN_TERMS = ("always", "never", "guarantees", "guaranteed", "ensures", "impossible")


def _function_record() -> FunctionRecord:
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
        exceptions=None,
    )


def _generated_docstring(
    summary: str = "Normal summary.",
    parameters: list[tuple[str, str]] | None = None,
    returns_description: str | None = None,
) -> GeneratedDocstring:
    params = tuple(DocstringParameter(name=name, description=description) for name, description in (parameters or []))
    returns = DocstringReturn(description=returns_description) if returns_description is not None else None
    return GeneratedDocstring(summary=summary, parameters=params, returns=returns, raises=())


def _request(
    summary: str = "Normal summary.",
    parameters: list[tuple[str, str]] | None = None,
    returns_description: str | None = None,
) -> VerificationRequest:
    return VerificationRequest(
        function_record=_function_record(),
        generated_docstring=_generated_docstring(summary, parameters, returns_description),
        forbidden_terms=_FORBIDDEN_TERMS,
    )


# ---------------------------------------------------------------------------
# verify_vocabulary_forbidden — summary
# ---------------------------------------------------------------------------


class TestVerifyVocabularyForbiddenSummary:
    """Tests for the summary field."""

    def test_forbidden_term_in_summary(self):
        errors = verify_vocabulary_forbidden(_request(summary="This function returns always the same value."))
        assert len(errors) == 1
        assert errors[0].error_type is VerificationErrorType.FORBIDDEN_TERM
        assert errors[0].section == "Summary"
        assert errors[0].granularity is PatchGranularity.SPAN
        assert "always" in errors[0].detail.lower()

    def test_multiple_forbidden_terms_in_summary(self):
        errors = verify_vocabulary_forbidden(_request(summary="This function always guaranteed returns the same value."))
        types = {error.error_type for error in errors}
        assert VerificationErrorType.FORBIDDEN_TERM in types
        assert len(errors) >= 2

    def test_summary_without_forbidden_term(self):
        errors = verify_vocabulary_forbidden(_request(summary="Calculate the sum of the elements."))
        assert errors == []

    def test_partial_term_is_not_detected(self):
        errors = verify_vocabulary_forbidden(_request(summary="reallways is not the forbidden term."))
        assert errors == []

    def test_term_inside_compound_word_is_not_detected(self):
        errors = verify_vocabulary_forbidden(_request(summary="The result is invariably correct."))
        assert errors == []

    def test_not_always_is_detected(self):
        errors = verify_vocabulary_forbidden(_request(summary="This is not always the case."))
        forbidden_in_summary = [error for error in errors if error.section == "Summary"]
        assert len(forbidden_in_summary) >= 1

    def test_case_insensitive(self):
        errors = verify_vocabulary_forbidden(_request(summary="ALWAYS returns true."))
        assert len(errors) == 1
        assert errors[0].section == "Summary"


# ---------------------------------------------------------------------------
# verify_vocabulary_forbidden — parameters
# ---------------------------------------------------------------------------


class TestVerifyVocabularyForbiddenParameters:
    """Tests for parameter descriptions."""

    def test_forbidden_term_in_parameter_description(self):
        errors = verify_vocabulary_forbidden(_request(parameters=[("x", "Guaranteed positive value.")]))
        parameter_errors = [error for error in errors if error.section == "Parameters"]
        assert len(parameter_errors) == 1
        assert parameter_errors[0].error_type is VerificationErrorType.FORBIDDEN_TERM
        assert "x" in parameter_errors[0].detail

    def test_parameter_description_without_forbidden_term(self):
        errors = verify_vocabulary_forbidden(_request(parameters=[("x", "Positive integer representing the size.")]))
        assert errors == []

    def test_multiple_parameters_with_forbidden_terms(self):
        errors = verify_vocabulary_forbidden(
            _request(
                parameters=[
                    ("a", "always positive"),
                    ("b", "never negative"),
                ]
            )
        )
        sections = [error.section for error in errors]
        assert sections.count("Parameters") == 2

    def test_detail_contains_parameter_name(self):
        errors = verify_vocabulary_forbidden(_request(parameters=[("my_param", "guaranteed valid.")]))
        assert any("my_param" in error.detail for error in errors)


# ---------------------------------------------------------------------------
# verify_vocabulary_forbidden — returns
# ---------------------------------------------------------------------------


class TestVerifyVocabularyForbiddenReturns:
    """Tests for the return description."""

    def test_forbidden_term_in_return_description(self):
        errors = verify_vocabulary_forbidden(_request(returns_description="Always returns a positive integer."))
        return_errors = [error for error in errors if error.section == "Returns"]
        assert len(return_errors) == 1
        assert return_errors[0].error_type is VerificationErrorType.FORBIDDEN_TERM

    def test_return_description_without_forbidden_term(self):
        errors = verify_vocabulary_forbidden(_request(returns_description="Integer representing the sum."))
        assert errors == []

    def test_absent_returns_have_no_error(self):
        errors = verify_vocabulary_forbidden(_request(returns_description=None))
        return_errors = [error for error in errors if error.section == "Returns"]
        assert return_errors == []


class TestVerifyVocabularyForbiddenAttributes:
    """Tests for class attribute descriptions."""

    def test_forbidden_term_in_attribute_description(self):
        generated_docstring = GeneratedDocstring(
            summary="Summary.",
            attributes=(DocstringAttribute(name="value", description="Always positive."),),
        )
        request = VerificationRequest(
            function_record=_function_record(),
            generated_docstring=generated_docstring,
            forbidden_terms=_FORBIDDEN_TERMS,
        )

        errors = verify_vocabulary_forbidden(request)

        assert len(errors) == 1
        assert errors[0].section == "Attributes"
        assert errors[0].observed == "Always"


# ---------------------------------------------------------------------------
# verify_vocabulary_forbidden — combinations
# ---------------------------------------------------------------------------


class TestVerifyVocabularyForbiddenCombinations:
    """Tests for combinations of fields."""

    def test_terms_in_multiple_sections(self):
        errors = verify_vocabulary_forbidden(
            _request(
                summary="always correct",
                parameters=[("x", "guaranteed valid")],
                returns_description="never null",
            )
        )
        sections = {error.section for error in errors}
        assert "Summary" in sections
        assert "Parameters" in sections
        assert "Returns" in sections

    def test_no_terms_in_any_section(self):
        errors = verify_vocabulary_forbidden(
            _request(
                summary="Calculate the sum.",
                parameters=[("x", "Integer value.")],
                returns_description="Sum of the elements.",
            )
        )
        assert errors == []


class TestVerifyVocabularyIntegration:
    """Integration tests through the verify orchestrator."""

    def test_forbidden_term_detected_via_verify(self):
        response = verify(_request(summary="This function always returns true."))
        assert not response.is_valid
        assert VerificationErrorType.FORBIDDEN_TERM in {error.error_type for error in response.errors}

    def test_valid_case_has_no_vocabulary_errors(self):
        response = verify(_request(summary="Calculate and return the sum."))
        vocabulary_errors = [error for error in response.errors if error.error_type is VerificationErrorType.FORBIDDEN_TERM]
        assert vocabulary_errors == []


# ---------------------------------------------------------------------------
# Enriched fields (iteration 3.7)
# ---------------------------------------------------------------------------


class TestVerifyVocabularyForbiddenRaises:
    """Tests for exception descriptions."""

    def test_forbidden_term_in_raises_description(self):
        generated_docstring = GeneratedDocstring(
            summary="Summary.",
            raises=(DocstringRaise(exception="ValueError", description="always raised if invalid."),),
        )
        request = VerificationRequest(
            function_record=_function_record(),
            generated_docstring=generated_docstring,
            forbidden_terms=_FORBIDDEN_TERMS,
        )
        errors = verify_vocabulary_forbidden(request)
        raises_errors = [error for error in errors if error.section == "Raises"]
        assert len(raises_errors) == 1
        assert raises_errors[0].error_type is VerificationErrorType.FORBIDDEN_TERM
        assert raises_errors[0].observed is not None
        assert raises_errors[0].observed.lower() == "always"
        assert raises_errors[0].parameter_name == "ValueError"

    def test_raises_description_without_forbidden_term(self):
        generated_docstring = GeneratedDocstring(
            summary="Summary.",
            raises=(DocstringRaise(exception="ValueError", description="Raised if the value is invalid."),),
        )
        request = VerificationRequest(
            function_record=_function_record(),
            generated_docstring=generated_docstring,
            forbidden_terms=_FORBIDDEN_TERMS,
        )
        errors = verify_vocabulary_forbidden(request)
        assert [error for error in errors if error.section == "Raises"] == []

    def test_empty_raises_have_no_error(self):
        errors = verify_vocabulary_forbidden(_request())
        assert [error for error in errors if error.section == "Raises"] == []


class TestVerifyVocabularyEnrichedFields:
    """Verify that observed and parameter_name are populated."""

    def test_observed_is_set_in_summary(self):
        errors = verify_vocabulary_forbidden(_request(summary="always returns true."))
        assert len(errors) == 1
        error = errors[0]
        assert error.observed is not None
        assert error.observed.lower() == "always"
        assert error.expected is None
        assert error.parameter_name is None

    def test_terms_are_request_local(self):
        always = _request(summary="always returns true.")
        never = _request(summary="never returns true.")
        only_never = VerificationRequest(
            function_record=_function_record(),
            generated_docstring=never.generated_docstring,
            forbidden_terms=("never",),
        )

        assert len(verify_vocabulary_forbidden(always)) == 1
        assert verify_vocabulary_forbidden(only_never)[0].observed == "never"

    def test_forbidden_term_in_notes(self):
        generated_docstring = GeneratedDocstring(summary="Summary.", notes=("always in notes.",))
        request = VerificationRequest(
            function_record=_function_record(),
            generated_docstring=generated_docstring,
            forbidden_terms=("always",),
        )

        errors = verify_vocabulary_forbidden(request)

        assert [error.section for error in errors] == ["Notes"]

    def test_observed_and_parameter_name_are_set_in_parameter(self):
        errors = verify_vocabulary_forbidden(_request(parameters=[("my_param", "guaranteed valid.")]))
        assert len(errors) == 1
        error = errors[0]
        assert error.observed is not None
        assert error.observed.lower() == "guaranteed"
        assert error.parameter_name == "my_param"
        assert error.expected is None

    def test_observed_is_set_in_returns(self):
        errors = verify_vocabulary_forbidden(_request(returns_description="never null."))
        assert len(errors) == 1
        error = errors[0]
        assert error.observed is not None
        assert error.observed.lower() == "never"
        assert error.parameter_name is None
        assert error.expected is None
