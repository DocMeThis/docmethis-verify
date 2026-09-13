# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Shared cross-cutting validation utilities."""

from collections.abc import Iterable
from enum import StrEnum
from functools import cache
from typing import Annotated, Literal, Protocol, cast, overload

from pydantic import Field, StringConstraints, TypeAdapter, ValidationError
from pydantic_core import ErrorDetails


class HasQualifiedName(Protocol):
    """Structural protocol for any object carrying a canonical `qualified_name`.

    Attributes
    ----------
    qualified_name : str
        Canonical qualified name of the object.

    """

    qualified_name: str


# When adding a type, update _ACCEPTED_TYPES and _format_error.
FiniteStrictNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
NonNegativeFiniteStrictNumber = Annotated[float, Field(ge=0, strict=True, allow_inf_nan=False)]
NonNegativeStrictNumber = Annotated[float, Field(ge=0, strict=True)]
NonNegativeStrictInt = Annotated[int, Field(ge=0, strict=True)]
OptionalStrictInt = Annotated[int | None, Field(strict=True)]
OptionalNonEmptyStr = Annotated[str | None, StringConstraints(min_length=1, strip_whitespace=True)]
OptionalNonNegativeStrictNumber = Annotated[float | None, Field(ge=0, strict=True)]
OptionalStrictNumber = Annotated[float | None, Field(strict=True)]
OptionalPositiveStrictInt = Annotated[int | None, Field(gt=0, strict=True)]
OptionalStr = Annotated[str | None, StringConstraints(strip_whitespace=True)]
OptionalStrictBool = Annotated[bool | None, Field(strict=True)]
PositiveFiniteStrictNumber = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]
PositiveStrictInt = Annotated[int, Field(gt=0, strict=True)]
PositiveStrictNumber = Annotated[float, Field(gt=0, strict=True)]
StrictStr = Annotated[str, StringConstraints(strict=True)]
StrictInt = Annotated[int, Field(strict=True)]
StrictNumber = Annotated[float, Field(strict=True)]
StrictBool = Annotated[bool, Field(strict=True)]
StrictDictStrObject = Annotated[dict[str, object], Field(strict=True)]
UnitIntervalStrictNumber = Annotated[float, Field(ge=0, le=1, strict=True)]

# Sequences depending on the types above
StrictListOfStrictStr = Annotated[list[StrictStr], Field(strict=True)]
StrictListOfStrictDictStrObject = Annotated[list[StrictDictStrObject], Field(strict=True)]
StrictTupleOfStrictStr = Annotated[tuple[StrictStr, ...], Field(strict=True)]
StrictTupleOfNonEmptyStr = Annotated[tuple[NonEmptyStr, ...], Field(strict=True)]


_ACCEPTED_TYPES = {
    int,
    float,
    bool,
    str,
    OptionalStrictInt,
    OptionalNonEmptyStr,
    OptionalNonNegativeStrictNumber,
    OptionalStrictNumber,
    OptionalPositiveStrictInt,
    OptionalStr,
    OptionalStrictBool,
    NonEmptyStr,
    FiniteStrictNumber,
    PositiveFiniteStrictNumber,
    NonNegativeFiniteStrictNumber,
    NonNegativeStrictNumber,
    NonNegativeStrictInt,
    PositiveStrictInt,
    PositiveStrictNumber,
    StrictStr,
    StrictInt,
    StrictNumber,
    StrictBool,
    StrictDictStrObject,
    StrictListOfStrictStr,
    StrictListOfStrictDictStrObject,
    StrictTupleOfStrictStr,
    StrictTupleOfNonEmptyStr,
    UnitIntervalStrictNumber,
}

_TYPE_ERRORS = {
    "string_type": "must be a string",
    "int_type": "must be an integer",
    "float_type": "must be a number",
    "bool_type": "must be a boolean",
    "list_type": "must be a list",
    "tuple_type": "must be a tuple",
}

_CHILD_TYPE_ERRORS = {
    "string_type": "must contain only strings",
    "int_type": "must contain only integers",
    "float_type": "must contain only numbers",
}

_VALUE_ERRORS = {
    "string_too_short": "must be a non-empty string",
    "greater_than": "must be strictly positive",
    "greater_than_equal": "must be non-negative",
    "finite_number": "must be a finite number",
    "less_than_equal": "must be between 0 and 1",  # used only for UnitIntervalStrictNumber
}

_CHILD_VALUE_ERRORS = {
    "string_too_short": "must contain only non-empty strings",
}

__all__ = [
    "HasQualifiedName",
    "check_and_normalize_non_empty_str",
    "check_no_duplicate_qualified_names",
    "dynamic_type_check",
    "normalize_str_enum_value",
    "type_check",
]


@cache
def _adapter_for(expected_alias: type | object) -> TypeAdapter:
    """Get a TypeAdapter for a Pydantic-annotated type alias.

    Parameters
    ----------
    expected_alias : type | object
        The Pydantic-annotated type alias to adapt into a TypeAdapter.

    Returns
    -------
    TypeAdapter
        A TypeAdapter instance for the provided Pydantic-annotated type alias.

    Raises
    ------
    TypeError
        Explicitly raised.

    """
    if expected_alias not in _ACCEPTED_TYPES:
        msg = f"Type not supported by type_check: {expected_alias!r}"
        raise TypeError(msg)
    return TypeAdapter(expected_alias)


def _format_error(field: str, err: ErrorDetails, or_none: str) -> TypeError | ValueError:
    """Format a Pydantic validation error as a clear message.

    Pydantic validation error messages are documented in pydantic/docs/errors/validation_errors.md, and the complete list is in
    pydantic_core.ErrorType.

    Parameters
    ----------
    field : str
        The name of the field being validated, used as the prefix in the generated error message.
    err : ErrorDetails
        The Pydantic validation error details to format, expected to contain 'loc' and 'type' keys.
    or_none : str
        Suffix to append to the formatted type error message when the error is not in a collection element, used to indicate that
        None is also allowed.

    Returns
    -------
    TypeError | ValueError
        A TypeError or ValueError whose message describes the validation error; TypeError is returned for type-related errors and
        ValueError for value-related errors.

    """
    has_loc = bool(err["loc"])

    err_type = err["type"]

    if err_type in _TYPE_ERRORS:
        if has_loc:  # error in a collection element
            msg = f"{field} {_CHILD_TYPE_ERRORS.get(err_type, f'contains invalid elements ({err_type})')}"
        else:
            msg = f"{field} {_TYPE_ERRORS[err_type]}{or_none}"
        return TypeError(msg)

    if has_loc:  # error in a collection element
        msg = f"{field} {_CHILD_VALUE_ERRORS.get(err_type, f'contains invalid elements ({err_type})')}"
    else:
        msg = f"{field} {_VALUE_ERRORS.get(err_type, f'is invalid ({err_type})')}"
    return ValueError(msg)


def type_check(*, value: object, expected_alias_type: object, field: str) -> None:
    """Raise a clear error if value does not match the expected annotated type (validated by Pydantic).

    Parameters
    ----------
    value : object
        The value to be validated against the expected type.
    expected_alias_type : object
        The expected type to validate the value against, provided as an alias type object.
    field : str
        The name of the field being validated, used in error messages.

    Raises
    ------
    _format_error
        Explicitly raised.

    """
    adapter = _adapter_for(expected_alias_type)

    try:
        adapter.validate_python(value)
    except ValidationError as exc:
        err = cast("ErrorDetails", exc.errors()[0])
        or_none = " or None" if adapter.core_schema["type"] == "nullable" else ""
        raise _format_error(field, err, or_none) from exc


def dynamic_type_check(
    *, value: object, field: str, expected_type: type, container: type | None = None, optional: bool = False
) -> None:
    """Dynamically validate an instance or container of instances.

    Unlike `type_check`, this uses pure Python validation rather than Pydantic.

    Parameters
    ----------
    value : object
        The object to validate against the expected type or, when a container is specified, the container whose items are checked
        against the expected type.
    field : str
        Name of the field being validated, used in error messages to identify the offending attribute or key.
    expected_type : type
        The expected Python type for the value, or for each element when a container is specified.
    container : type | None = None
        Optional container type used to validate that the value is an instance of the container and that its items match the
        expected type.
    optional : bool = False
        Whether the value is optional; when True, the value may be None. Defaults to False.

    Raises
    ------
    TypeError
        Explicitly raised.

    """
    if container is None and not optional:
        if not isinstance(value, expected_type):
            msg = f"{field} must be an instance of {expected_type.__name__}"
            raise TypeError(msg)
        return

    if not isinstance(value, container):
        msg = f"{field} must be a {container.__name__}"
        raise TypeError(msg)

    items = cast("tuple[object, ...] | list[object]", value)
    if not all(isinstance(item, expected_type) for item in items):
        msg = f"{field} must contain only {expected_type.__name__} instances"
        raise TypeError(msg)


@overload
def check_and_normalize_non_empty_str(*, value: object, field: str, optional: Literal[False] = False) -> str: ...


@overload
def check_and_normalize_non_empty_str(*, value: object, field: str, optional: Literal[True]) -> str | None: ...


def check_and_normalize_non_empty_str(*, value: object, field: str, optional: bool = False) -> str | None:
    """Validate that value is a non-empty string and normalize it by removing surrounding whitespace.

    Parameters
    ----------
    value : object
        The value to validate as a non-empty string.
    field : str
        The name of the field being validated, used in the error message.
    optional : bool = False
        Whether the value may be None. Defaults to False.

    Returns
    -------
    str | None
        The normalized non-empty string, or None when `optional` is True and the value is None.

    Raises
    ------
    _format_error
        Explicitly raised.

    """
    adapter = _adapter_for(OptionalNonEmptyStr) if optional else _adapter_for(NonEmptyStr)
    try:
        return adapter.validate_python(value)
    except ValidationError as exc:
        err = cast("ErrorDetails", exc.errors()[0])
        raise _format_error(field, err, "") from exc


def check_no_duplicate_qualified_names(items: Iterable[HasQualifiedName], *, field: str) -> None:
    """Raise ValueError if two items in items share the same qualified_name.

    Parameters
    ----------
    items : Iterable[HasQualifiedName]
        Ordered collection of objects carrying a `qualified_name` attribute.
    field : str
        Name of the field used in the error message.

    Raises
    ------
    ValueError
        On the first duplicate `qualified_name` detected.

    """
    seen: set[str] = set()
    for index, item in enumerate(items):
        if item.qualified_name in seen:
            msg = f"{field}[{index}] contains a duplicate qualified_name: {item.qualified_name!r}"
            raise ValueError(msg)
        seen.add(item.qualified_name)


def normalize_str_enum_value[E: StrEnum](*, value: object, enum_type: type[E], field: str) -> E:
    """Normalize a value to a member of `enum_type`.

    Parameters
    ----------
    value : object
        The value to normalize to a member of enum_type. It may be an instance of enum_type or a string corresponding to one of
        the enum member values.
    enum_type : type[E]
        The enum type that defines the allowed values and to which the input value will be converted.
    field : str
        The name of the field being validated, used in error messages to identify which input caused the failure.

    Returns
    -------
    E
        The corresponding member of enum_type for the normalized input value.

    Raises
    ------
    ValueError
        Explicitly raised.
    TypeError
        Explicitly raised.

    """
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        msg = f"{field} must be a string or a {enum_type.__name__}"
        raise TypeError(msg)
    try:
        return enum_type(value)
    except ValueError as exc:
        accepted = ", ".join(repr(member.value) for member in enum_type)
        msg = f"{field} must be one of [{accepted}], not {value!r}"
        raise ValueError(msg) from exc


class DocumentationIndexOrphanError(ValueError):
    """Orphan documentation entries absent from the M1 tree.

    Parameters
    ----------
    orphan_qualified_names : tuple[str, ...]
        A tuple of qualified names that are orphaned in the documentation index.

    Attributes
    ----------
    orphan_qualified_names : tuple[str, ...]
        The normalized tuple of orphaned qualified names.

    Raises
    ------
    ValueError
        If `orphan_qualified_names` is empty.

    """

    def __init__(self, *, orphan_qualified_names: tuple[str, ...]) -> None:
        """Build a stable error for orphan documentation keys.

        Parameters
        ----------
        orphan_qualified_names : tuple[str, ...]
            A tuple of qualified names that are orphaned in the documentation index.

        Raises
        ------
        ValueError
            Explicitly raised.

        """
        if not orphan_qualified_names:
            msg = "orphan_qualified_names cannot be empty"
            raise ValueError(msg)

        self.orphan_qualified_names = tuple(
            check_and_normalize_non_empty_str(value=name, field="orphan_qualified_names[]", optional=False)
            for name in orphan_qualified_names
        )
        msg = f"documentation_index contains orphan entries: {', '.join(self.orphan_qualified_names)}"
        super().__init__(msg)
