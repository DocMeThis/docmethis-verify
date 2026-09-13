# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Consistency tests for the single DMT nomenclature registry (R0)."""

from __future__ import annotations

import re

import pytest

from docmethis_verify.dmt import (
    DIA_CODE_BY_IMPACT_KIND,
    DIA_CODES,
    DIA_IMPACT_KIND_BY_CODE,
    REGISTRY,
    CodeDMT,
    find_code,
)
from docmethis_verify.models.enums import PatchGranularity


def test_codes_are_unique_and_well_formatted() -> None:
    """Every registry code is unique and uses the canonical format."""
    codes = [entry.code for entry in REGISTRY]
    assert len(codes) == len(set(codes))
    for entry in REGISTRY:
        assert re.fullmatch(r"DMT-(?:[0-9]{4}|CORE-[0-9]{3})", entry.code)
        assert entry.description
    with pytest.raises(ValueError, match="invalid DMT code"):
        CodeDMT("DMT-123", "Obsolete code.", family=0, severity="warning")


def test_emitted_codes_have_a_declared_emitter() -> None:
    """A code marked as emitted is emitted by at least one declared emitter."""
    for entry in REGISTRY:
        if entry.status == "emitted":
            assert entry.emitter, f"{entry.code} is emitted but has no declared emitter"


def test_reserved_codes_have_no_emitter() -> None:
    """Reserved codes do not declare an emitter."""
    for entry in REGISTRY:
        if entry.status == "reserved":
            assert not entry.emitter


def test_fixability_and_granularity_are_consistent() -> None:
    """Granularity exists only on a fixable code.

    The inverse is valid: a complete insertion (e.g. DMT-1120, F0 flow) is
    fixable without targeted section/span/entry granularity.
    """
    for entry in REGISTRY:
        if entry.granularity is not None:
            assert entry.fixable, f"{entry.code} has granularity but is not fixable"
            assert entry.granularity in PatchGranularity


def test_find_code_and_reject_unknown_code() -> None:
    """find_code locates entries and rejects unknown codes."""
    assert isinstance(find_code("DMT-2001"), CodeDMT)
    with pytest.raises(ValueError, match="DMT code not found in registry"):
        find_code("DMT-CORE-998")


def test_class_aggregate_exception_code_is_check_only_and_not_fixable() -> None:
    """The class aggregate rule cannot be emitted by Verify or patched by Fix."""
    entry = find_code("DMT-4301")

    assert entry.status == "emitted"
    assert entry.emitter == frozenset({"check"})
    assert entry.fixable is False


def test_999_is_never_emitted() -> None:
    """DMT-CORE-999 is a configuration pseudo-code that can never be emitted."""
    entry = find_code("DMT-CORE-999")
    assert entry.status == "reserved"
    assert not entry.emitter
    assert not entry.fixable


def test_dia_codes_are_emitted_and_bijective() -> None:
    """Each DIA impact has a distinct public code emitted by Check."""
    assert DIA_CODE_BY_IMPACT_KIND == {
        "exposed_exception": "DMT-4201",
        "removed_exception": "DMT-4202",
        "io_effect": "DMT-7302",
        "observable_property": "DMT-7303",
        "override": "DMT-5201",
        "heritage": "DMT-5202",
    }
    assert set(DIA_CODE_BY_IMPACT_KIND) == {
        "exposed_exception",
        "removed_exception",
        "io_effect",
        "observable_property",
        "override",
        "heritage",
    }
    assert set(DIA_CODE_BY_IMPACT_KIND.values()) == set(DIA_CODES)
    assert {code: kind for kind, code in DIA_CODE_BY_IMPACT_KIND.items()} == DIA_IMPACT_KIND_BY_CODE
    for code in DIA_CODES:
        entry = find_code(code)
        assert entry.status == "emitted"
        assert entry.emitter == frozenset({"check"})
