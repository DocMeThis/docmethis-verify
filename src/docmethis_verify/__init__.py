# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Public API for deterministic docstring verification."""

from docmethis_verify.models import (
    FormatWarning,
    FormatWarningSpan,
    PatchGranularity,
    VerificationError,
    VerificationErrorType,
    VerificationRequest,
    VerificationResponse,
)
from docmethis_verify.return_annotations import ReturnAnnotationKind, classify_return_annotation

__all__ = [
    "FormatWarning",
    "FormatWarningSpan",
    "PatchGranularity",
    "ReturnAnnotationKind",
    "VerificationError",
    "VerificationErrorType",
    "VerificationRequest",
    "VerificationResponse",
    "classify_return_annotation",
]
