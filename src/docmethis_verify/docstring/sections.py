# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Shared registry of NumPy docstring sections."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "NUMPY_SECTION_ALIASES",
    "NUMPY_SECTION_ORDER",
    "NUMPY_SECTION_TITLES",
    "canonicalize_numpy_section_title",
    "find_numpy_section_underline_index",
    "is_numpy_section_underline",
    "numpy_section_title_from_line",
]


NUMPY_SECTION_ORDER: tuple[str, ...] = (
    "Parameters",
    "Other Parameters",
    "Returns",
    "Yields",
    "Raises",
    "Warnings",
    "See Also",
    "Notes",
    "References",
    "Examples",
    "Attributes",
    "Methods",
)
"""Canonical order used by the project's NumPy tools.

``Warnings`` is the selected canonical title. ``Warns`` is accepted as an alias,
but is not emitted as a canonical title.
"""

NUMPY_SECTION_TITLES: frozenset[str] = frozenset(NUMPY_SECTION_ORDER)
"""Recognized canonical NumPy section titles."""

NUMPY_SECTION_ALIASES: dict[str, str] = {
    "Parameter": "Parameters",
    "Param": "Parameters",
    "Params": "Parameters",
    "Arguments": "Parameters",
    "Args": "Parameters",
    "Paramètre": "Parameters",
    "Paramètres": "Parameters",
    "Parametre": "Parameters",
    "Parametres": "Parameters",
    "Argument": "Parameters",
    "Other Parameter": "Other Parameters",
    "Other Params": "Other Parameters",
    "Other": "Other Parameters",
    "Others": "Other Parameters",
    "Return": "Returns",
    "Retour": "Returns",
    "Retourne": "Returns",
    "Retours": "Returns",
    "Yield": "Yields",
    "Raise": "Raises",
    "Lève": "Raises",
    "Leve": "Raises",
    "Error": "Raises",
    "Errors": "Raises",
    "Erreur": "Raises",
    "Erreurs": "Raises",
    "Exception": "Raises",
    "Exceptions": "Raises",
    "Warn": "Warnings",
    "Warns": "Warnings",
    "Warning": "Warnings",
    "Avertissement": "Warnings",
    "Avertissements": "Warnings",
    "Attention": "Warnings",
    "Voir aussi": "See Also",
    "Voir": "See Also",
    "Voiraussi": "See Also",
    "Note": "Notes",
    "Reference": "References",
    "Example": "Examples",
    "Exemple": "Examples",
    "Exemples": "Examples",
    "Attribute": "Attributes",
    "Attribut": "Attributes",
    "Attributs": "Attributes",
    "Method": "Methods",
    "Méthode": "Methods",
    "Méthodes": "Methods",
    "Methode": "Methods",
    "Methodes": "Methods",
}
"""Accepted aliases for canonical NumPy titles."""


def canonicalize_numpy_section_title(title: str) -> str | None:
    """Return the canonical title for a raw NumPy section, or ``None``.

    Comparison is intentionally tolerant of case and repeated whitespace so generators can be normalized before validation.

    Parameters
    ----------
    title : str
        The raw NumPy section title to canonicalize.

    Returns
    -------
    str | None
        The canonical title for a raw NumPy section, or None if the normalized title is empty or not recognized.

    """
    normalized_title = _normalize_title(title)
    if not normalized_title:
        return None
    return _SECTIONS_BY_NORMALIZED_TITLE.get(normalized_title)


def numpy_section_title_from_line(line: str) -> str | None:
    """Return the canonical title of a NumPy section carried by a line.

    Parameters
    ----------
    line : str
        The line of text to inspect for a NumPy section title.

    Returns
    -------
    str | None
        The canonical title of the NumPy section if the line contains a recognized section title, otherwise None.

    """
    title = line.strip()
    canonical = canonicalize_numpy_section_title(title)
    if canonical is not None:
        return canonical

    if title.endswith(":"):
        return canonicalize_numpy_section_title(title[:-1])
    return None


def is_numpy_section_underline(line: str, *, strict: bool = False) -> bool:
    """Indicate whether a line is a NumPy section underline.

    Parameters
    ----------
    line : str
        The line to inspect for a NumPy section underline.
    strict : bool = False
        When True, require the line to consist solely of hyphen characters with no leading or trailing whitespace; when False (the
        default), allow equals signs and tildes and ignore surrounding whitespace.

    Returns
    -------
    bool
        Indicate whether a line is a NumPy section underline. In strict mode, the line must be non-empty and consist solely of
        hyphens. In non-strict mode, whitespace is ignored and the stripped line must be non-empty and contain only hyphen,
        equals, or tilde characters.

    """
    if strict:
        return bool(line) and set(line) == {"-"}

    text = line.strip()
    return bool(text) and set(text) <= {"-", "=", "~"}


def find_numpy_section_underline_index(lines: Sequence[str], index: int) -> int | None:
    """Find a direct NumPy section underline or one separated by blank lines.

    Parameters
    ----------
    lines : Sequence[str]
        The sequence of text lines to search for a NumPy section underline.
    index : int
        Index in the sequence of lines at which to start searching for a NumPy section underline.

    Returns
    -------
    int | None
        Returns the index of the NumPy section underline line if found, either immediately at the given position or after skipping
        blank lines; otherwise returns None.

    """
    cursor = index
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    if cursor < len(lines) and is_numpy_section_underline(lines[cursor]):
        return cursor
    return None


def _normalize_title(title: str) -> str:
    """Normalize a section title for comparison.

    Parameters
    ----------
    title : str
        The section title to normalize.

    Returns
    -------
    str
        The normalized section title as a string, with leading and trailing whitespace removed, internal whitespace collapsed to
        single spaces, and all characters converted to lowercase via casefolding.

    """
    return " ".join(title.strip().split()).casefold()


_SECTIONS_BY_NORMALIZED_TITLE = {
    **{_normalize_title(title): title for title in NUMPY_SECTION_TITLES},
    **{_normalize_title(alias): canonical for alias, canonical in NUMPY_SECTION_ALIASES.items()},
}
