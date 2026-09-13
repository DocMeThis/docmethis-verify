# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for the shared NumPy section registry."""

from __future__ import annotations

from docmethis_verify.docstring.sections import (
    NUMPY_SECTION_ALIASES,
    NUMPY_SECTION_ORDER,
    NUMPY_SECTION_TITLES,
    canonicalize_numpy_section_title,
    is_numpy_section_underline,
)


def test_canonicalize_section_titles_and_aliases() -> None:
    """Canonicalization covers raw titles and tolerated aliases."""
    assert canonicalize_numpy_section_title("parameters") == "Parameters"
    assert canonicalize_numpy_section_title("  See   Also  ") == "See Also"
    assert canonicalize_numpy_section_title("Other Params") == "Other Parameters"
    assert canonicalize_numpy_section_title("Voir aussi") == "See Also"
    assert canonicalize_numpy_section_title("Exemples") == "Examples"
    assert canonicalize_numpy_section_title("unknown section") is None


def test_canonicalize_f2_required_aliases() -> None:
    """Aliases needed by Fix F2 are centralized in the shared registry."""
    assert canonicalize_numpy_section_title("Params") == "Parameters"
    assert canonicalize_numpy_section_title("Retours") == "Returns"
    assert canonicalize_numpy_section_title("Errors") == "Raises"
    assert canonicalize_numpy_section_title("Erreurs") == "Raises"
    assert canonicalize_numpy_section_title("Méthodes") == "Methods"
    assert canonicalize_numpy_section_title("Other") == "Other Parameters"
    assert canonicalize_numpy_section_title("Others") == "Other Parameters"


def test_canonical_titles_are_recognized_without_redundant_alias() -> None:
    """A canonical title does not need an identical entry in the aliases."""
    assert "See Also" not in NUMPY_SECTION_ALIASES
    assert canonicalize_numpy_section_title("See Also") == "See Also"


def test_warnings_is_canonical_and_warns_is_alias() -> None:
    """The shared decision defines Warnings as canonical and Warns as an alias."""
    assert "Warnings" in NUMPY_SECTION_TITLES
    assert "Warns" not in NUMPY_SECTION_TITLES
    assert "Warnings" in NUMPY_SECTION_ORDER
    assert canonicalize_numpy_section_title("Warns") == "Warnings"
    assert canonicalize_numpy_section_title("Warnings") == "Warnings"


def test_strict_numpy_section_underline() -> None:
    """Strict mode recognizes only a raw line of hyphens."""
    assert is_numpy_section_underline("---", strict=True)
    assert not is_numpy_section_underline(" ---", strict=True)
    assert not is_numpy_section_underline("--- ", strict=True)
    assert not is_numpy_section_underline("===", strict=True)
    assert not is_numpy_section_underline("~~~", strict=True)
    assert not is_numpy_section_underline("--=", strict=True)


def test_tolerant_numpy_section_underline_preserves_fix_tolerance() -> None:
    """The default mode remains tolerant for Fix tools."""
    assert is_numpy_section_underline(" --- ")
    assert is_numpy_section_underline("===")
    assert is_numpy_section_underline("~~~")
    assert is_numpy_section_underline("--=")
    assert not is_numpy_section_underline("")
