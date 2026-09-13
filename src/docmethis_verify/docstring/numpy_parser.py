# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Minimal parser and writer for the NumPy docstring format."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from textwrap import dedent
from types import MappingProxyType

from docmethis_verify.docstring.sections import is_numpy_section_underline
from docmethis_verify.docstring.text_lines import trim_outer_blank_lines


@dataclass(kw_only=True, slots=True, frozen=True)
class NumpyDocstring:
    """Simple representation of a NumPy docstring.

    Attributes
    ----------
    summary : str
        Summary text of the docstring.
    sections : Mapping[str, tuple[str, ...]]
        Mapping of section title to its lines, read-only.

    """

    summary: str = ""
    sections: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze sections to prevent mutations after parsing."""
        normalized_sections = {title: tuple(lines) for title, lines in self.sections.items()}
        # Insertion order is preserved by Python 3.7+ dictionaries.
        object.__setattr__(self, "sections", MappingProxyType(normalized_sections))

    @property
    def parameters(self) -> tuple[str, ...]:
        """Return the contents of the Parameters section.

        Returns
        -------
        tuple[str, ...]
            A tuple of strings containing the lines of the Parameters section.

        """
        return self.sections.get("Parameters", ())

    @property
    def returns(self) -> tuple[str, ...]:
        """Return the contents of the Returns section.

        Returns
        -------
        tuple[str, ...]
            The contents of the Returns section as a tuple of strings.

        """
        return self.sections.get("Returns", ())

    @property
    def raises(self) -> tuple[str, ...]:
        """Return the contents of the Raises section.

        Returns
        -------
        tuple[str, ...]
            The contents of the Raises section as a tuple of strings.

        """
        return self.sections.get("Raises", ())

    @property
    def notes(self) -> tuple[str, ...]:
        """Return the contents of the Notes section.

        Returns
        -------
        tuple[str, ...]
            A tuple of strings containing the lines from the Notes section, or an empty tuple if no Notes section is present.

        """
        return self.sections.get("Notes", ())

    @property
    def examples(self) -> tuple[str, ...]:
        """Return the contents of the Examples section.

        Returns
        -------
        tuple[str, ...]
            A tuple of strings containing the lines of the Examples section.

        """
        return self.sections.get("Examples", ())

    @property
    def attributes(self) -> tuple[str, ...]:
        """Return the contents of the Attributes section.

        Returns
        -------
        tuple[str, ...]
            A tuple of strings containing the contents of the Attributes section, or an empty tuple if the section is not present.

        """
        return self.sections.get("Attributes", ())

    @property
    def see_also(self) -> tuple[str, ...]:
        """Return the contents of the See Also section.

        Returns
        -------
        tuple[str, ...]
            The contents of the See Also section as a tuple of strings.

        """
        return self.sections.get("See Also", ())

    @property
    def warnings(self) -> tuple[str, ...]:
        """Return the contents of the Warnings section.

        Returns
        -------
        tuple[str, ...]
            A tuple of strings containing the contents of the Warnings section.

        """
        return self.sections.get("Warnings", ())

    @property
    def is_empty(self) -> bool:
        """Indicate whether the docstring contains neither a summary nor a section.

        Returns
        -------
        bool
            True if the docstring contains neither a summary nor a section, False otherwise.

        """
        return not self.summary and not self.sections


def parse_numpy_docstring(docstring: str, *, strict_headings: bool = False) -> NumpyDocstring:
    """Parse a NumPy-format docstring into a usable structure.

    Parameters
    ----------
    docstring : str
        The NumPy-format docstring to parse into a structured representation.
    strict_headings : bool = False
        When True, require section headings to follow the strict NumPy docstring heading format; when False, allow more flexible
        heading detection.

    Returns
    -------
    NumpyDocstring
        Returns a NumpyDocstring instance containing the parsed summary and section content from the input NumPy-format docstring.

    """
    normalized_lines = trim_outer_blank_lines([line.rstrip() for line in dedent(docstring).splitlines()])
    if not normalized_lines:
        return NumpyDocstring()

    sections: dict[str, tuple[str, ...]] = {}
    summary_lines: list[str] = []
    current_heading: str | None = None
    current_section: list[str] = []

    line_index = 0
    while line_index < len(normalized_lines):
        heading = _extract_heading(normalized_lines, line_index, strict_headings=strict_headings)

        if heading is not None:
            if current_heading is not None:
                sections[current_heading] = trim_outer_blank_lines(current_section)

            current_heading = heading
            current_section = []

            line_index += 2
            continue

        if current_heading is None:
            summary_lines.append(normalized_lines[line_index])
        else:
            current_section.append(normalized_lines[line_index])

        line_index += 1

    if current_heading is not None:
        sections[current_heading] = trim_outer_blank_lines(current_section)

    return NumpyDocstring(
        summary="\n".join(trim_outer_blank_lines(summary_lines)),
        sections=sections,
    )


def render_numpy_docstring(docstring: NumpyDocstring) -> str:
    """Render a `NumpyDocstring` structure as NumPy text.

    Parameters
    ----------
    docstring : NumpyDocstring
        The NumpyDocstring object containing the structured docstring content to render as NumPy-style text.

    Returns
    -------
    str
        The docstring rendered as a string in NumPy format.

    Raises
    ------
    ValueError
        Explicitly raised.

    """
    rendered_lines: list[str] = []
    summary_lines = trim_outer_blank_lines(docstring.summary.splitlines())
    rendered_lines.extend(summary_lines)

    for title, section_lines in docstring.sections.items():
        normalized_title = title.strip()
        if not normalized_title:
            msg = "A NumPy section title cannot be empty"
            raise ValueError(msg)

        if rendered_lines:
            rendered_lines.append("")

        rendered_lines.append(normalized_title)
        rendered_lines.append("-" * len(normalized_title))
        rendered_lines.extend(trim_outer_blank_lines([line.rstrip() for line in section_lines]))

    return "\n".join(trim_outer_blank_lines(rendered_lines))


def _extract_heading(lines: Sequence[str], line_index: int, *, strict_headings: bool) -> str | None:
    """Detect a NumPy section header from a line index.

    Parameters
    ----------
    lines : Sequence[str]
        The sequence of docstring lines in which to detect a NumPy section header. It is read-only and indexed by line_index; the
        function examines the current line and the following line.
    line_index : int
        Zero-based index into the lines sequence indicating the line to inspect as the potential section heading.
    strict_headings : bool
        When True, requires the section underline to be exactly the same length as the title for a heading to be recognized; when
        False, the heading is accepted even if the underline length differs.

    Returns
    -------
    str | None
        The detected section title, or None if the line at line_index is not followed by a valid NumPy section underline or, when
        strict_headings is True, the underline does not match the title length.

    """
    if line_index + 1 >= len(lines):
        return None

    title = lines[line_index].strip()
    underline = lines[line_index + 1].strip()
    if title and is_numpy_section_underline(underline, strict=True):
        if strict_headings and len(underline) != len(title):
            return None
        return title

    return None
