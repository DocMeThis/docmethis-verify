# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Type verifiers for deterministic verification."""

from docmethis_extract_python.api import Confidence, FunctionRecord, NormalReturnStatus

from docmethis_verify.dmt import DMT_2120, DMT_3010
from docmethis_verify.models.contracts import VerificationError, VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType
from docmethis_verify.return_annotations import ReturnAnnotationKind, classify_return_annotation

__all__ = ["verify_type_return_missing", "verify_types_parameters_missing"]


def verify_types_parameters_missing(request: VerificationRequest) -> list[VerificationError]:
    """Return errors for generated parameters whose explicit M1 type is undocumented.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the function record and generated docstring to inspect for missing parameter type
        documentation.

    Returns
    -------
    list[VerificationError]
        A list of VerificationError objects for each generated parameter whose explicit M1 type is not documented; empty if none
        are missing.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.types is None:
        return []

    errors: list[VerificationError] = []
    for parameter in request.generated_docstring.parameters:
        type_info = request.function_record.types.parameters.get(parameter.name)
        if type_info is None:
            continue

        if type_info.confidence is not Confidence.EXPLICIT:
            continue

        if parameter.annotation is None:
            errors.append(
                VerificationError(
                    error_type=VerificationErrorType.PARAMETER_TYPE_MISSING,
                    section="Parameters",
                    granularity=PatchGranularity.SPAN,
                    detail=f"parameter '{parameter.name}': type '{type_info.type_str}' is not documented",
                    parameter_name=parameter.name,
                    expected=type_info.type_str,
                    dmt_code=DMT_2120,
                )
            )

    return errors


def verify_type_return_missing(request: VerificationRequest) -> list[VerificationError]:
    """Return an error when an explicit M1 return type is undocumented in Returns.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the generated docstring and function record to check for an undocumented explicit
        return type.

    Returns
    -------
    list[VerificationError]
        Returns a list of VerificationError objects. The list is empty when the generated docstring has no Returns section, when
        the function record is not a FunctionRecord or has no type information, when no normal return is possible, when the
        annotation resolves to None/Never/NoReturn, when the recorded return type is absent or not explicitly confident, or when
        the generated docstring already documents a return annotation. Unresolved annotations retain the existing type check.

    """
    if request.generated_docstring.returns is None:
        return []

    if (
        not isinstance(request.function_record, FunctionRecord)
        or request.function_record.types is None
        or request.function_record.normal_return_status is NormalReturnStatus.PROVEN_ABSENT
    ):
        return []

    return_type = request.function_record.types.return_type
    if return_type is None:
        return []

    if return_type.confidence is not Confidence.EXPLICIT or request.generated_docstring.returns.annotation is not None:
        return []

    signature = request.function_record.signature
    annotation = signature.return_annotation if signature is not None else return_type.raw or return_type.type_str
    if classify_return_annotation(annotation, module=request.module_record) in {
        ReturnAnnotationKind.NONE,
        ReturnAnnotationKind.NO_RETURN,
    }:
        return []

    return [
        VerificationError(
            error_type=VerificationErrorType.RETURNS_TYPE_MISSING,
            section="Returns",
            granularity=PatchGranularity.SPAN,
            detail=f"return: type '{return_type.type_str}' is not documented",
            expected=return_type.type_str,
            dmt_code=DMT_3010,
        )
    ]
