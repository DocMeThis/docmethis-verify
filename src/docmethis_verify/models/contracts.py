# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Contracts for deterministic docstring verification."""

from typing import Literal

from docmethis_extract_python.api import ClassRecord, FunctionRecord, ModuleRecord
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from docmethis_verify.docstring.models import GeneratedDocstring
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.models.format_warning import FormatWarning, FormatWarningSpan
from docmethis_verify.validation import NonEmptyStr, NonNegativeStrictInt, OptionalNonEmptyStr, StrictTupleOfNonEmptyStr

__all__ = ["FormatWarning", "FormatWarningSpan", "VerificationError", "VerificationRequest", "VerificationResponse"]

_CONFIG_DICT = ConfigDict(extra="forbid")

# Valid sections by error type, used by __post_init__ to keep each
# VerificationError internally consistent at construction time.
_VALID_SECTIONS: dict[VerificationErrorType, frozenset[str]] = {
    VerificationErrorType.PARAMETER_MISSING: frozenset({"Parameters"}),
    VerificationErrorType.PARAMETER_GHOST: frozenset({"Parameters"}),
    VerificationErrorType.PARAMETER_ORDER_WRONG: frozenset({"Parameters"}),
    VerificationErrorType.PARAMETER_TYPE_MISSING: frozenset({"Parameters"}),
    VerificationErrorType.RETURNS_TYPE_MISSING: frozenset({"Returns"}),
    VerificationErrorType.RAISES_GHOST: frozenset({"Raises"}),
    VerificationErrorType.RAISES_MISSING: frozenset({"Raises"}),
    VerificationErrorType.FORBIDDEN_TERM: frozenset(
        {"Summary", "Parameters", "Attributes", "Returns", "Raises", "Notes", "Examples"}
    ),
}

_EXPECTED_GRANULARITIES: dict[VerificationErrorType, PatchGranularity] = {
    VerificationErrorType.PARAMETER_MISSING: PatchGranularity.ENTRY,
    VerificationErrorType.PARAMETER_GHOST: PatchGranularity.ENTRY,
    VerificationErrorType.PARAMETER_ORDER_WRONG: PatchGranularity.SECTION,
    VerificationErrorType.PARAMETER_TYPE_MISSING: PatchGranularity.SPAN,
    VerificationErrorType.RETURNS_TYPE_MISSING: PatchGranularity.SPAN,
    VerificationErrorType.RAISES_GHOST: PatchGranularity.ENTRY,
    VerificationErrorType.RAISES_MISSING: PatchGranularity.ENTRY,
    VerificationErrorType.FORBIDDEN_TERM: PatchGranularity.SPAN,
}

_REQUIRED_IDENTITY_FIELDS: dict[VerificationErrorType, frozenset[str]] = {
    VerificationErrorType.PARAMETER_MISSING: frozenset({"parameter_name", "expected"}),
    VerificationErrorType.PARAMETER_GHOST: frozenset({"parameter_name", "observed"}),
    VerificationErrorType.PARAMETER_ORDER_WRONG: frozenset({"expected", "observed"}),
    VerificationErrorType.PARAMETER_TYPE_MISSING: frozenset({"parameter_name", "expected"}),
    VerificationErrorType.RETURNS_TYPE_MISSING: frozenset({"expected"}),
    VerificationErrorType.RAISES_GHOST: frozenset({"observed"}),
    VerificationErrorType.RAISES_MISSING: frozenset({"expected", "provenance"}),
    VerificationErrorType.FORBIDDEN_TERM: frozenset({"observed"}),
}


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class VerificationError:
    """Structured verification error emitted by deterministic verification.

    The `observed` and `expected` fields are the structured source of truth.
    Each verifier builds the human-readable `detail` text and is responsible
    for keeping it consistent with `observed` and `expected`.

    Attributes
    ----------
    error_type : VerificationErrorType
        Kind of verification error.
    section : NonEmptyStr
        Docstring section the error applies to.
    granularity : PatchGranularity
        Granularity of the patch required to fix the error.
    detail : NonEmptyStr
        Human-readable description of the error.
    parameter_name : OptionalNonEmptyStr
        Parameter the error applies to, when relevant.
    observed : OptionalNonEmptyStr
        Structured observed value, when relevant.
    expected : OptionalNonEmptyStr
        Structured expected value, when relevant.
    provenance : Literal["local", "propagated"] | None
        Origin of the error: detected locally or propagated.
    dmt_code : str | None
        DMT code associated with the error, when known.

    Raises
    ------
    ValueError
        If the section, granularity, or identity fields are inconsistent
        with the error type.

    """

    error_type: VerificationErrorType
    section: NonEmptyStr
    granularity: PatchGranularity
    detail: NonEmptyStr
    parameter_name: OptionalNonEmptyStr = None
    observed: OptionalNonEmptyStr = None
    expected: OptionalNonEmptyStr = None
    provenance: Literal["local", "propagated"] | None = None
    dmt_code: str | None = None

    def __post_init__(self) -> None:
        """Validate error routing and structured identity.

        Raises
        ------
        ValueError
            Explicitly raised.

        """
        valid_sections = _VALID_SECTIONS.get(self.error_type)
        if valid_sections is not None and self.section not in valid_sections:
            msg = (
                f"section '{self.section}' is invalid for error_type '{self.error_type.value}'"
                f" — expected: {sorted(valid_sections)}"
            )
            raise ValueError(msg)

        expected_granularity = _EXPECTED_GRANULARITIES[self.error_type]
        if self.granularity is not expected_granularity:
            msg = (
                f"granularity '{self.granularity.value}' is invalid for error_type '{self.error_type.value}'"
                f" — expected: '{expected_granularity.value}'"
            )
            raise ValueError(msg)

        for field in _REQUIRED_IDENTITY_FIELDS[self.error_type]:
            if getattr(self, field) is None:
                msg = f"identity field '{field}' is required for error_type '{self.error_type.value}'"
                raise ValueError(msg)


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class VerificationRequest:
    """Request for verifying a generated docstring against extracted facts.

    Attributes
    ----------
    generated_docstring : GeneratedDocstring
        The docstring to verify.
    function_record : FunctionRecord | ClassRecord | ModuleRecord
        Extracted facts about the documented symbol.
    forbidden_terms : StrictTupleOfNonEmptyStr
        Terms forbidden in the docstring.
    module_record : ModuleRecord | None
        Enclosing module facts used to resolve return annotation imports. Unresolved names remain unknown when omitted.
    exception_documentation_depth : NonNegativeStrictInt
        Maximum documented exception call distance; one includes local raises and direct callees.

    """

    generated_docstring: GeneratedDocstring
    function_record: FunctionRecord | ClassRecord | ModuleRecord
    forbidden_terms: StrictTupleOfNonEmptyStr = ()
    module_record: ModuleRecord | None = None
    exception_documentation_depth: NonNegativeStrictInt = 1


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class VerificationResponse:
    """Verification response produced by deterministic verification.

    Attributes
    ----------
    errors : tuple[VerificationError, ...]
        Verification errors found.
    warnings : tuple[FormatWarning, ...]
        Format warnings found.

    """

    errors: tuple[VerificationError, ...]
    warnings: tuple[FormatWarning, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the docstring has no verification errors.

        Returns
        -------
        bool
            True if the docstring has no verification errors, False otherwise.

        """
        return len(self.errors) == 0
