# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Pure structural verifiers for deterministic verification."""

from docmethis_extract_python.api import FunctionRecord, implicit_receiver_exclusion_reason

from docmethis_verify.dmt import DMT_2001, DMT_2002, DMT_2003
from docmethis_verify.models.contracts import VerificationError, VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType


def check_missing_parameters(request: VerificationRequest) -> list[VerificationError]:
    """Return an error for each M1 parameter missing from the generated docstring.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the function record and generated docstring to inspect for missing M1 parameters.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError objects, one for each M1 parameter that is missing from the generated docstring. The list is
        empty when no such parameters are missing or when the request does not contain a function record with a signature.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.signature is None:
        return []

    m1_names = list(
        dict.fromkeys(
            parameter.name
            for parameter in request.function_record.signature.parameters
            if implicit_receiver_exclusion_reason(
                parameter_name=parameter.name,
                method_kind=request.function_record.method_kind,
            )
            is None
        )
    )
    m2_names = {parameter.name for parameter in request.generated_docstring.parameters}

    return [
        VerificationError(
            error_type=VerificationErrorType.PARAMETER_MISSING,
            section="Parameters",
            granularity=PatchGranularity.ENTRY,
            detail=f"parameter '{parameter_name}' is not documented",
            parameter_name=parameter_name,
            expected=parameter_name,
            dmt_code=DMT_2001,
        )
        for parameter_name in m1_names
        if parameter_name not in m2_names
    ]


def verify_parameters_ghosts(request: VerificationRequest) -> list[VerificationError]:
    """Return an error for each generated parameter absent from the M1 signature.

    Parameters
    ----------
    request : VerificationRequest
        The request object containing the function record and generated docstring data used to verify parameter ghosts.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError objects, one for each generated parameter that is absent from the M1 signature; empty if no
        such parameters are found.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.signature is None:
        return []

    m1_names = {
        parameter.name
        for parameter in request.function_record.signature.parameters
        if implicit_receiver_exclusion_reason(
            parameter_name=parameter.name,
            method_kind=request.function_record.method_kind,
        )
        is None
    }
    m2_names = list(dict.fromkeys(parameter.name for parameter in request.generated_docstring.parameters))

    return [
        VerificationError(
            error_type=VerificationErrorType.PARAMETER_GHOST,
            section="Parameters",
            granularity=PatchGranularity.ENTRY,
            detail=f"parameter '{parameter_name}' is absent from the signature",
            parameter_name=parameter_name,
            observed=parameter_name,
            dmt_code=DMT_2002,
        )
        for parameter_name in m2_names
        if parameter_name not in m1_names
    ]


def verify_order_parameters(request: VerificationRequest) -> list[VerificationError]:
    """Return an error if generated parameter order differs from the M1 signature.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the function record and generated docstring to check.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError objects. The list is empty when the generated parameter order matches the M1 signature;
        otherwise it contains a single VerificationError describing the parameter order mismatch.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.signature is None:
        return []

    m1_names = [
        parameter.name
        for parameter in request.function_record.signature.parameters
        if implicit_receiver_exclusion_reason(
            parameter_name=parameter.name,
            method_kind=request.function_record.method_kind,
        )
        is None
    ]
    m2_names = [parameter.name for parameter in request.generated_docstring.parameters]

    common_names = set(m1_names) & set(m2_names)
    expected_order = [name for name in m1_names if name in common_names]
    documented_order = [name for name in m2_names if name in common_names]

    if expected_order == documented_order:
        return []

    return [
        VerificationError(
            error_type=VerificationErrorType.PARAMETER_ORDER_WRONG,
            section="Parameters",
            granularity=PatchGranularity.SECTION,
            detail=f"expected order: {expected_order}, documented: {documented_order}",
            expected=", ".join(expected_order),
            observed=", ".join(documented_order),
            dmt_code=DMT_2003,
        )
    ]
