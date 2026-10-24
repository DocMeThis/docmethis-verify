# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Conservative classification of declared return annotations."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from docmethis_extract_python.api import MISSING_VALUE, ModuleRecord

if TYPE_CHECKING:
    from collections.abc import Collection

__all__ = ["ReturnAnnotationKind", "classify_return_annotation"]

_TYPING_MODULES = frozenset({"typing", "typing_extensions"})
_TYPING_PREFIXES = tuple(f"{module}." for module in _TYPING_MODULES)
_OPTIONAL_TYPES = frozenset({"typing.Optional", "typing_extensions.Optional"})
_UNION_TYPES = frozenset({"typing.Union", "typing_extensions.Union"})
_ANNOTATED_TYPES = frozenset({"typing.Annotated", "typing_extensions.Annotated"})
_NO_RETURN_TYPES = frozenset(
    {
        "typing.Never",
        "typing.NoReturn",
        "typing_extensions.Never",
        "typing_extensions.NoReturn",
    }
)
_UNKNOWN_TYPING_TYPES = frozenset({"typing.Any", "typing_extensions.Any"})
_BUILTIN_VALUE_TYPES = frozenset(
    {
        "bool",
        "bytearray",
        "bytes",
        "complex",
        "dict",
        "float",
        "frozenset",
        "int",
        "list",
        "memoryview",
        "object",
        "range",
        "set",
        "str",
        "tuple",
        "type",
    },
)
_AMBIGUOUS_UNQUALIFIED_TYPES = frozenset({"Any", "Never", "NoReturn", "NoneType", "Optional", "Union"})
_TYPING_STAR_MEMBERS = frozenset({"Annotated", "Any", "Never", "NoReturn", "Optional", "Union"})


class ReturnAnnotationKind(StrEnum):
    """Meaning that can be established for one declared return annotation."""

    UNANNOTATED = "unannotated"
    VALUE = "value"
    NULLABLE = "nullable"
    NONE = "none"
    NO_RETURN = "no_return"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class _NameContext:
    """Import and local-type facts needed to resolve annotation names."""

    members: dict[str, str | None]
    modules: dict[str, str | None]
    star_modules: frozenset[str]
    unknown_star: bool
    local_type_names: frozenset[str]


def classify_return_annotation(
    annotation: str | None,
    *,
    module: ModuleRecord | None = None,
) -> ReturnAnnotationKind:
    """Classify a return annotation without resolving arbitrary user aliases.

    A ``Never``/``NoReturn`` spelling counts only when imported from
    ``typing`` or ``typing_extensions``. Unresolved names and aliases remain
    ``UNKNOWN``; no annotation is treated as an ordinary value type.
    """
    if annotation is None or annotation == MISSING_VALUE:
        return ReturnAnnotationKind.UNANNOTATED
    if not isinstance(annotation, str) or not annotation.strip():
        return ReturnAnnotationKind.UNKNOWN
    try:
        expression = ast.parse(annotation, mode="eval").body
    except SyntaxError:
        return ReturnAnnotationKind.UNKNOWN
    return _classify_expression(expression, context=_name_context(module))


def _name_context(module: ModuleRecord | None) -> _NameContext:
    """Build an import-aware context without importing or executing project code."""
    members: dict[str, str | None] = {}
    modules: dict[str, str | None] = {}
    star_modules: set[str] = set()
    unknown_star = False
    if module is not None:
        for import_record in module.imports:
            source_module = import_record.module
            if import_record.name is None:
                local_name = import_record.alias or source_module.split(".", maxsplit=1)[0]
                target_module = source_module if source_module in _TYPING_MODULES | {"types"} else None
                _bind(modules, local_name, target_module)
            elif import_record.name == "*":
                if source_module in _TYPING_MODULES:
                    star_modules.add(source_module)
                else:
                    unknown_star = True
            else:
                local_name = import_record.alias or import_record.name
                target = f"{source_module}.{import_record.name}" if source_module in _TYPING_MODULES | {"types"} else None
                _bind(members, local_name, target)
    for name in members.keys() & modules.keys():
        members[name] = None
        modules[name] = None
    local_type_names = (
        frozenset(class_record.qualified_name.rsplit(".", maxsplit=1)[-1] for class_record in module.classes)
        if module is not None
        else frozenset()
    )
    return _NameContext(
        members=members,
        modules=modules,
        star_modules=frozenset(star_modules),
        unknown_star=unknown_star,
        local_type_names=local_type_names,
    )


def _bind(bindings: dict[str, str | None], name: str, value: str | None) -> None:
    """Keep conflicting local imports unresolved rather than guessing."""
    if name in bindings and bindings[name] != value:
        bindings[name] = None
    else:
        bindings[name] = value


def _classify_expression(node: ast.expr, *, context: _NameContext) -> ReturnAnnotationKind:  # noqa: C901, PLR0911
    """Classify one annotation expression or return UNKNOWN when ambiguous."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return ReturnAnnotationKind.NONE
        if isinstance(node.value, str):
            try:
                nested = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return ReturnAnnotationKind.UNKNOWN
            if isinstance(nested, ast.Constant) and isinstance(nested.value, str):
                return ReturnAnnotationKind.UNKNOWN
            return _classify_expression(nested, context=context)
        return ReturnAnnotationKind.UNKNOWN
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _combine_union(
            (
                _classify_expression(node.left, context=context),
                _classify_expression(node.right, context=context),
            ),
        )
    if isinstance(node, ast.Subscript):
        constructor = _resolve_name(node.value, context=context)
        if constructor in _OPTIONAL_TYPES:
            return _combine_union((_classify_expression(node.slice, context=context), ReturnAnnotationKind.NONE))
        if constructor in _UNION_TYPES:
            arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else (node.slice,)
            return _combine_union(_classify_expression(argument, context=context) for argument in arguments)
        if constructor in _ANNOTATED_TYPES:
            arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else (node.slice,)
            return _classify_expression(arguments[0], context=context) if arguments else ReturnAnnotationKind.UNKNOWN
        return _kind_from_reference(constructor)
    if isinstance(node, ast.Call):
        called = _resolve_name(node.func, context=context)
        if (
            called == "builtins.type"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value is None
        ):
            return ReturnAnnotationKind.NONE
        return ReturnAnnotationKind.UNKNOWN
    return _kind_from_reference(_resolve_name(node, context=context))


def _resolve_name(node: ast.expr, *, context: _NameContext) -> str | None:  # noqa: C901, PLR0911
    """Resolve supported standard typing names using imports and local classes."""
    if isinstance(node, ast.Name):
        if context.unknown_star:
            return None
        if node.id in context.members:
            if node.id in context.local_type_names:
                return None
            return context.members[node.id]
        if node.id in context.local_type_names:
            return "<local-type>"
        if node.id in _BUILTIN_VALUE_TYPES:
            return f"builtins.{node.id}"
        if node.id in _TYPING_STAR_MEMBERS:
            targets = {f"{module}.{node.id}" for module in context.star_modules}
            return next(iter(targets)) if len(targets) == 1 else None
        if node.id in _AMBIGUOUS_UNQUALIFIED_TYPES:
            return None
        return None

    qualified = _qualified_name(node)
    if qualified is None:
        return None
    root, separator, suffix = qualified.partition(".")
    if not separator:
        return None
    if root in context.local_type_names or (context.unknown_star and root in context.modules):
        return None
    if root in context.modules:
        module_name = context.modules[root]
        return f"{module_name}.{suffix}" if module_name is not None else None
    return None


def _qualified_name(node: ast.expr) -> str | None:
    """Return a dotted name or None when the expression is not a name path."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent is not None else None
    return None


def _kind_from_reference(reference: str | None) -> ReturnAnnotationKind:
    """Map one resolved reference to its classification."""
    if reference in _NO_RETURN_TYPES:
        return ReturnAnnotationKind.NO_RETURN
    if reference == "types.NoneType":
        return ReturnAnnotationKind.NONE
    if reference in _UNKNOWN_TYPING_TYPES or reference in _OPTIONAL_TYPES | _UNION_TYPES:
        return ReturnAnnotationKind.UNKNOWN
    if reference == "<local-type>" or (reference is not None and reference.startswith("builtins.")):
        return ReturnAnnotationKind.VALUE
    if reference is not None and reference.startswith((*_TYPING_PREFIXES, "types.")):
        return ReturnAnnotationKind.VALUE
    return ReturnAnnotationKind.UNKNOWN


def _combine_union(kinds: Collection[ReturnAnnotationKind]) -> ReturnAnnotationKind:
    """Combine union members without hiding unresolved aliases."""
    kind_set = frozenset(kinds)
    if not kind_set or ReturnAnnotationKind.UNKNOWN in kind_set:
        return ReturnAnnotationKind.UNKNOWN
    value_kinds = kind_set - {ReturnAnnotationKind.NONE, ReturnAnnotationKind.NO_RETURN}
    if value_kinds:
        return ReturnAnnotationKind.NULLABLE if ReturnAnnotationKind.NONE in kind_set else ReturnAnnotationKind.VALUE
    if ReturnAnnotationKind.NONE in kind_set:
        return ReturnAnnotationKind.NONE
    if ReturnAnnotationKind.NO_RETURN in kind_set:
        return ReturnAnnotationKind.NO_RETURN
    return ReturnAnnotationKind.UNKNOWN
