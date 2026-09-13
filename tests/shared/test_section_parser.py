# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for the NumPy section parser (section_parser.py)."""

from __future__ import annotations

from docmethis_verify.docstring.numpy_parser import parse_numpy_docstring
from docmethis_verify.docstring.section_parser import (
    find_section,
    parse_parameters,
    parse_raises,
    parse_return,
)


def _parse_lines(docstring: str, section: str) -> tuple[str, ...]:
    """Parse a docstring and return a section's raw lines, including aliases."""
    parsed = parse_numpy_docstring(docstring)
    return find_section(parsed, section)


class TestParseParameters:
    """Tests for parse_parameters()."""

    def test_parameter_with_type(self) -> None:
        """Line with a type: name : type."""
        lines = ("x : int",)
        params = parse_parameters(lines)
        assert len(params) == 1
        assert params[0].name == "x"
        assert params[0].annotation == "int"

    def test_parameter_without_type(self) -> None:
        """Line without a type: name only (C4 regression)."""
        lines = ("docstring",)
        params = parse_parameters(lines)
        assert len(params) == 1
        assert params[0].name == "docstring"
        assert params[0].annotation is None

    def test_multiple_parameters(self) -> None:
        """Several parameters on multiple lines."""
        lines = ("x : int", "    Description of x.", "y : str", "    Description of y.")
        params = parse_parameters(lines)
        assert len(params) == 2
        assert params[0].name == "x"
        assert params[0].annotation == "int"
        assert params[1].name == "y"
        assert params[1].annotation == "str"

    def test_mixed_typed_and_untyped_parameters(self) -> None:
        """A mix of typed and untyped parameters."""
        lines = ("x : int", "docstring", "    The document.", "y : str")
        params = parse_parameters(lines)
        assert len(params) == 3
        assert params[0].name == "x"
        assert params[1].name == "docstring"
        assert params[1].annotation is None
        assert params[2].name == "y"

    def test_empty_section(self) -> None:
        """Empty Parameters section."""
        assert parse_parameters(()) == ()

    def test_indented_description_is_not_parsed_as_parameter(self) -> None:
        """An indented line is not a parameter."""
        lines = ("x : int", "    just a description", "y : str")
        params = parse_parameters(lines)
        assert len(params) == 2
        assert params[0].name == "x"

    def test_french_parameters_section_is_found_through_alias(self) -> None:
        """The 'Parametres' section (French) is found through an alias."""
        docstring = """Function.

Parametres
----------
x : int
    Description of x.
"""
        lines = _parse_lines(docstring, "Parameters")
        params = parse_parameters(lines)
        assert len(params) == 1
        assert params[0].name == "x"
        assert params[0].annotation == "int"


class TestParseReturn:
    """Tests for parse_return()."""

    def test_return_type(self) -> None:
        """First non-indented line is the type."""
        lines = ("int", "    Description.")
        ret = parse_return(lines)
        assert ret is not None
        assert ret.annotation == "int"
        assert "Description" in ret.description

    def test_return_type_only(self) -> None:
        """Type only, without a description."""
        lines = ("int",)
        ret = parse_return(lines)
        assert ret is not None
        assert ret.annotation == "int"

    def test_untyped_return_description(self) -> None:
        """First indented line means no type (C3/C4 regression)."""
        lines = ("    Computed value.",)
        ret = parse_return(lines)
        assert ret is not None
        assert ret.annotation is None
        assert "Computed value" in ret.description

    def test_untyped_return_description_on_multiple_lines(self) -> None:
        """Untyped description on multiple lines."""
        lines = ("    Computed value.", "    Used for X.")
        ret = parse_return(lines)
        assert ret is not None
        assert ret.annotation is None
        assert "Computed value" in ret.description

    def test_empty_returns_section(self) -> None:
        """Empty Returns section."""
        assert parse_return(()) is None


class TestParseRaises:
    """Tests for parse_raises()."""

    def test_exception_simple(self) -> None:
        """Exception with a description."""
        lines = ("ValueError", "    When x is invalid.")
        excs = parse_raises(lines)
        assert len(excs) == 1
        assert excs[0].exception == "ValueError"

    def test_multiple_exceptions(self) -> None:
        """Several exceptions."""
        lines = ("ValueError", "TypeError", "    Incorrect type.")
        excs = parse_raises(lines)
        assert len(excs) == 2
        assert excs[0].exception == "ValueError"
        assert excs[1].exception == "TypeError"

    def test_empty_raises_section(self) -> None:
        """Empty Raises section."""
        assert parse_raises(()) == ()


class TestFindSection:
    """Tests for find_section()."""

    def test_section_parameters(self) -> None:
        """Parameters section found by canonical name."""
        docstring = """Function.

Parameters
----------
x : int
"""
        lines = _parse_lines(docstring, "Parameters")
        assert len(lines) == 1
        assert lines[0] == "x : int"

    def test_french_parameters_section_alias(self) -> None:
        """The 'Parametres' section is found through an alias."""
        docstring = """Function.

Parametres
----------
x : int
"""
        lines = _parse_lines(docstring, "Parameters")
        assert len(lines) == 1
        assert lines[0] == "x : int"

    def test_french_returns_section_alias(self) -> None:
        """The 'Retourne' section is found through an alias."""
        docstring = """Function.

Retourne
--------
int
"""
        lines = _parse_lines(docstring, "Returns")
        assert len(lines) == 1

    def test_french_raises_section_alias(self) -> None:
        """The 'Leve' section is found through an alias."""
        docstring = """Function.

Leve
----
ValueError
"""
        lines = _parse_lines(docstring, "Raises")
        assert len(lines) == 1

    def test_other_parameters_alias_is_shared(self) -> None:
        """The 'Other Params' section is found through the shared registry."""
        docstring = """Function.

Other Params
------------
debug : bool
"""
        lines = _parse_lines(docstring, "Other Parameters")
        assert lines == ("debug : bool",)

    def test_missing_section(self) -> None:
        """A missing section returns ()."""
        docstring = """Function."""
        lines = _parse_lines(docstring, "Parameters")
        assert lines == ()

    def test_parameter_docstring_without_type(self) -> None:
        """Regression: docstring without ':' in the Parametres section (C4)."""
        doc = """My function.

Parametres
----------
docstring
    NumpyDocstring instance.
*canonical_names
    Canonical section names.
"""
        parsed = parse_numpy_docstring(doc)
        lines = find_section(parsed, "Parameters")
        params = parse_parameters(lines)
        assert len(params) == 2
        assert params[0].name == "docstring"
        assert params[0].annotation is None
        assert params[1].name == "canonical_names"
        assert params[1].annotation is None

    def test_asterisk_varargs_parameter(self) -> None:
        """A *args entry in the docstring must not create DMT-2002."""
        doc = """Function with *args.

Parametres
----------
*canonical_names
    Canonical names.
"""
        parsed = parse_numpy_docstring(doc)
        lines = find_section(parsed, "Parameters")
        params = parse_parameters(lines)
        assert len(params) == 1
        assert params[0].name == "canonical_names"  # asterisk stripped
        assert params[0].annotation is None
