# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Tests for conservative return-annotation classification."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from docmethis_extract_python.api import MISSING_VALUE, ModuleRecord, extract_module_record

from docmethis_verify import ReturnAnnotationKind, classify_return_annotation

if TYPE_CHECKING:
    from pathlib import Path


def _module(tmp_path: Path, source: str) -> ModuleRecord:
    """Extract a module to provide authentic import and local-class facts."""
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    record = extract_module_record(path, "module", is_stub=False, is_test=False, file_hash="test")
    assert record is not None
    return record


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(None, ReturnAnnotationKind.UNANNOTATED, id="none-input"),
        pytest.param(MISSING_VALUE, ReturnAnnotationKind.UNANNOTATED, id="missing-sentinel"),
        pytest.param("None", ReturnAnnotationKind.NONE, id="none-type"),
        pytest.param("int", ReturnAnnotationKind.VALUE, id="builtin-value"),
        pytest.param("str | None", ReturnAnnotationKind.NULLABLE, id="pep604-nullable"),
        pytest.param("typing.NoReturn", ReturnAnnotationKind.UNKNOWN, id="qualified-without-import"),
        pytest.param("NoReturn", ReturnAnnotationKind.UNKNOWN, id="ambiguous-unqualified-no-return"),
        pytest.param("typing.Never", ReturnAnnotationKind.UNKNOWN, id="unresolved-qualified-module"),
        pytest.param("UnknownAlias", ReturnAnnotationKind.UNKNOWN, id="unresolved-alias"),
        pytest.param("int | UnknownAlias", ReturnAnnotationKind.UNKNOWN, id="partially-unresolved-union"),
        pytest.param("int | Never", ReturnAnnotationKind.UNKNOWN, id="union-with-ambiguous-never"),
        pytest.param("typing.Any", ReturnAnnotationKind.UNKNOWN, id="unbounded-any"),
        pytest.param("Annotated[int", ReturnAnnotationKind.UNKNOWN, id="invalid-annotation"),
    ],
)
def test_classify_return_annotation_without_import_context(
    annotation: str | None,
    expected: ReturnAnnotationKind,
) -> None:
    """Unresolved names stay unknown, while built-in and literal facts classify directly."""
    assert classify_return_annotation(annotation) is expected


@pytest.mark.parametrize(
    ("annotation", "source", "expected"),
    [
        pytest.param("Never", "from typing import Never\n", ReturnAnnotationKind.NO_RETURN, id="typing-never"),
        pytest.param("NoReturn", "from typing import NoReturn\n", ReturnAnnotationKind.NO_RETURN, id="typing-no-return"),
        pytest.param(
            "typing.NoReturn",
            "import typing\n",
            ReturnAnnotationKind.NO_RETURN,
            id="qualified-typing-no-return",
        ),
        pytest.param("NR", "from typing import NoReturn as NR\n", ReturnAnnotationKind.NO_RETURN, id="member-alias"),
        pytest.param(
            "te.Never",
            "import typing_extensions as te\n",
            ReturnAnnotationKind.NO_RETURN,
            id="module-alias",
        ),
        pytest.param(
            "typing_extensions.NoReturn",
            "import typing_extensions\n",
            ReturnAnnotationKind.NO_RETURN,
            id="qualified-extension",
        ),
        pytest.param("types.NoneType", "import types\n", ReturnAnnotationKind.NONE, id="qualified-none-type"),
        pytest.param("NoneType", "from types import NoneType\n", ReturnAnnotationKind.NONE, id="imported-none-type"),
        pytest.param(
            "Optional[int]",
            "from typing import Optional\n",
            ReturnAnnotationKind.NULLABLE,
            id="typing-optional",
        ),
        pytest.param(
            "typing.Union[str, None]",
            "import typing\n",
            ReturnAnnotationKind.NULLABLE,
            id="typing-union",
        ),
        pytest.param(
            "MaybeNever",
            "from application.types import NoReturn as MaybeNever\n",
            ReturnAnnotationKind.UNKNOWN,
            id="custom-import-alias-is-not-trusted",
        ),
        pytest.param(
            "Never",
            "from typing import NoReturn as Never\nclass Never:\n    pass\n",
            ReturnAnnotationKind.UNKNOWN,
            id="conflicting-local-type-and-import",
        ),
    ],
)
def test_classify_return_annotation_resolves_supported_typing_imports(
    annotation: str,
    source: str,
    expected: ReturnAnnotationKind,
    tmp_path: Path,
) -> None:
    """Only imports from typing modules establish Never/NoReturn and nullable aliases."""
    assert classify_return_annotation(annotation, module=_module(tmp_path, source)) is expected


def test_classify_return_annotation_uses_local_type_declarations(tmp_path: Path) -> None:
    """A locally declared return class is a known value type."""
    module = _module(tmp_path, "class DiffRange:\n    pass\n")
    assert classify_return_annotation("DiffRange", module=module) is ReturnAnnotationKind.VALUE


def test_classify_return_annotation_handles_aliased_and_combined_no_return_types(tmp_path: Path) -> None:
    """An imported Never alias stays no-return, while a union with a value is a value type."""
    module = _module(tmp_path, "from typing import Never as Bottom\n")
    assert classify_return_annotation("Bottom", module=module) is ReturnAnnotationKind.NO_RETURN
    assert classify_return_annotation("Bottom | int", module=module) is ReturnAnnotationKind.VALUE
    assert classify_return_annotation("Bottom | None", module=module) is ReturnAnnotationKind.NONE


@pytest.mark.parametrize(
    ("annotation", "imports"),
    [
        ("t.Optional[int]", ("import typing as t", "from types import SimpleNamespace as t")),
        ("Maybe[int]", ("from typing import Optional as Maybe", "import application as Maybe")),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_module_and_member_import_collisions_remain_unknown(
    annotation: str,
    imports: tuple[str, str],
    reverse: bool,
    tmp_path: Path,
) -> None:
    """Module and member aliases share a namespace, regardless of import order."""
    source = "\n".join(reversed(imports) if reverse else imports) + "\n"
    assert classify_return_annotation(annotation, module=_module(tmp_path, source)) is ReturnAnnotationKind.UNKNOWN
