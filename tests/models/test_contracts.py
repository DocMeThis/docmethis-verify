# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for verification contracts, structural invariants, and immutability."""

import pytest
from pydantic import ValidationError

from docmethis_verify.models.contracts import VerificationError, VerificationResponse
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType

_VALID_ERRORS: dict[VerificationErrorType, dict[str, object]] = {
    VerificationErrorType.PARAMETER_MISSING: {
        "section": "Parameters",
        "granularity": PatchGranularity.ENTRY,
        "parameter_name": "x",
        "expected": "x",
    },
    VerificationErrorType.PARAMETER_GHOST: {
        "section": "Parameters",
        "granularity": PatchGranularity.ENTRY,
        "parameter_name": "x",
        "observed": "x",
    },
    VerificationErrorType.PARAMETER_ORDER_WRONG: {
        "section": "Parameters",
        "granularity": PatchGranularity.SECTION,
        "expected": "x, y",
        "observed": "y, x",
    },
    VerificationErrorType.PARAMETER_TYPE_MISSING: {
        "section": "Parameters",
        "granularity": PatchGranularity.SPAN,
        "parameter_name": "x",
        "expected": "int",
    },
    VerificationErrorType.RETURNS_TYPE_MISSING: {
        "section": "Returns",
        "granularity": PatchGranularity.SPAN,
        "expected": "int",
    },
    VerificationErrorType.RAISES_GHOST: {
        "section": "Raises",
        "granularity": PatchGranularity.ENTRY,
        "observed": "ValueError",
    },
    VerificationErrorType.RAISES_MISSING: {
        "section": "Raises",
        "granularity": PatchGranularity.ENTRY,
        "expected": "ValueError",
        "provenance": "local",
    },
    VerificationErrorType.FORBIDDEN_TERM: {
        "section": "Summary",
        "granularity": PatchGranularity.SPAN,
        "observed": "always",
    },
}


def _make_error(
    error_type: VerificationErrorType = VerificationErrorType.PARAMETER_MISSING,
    detail: str = "parameter 'x' is absent from the M1 signature",
    **overrides: object,
) -> VerificationError:
    data = dict(_VALID_ERRORS[error_type])
    data.update(overrides)
    return VerificationError(error_type=error_type, detail=detail, **data)  # type: ignore[arg-type]


class TestVerificationError:
    """Tests for VerificationError structural invariants."""

    def test_valid_construction(self):
        err = _make_error()
        assert err.error_type is VerificationErrorType.PARAMETER_MISSING
        assert err.section == "Parameters"
        assert err.granularity is PatchGranularity.ENTRY

    def test_optional_fields_remain_none(self):
        err = _make_error(VerificationErrorType.RAISES_GHOST)
        assert err.parameter_name is None
        assert err.observed == "ValueError"
        assert err.expected is None

    def test_enriched_fields_are_populated(self):
        err = VerificationError(
            error_type=VerificationErrorType.PARAMETER_MISSING,
            section="Parameters",
            granularity=PatchGranularity.ENTRY,
            detail="parameter 'x' is absent",
            parameter_name="x",
            expected="x",
        )
        assert err.parameter_name == "x"
        assert err.expected == "x"
        assert err.observed is None

    def test_empty_enriched_fields_are_forbidden(self):
        with pytest.raises(ValidationError):
            _make_error(VerificationErrorType.PARAMETER_MISSING, parameter_name="")

    def test_immutable(self):
        err = _make_error()
        with pytest.raises((AttributeError, TypeError)):
            err.section = "Returns"  # type: ignore[misc]

    def test_empty_detail_is_forbidden(self):
        with pytest.raises(ValidationError):
            _make_error(VerificationErrorType.PARAMETER_GHOST, detail="")

    def test_empty_section_is_forbidden(self):
        with pytest.raises(ValidationError):
            _make_error(VerificationErrorType.RETURNS_TYPE_MISSING, section="", detail="Returns absent")

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(ValidationError):
            _make_error(VerificationErrorType.PARAMETER_MISSING, unknown_field="forbidden")

    def test_section_matches_error_type(self):
        err = _make_error()
        assert err.section == "Parameters"

    def test_section_mismatch_with_error_type_is_forbidden(self):
        with pytest.raises((ValueError, ValidationError)):
            _make_error(VerificationErrorType.PARAMETER_MISSING, section="Returns")

    def test_forbidden_term_accepts_all_valid_sections(self):
        for section in ("Summary", "Parameters", "Attributes", "Returns", "Raises"):
            err = _make_error(VerificationErrorType.FORBIDDEN_TERM, section=section, detail="detail")
            assert err.section == section


class TestGranularityRouting:
    """Verify granularity-to-patch mapping as an integration invariant."""

    def test_entry_implies_entry_patch(self):
        err = _make_error(VerificationErrorType.PARAMETER_MISSING, detail="detail")
        assert err.granularity is PatchGranularity.ENTRY
        assert PatchGranularity.ENTRY.value == "entry"

    def test_section_implies_section_patch(self):
        err = _make_error(VerificationErrorType.PARAMETER_ORDER_WRONG, detail="detail")
        assert err.granularity is PatchGranularity.SECTION

    def test_span_implies_span_patch(self):
        err = _make_error(VerificationErrorType.FORBIDDEN_TERM, detail="detail")
        assert err.granularity is PatchGranularity.SPAN

    def test_each_error_type_has_consistent_granularity(self):
        # SECTION: patch the whole Parameters section.
        section_types = [
            (VerificationErrorType.PARAMETER_ORDER_WRONG, "Parameters"),
        ]
        for error_type, section in section_types:
            err = _make_error(error_type, section=section, detail="d")
            assert err.granularity is PatchGranularity.SECTION, f"{error_type} should be SECTION"

        # ENTRY: a named entry in a section.
        entry_types = [
            (VerificationErrorType.PARAMETER_MISSING, "Parameters"),
            (VerificationErrorType.PARAMETER_GHOST, "Parameters"),
            (VerificationErrorType.RAISES_MISSING, "Raises"),
            (VerificationErrorType.RAISES_GHOST, "Raises"),
        ]
        for error_type, section in entry_types:
            err = _make_error(error_type, section=section, detail="d")
            assert err.granularity is PatchGranularity.ENTRY, f"{error_type} should be ENTRY"

        # SPAN: a targeted error in existing text.
        span_types = [
            (VerificationErrorType.PARAMETER_TYPE_MISSING, "Parameters"),
            (VerificationErrorType.RETURNS_TYPE_MISSING, "Returns"),
            (VerificationErrorType.FORBIDDEN_TERM, "Summary"),
        ]
        for error_type, section in span_types:
            err = _make_error(error_type, section=section, detail="d")
            assert err.granularity is PatchGranularity.SPAN, f"{error_type} should be SPAN"

    @pytest.mark.parametrize(
        ("error_type", "granularity"),
        [
            (error_type, granularity)
            for error_type, fields in _VALID_ERRORS.items()
            for granularity in PatchGranularity
            if granularity != fields["granularity"]
        ],
    )
    def test_error_type_rejects_all_inconsistent_granularities(
        self,
        error_type: VerificationErrorType,
        granularity: PatchGranularity,
    ) -> None:
        """Each verification error type imposes the granularity consumed by Check and Fix."""
        with pytest.raises((ValueError, ValidationError), match="granularity"):
            _make_error(error_type, granularity=granularity)

    @pytest.mark.parametrize(
        ("error_type", "field"),
        [
            (VerificationErrorType.PARAMETER_MISSING, "parameter_name"),
            (VerificationErrorType.PARAMETER_MISSING, "expected"),
            (VerificationErrorType.PARAMETER_GHOST, "parameter_name"),
            (VerificationErrorType.PARAMETER_GHOST, "observed"),
            (VerificationErrorType.PARAMETER_ORDER_WRONG, "expected"),
            (VerificationErrorType.PARAMETER_ORDER_WRONG, "observed"),
            (VerificationErrorType.PARAMETER_TYPE_MISSING, "parameter_name"),
            (VerificationErrorType.PARAMETER_TYPE_MISSING, "expected"),
            (VerificationErrorType.RETURNS_TYPE_MISSING, "expected"),
            (VerificationErrorType.RAISES_GHOST, "observed"),
            (VerificationErrorType.RAISES_MISSING, "expected"),
            (VerificationErrorType.RAISES_MISSING, "provenance"),
            (VerificationErrorType.FORBIDDEN_TERM, "observed"),
        ],
    )
    def test_error_type_requires_identity_fields(
        self,
        error_type: VerificationErrorType,
        field: str,
    ) -> None:
        """Targeting data cannot be replaced by human-readable text."""
        with pytest.raises((ValueError, ValidationError), match="identity field"):
            _make_error(error_type, **{field: None})


class TestVerificationResponse:
    """Tests for VerificationResponse invariants."""

    def test_is_valid_without_errors(self):
        rep = VerificationResponse(errors=(), warnings=())
        assert rep.is_valid is True

    def test_is_valid_with_errors(self):
        rep = VerificationResponse(errors=(_make_error(),), warnings=())
        assert rep.is_valid is False

    def test_is_valid_derived_value_is_not_mutable(self):
        rep = VerificationResponse(errors=(), warnings=())
        with pytest.raises((AttributeError, TypeError)):
            rep.is_valid = False  # type: ignore[misc]

    def test_errors_are_immutable(self):
        rep = VerificationResponse(errors=(_make_error(),), warnings=())
        with pytest.raises((AttributeError, TypeError)):
            rep.errors = ()  # type: ignore[misc]

    def test_multiple_errors(self):
        errors = (
            _make_error(VerificationErrorType.PARAMETER_MISSING),
            _make_error(VerificationErrorType.RETURNS_TYPE_MISSING, section="Returns"),
        )
        response = VerificationResponse(errors=errors, warnings=())
        assert not response.is_valid
        assert len(response.errors) == 2
