# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Canonical document models shared across modules."""

from enum import StrEnum
from typing import Literal

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass

from docmethis_verify.validation import NonEmptyStr, OptionalNonEmptyStr, StrictBool, StrictTupleOfNonEmptyStr

DOCSTRING_EXCHANGE_VERSION: Literal["1.0"] = "1.0"
SchemaVersion = Literal["1.0"]
_CONFIG_DICT = ConfigDict(extra="forbid")


class DocstringExampleProvenance(StrEnum):
    """Canonical provenance values for an example.

    Attributes
    ----------
    SYNTHETIC_MINIMAL : str
        Example generated synthetically with minimal setup.
    DYNAMIC_OBSERVED : str
        Example observed from a dynamic execution.

    """

    SYNTHETIC_MINIMAL = "synthetic_minimal"
    DYNAMIC_OBSERVED = "dynamic_observed"


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringParameter:
    """Description of a parameter.

    Attributes
    ----------
    name : NonEmptyStr
        Parameter name.
    description : NonEmptyStr
        Parameter description.
    annotation : OptionalNonEmptyStr
        Type annotation of the parameter, when available.
    default : OptionalNonEmptyStr
        Default value of the parameter, when available.

    """

    name: NonEmptyStr
    description: NonEmptyStr
    annotation: OptionalNonEmptyStr = None
    default: OptionalNonEmptyStr = None


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringAttribute:
    """Description of a class attribute.

    Attributes
    ----------
    name : NonEmptyStr
        Attribute name.
    description : NonEmptyStr
        Attribute description.
    annotation : OptionalNonEmptyStr
        Type annotation of the attribute, when available.

    """

    name: NonEmptyStr
    description: NonEmptyStr
    annotation: OptionalNonEmptyStr = None


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringReturn:
    """Description of the Returns section.

    Attributes
    ----------
    description : NonEmptyStr
        Description of the returned value.
    annotation : OptionalNonEmptyStr
        Return type annotation, when available.

    """

    description: NonEmptyStr
    annotation: OptionalNonEmptyStr = None


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringRaise:
    """Description of a documented exception.

    Attributes
    ----------
    exception : NonEmptyStr
        Name of the documented exception.
    description : NonEmptyStr
        Conditions under which the exception is raised.

    """

    exception: NonEmptyStr
    description: NonEmptyStr


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringNote:
    """Targeted Notes fragment with its deterministic topic.

    Attributes
    ----------
    topic : NonEmptyStr
        Deterministic topic of the note.
    description : NonEmptyStr
        Content of the note.

    """

    topic: NonEmptyStr
    description: NonEmptyStr


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class DocstringExample:
    """Example attached to the canonical documentation core.

    Attributes
    ----------
    description : NonEmptyStr
        Purpose of the example.
    snippet : NonEmptyStr
        Code snippet illustrating the example.
    provenance : DocstringExampleProvenance
        Origin of the example.
    setup : OptionalNonEmptyStr
        Setup code required before the call, when present.
    call : OptionalNonEmptyStr
        Call expression of the example, when present.
    result : OptionalNonEmptyStr
        Expected result of the example, when present.
    confidence : OptionalNonEmptyStr
        Confidence statement about the example, when present.
    contradiction_suspected : StrictBool
        Whether the example contradicts the docstring.

    """

    description: NonEmptyStr
    snippet: NonEmptyStr
    provenance: DocstringExampleProvenance

    setup: OptionalNonEmptyStr = None
    call: OptionalNonEmptyStr = None
    result: OptionalNonEmptyStr = None
    confidence: OptionalNonEmptyStr = None
    contradiction_suspected: StrictBool = False


@dataclass(kw_only=True, slots=True, frozen=True, config=_CONFIG_DICT)
class GeneratedDocstring:
    """Canonical documentation core shared with downstream modules.

    Attributes
    ----------
    summary : NonEmptyStr
        One-line summary of the documented symbol.
    parameters : tuple[DocstringParameter, ...]
        Documented parameters.
    attributes : tuple[DocstringAttribute, ...]
        Documented class attributes.
    returns : DocstringReturn | None
        Documented return value, when present.
    raises : tuple[DocstringRaise, ...]
        Documented exceptions.
    notes : StrictTupleOfNonEmptyStr
        Free-form notes.
    examples : tuple[DocstringExample, ...]
        Attached examples.

    """

    summary: NonEmptyStr
    parameters: tuple[DocstringParameter, ...] = Field(default_factory=tuple, strict=True)
    attributes: tuple[DocstringAttribute, ...] = Field(default_factory=tuple, strict=True)
    returns: DocstringReturn | None = None
    raises: tuple[DocstringRaise, ...] = Field(default_factory=tuple, strict=True)
    notes: StrictTupleOfNonEmptyStr = Field(default_factory=tuple, strict=True)
    examples: tuple[DocstringExample, ...] = Field(default_factory=tuple, strict=True)
