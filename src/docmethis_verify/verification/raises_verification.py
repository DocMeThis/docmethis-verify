# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Raises section verifiers for deterministic verification."""

from docmethis_extract_python.api import ExceptionRecord, FunctionRecord, Provenance, exception_escapes

from docmethis_verify.dmt import DMT_4001, DMT_4002
from docmethis_verify.exception_scope import documentable_exceptions
from docmethis_verify.models.contracts import VerificationError, VerificationRequest
from docmethis_verify.models.enums import PatchGranularity, VerificationErrorType

__all__ = ["verify_raises_ghosts", "verify_raises_missing"]


def _simple_exception_name(exception_name: str) -> str:
    """Return an exception's simple name without its module qualification.

    Known limitation: exceptions from different modules with the same simple name
    (for example, pkg_a.TimeoutError and pkg_b.TimeoutError) are indistinguishable.

    Parameters
    ----------
    exception_name : str
        The exception name to reduce to its simple, unqualified form, typically a fully qualified dotted path such as
        'pkg.mod.ExceptionName'.

    Returns
    -------
    str
        The simple name of the exception, lowercased and without any module qualification.

    """
    return exception_name.rsplit(".", maxsplit=1)[-1].lower()


def verify_raises_ghosts(request: VerificationRequest) -> list[VerificationError]:
    """Return errors for generated exceptions absent from M1 observations.

    Parameters
    ----------
    request : VerificationRequest
        The VerificationRequest instance that supplies the function record and generated docstring needed to identify
        documented exceptions that are not observed.

    Returns
    -------
    list[VerificationError]
        Return errors for generated exceptions absent from M1 observations.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.exceptions is None:
        return []

    m1_names = {
        _simple_exception_name(exception.exception_type)
        for exception in documentable_exceptions(request.function_record, depth=request.exception_documentation_depth)
    }
    seen_ghost_names: set[str] = set()
    errors: list[VerificationError] = []
    observed_names = {
        _simple_exception_name(exception.exception_type)
        for exception in request.function_record.exceptions
        if exception_escapes(request.function_record, exception)
    }
    for documented_raise in request.generated_docstring.raises:
        normalized_name = _simple_exception_name(documented_raise.exception)
        if normalized_name in m1_names or normalized_name in seen_ghost_names:
            continue

        seen_ghost_names.add(normalized_name)
        errors.append(
            VerificationError(
                error_type=VerificationErrorType.RAISES_GHOST,
                section="Raises",
                granularity=PatchGranularity.ENTRY,
                detail=(
                    f"exception '{documented_raise.exception}' is outside the configured documentation depth "
                    f"({request.exception_documentation_depth})"
                    if normalized_name in observed_names
                    else f"exception '{documented_raise.exception}' is documented but not observed"
                ),
                observed=documented_raise.exception,
                dmt_code=DMT_4002,
            )
        )

    return errors


def _missing_exceptions_by_name(
    exceptions: list[ExceptionRecord],
    m2_names: set[str],
) -> list[ExceptionRecord]:
    """Deduplicate missing exceptions while preferring local observations.

    Parameters
    ----------
    exceptions : list[ExceptionRecord]
        The list of exception records to deduplicate by normalized exception name.
    m2_names : set[str]
        Set of exception type names to exclude from the missing exceptions output; any exception whose normalized name is in this
        set is skipped.

    Returns
    -------
    list[ExceptionRecord]
        A list of deduplicated ExceptionRecord objects for the missing exceptions, excluding any exception names present in
        m2_names; when duplicates exist, records with local observation provenance are preferred over callgraph propagation.

    """
    unique_exceptions: dict[str, ExceptionRecord] = {}
    for exception in exceptions:
        normalized_name = _simple_exception_name(exception.exception_type)
        if normalized_name in m2_names:
            continue

        previous = unique_exceptions.get(normalized_name)
        if previous is None or (
            previous.provenance is Provenance.CALLGRAPH_PROPAGATION
            and exception.provenance is not Provenance.CALLGRAPH_PROPAGATION
        ):
            unique_exceptions[normalized_name] = exception

    return list(unique_exceptions.values())


def verify_raises_missing(request: VerificationRequest) -> list[VerificationError]:
    """Return errors for M1 exceptions absent from the generated docstring.

    Parameters
    ----------
    request : VerificationRequest
        The verification request containing the function record and generated docstring used to identify M1 exceptions that are
        missing from the documented raises section.

    Returns
    -------
    list[VerificationError]
        Returns a list of VerificationError objects for exceptions that are present in the function's Raises section but absent
        from the generated docstring. Each error identifies the undocumented exception and includes details such as the exception
        type, provenance, and the DMT code for a missing raises entry.

    """
    if not isinstance(request.function_record, FunctionRecord) or request.function_record.exceptions is None:
        return []

    m2_names = {_simple_exception_name(documented_raise.exception) for documented_raise in request.generated_docstring.raises}
    exposed_exceptions = list(documentable_exceptions(request.function_record, depth=request.exception_documentation_depth))
    missing_exceptions = _missing_exceptions_by_name(exposed_exceptions, m2_names)

    return [
        VerificationError(
            error_type=VerificationErrorType.RAISES_MISSING,
            section="Raises",
            granularity=PatchGranularity.ENTRY,
            detail=f"exception '{exception.exception_type}' is not documented",
            expected=exception.exception_type,
            provenance="propagated" if exception.provenance is Provenance.CALLGRAPH_PROPAGATION else "local",
            dmt_code=DMT_4001,
        )
        for exception in missing_exceptions
    ]
