# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Contract tests for source-anchored format warnings."""

from __future__ import annotations

from docmethis_verify import FormatWarningSpan
from docmethis_verify.verification.format_validator import validate_docstring_format


def test_format_warnings_expose_bounded_spans_and_structured_order() -> None:
    """Every deterministic format warning points into the normalized body."""
    body = """Summary.

Returns
----
int

Parameters
----------
x:int
    Value.
"""

    warnings = validate_docstring_format(body)

    expected = {"underline_length", "section_order", "param_colon_spacing"}
    actual = {warning.kind for warning in warnings}
    assert expected <= actual
    for warning in warnings:
        if warning.kind not in expected:
            continue
        assert isinstance(warning.span, FormatWarningSpan)
        assert 0 <= warning.span.start <= warning.span.end <= len(body)
    order_warning = next(warning for warning in warnings if warning.kind == "section_order")
    assert order_warning.expected == "Parameters, Returns"


def test_format_warning_span_is_public() -> None:
    """The span contract is available from the package root."""
    assert FormatWarningSpan(2, 4).start == 2
