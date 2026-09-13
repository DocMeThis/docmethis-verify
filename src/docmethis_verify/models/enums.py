# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Closed enumerations used by deterministic verification."""

from enum import Enum, StrEnum


class PatchGranularity(StrEnum):
    """Granularity of a patch applied to a docstring.

    Attributes
    ----------
    SECTION : str
        Patch applied to a whole section.
    SPAN : str
        Patch applied to a span within a section.
    ENTRY : str
        Patch applied to a single entry.

    """

    SECTION = "section"
    SPAN = "span"
    ENTRY = "entry"


class VerificationErrorType(Enum):
    """Types of structured verification errors produced by deterministic verification.

    Attributes
    ----------
    PARAMETER_MISSING : str
        A parameter is undocumented.
    PARAMETER_GHOST : str
        A documented parameter is absent from the signature.
    PARAMETER_ORDER_WRONG : str
        Documented parameters are in the wrong order.
    PARAMETER_TYPE_MISSING : str
        A parameter type is missing from the docstring.
    RETURNS_TYPE_MISSING : str
        The return type is missing from the docstring.
    RAISES_GHOST : str
        A documented exception has no detected raise source.
    RAISES_MISSING : str
        A raised exception is undocumented.
    FORBIDDEN_TERM : str
        A forbidden term appears in the docstring.

    """

    PARAMETER_MISSING = "ParameterMissing"
    PARAMETER_GHOST = "ParameterGhost"
    PARAMETER_ORDER_WRONG = "ParameterOrderWrong"
    PARAMETER_TYPE_MISSING = "ParameterTypeMissing"
    RETURNS_TYPE_MISSING = "ReturnsTypeMissing"
    RAISES_GHOST = "RaisesGhost"
    RAISES_MISSING = "RaisesMissing"
    FORBIDDEN_TERM = "ForbiddenTerm"
