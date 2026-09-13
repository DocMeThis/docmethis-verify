# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Parse raw NumPy section lines into typed structures."""

from collections.abc import Sequence
from itertools import chain

from docmethis_verify.docstring.models import DocstringAttribute, DocstringParameter, DocstringRaise, DocstringReturn
from docmethis_verify.docstring.sections import NUMPY_SECTION_ALIASES

_ALIASES_BY_CANONICAL: dict[str, tuple[str, ...]] = {}
for alias, canonical in NUMPY_SECTION_ALIASES.items():
    if canonical not in _ALIASES_BY_CANONICAL:
        _ALIASES_BY_CANONICAL[canonical] = ()
    _ALIASES_BY_CANONICAL[canonical] = (*_ALIASES_BY_CANONICAL[canonical], alias)


def find_section(
    docstring: object,
    *canonical_names: str,
) -> tuple[str, ...]:
    """Find a section in a NumpyDocstring object by its canonical name and known aliases.

    Parameters
    ----------
    docstring : object
        NumpyDocstring instance.
    *canonical_names : str
        Canonical section names to find (e.g. ``"Parameters"``, ``"Returns"``). Aliases (French and English variants) are tried
        automatically.

    Returns
    -------
    tuple[str, ...]
        Lines from the first section found, or ``()`` if none.

    """
    try:
        sections = docstring.sections  # type: ignore[attr-defined]
    except AttributeError:
        return ()

    for canonical in canonical_names:
        candidate_names = chain((canonical,), _ALIASES_BY_CANONICAL.get(canonical, ()))
        for name in candidate_names:
            section = sections.get(name)
            if section:
                return section
    return ()


def parse_parameters(lines: Sequence[str]) -> tuple[DocstringParameter, ...]:
    """Parse raw lines from the Parameters section.

    Each parameter starts with a ``name : type`` line, optionally followed by
    indented description lines.

    Parameters
    ----------
    lines : Sequence[str]
        The raw lines of the Parameters section to parse.

    Returns
    -------
    tuple[DocstringParameter, ...]
        A tuple of DocstringParameter objects parsed from the input lines, one for each parameter entry found.

    """
    if not lines:
        return ()

    params: list[DocstringParameter] = []
    current_name = ""
    current_type = ""
    current_desc: list[str] = []

    for line in lines:
        # Detect a new entry: non-indented line, with or without a type.
        if line and line[0] != " ":
            # Save the current parameter.
            if current_name:
                params.append(_build_parameter(current_name, current_type, current_desc))

            # Extract the new entry's name and type.
            if ":" in line:
                parts = line.split(":", 1)
                current_name = parts[0].strip()
                current_type = parts[1].strip() if len(parts) > 1 else ""
            else:
                current_name = line.strip()
                current_type = ""
            # Normalize *args and **kwargs: M1 does not retain the * prefix
            # in the parameter name.
            if current_name.startswith("*"):
                current_name = current_name.lstrip("*")
            current_desc = []
        else:
            current_desc.append(line.strip())

    if current_name:
        params.append(_build_parameter(current_name, current_type, current_desc))

    return tuple(params)


def parse_attributes(lines: Sequence[str]) -> tuple[DocstringAttribute, ...]:
    """Parse raw lines from the Attributes section using NumPy entry syntax.

    Parameters
    ----------
    lines : Sequence[str]
        The raw lines of the Attributes section to parse.

    Returns
    -------
    tuple[DocstringAttribute, ...]
        A tuple of DocstringAttribute objects parsed from the input lines.

    """
    return tuple(
        DocstringAttribute(name=parameter.name, description=parameter.description, annotation=parameter.annotation)
        for parameter in parse_parameters(lines)
    )


def _build_parameter(name: str, type_str: str, desc_lines: list[str]) -> DocstringParameter:
    """Construct a DocstringParameter from a name, type string, and description lines.

    Parameters
    ----------
    name : str
        The name of the parameter to be included in the DocstringParameter.
    type_str : str
        The type annotation string for the parameter, used to populate the annotation field; an empty string results in a None
        annotation.
    desc_lines : list[str]
        Lines of the parameter description from the docstring, used to build the parameter's description text.

    Returns
    -------
    DocstringParameter
        A DocstringParameter built from the provided name, optional type annotation, and joined description lines, with the
        description defaulting to the name when no non-empty description lines are present.

    """
    desc = " ".join(line for line in desc_lines if line)
    annotation = type_str or None
    return DocstringParameter(name=name, description=desc or name, annotation=annotation)


def parse_return(lines: Sequence[str]) -> DocstringReturn | None:
    """Parse raw lines from the Returns section.

    The first non-empty line is the type; subsequent lines are the description. If the first line is indented, it is treated as
    the description (untyped return).

    Parameters
    ----------
    lines : Sequence[str]
        Raw lines from the Returns section to parse.

    Returns
    -------
    DocstringReturn | None
        Returns a DocstringReturn object parsed from the input lines, or None if the lines are empty or contain only blank lines.
        If the first line is indented, the return is untyped and the stripped lines become the description; otherwise, the first
        non-empty line is the type annotation and the remaining lines form the description.

    """
    if not lines:
        return None

    stripped = [ln for ln in (line.strip() for line in lines) if ln]
    if not stripped:
        return None

    first_line = lines[0]
    first_is_indented = first_line and first_line[0] == " "

    if first_is_indented:
        desc = " ".join(stripped).strip()
        return DocstringReturn(description=desc, annotation=None)

    annotation = stripped[0]
    desc = " ".join(stripped[1:]).strip() if len(stripped) > 1 else ""
    return DocstringReturn(description=desc or annotation, annotation=annotation)


def parse_raises(lines: Sequence[str]) -> tuple[DocstringRaise, ...]:
    """Parse raw lines from the Raises section.

    Each exception starts with an ``ExceptionType`` line, optionally followed by indented description lines.

    Parameters
    ----------
    lines : Sequence[str]
        The raw lines from the Raises section to parse.

    Returns
    -------
    tuple[DocstringRaise, ...]
        A tuple of DocstringRaise objects, one for each exception parsed from the Raises section, in the order they appear.

    """
    if not lines:
        return ()

    raises: list[DocstringRaise] = []
    current_exc = ""
    current_desc: list[str] = []

    for line in lines:
        stripped = line.strip()
        if line and line[0] != " " and stripped:
            if current_exc:
                raises.append(_build_raise(current_exc, current_desc))

            current_exc = stripped
            current_desc = []
        else:
            current_desc.append(stripped)

    if current_exc:
        raises.append(_build_raise(current_exc, current_desc))

    return tuple(raises)


def _build_raise(exception: str, desc_lines: list[str]) -> DocstringRaise:
    """Builds a DocstringRaise object from an exception name and its description lines.

    Parameters
    ----------
    exception : str
        The name or identifier of the exception being documented in the raise section.
    desc_lines : list[str]
        The lines of the description for the exception, used to form the full description text.

    Returns
    -------
    DocstringRaise
        A DocstringRaise object built from the given exception and description lines, with the description set to the joined
        non-empty lines, or to the exception string when no description is provided.

    """
    desc = " ".join(line for line in desc_lines if line)
    return DocstringRaise(exception=exception, description=desc or exception)
