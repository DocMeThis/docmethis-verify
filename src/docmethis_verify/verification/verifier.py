# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Deterministic verification orchestrator."""

from docmethis_extract_python.api import ClassRecord, ModuleRecord

from docmethis_verify.models.contracts import VerificationRequest, VerificationResponse
from docmethis_verify.verification.format_validator import validate_docstring_format
from docmethis_verify.verification.raises_verification import verify_raises_ghosts, verify_raises_missing
from docmethis_verify.verification.structural import (
    check_missing_parameters,
    verify_order_parameters,
    verify_parameters_ghosts,
)
from docmethis_verify.verification.types_verification import (
    verify_type_return_missing,
    verify_types_parameters_missing,
)
from docmethis_verify.verification.vocabulary_verification import verify_vocabulary_forbidden


def verify(request: VerificationRequest) -> VerificationResponse:
    """Return the structured verification response for a generated docstring.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the function record to be checked and all data needed for docstring verification.

    Returns
    -------
    VerificationResponse
        A VerificationResponse containing the errors and warnings collected during verification of the docstring.

    """
    if isinstance(request.function_record, (ClassRecord, ModuleRecord)):
        errors = verify_vocabulary_forbidden(request)
    else:
        errors = (
            *check_missing_parameters(request),
            *verify_parameters_ghosts(request),
            *verify_order_parameters(request),
            *verify_types_parameters_missing(request),
            *verify_type_return_missing(request),
            *verify_raises_ghosts(request),
            *verify_raises_missing(request),
            *verify_vocabulary_forbidden(request),
        )

    raw_docstring = request.function_record.existing_docstring or ""
    warnings = tuple(validate_docstring_format(raw_docstring))

    return VerificationResponse(errors=errors, warnings=warnings)
