# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Documentary policy is independent of the complete AST exception facts."""

from pathlib import Path

import pytest
from docmethis_extract_python.api import ConfigurationDocmethis, analyze_project, iter_functions

from docmethis_verify import VerificationRequest, documentable_exceptions
from docmethis_verify.docstring.models import DocstringRaise, GeneratedDocstring
from docmethis_verify.verification.verifier import verify


@pytest.mark.parametrize("depth", [0, 1, 2, 4])
def test_verification_uses_the_same_scope_for_missing_and_ghost_raises(tmp_path: Path, depth: int) -> None:
    """Known deeper facts are excluded by policy, never requested again after removal."""
    (tmp_path / "module.py").write_text(
        "def a():\n    b()\ndef b():\n    c()\ndef c():\n    raise ValueError('bad')\n",
        encoding="utf-8",
    )
    project = analyze_project(tmp_path, ConfigurationDocmethis(exception_analysis_depth=4), skip_dynamic=True, write_cache=False)
    record = next(function for function in iter_functions(project.modules) if function.qualified_name.endswith(".a"))
    original = tuple(record.exceptions)
    for documented in (False, True):
        generated = GeneratedDocstring(
            summary="Run the operation.",
            raises=(DocstringRaise(exception="ValueError", description="If invalid."),) if documented else (),
        )
        response = verify(
            VerificationRequest(generated_docstring=generated, function_record=record, exception_documentation_depth=depth)
        )
        errors = [error for error in response.errors if error.dmt_code in {"DMT-4001", "DMT-4002"}]
        assert [error.dmt_code for error in errors] == (
            ["DMT-4002"] if documented and depth < 2 else ["DMT-4001"] if not documented and depth >= 2 else []
        )
        if errors and depth < 2:
            assert "outside the configured documentation depth" in errors[0].detail
    assert tuple(record.exceptions) == original
    assert len(documentable_exceptions(record, depth=depth)) == (1 if depth >= 2 else 0)
