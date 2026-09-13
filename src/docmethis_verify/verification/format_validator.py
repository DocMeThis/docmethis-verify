# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Validate NumPy docstring formatting and report malformed sections."""

import ast
from collections.abc import Sequence
from textwrap import dedent

from docmethis_verify.docstring.numpy_parser import NumpyDocstring, parse_numpy_docstring
from docmethis_verify.docstring.sections import (
    NUMPY_SECTION_ORDER,
    NUMPY_SECTION_TITLES,
    canonicalize_numpy_section_title,
    numpy_section_title_from_line,
)
from docmethis_verify.models.format_warning import FormatWarning, FormatWarningSpan


def _make_format_warning(  # noqa: PLR0913 - published warning fields stay explicit.
    section: str,
    kind: str,
    detail: str,
    *,
    line: int | None = None,
    discriminator: str | None = None,
    expected: str | None = None,
    span: FormatWarningSpan | None = None,
) -> FormatWarning:
    """Creates and returns a FormatWarning instance with the specified section, kind, detail, line, and discriminator.

    Parameters
    ----------
    section : str
        The documentation section (e.g., 'Parameters', 'Returns') in which the format issue was detected.
    kind : str
        The category or type of format warning being created.
    detail : str
        A string containing specific details about the format issue being reported.
    line : int | None = None
        Line number in the source document associated with the format warning, if applicable.
    discriminator : str | None = None
        Optional discriminator to differentiate warnings that would otherwise have identical section, kind, and detail.
    expected : str | None = None
        Structured expected value used by deterministic consumers, when known.
    span : FormatWarningSpan | None = None
        Warning-local half-open character bounds in the normalized docstring body, when known.

    Returns
    -------
    FormatWarning
        A FormatWarning instance constructed from the given section, kind, detail, line, and discriminator.

    """
    return FormatWarning(
        section=section,
        kind=kind,
        detail=detail,
        line=line,
        discriminator=discriminator,
        expected=expected,
        span=span,
    )


_MIN_SECTION_TYPO_LENGTH = 5

# Minimum number of words for an exception line to contain a description after
# the colon ("ValueError: reason" versus "ValueError:").
_MIN_DESCRIPTION_WORDS = 2


def _exception_name(line: str) -> str:
    """Return the first token of an exception line without its trailing colon.

    ``"ValueError: reason"`` and ``"ValueError : reason"`` produce the same ``"ValueError"`` name for a stable discriminator.

    Parameters
    ----------
    line : str
        The exception line from which to extract the exception name. It may include a reason after a colon, with optional
        whitespace before the colon.

    Returns
    -------
    str
        The exception name as a string, consisting of the first whitespace-separated token of the input line with any trailing
        colon removed.

    """
    first_token = line.split(maxsplit=1)[0] if line.split() else line
    return first_token.removesuffix(":")


_MAX_DIFFERENCES_PERMUTATION = 3


def validate_docstring_format(docstring: str) -> list[FormatWarning]:
    """Validate the format of a complete NumPy docstring.

    Parameters
    ----------
    docstring : str
        The complete NumPy docstring text to be validated.

    Returns
    -------
    list[FormatWarning]
        A list of FormatWarning objects describing format issues found in the docstring. An empty list indicates that no format
        problems were detected.

    """
    if not docstring or not docstring.strip():
        return []

    normalized_docstring = dedent(docstring)
    raw_lines = normalized_docstring.splitlines()
    parsed = parse_numpy_docstring(docstring)
    return _validate_from_parsed(raw_lines, parsed, line_spans=_line_spans(normalized_docstring))


def _validate_from_parsed(
    raw_lines: list[str],
    parsed: NumpyDocstring,
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validates a parsed NumPy docstring against formatting rules and returns a list of format warnings.

    Parameters
    ----------
    raw_lines : list[str]
        A list of strings containing the unmodified lines of the docstring being validated.
    parsed : NumpyDocstring
        The parsed NumpyDocstring object containing the structured sections of the docstring to be validated.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the physical lines in ``raw_lines``, when already computed.

    Returns
    -------
    list[FormatWarning]
        A list of FormatWarning objects representing all formatting issues found during validation. If the docstring is
        well-formed, the list is empty.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or _line_spans("\n".join(raw_lines)))
    warnings.extend(_validate_headings(raw_lines, line_spans=spans))
    warnings.extend(_validate_section_order(parsed, raw_lines=raw_lines, line_spans=spans))
    warnings.extend(_validate_blank_lines_between_sections(raw_lines, line_spans=spans))
    parameters, parameter_spans = _section_lines(raw_lines, spans, section="Parameters")
    returns, return_spans = _section_lines(raw_lines, spans, section="Returns")
    raises, raises_spans = _section_lines(raw_lines, spans, section="Raises")
    warnings.extend(_validate_parameters_section(parameters or parsed.parameters, line_spans=parameter_spans))
    warnings.extend(_validate_returns_section(returns or parsed.returns, line_spans=return_spans))
    warnings.extend(_validate_raises_section(raises or parsed.raises, line_spans=raises_spans))

    if not parsed.summary and parsed.sections:
        first_section = next((span for _title, span in _section_headers(raw_lines, spans)), None)
        insertion_span = None if first_section is None else FormatWarningSpan(first_section.start, first_section.start)
        warnings.append(_make_format_warning("Summary", "empty_summary", "empty summary", span=insertion_span))

    return warnings


def _line_spans(text: str) -> tuple[FormatWarningSpan, ...]:
    """Return character bounds for each physical line in ``text``."""
    spans: list[FormatWarningSpan] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        spans.append(FormatWarningSpan(offset, offset + len(content)))
        offset += len(line)
    if offset < len(text):
        spans.append(FormatWarningSpan(offset, len(text)))
    return tuple(spans)


def _section_headers(
    raw_lines: Sequence[str],
    line_spans: Sequence[FormatWarningSpan],
) -> tuple[tuple[str, FormatWarningSpan], ...]:
    """Return strict heading titles and their complete header spans."""
    headers: list[tuple[str, FormatWarningSpan]] = []
    for index in range(len(raw_lines) - 1):
        heading = _detect_heading_at(list(raw_lines), index)
        if heading is None or index + 1 >= len(line_spans):
            continue
        title, _underline = heading
        end = line_spans[index + 1].end
        headers.append((title, FormatWarningSpan(line_spans[index].start, end)))
    return tuple(headers)


def _section_lines(
    raw_lines: Sequence[str],
    line_spans: Sequence[FormatWarningSpan],
    *,
    section: str,
) -> tuple[tuple[str, ...], tuple[FormatWarningSpan, ...]]:
    """Return raw content lines and source spans for one canonical section."""
    headers: list[tuple[int, str]] = []
    for index in range(len(raw_lines) - 1):
        heading = _detect_heading_at(list(raw_lines), index)
        if heading is None:
            continue
        canonical = numpy_section_title_from_line(heading[0])
        if canonical == section:
            headers.append((index, canonical))
    if not headers:
        return (), ()
    start = headers[0][0] + 2
    end = len(raw_lines)
    for index in range(start, len(raw_lines) - 1):
        if _detect_heading_at(list(raw_lines), index) is not None:
            end = index
            break
    return tuple(raw_lines[start:end]), tuple(line_spans[start:end])


def _detect_heading_at(lines: list[str], i: int) -> tuple[str, str] | None:
    """Detect a markdown-style heading at a given line index by checking if the next line consists solely of dashes.

    Parameters
    ----------
    lines : list[str]
        The sequence of text lines in which to detect a heading at the given position.
    i : int
        Zero-based index of the line in `lines` to inspect as a potential heading title.

    Returns
    -------
    tuple[str, str] | None
        A tuple (title, underline) if the line at index i is a heading (the next line is a non-empty dash-only underline),
        otherwise None.

    """
    if i + 1 >= len(lines):
        return None
    title = lines[i].strip()
    underline = lines[i + 1].strip()
    if title and underline and set(underline) <= {"-"}:
        return title, underline
    return None


def _validate_headings(
    raw_lines: list[str],
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validate heading formatting and section names in raw docstring lines, returning a list of format warnings.

    Parameters
    ----------
    raw_lines : list[str]
        The raw lines of the document or source text to be validated for heading formatting.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the physical lines in ``raw_lines``, when already computed.

    Returns
    -------
    list[FormatWarning]
        Validates heading lines in raw source lines for NumPy docstring format compliance, returning a list of FormatWarning
        objects for any detected issues such as incorrect underline lengths, misspelled section titles, or unknown section
        headings.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or _line_spans("\n".join(raw_lines)))
    for i in range(len(raw_lines) - 1):
        heading = _detect_heading_at(raw_lines, i)
        if heading is None:
            continue
        title, underline = heading
        title_span = spans[i] if i < len(spans) else None
        underline_span = spans[i + 1] if i + 1 < len(spans) else None

        if len(underline) != len(title):
            warnings.append(
                _make_format_warning(
                    title,
                    "underline_length",
                    f"underline length {len(underline)} for a title of {len(title)} characters",
                    line=i + 1,
                    span=underline_span,
                )
            )

        correction = section_canonical_probable(title)
        if correction is not None and correction != title:
            warnings.append(
                _make_format_warning(
                    title,
                    "misspelled_section",
                    f"section '{title}' should be '{correction}'",
                    line=i + 1,
                    span=title_span,
                )
            )
        elif correction not in NUMPY_SECTION_TITLES:
            warnings.append(
                _make_format_warning(
                    title,
                    "unknown_section",
                    f"unknown section '{title}' in NumPy format",
                    line=i + 1,
                    span=title_span,
                )
            )

    return warnings


def section_canonical_probable(title: str) -> str | None:
    """Return the probable canonical NumPy section for a detected title.

    Parameters
    ----------
    title : str
        The title string of a section as detected in a docstring, used to determine the corresponding canonical NumPy section
        name.

    Returns
    -------
    str | None
        The probable canonical NumPy section title, or None if no probable canonical section can be determined.

    """
    correction = canonicalize_numpy_section_title(title)
    if correction is not None:
        return correction

    normalized_title = _normalize_title_typo(title)
    if len(normalized_title.replace(" ", "")) < _MIN_SECTION_TYPO_LENGTH:
        return None

    candidates = [section for section in NUMPY_SECTION_ORDER if _is_probable_typo(title, section)]
    if len(candidates) == 1:
        return candidates[0]

    return None


def _normalize_title_typo(title: str) -> str:
    """Normalize a section title for conservative typo comparison.

    Parameters
    ----------
    title : str
        The section title to be normalized.

    Returns
    -------
    str
        The normalized section title with leading and trailing whitespace removed, converted to lowercase for case-insensitive
        comparison, stripped of a trailing colon if present, and internal whitespace collapsed into single spaces.

    """
    return " ".join(title.strip().casefold().removesuffix(":").split())


def _is_probable_typo(source: str, target: str) -> bool:
    """Return whether a title differs from a canonical section by a simple typo.

    Parameters
    ----------
    source : str
        The title to examine for a probable typo relative to the target canonical section.
    target : str
        The canonical section title to compare against the source string.

    Returns
    -------
    bool
        True if the source title is considered a probable typo of the target canonical section; False otherwise.

    """
    normalized_source = _normalize_title_typo(source)
    normalized_target = _normalize_title_typo(target)

    if normalized_source == normalized_target:
        return True

    if abs(len(normalized_source) - len(normalized_target)) > 1:
        return False

    if len(normalized_source) == len(normalized_target):
        return _single_substitution_or_local_permutation(normalized_source, normalized_target)

    shorter, longer = (
        (normalized_source, normalized_target)
        if len(normalized_source) < len(normalized_target)
        else (normalized_target, normalized_source)
    )
    return _single_insertion_or_deletion(shorter, longer)


def _single_substitution_or_local_permutation(source: str, target: str) -> bool:
    """Test one substitution or a bounded local permutation.

    Parameters
    ----------
    source : str
        The original string to compare against target; it is checked for either a single differing character or a bounded local
        permutation of characters at differing positions.
    target : str
        The candidate string that is checked against source for a single substitution or a bounded local permutation.

    Returns
    -------
    bool
        Return True if the target string differs from the source string by exactly one substitution or by a bounded local
        permutation of differing characters; otherwise return False.

    """
    differences = [index for index, (a, b) in enumerate(zip(source, target, strict=True)) if a != b]
    if len(differences) == 1:
        return True

    if len(differences) > _MAX_DIFFERENCES_PERMUTATION:
        return False

    return sorted(source[index] for index in differences) == sorted(target[index] for index in differences)


def _single_insertion_or_deletion(shorter: str, longer: str) -> bool:
    """Test one insertion or deletion between two normalized strings.

    Parameters
    ----------
    shorter : str
        The shorter of the two normalized strings to compare.
    longer : str
        The string that is expected to be longer than the other input; the function tests whether removing exactly one character
        from this string produces the shorter string.

    Returns
    -------
    bool
        True if the shorter string can be obtained by removing exactly one character from the longer string, indicating the two
        normalized strings differ by a single insertion or deletion; False otherwise.

    """
    return any(longer[:index] + longer[index + 1 :] == shorter for index in range(len(longer)))


def _validate_blank_lines_between_sections(
    raw_lines: list[str],
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Detects missing blank lines before section headings in raw documentation lines.

    Parameters
    ----------
    raw_lines : list[str]
        The raw lines of the source document to validate, used to detect section headings and check for missing blank lines
        between sections.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the physical lines in ``raw_lines``, when already computed.

    Returns
    -------
    list[FormatWarning]
        A list of FormatWarning objects, each representing a detected formatting issue related to missing blank lines between
        sections.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or _line_spans("\n".join(raw_lines)))
    next_line_after_previous_underline = -1
    for i in range(len(raw_lines) - 1):
        heading = _detect_heading_at(raw_lines, i)
        if heading is None:
            continue
        title = heading[0]
        if next_line_after_previous_underline >= 0 and i - next_line_after_previous_underline < 1:
            insertion = spans[i].start if i < len(spans) else None
            warnings.append(
                _make_format_warning(
                    title,
                    "missing_blank_line",
                    "missing blank line before section",
                    line=i + 1,
                    span=None if insertion is None else FormatWarningSpan(insertion, insertion),
                )
            )
        next_line_after_previous_underline = i + 2
    return warnings


def _validate_section_order(
    parsed: NumpyDocstring,
    *,
    raw_lines: Sequence[str] | None = None,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validate that the sections in a parsed NumPy docstring appear in the conventional order.

    Parameters
    ----------
    parsed : NumpyDocstring
        The parsed NumpyDocstring object whose sections are examined to validate their ordering against the conventional NumPy
        section order.
    raw_lines : Sequence[str] | None = None
        Raw physical lines used to calculate the warning span, when available.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for ``raw_lines``, when available.

    Returns
    -------
    list[FormatWarning]
        Return a list of FormatWarning objects indicating any problems found in the order of NumPy docstring sections. The list is
        empty when the section order conforms to the expected canonical order.

    """
    warnings: list[FormatWarning] = []
    actual = [canonical for name in parsed.sections if (canonical := canonicalize_numpy_section_title(name)) is not None]
    expected = [section for section in NUMPY_SECTION_ORDER if section in actual]
    if actual != expected:
        spans = tuple(line_spans or ())
        headers = _section_headers(raw_lines or (), spans) if raw_lines is not None else ()
        order_span = None
        if headers and spans:
            order_span = FormatWarningSpan(headers[0][1].start, spans[-1].end)
        warnings.append(
            _make_format_warning(
                "general",
                "section_order",
                f"non-conventional order: expected {expected}, found {actual}",
                expected=", ".join(expected),
                span=order_span,
            )
        )
    return warnings


def _validate_parameters_section(
    lines: Sequence[str],
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validates the formatting of a docstring Parameters section and returns a list of format warnings.

    Parameters
    ----------
    lines : Sequence[str]
        A sequence of strings representing the lines of the Parameters section to validate.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the supplied section lines, when available.

    Returns
    -------
    list[FormatWarning]
        Validates the lines of a parameters section and returns a list of FormatWarning objects for any formatting issues found.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or ())
    prev_indent: int | None = None
    current_parameter: str | None = None

    for line_index, line in enumerate(lines):
        span = spans[line_index] if line_index < len(spans) else None
        stripped = line.strip()
        if not stripped:
            prev_indent = None
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0:
            if ":" not in stripped:
                current_parameter = stripped
                warnings.append(
                    _make_format_warning(
                        "Parameters",
                        "param_missing_colon",
                        f"parameter '{stripped}' missing ' : type'",
                        discriminator=stripped,
                        span=span,
                    )
                )
            else:
                colon_idx = stripped.index(":")
                name_part = stripped[:colon_idx].strip()
                type_part = stripped[colon_idx + 1 :].strip()

                if not name_part:
                    warnings.append(
                        _make_format_warning(
                            "Parameters",
                            "param_empty_name",
                            "empty parameter name before ':'",
                            span=span,
                        )
                    )

                has_space_before = colon_idx > 0 and stripped[colon_idx - 1] == " "
                has_space_after = colon_idx + 1 < len(stripped) and stripped[colon_idx + 1] == " "

                if not has_space_before or not has_space_after:
                    warnings.append(
                        _make_format_warning(
                            "Parameters",
                            "param_colon_spacing",
                            f"incorrect spacing around ':' in '{stripped}'",
                            discriminator=name_part,
                            span=span,
                        )
                    )

                if not type_part:
                    warnings.append(
                        _make_format_warning(
                            "Parameters",
                            "param_missing_type",
                            f"parameter '{name_part}' declared without a type",
                            discriminator=name_part,
                            span=span,
                        )
                    )

                current_parameter = name_part or stripped

            prev_indent = None
        else:
            if prev_indent is not None and indent != prev_indent:
                warnings.append(
                    _make_format_warning(
                        "Parameters",
                        "inconsistent_indentation",
                        f"inconsistent indentation in description (line: {stripped[:50]})",
                        discriminator=current_parameter,
                        span=span,
                    )
                )
            prev_indent = indent

    return warnings


def _validate_returns_section(
    lines: Sequence[str],
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validate the Returns section of a docstring for formatting issues and return a list of warnings.

    Parameters
    ----------
    lines : Sequence[str]
        Lines of the returns section to validate, with each element representing one line of the docstring.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the supplied section lines, when available.

    Returns
    -------
    list[FormatWarning]
        A list of FormatWarning instances representing detected formatting problems in the given returns section lines. An empty
        list indicates no issues were found.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or ())
    non_blank = [(index, line.strip()) for index, line in enumerate(lines) if line.strip()]

    if not non_blank:
        return warnings

    if len(non_blank) > 1:
        first_index, first = non_blank[0]
        if first[0].islower() and " " in first.strip() and not _looks_like_type_expression(first):
            warnings.append(
                _make_format_warning(
                    "Returns",
                    "return_type_and_desc_inverted",
                    f"first line '{first[:50]}' appears to be a description, not a type",
                    span=spans[first_index] if first_index < len(spans) else None,
                )
            )

    return warnings


def _looks_like_type_expression(value: str) -> bool:
    """Return whether a Returns first line is syntactically type-like.

    Parameters
    ----------
    value : str
        The string to check for type-expression syntax.

    Returns
    -------
    bool
        True if the input string can be parsed as a valid type expression, False otherwise.

    """
    try:
        ast.parse(value, mode="eval")
    except (SyntaxError, ValueError):
        return False
    return True


def _validate_raises_section(
    lines: Sequence[str],
    *,
    line_spans: Sequence[FormatWarningSpan] | None = None,
) -> list[FormatWarning]:
    """Validate the format of a Raises section by checking exception names and descriptions for common issues.

    Parameters
    ----------
    lines : Sequence[str]
        A sequence of strings containing the lines of the 'Raises' section to be validated.
    line_spans : Sequence[FormatWarningSpan] | None = None
        Character bounds for the supplied section lines, when available.

    Returns
    -------
    list[FormatWarning]
        A list of FormatWarning objects describing formatting problems found while validating the Raises section, or an empty list
        if no problems are detected.

    """
    warnings: list[FormatWarning] = []
    spans = tuple(line_spans or ())
    current_exception = ""
    current_exception_span: FormatWarningSpan | None = None
    has_description = False

    for line_index, line in enumerate(lines):
        span = spans[line_index] if line_index < len(spans) else None
        stripped = line.strip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())
        if indent == 0:
            if current_exception and not has_description:
                warnings.append(
                    _make_format_warning(
                        "Raises",
                        "raises_missing_description",
                        f"exception '{current_exception}' without a description",
                        discriminator=_exception_name(current_exception),
                        span=current_exception_span,
                    )
                )

            current_exception = stripped
            current_exception_span = span
            has_description = False

            words = stripped.split()
            description_same_line = (len(words) > 1 and words[1][0].islower()) or (
                len(words) > _MIN_DESCRIPTION_WORDS and words[1] == ":"
            )
            if words and words[0][0].isupper() and description_same_line:
                warnings.append(
                    _make_format_warning(
                        "Raises",
                        "raises_type_and_desc_on_same_line",
                        f"type '{words[0]}' and description on the same line",
                        discriminator=_exception_name(stripped),
                        span=span,
                    )
                )
                has_description = True

            if current_exception and current_exception[0].islower():
                warnings.append(
                    _make_format_warning(
                        "Raises",
                        "raises_invalid_name",
                        f"exception name '{current_exception}' should start with an uppercase letter",
                        discriminator=_exception_name(current_exception),
                        span=span,
                    )
                )
        else:
            has_description = True

    if current_exception and not has_description:
        warnings.append(
            _make_format_warning(
                "Raises",
                "raises_missing_description",
                f"exception '{current_exception}' without a description",
                discriminator=_exception_name(current_exception),
                span=current_exception_span,
            )
        )

    return warnings
