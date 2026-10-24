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
    """Extract a module to provide authentic import and local-class facts.

    Parameters
    ----------
    tmp_path : Path
        Writes the given source text to a file named module.py inside the provided temporary directory path, then extracts a
        module record from that file with the module name "module", is_stub and is_test both false, and file_hash "test"; asserts
        the record is not None and returns it.
    source : str
        Accepts a required positional-or-keyword parameter named source annotated as str. Writes the source text to a file named
        module.py under tmp_path, extracts a module record from that file, asserts the record is not None, and returns the
        resulting ModuleRecord.

    Returns
    -------
    ModuleRecord
        Returns the ModuleRecord produced by extracting the written module file. The extraction result is asserted to be non-None
        before being returned.
    """
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
    """Unresolved names stay unknown, while built-in and literal facts classify directly.

    Parameters
    ----------
    annotation : str | None
        Accepts a positional-or-keyword parameter named annotation, annotated as str | None, with no default value. The function
        passes it to classify_return_annotation and asserts that the result is the expected value.
    expected : ReturnAnnotationKind
        Passed as the second argument to classify_return_annotation and compared against its return value with an identity
        assertion.
    """
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
    """Only imports from typing modules establish Never/NoReturn and nullable aliases.

    Parameters
    ----------
    annotation : str
        Accepts a string value for the annotation parameter and uses it as the annotation argument passed to
        classify_return_annotation.
    source : str
        A required string argument named source, passed positionally or by keyword. The test writes it as the content of a
        temporary module (via _module) so that classify_return_annotation can resolve typing imports from that module's source.
    expected : ReturnAnnotationKind
        The expected value is a ReturnAnnotationKind supplied by the test and compared against the identical value returned by
        classify_return_annotation, using the test's temporary module built from the source. No default is provided.
    tmp_path : Path
        Passed as a positional-or-keyword argument annotated as Path, with no default. Its value is used to build a module via
        _module together with source, and that module is passed to classify_return_annotation.
    """
    assert classify_return_annotation(annotation, module=_module(tmp_path, source)) is expected


def test_classify_return_annotation_uses_local_type_declarations(tmp_path: Path) -> None:
    """A locally declared return class is a known value type.

    Parameters
    ----------
    tmp_path : Path
        Accepts a pathlib.Path argument named tmp_path with no default. Passes it to the project helper _module to construct a
        module from source declaring a local DiffRange class, then asserts that classify_return_annotation with that module
        returns ReturnAnnotationKind.VALUE.
    """
    module = _module(tmp_path, "class DiffRange:\n    pass\n")
    assert classify_return_annotation("DiffRange", module=module) is ReturnAnnotationKind.VALUE


def test_classify_return_annotation_handles_aliased_and_combined_no_return_types(tmp_path: Path) -> None:
    """An imported Never alias stays no-return, while a union with a value is a value type.

    Parameters
    ----------
    tmp_path : Path
        Receives a filesystem path used as the location for a test module created from source text defining an alias for
        typing.Never. The test then checks that classifying the alias name yields a no-return kind, that classifying its union
        with int yields a value kind, and that classifying its union with None yields a none kind.
    """
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
    """Module and member aliases share a namespace, regardless of import order.

    Parameters
    ----------
    annotation : str
        Accepts a string annotation that is passed directly to classify_return_annotation and asserted to classify as
        ReturnAnnotationKind.UNKNOWN.
    imports : tuple[str, str]
        A required positional-or-keyword parameter annotated as a tuple of two strings. It supplies two import statements whose
        order is reversed before being joined into module source when reverse is true, otherwise used as given.
    reverse : bool
        When reverse is true, the two import statements are joined in reversed order to build the source; otherwise they are
        joined in their given order. The test then asserts that classify_return_annotation returns ReturnAnnotationKind.UNKNOWN
        for the annotation and the module created from that source.
    tmp_path : Path
        tmp_path is a required positional or keyword argument annotated as Path. It is passed to the _module helper to supply the
        module used by the test.
    """
    source = "\n".join(reversed(imports) if reverse else imports) + "\n"
    assert classify_return_annotation(annotation, module=_module(tmp_path, source)) is ReturnAnnotationKind.UNKNOWN
