# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Verify forbidden vocabulary in free-text docstring sections."""

import re

from docmethis_verify.dmt import DMT_7200
from docmethis_verify.models.contracts import VerificationError, VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.validation import OptionalNonEmptyStr
from docmethis_verify.verification.forbidden_terms import compile_forbidden_patterns

__all__ = ["verify_vocabulary_forbidden"]


def _errors_in_text(
    *,
    text: str,
    section: str,
    detail_template: str,
    patterns: tuple[re.Pattern[str], ...],
    parameter_name: OptionalNonEmptyStr = None,
) -> list[VerificationError]:
    """Return one error for each forbidden term occurrence in text.

    Parameters
    ----------
    text : str
        The text to scan for forbidden term occurrences.
    section : str
        The section name that identifies where a forbidden term was found; it is a required keyword-only argument and is
        propagated to the section field of each returned error.
    detail_template : str
        Template string used to construct the detail message for each verification error. It should contain a {term} placeholder,
        which is replaced with the matched forbidden term from the text.
    patterns : tuple[re.Pattern[str], ...]
        Compiled regular expression patterns to search for in the text; each match of any pattern is reported as a forbidden term
        occurrence.
    parameter_name : OptionalNonEmptyStr = None
        Optional name of the parameter being checked, used to associate the returned verification errors with a specific
        parameter.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError instances, one for each occurrence of a forbidden term in text.

    """
    return [
        VerificationError(
            error_type=VerificationErrorType.FORBIDDEN_TERM,
            section=section,
            granularity=PatchGranularity.SPAN,
            detail=detail_template.format(term=match.group()),
            parameter_name=parameter_name,
            observed=match.group(),
            dmt_code=DMT_7200,
        )
        for pattern in patterns
        for match in pattern.finditer(text)
    ]


def verify_vocabulary_forbidden(request: VerificationRequest) -> list[VerificationError]:
    """Return errors for each forbidden term found in free-text docstring sections.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the generated docstring and the forbidden terms to check for.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError instances describing each occurrence of a forbidden term in the free-text docstring sections;
        empty if no forbidden terms are found.

    """
    patterns = compile_forbidden_patterns(request.forbidden_terms)
    errors: list[VerificationError] = []

    errors.extend(
        _errors_in_text(
            text=request.generated_docstring.summary,
            section="Summary",
            detail_template="forbidden term '{term}' in summary",
            patterns=patterns,
        )
    )

    for parameter in request.generated_docstring.parameters:
        errors.extend(
            _errors_in_text(
                text=parameter.description,
                section="Parameters",
                detail_template=f"forbidden term '{{term}}' in parameter '{parameter.name}' description",
                patterns=patterns,
                parameter_name=parameter.name,
            )
        )

    for attribute in request.generated_docstring.attributes:
        errors.extend(
            _errors_in_text(
                text=attribute.description,
                section="Attributes",
                detail_template=f"forbidden term '{{term}}' in attribute '{attribute.name}' description",
                patterns=patterns,
            )
        )

    if request.generated_docstring.returns is not None:
        errors.extend(
            _errors_in_text(
                text=request.generated_docstring.returns.description,
                section="Returns",
                detail_template="forbidden term '{term}' in return description",
                patterns=patterns,
            )
        )

    for documented_raise in request.generated_docstring.raises:
        errors.extend(
            _errors_in_text(
                text=documented_raise.description,
                section="Raises",
                detail_template=f"forbidden term '{{term}}' in exception '{documented_raise.exception}' description",
                patterns=patterns,
                parameter_name=documented_raise.exception,
            )
        )

    for note in request.generated_docstring.notes:
        errors.extend(
            _errors_in_text(
                text=note,
                section="Notes",
                detail_template="forbidden term '{term}' in notes",
                patterns=patterns,
            )
        )

    for example in request.generated_docstring.examples:
        errors.extend(
            _errors_in_text(
                text=example.description,
                section="Examples",
                detail_template="forbidden term '{term}' in example description",
                patterns=patterns,
            )
        )

    return errors
