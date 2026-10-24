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
    """Meaning that can be established for one declared return annotation.

    Attributes
    ----------
    UNANNOTATED
        A class attribute of ReturnAnnotationKind whose value is the string "unannotated".
    VALUE
        A class attribute of ReturnAnnotationKind whose value is the string "value".
    NULLABLE
        A class attribute of ReturnAnnotationKind whose value is the string "nullable".
    NONE
        ReturnAnnotationKind is a string enumeration whose members are UNANNOTATED, VALUE, NULLABLE, NONE, NO_RETURN, and UNKNOWN,
        with string values "unannotated", "value", "nullable", "none", "no_return", and "unknown" respectively. It is intended to
        represent the meaning established for a declared return annotation.
    NO_RETURN
        NO_RETURN is a class attribute of ReturnAnnotationKind, an enum.StrEnum, with the value "no_return".
    UNKNOWN
        A class attribute of ReturnAnnotationKind whose value is the string "unknown".
    """

    UNANNOTATED = "unannotated"
    VALUE = "value"
    NULLABLE = "nullable"
    NONE = "none"
    NO_RETURN = "no_return"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class _NameContext:
    """Import and local-type facts needed to resolve annotation names.

    Attributes
    ----------
    members
        A class attribute that holds a dictionary mapping names to optional strings.
    modules
        A class attribute named modules, declared on the frozen, slotted dataclass _NameContext, holding a mapping from string
        keys to string-or-None values.
    star_modules
        A frozen, slotted dataclass attribute holding a frozenset of strings representing star-imported module names.
    unknown_star
        A boolean instance attribute of the frozen slotted dataclass _NameContext, declared alongside members, modules,
        star_modules, and local_type_names. It indicates whether a star import with unresolved contents is present.
    local_type_names
        A class attribute named local_type_names holding a frozenset of strings, declared as a dataclass field on the frozen,
        slotted class _NameContext, which stores import and local-type facts for resolving annotation names.
    """

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

    A ``Never``/``NoReturn`` spelling counts only when imported from ``typing`` or ``typing_extensions``. Unresolved names and
    aliases remain ``UNKNOWN``; no annotation is treated as an ordinary value type.

    Parameters
    ----------
    annotation : str | None
        Accepts a string or None as its positional-or-keyword annotation argument, with no default value. Also accepts an optional
        keyword-only module argument of type ModuleRecord or None, defaulting to None. Returns UNANNOTATED when the annotation is
        None or equals MISSING_VALUE, UNKNOWN when the annotation is not a string, is blank apart from whitespace, or fails to
        parse as an expression, and otherwise delegates classification of the parsed expression to an internal helper using the
        supplied module's name context.
    module : ModuleRecord | None = None
        Accepts a return annotation string or None, plus an optional keyword-only module record. When the annotation is None or
        the missing-value marker, returns UNANNOTATED. When the annotation is not a string or is blank, returns UNKNOWN. When the
        annotation fails to parse as a Python expression, returns UNKNOWN. Otherwise parses the annotation as an expression and
        returns the result of classifying that expression using a name context derived from the supplied module.

    Returns
    -------
    ReturnAnnotationKind
        Returns UNANNOTATED when the annotation is None or equals MISSING_VALUE. Returns UNKNOWN when the annotation is not a
        string, is blank after stripping, or cannot be parsed as an expression. Otherwise returns the result of
        _classify_expression applied to the parsed expression with a name context derived from the provided module.
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
    """Build an import-aware context without importing or executing project code.

    Parameters
    ----------
    module : ModuleRecord | None
        Accepts a ModuleRecord or None. When a module is provided, its imports populate member and module name mappings: imports
        without a name bind a local alias derived from the alias or the first segment of the source module to the source module
        only when it belongs to typing modules or types, star imports from typing modules add to star modules while other star
        imports mark an unknown star, and named imports bind a local alias to the fully qualified name only when the source module
        belongs to typing modules or types. Names bound in both member and module mappings are set to None in both. Local type
        names are the final dot-separated segments of the module's class qualified names, or an empty set when no module is given.
        Returns a context containing these mappings, star module names, the unknown star flag, and local type names.

    Returns
    -------
    _NameContext
        Returns a _NameContext containing members and modules dictionaries, star_modules and local_type_names frozensets, and an
        unknown_star boolean. Members and modules map local names to fully qualified typing/types targets or None; when no module
        is supplied, all collections and the star flag are empty or false, and local_type_names is an empty frozenset. Each import
        either binds a local name in members or modules, adds a typing module to star_modules, or sets unknown_star when a star
        import comes from a non-typing module. A local name bound in both members and modules maps to None in both.
        local_type_names holds the unqualified class names of the supplied module. No project code is imported or executed.
    """
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
    """Keep conflicting local imports unresolved rather than guessing.

    Parameters
    ----------
    bindings : dict[str, str | None]
        Accepts a dictionary mapping names to strings or None, a name, and a value. If the name is already present in the
        dictionary with a different value, sets that name's entry to None; otherwise sets it to the given value.
    name : str
        Accepts a name string and a string-or-null value, then updates a bindings mapping: if the name already maps to a different
        value, it sets that entry to None; otherwise it sets the entry to the given value.
    value : str | None
        A positional-or-keyword parameter named value annotated as str | None with no default. The function records value into the
        bindings mapping under name; if name is already present with a different value, the stored entry is set to None instead.
    """
    if name in bindings and bindings[name] != value:
        bindings[name] = None
    else:
        bindings[name] = value


def _classify_expression(node: ast.expr, *, context: _NameContext) -> ReturnAnnotationKind:  # noqa: C901, PLR0911
    """Classify one annotation expression or return UNKNOWN when ambiguous.

    Parameters
    ----------
    node : ast.expr
        Accepts an AST expression annotation to classify and a keyword-only name context. Returns a return-annotation kind by
        recursively examining the expression: a constant None yields NONE; a string constant is parsed as an expression and
        classified, with syntax errors or nested string constants yielding UNKNOWN; bitwise-or unions combine classifications of
        both operands; subscript expressions resolve the constructor name and handle Optional, Union, and Annotated forms
        accordingly, otherwise classify from the reference; a call to builtins.type with a single None argument yields NONE, other
        calls UNKNOWN; other expressions classify from the resolved name. Unsupported constant values yield UNKNOWN.
    context : _NameContext
        A required keyword-only argument annotated as _NameContext. It is passed to _resolve_name and to recursive calls of
        _classify_expression for resolving names within the annotation expression.

    Returns
    -------
    ReturnAnnotationKind
        Returns a ReturnAnnotationKind classifying the annotation expression. None literals and type(None) calls yield NONE.
        String literals are parsed and classified recursively unless unparsable, a quoted string, or another constant, in which
        case UNKNOWN is returned. Other constants yield UNKNOWN. BitOr unions combine the kinds of both operands. Optional
        subscripts combine the slice kind with NONE; Union subscripts combine the kinds of all arguments; Annotated subscripts
        classify the first argument, or UNKNOWN when there are none. Other subscripts and names yield a kind from a reference.
        Calls other than type(None) yield UNKNOWN.
    """
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
    """Resolve supported standard typing names using imports and local classes.

    Parameters
    ----------
    node : ast.expr
        Accepts a positional-or-keyword AST expression annotated as ast.expr. Resolves supported standard typing names from the
        node using imports and local classes, returning a dotted name string or None when the name is unknown, ambiguous, or a
        local type.
    context : _NameContext
        A keyword-only _NameContext providing the import, star-import, member, module, and local type name information used to
        resolve an AST expression to a qualified name or a placeholder.

    Returns
    -------
    str | None
        Returns a dotted qualified name string when the expression is a supported standard typing name, builtin value type, or a
        name resolving through known imports or local classes. Returns the literal "<local-type>" for names identifying local type
        names not otherwise mapped. Returns None when the name cannot be resolved, including under an unknown star import,
        ambiguous unqualified types, unknown names, non-qualified expressions, or unresolved roots.
    """
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
    """Return a dotted name or None when the expression is not a name path.

    Parameters
    ----------
    node : ast.expr
        Accepts an AST expression node. Determines whether the expression forms a name path: an ast.Name yields its identifier,
        and an ast.Attribute yields its attribute name prefixed by the qualified name of its value when that value's qualified
        name is not None. Any other expression, or an attribute whose parent qualified name is None, yields None.

    Returns
    -------
    str | None
        Returns the identifier when the expression is an ast.Name, or a dot-joined qualified name built recursively from an
        ast.Attribute's value and attribute when the parent name resolves. Returns None when the expression is not a name path or
        when an attribute's parent name cannot be resolved.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent is not None else None
    return None


def _kind_from_reference(reference: str | None) -> ReturnAnnotationKind:
    """Map one resolved reference to its classification.

    Parameters
    ----------
    reference : str | None
        Accepts a reference that may be a string or None. Returns NO_RETURN when the reference is in the set of no-return types,
        NONE when it equals "types.NoneType", and UNKNOWN when it is in the unknown typing types or in the optional or union type
        sets. Returns VALUE when the reference is "<local-type>", when it is a non-None string starting with "builtins.", or when
        it is a non-None string starting with any typing prefix or "types.". Returns UNKNOWN otherwise.

    Returns
    -------
    ReturnAnnotationKind
        Returns a ReturnAnnotationKind classification based on the supplied reference string. Returns
        ReturnAnnotationKind.NO_RETURN when the reference is in the no-return type set, ReturnAnnotationKind.NONE when it equals
        "types.NoneType", and ReturnAnnotationKind.UNKNOWN when it is in the unknown typing types or the optional/union type sets,
        or when no earlier condition matches. Returns ReturnAnnotationKind.VALUE when the reference is "<local-type>", starts with
        "builtins.", or starts with one of the typing prefixes or "types.".
    """
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
    """Combine union members without hiding unresolved aliases.

    Parameters
    ----------
    kinds : Collection[ReturnAnnotationKind]
        Accepts a collection of return annotation kinds and derives a single combined kind. Returns UNKNOWN when the collection is
        empty or contains UNKNOWN. When kinds other than NONE and NO_RETURN are present, returns NULLABLE if NONE is also present,
        otherwise VALUE. When only NONE and/or NO_RETURN are present, returns NONE if NONE is present, otherwise NO_RETURN. Falls
        back to UNKNOWN.

    Returns
    -------
    ReturnAnnotationKind
        Returns ReturnAnnotationKind.UNKNOWN when the input collection is empty or contains UNKNOWN. When value kinds are present,
        returns NULLABLE if NONE is also present, otherwise VALUE. When no value kinds are present, returns NONE if NONE is in the
        set, otherwise NO_RETURN if NO_RETURN is in the set, otherwise UNKNOWN.
    """
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
