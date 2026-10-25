# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Shared documentary scope for observed exception facts."""

from docmethis_extract_python.api import ExceptionRecord, FunctionRecord, exception_escapes

from docmethis_verify.validation import dynamic_type_check

__all__ = ["documentable_exceptions"]


def documentable_exceptions(function_record: FunctionRecord, *, depth: int = 1) -> tuple[ExceptionRecord, ...]:
    """Select escaping exception facts within the configured call distance.

    Parameters
    ----------
    function_record : FunctionRecord
        Complete AST facts, kept unchanged by documentary selection.
    depth : int
        Maximum documented call distance. Zero includes local raises only.

    Returns
    -------
    tuple[ExceptionRecord, ...]
        Escaping facts within scope, retaining their original distances and provenance.

    Raises
    ------
    ValueError
        If depth is not a non-negative strict integer.
    """
    dynamic_type_check(value=function_record, expected_type=FunctionRecord, field="function_record")
    if type(depth) is not int or depth < 0:
        message = "exception_documentation_depth must be a non-negative integer."
        raise ValueError(message)
    return tuple(
        exception
        for exception in function_record.exceptions or ()
        if exception.propagation_depth <= depth and exception_escapes(function_record, exception)
    )
