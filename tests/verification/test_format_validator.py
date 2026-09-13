# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for NumPy docstring format validation."""

from docmethis_verify.verification.format_validator import validate_docstring_format


class TestEmptyDocstring:
    """Empty and missing docstring edge cases."""

    def test_empty_docstring(self) -> None:
        assert validate_docstring_format("") == []

    def test_whitespace_only_docstring(self) -> None:
        assert validate_docstring_format("   \n  \n") == []

    def test_none_docstring(self) -> None:
        assert validate_docstring_format("") == []


class TestWellFormedDocstring:
    """Well-formed NumPy docstring without warnings."""

    def test_summary_only(self) -> None:
        doc = "A simple description."
        assert validate_docstring_format(doc) == []

    def test_summary_and_parameters(self) -> None:
        doc = """Summary.

Parameters
----------
x : int
    Description of x.
y : str
    Description of y.
"""
        assert validate_docstring_format(doc) == []

    def test_complete(self) -> None:
        doc = """Function summary.

Parameters
----------
x : int
    The first parameter.

Returns
-------
int
    The return value.

Raises
------
ValueError
    If x is negative.

Examples
--------
>>> f(1)
1
"""
        assert validate_docstring_format(doc) == []

    def test_with_indentation(self) -> None:
        doc = """    Indented summary.

    Parameters
    ----------
    x : int
        Description.
    """
        assert validate_docstring_format(doc) == []


class TestMalformedHeading:
    """Detection of malformed headings."""

    def test_underline_too_short(self) -> None:
        doc = """Summary.

Parameters
---------
x : int
"""
        warnings = validate_docstring_format(doc)
        kinds = {w.kind for w in warnings}
        assert "underline_length" in kinds

    def test_underline_too_long(self) -> None:
        doc = """Summary.

Parameters
------------
x : int
"""
        warnings = validate_docstring_format(doc)
        kinds = {w.kind for w in warnings}
        assert "underline_length" in kinds


class TestSectionSpelling:
    """Misspelled section headings."""

    def test_param_instead_of_parameters(self) -> None:
        doc = """Summary.

Param
-----
x : int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Param" for w in warnings)

    def test_args_instead_of_parameters(self) -> None:
        doc = """Summary.

Args
----
x : int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Args" for w in warnings)

    def test_return_instead_of_returns(self) -> None:
        doc = """Summary.

Return
------
int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" for w in warnings)

    def test_raise_instead_of_raises(self) -> None:
        doc = """Summary.

Raise
-----
ValueError
    If the value is invalid.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" for w in warnings)

    def test_warns_is_an_alias_of_warnings(self) -> None:
        doc = """Summary.

Warns
-----
RuntimeWarning
    If the result is approximate.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Warns" for w in warnings)
        assert not any(w.kind == "unknown_section" and w.section == "Warns" for w in warnings)

    def test_probable_returns_typo(self) -> None:
        doc = """Summary.

Retruns
-------
int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Retruns" for w in warnings)
        assert not any(w.kind == "unknown_section" and w.section == "Retruns" for w in warnings)

    def test_probable_returns_typo_with_colon(self) -> None:
        doc = """Summary.

Retruns:
--------
int
"""
        warnings = validate_docstring_format(doc)
        warning = next(w for w in warnings if w.kind == "misspelled_section" and w.section == "Retruns:")
        assert warning.line == 3
        assert not any(w.kind == "unknown_section" and w.section == "Retruns:" for w in warnings)

    def test_probable_parameters_typo_with_colon(self) -> None:
        doc = """Summary.

Paramters:
----------
x : int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Paramters:" for w in warnings)
        assert not any(w.kind == "unknown_section" and w.section == "Paramters:" for w in warnings)

    def test_local_parameters_permutation(self) -> None:
        doc = """Summary.

Paratemers
----------
x : int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Paratemers" for w in warnings)
        assert not any(w.kind == "unknown_section" and w.section == "Paratemers" for w in warnings)

    def test_local_returns_permutation(self) -> None:
        doc = """Summary.

Retnurs
-------
int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "misspelled_section" and w.section == "Retnurs" for w in warnings)
        assert not any(w.kind == "unknown_section" and w.section == "Retnurs" for w in warnings)


class TestUnknownSection:
    """Sections not recognized by NumPy format."""

    def test_unknown_section(self) -> None:
        doc = """Summary.

MaSection
---------
Content.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "unknown_section" for w in warnings)

    def test_unknown_section_ignores_canonical_sections(self) -> None:
        doc = """Summary.

Parameters
----------
x : int

MaSection
---------
Content.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "unknown_section" for w in warnings)

    def test_shared_extended_numpy_sections_are_known(self) -> None:
        doc = """Summary.

Other Parameters
----------------
debug : bool
    Enable tracing.

Yields
------
int
    Produced value.

Warnings
--------
RuntimeWarning
    If the value is approximate.

References
----------
Internal reference.

Methods
-------
run
    Run the operation.
"""
        warnings = validate_docstring_format(doc)
        assert not any(w.kind == "unknown_section" for w in warnings)

    def test_non_adjacent_anagram_remains_unknown(self) -> None:
        doc = """Summary.

Sraies
------
ValueError
    If the value is invalid.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "unknown_section" and w.section == "Sraies" for w in warnings)
        assert not any(w.kind == "misspelled_section" and w.section == "Sraies" for w in warnings)


class TestSectionOrder:
    """Non-conventional section order."""

    def test_inverted_order(self) -> None:
        doc = """Summary.

Raises
------
ValueError
    If the value is invalid.

Returns
-------
int
    The value.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "section_order" for w in warnings)

    def test_correct_order(self) -> None:
        doc = """Summary.

Returns
-------
int

Raises
------
ValueError
"""
        warnings = validate_docstring_format(doc)
        assert not any(w.kind == "section_order" for w in warnings)


class TestParametersSection:
    """Validation of the Parameters section."""

    def test_parameter_without_type(self) -> None:
        doc = """Summary.

Parameters
----------
x :
    Description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "param_missing_type" for w in warnings)

    def test_parameter_without_colon(self) -> None:
        doc = """Summary.

Parameters
----------
x int
    Description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "param_missing_colon" for w in warnings)

    def test_incorrect_colon_spacing(self) -> None:
        doc = """Summary.

Parameters
----------
x:int
    Description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "param_colon_spacing" for w in warnings)

    def test_parameter_without_name(self) -> None:
        doc = """Summary.

Parameters
----------
: int
    Description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "param_empty_name" for w in warnings)


class TestReturnsSection:
    """Validation of the Returns section."""

    def test_description_before_type(self) -> None:
        doc = """Summary.

Returns
-------
the return value.
int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "return_type_and_desc_inverted" for w in warnings)

    def test_type_expression_with_spaces_is_not_a_description(self) -> None:
        for return_type in ("tuple[str, ...]", "str | None"):
            doc = f"""Summary.

Returns
-------
{return_type}
    The return value.
"""
            warnings = validate_docstring_format(doc)
            assert not any(w.kind == "return_type_and_desc_inverted" for w in warnings)

    def test_empty_section(self) -> None:
        doc = """Summary.

Returns
-------
"""
        warnings = validate_docstring_format(doc)
        assert not any(w.kind.startswith("return_") for w in warnings)


class TestRaisesSection:
    """Validation of the Raises section."""

    def test_exception_without_description(self) -> None:
        doc = """Summary.

Raises
------
ValueError
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "raises_missing_description" for w in warnings)

    def test_exception_type_and_description_on_same_line(self) -> None:
        doc = """Summary.

Raises
------
ValueError description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "raises_type_and_desc_on_same_line" for w in warnings)

    def test_lowercase_exception_name(self) -> None:
        doc = """Summary.

Raises
------
valueError
    Description.
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "raises_invalid_name" for w in warnings)


class TestBlankLines:
    """Missing blank lines between sections."""

    def test_missing_blank_line(self) -> None:
        doc = """Summary.

Parameters
----------
Returns
-------
int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "missing_blank_line" for w in warnings)

    def test_present_blank_line(self) -> None:
        doc = """Summary.

Parameters
----------

Returns
-------
int
"""
        warnings = validate_docstring_format(doc)
        assert not any(w.kind == "missing_blank_line" for w in warnings)


class TestEmptySummary:
    """Empty summary when sections exist."""

    def test_empty_summary_with_sections(self) -> None:
        doc = """Parameters
----------
x : int
"""
        warnings = validate_docstring_format(doc)
        assert any(w.kind == "empty_summary" for w in warnings)

    def test_present_summary_with_sections(self) -> None:
        doc = """Summary.

Parameters
----------
x : int
"""
        warnings = validate_docstring_format(doc)
        assert not any(w.kind == "empty_summary" for w in warnings)
