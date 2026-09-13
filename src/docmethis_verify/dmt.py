# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Single source registry for DMT nomenclature (grid v3, frozen in R0).

Source of truth for DocMeThis diagnostic codes. This module is the executable
authority for the public verification registry.

Three-axis diagnostic model:

- `severity`: documentation impact of the defect if it is real;
- `confidence`: detection reliability;
- `default_enabled`: whether the rule is enabled by default.

`disabled` is not a severity: the transitional technical schema
(`error | warning | disabled`) is derived through `technical_severity()`.

Allocation rules (universal non-reuse): a number that has been assigned, emitted,
or published is never reused for another defect, regardless of its initial
status. Reserved ranges: x9x per family (family experimental), 900-949
(cross-cutting experimental), and 980-998 (internal product use); 999 is a
configuration pseudo-code that can never be emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from docmethis_verify.models.enums import PatchGranularity

__all__ = [
    "CODE_BY_WARNING_KIND",
    "DIA_CODES",
    "DIA_CODE_BY_IMPACT_KIND",
    "DIA_IMPACT_KIND_BY_CODE",
    "DMT_0002",
    "DMT_0102",
    "DMT_999",
    "DMT_1101",
    "DMT_1110",
    "DMT_1120",
    "DMT_1130",
    "DMT_1140",
    "DMT_1150",
    "DMT_1201",
    "DMT_1210",
    "DMT_1220",
    "DMT_1230",
    "DMT_1240",
    "DMT_1250",
    "DMT_1301",
    "DMT_1310",
    "DMT_1320",
    "DMT_1330",
    "DMT_1340",
    "DMT_1350",
    "DMT_2001",
    "DMT_2002",
    "DMT_2003",
    "DMT_2120",
    "DMT_3001",
    "DMT_3010",
    "DMT_4001",
    "DMT_4002",
    "DMT_4101",
    "DMT_4102",
    "DMT_4201",
    "DMT_4202",
    "DMT_4301",
    "DMT_5201",
    "DMT_5202",
    "DMT_6000",
    "DMT_6049",
    "DMT_6051",
    "DMT_6200",
    "DMT_6201",
    "DMT_6202",
    "DMT_6210",
    "DMT_6211",
    "DMT_6212",
    "DMT_6218",
    "DMT_6220",
    "DMT_6240",
    "DMT_7001",
    "DMT_7002",
    "DMT_7200",
    "DMT_7302",
    "DMT_7303",
    "DOCSTRING_INSERTION_CODES",
    "EMITTED_CODES",
    "KNOWN_CODES",
    "REGISTRY",
    "UNDOCUMENTED_CODES",
    "CodeDMT",
    "find_code",
    "technical_severity",
]

type DMTSeverity = Literal["error", "warning", "info"]
type DMTConfidence = Literal["high", "medium", "low"]
type DMTStatus = Literal["emitted", "reserved", "experimental", "deprecated", "replaced"]
type TechnicalSeverity = Literal["error", "warning", "disabled"]

_CANONICAL_CODE_LENGTH = 4
_CORE_CODE_LENGTH = 8


@dataclass(frozen=True, slots=True)
class CodeDMT:
    """Registry entry: exact meaning of a DMT code.

    Attributes
    ----------
    code : str
        The DMT code in `DMT-XXXX` or `DMT-CORE-XXX` format.
    description : str
        Human-readable meaning of the code.
    family : int
        Hundreds place of the code, grouping codes by diagnostic family.
    severity : DMTSeverity
        Documentation impact of the defect if it is real.
    confidence : DMTConfidence
        Detection reliability of the rule.
    default_enabled : bool
        Whether the rule is enabled by default.
    status : DMTStatus
        Lifecycle status of the code in the registry.
    replaced_by : str | None
        Code that supersedes this one, when the code is deprecated.
    emitter : frozenset[str]
        Set of emitters allowed to emit this code.
    fixable : bool
        Whether the defect can be patched automatically.
    granularity : PatchGranularity | None
        Granularity of the patch applied by the fixer, when fixable.

    Raises
    ------
    ValueError
        If the code does not match the `DMT-XXXX` or `DMT-CORE-XXX` format.

    """

    code: str
    description: str
    family: int  # hundreds place
    severity: DMTSeverity
    confidence: DMTConfidence = "medium"
    default_enabled: bool = False
    status: DMTStatus = "reserved"
    replaced_by: str | None = None
    emitter: frozenset[str] = frozenset()
    fixable: bool = False
    granularity: PatchGranularity | None = None

    def __post_init__(self) -> None:
        """Validate the `DMT-XXXX` or `DMT-CORE-XXX` code format.

        Raises
        ------
        ValueError
            Explicitly raised.

        """
        suffix = self.code.removeprefix("DMT-")
        valid_format = self.code.startswith("DMT-") and (
            (len(suffix) == _CANONICAL_CODE_LENGTH and suffix.isdigit())
            or (suffix.startswith("CORE-") and len(suffix) == _CORE_CODE_LENGTH and suffix[5:].isdigit())
        )
        if not valid_format:
            msg = f"invalid DMT code: {self.code!r}"
            raise ValueError(msg)


DMT_1101 = "DMT-1101"
DMT_1201 = "DMT-1201"
DMT_1301 = "DMT-1301"
DMT_1110 = "DMT-1110"
DMT_1210 = "DMT-1210"
DMT_1310 = "DMT-1310"
DMT_1120 = "DMT-1120"
DMT_1220 = "DMT-1220"
DMT_1320 = "DMT-1320"
DMT_1130 = "DMT-1130"
DMT_1230 = "DMT-1230"
DMT_1330 = "DMT-1330"
DMT_1140 = "DMT-1140"
DMT_1240 = "DMT-1240"
DMT_1250 = "DMT-1250"
DMT_1340 = "DMT-1340"
DMT_1150 = "DMT-1150"
DMT_1350 = "DMT-1350"
DMT_2001 = "DMT-2001"
DMT_2002 = "DMT-2002"
DMT_2003 = "DMT-2003"
DMT_3001 = "DMT-3001"
DMT_4001 = "DMT-4001"
DMT_4002 = "DMT-4002"
DMT_4301 = "DMT-4301"
DMT_2120 = "DMT-2120"
DMT_3010 = "DMT-3010"
DMT_6201 = "DMT-6201"
DMT_6049 = "DMT-6049"
DMT_6202 = "DMT-6202"
DMT_6051 = "DMT-6051"
DMT_6200 = "DMT-6200"
DMT_6210 = "DMT-6210"
DMT_6218 = "DMT-6218"
DMT_6211 = "DMT-6211"
DMT_6212 = "DMT-6212"
DMT_6000 = "DMT-6000"
DMT_6220 = "DMT-6220"
DMT_4101 = "DMT-4101"
DMT_4102 = "DMT-4102"
DMT_6240 = "DMT-6240"
DMT_0002 = "DMT-0002"
DMT_0102 = "DMT-0102"
DMT_7001 = "DMT-7001"
DMT_7002 = "DMT-7002"
DMT_7200 = "DMT-7200"
DMT_4201 = "DMT-4201"
DMT_4202 = "DMT-4202"
DMT_5201 = "DMT-5201"
DMT_5202 = "DMT-5202"
DMT_7302 = "DMT-7302"
DMT_7303 = "DMT-7303"
DMT_999 = "DMT-CORE-999"

REGISTRY: tuple[CodeDMT, ...] = (
    CodeDMT(
        "DMT-CORE-000",
        "Unexpected internal error.",
        family=0,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="reserved",
    ),
    CodeDMT(
        "DMT-CORE-001",
        "Invalid configuration.",
        family=0,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="reserved",
    ),
    CodeDMT(
        "DMT-CORE-020",
        "File excluded or ignored by configuration.",
        family=0,
        severity="info",
        confidence="high",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-0001",
        "File cannot be analyzed.",
        family=0,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="reserved",
    ),
    CodeDMT(
        "DMT-CORE-030",
        "Unsupported language.",
        family=0,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="reserved",
    ),
    CodeDMT(
        "DMT-CORE-031",
        "Unsupported docstyle.",
        family=0,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="reserved",
    ),
    # DMT-1xx — Missing documentation (canonical types x visibility, groups of five).
    CodeDMT(
        "DMT-1101",
        "Public module has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1201",
        "Protected module has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1301",
        "Private module has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1401",
        "Other module has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1501",
        "Unknown module has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1110",
        "Public class has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1210",
        "Protected class has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1310",
        "Private class has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1410",
        "Other class has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1510",
        "Unknown class has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1120",
        "Public function has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1220",
        "Protected function has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1320",
        "Private function has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1420",
        "Other function has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1520",
        "Unknown function has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1130",
        "Public method has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1230",
        "Protected method has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1330",
        "Private method has no docstring.",
        family=1,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"audit", "check"}),
    ),
    CodeDMT(
        "DMT-1430",
        "Other method has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1530",
        "Unknown method has no docstring.",
        family=1,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1140",
        "Public property has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1240",
        "Protected property has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1340",
        "Private property has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1440",
        "Other property has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1540",
        "Unknown property has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1150",
        "Public attribute has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1250",
        "Protected attribute has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1350",
        "Private attribute has no docstring.",
        family=1,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-1450",
        "Other attribute has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-1550",
        "Unknown attribute has no docstring.",
        family=1,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_2001,
        "Parameter is undocumented.",
        family=2,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.ENTRY,
    ),
    CodeDMT(
        DMT_2002,
        "Documented parameter is absent from the signature.",
        family=2,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.ENTRY,
    ),
    CodeDMT(
        DMT_2003,
        "Inconsistent parameter order.",
        family=2,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.SECTION,
    ),
    CodeDMT(
        DMT_3001,
        "Return value is undocumented.",
        family=2,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.SECTION,
    ),
    CodeDMT(
        "DMT-3002",
        "Documented return value has no detected return.",
        family=2,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_4001,
        "Raised exception is undocumented.",
        family=2,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.ENTRY,
    ),
    CodeDMT(
        DMT_4002,
        "Documented exception has no detected raise source.",
        family=2,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.ENTRY,
    ),
    CodeDMT(
        DMT_4301,
        "Raised exception is undocumented in a class-level aggregate.",
        family=2,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
    ),
    CodeDMT(
        "DMT-2201",
        "Default value is undocumented.",
        family=2,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-3101",
        "Yield is undocumented.",
        family=2,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-3102",
        "Documented yield has no detected yield.",
        family=2,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-2100",
        "Parameter has no type annotation.",
        family=3,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-3003",
        "Return type is missing from the annotation.",
        family=3,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_2120,
        "Parameter type is absent from the docstring.",
        family=3,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.SPAN,
    ),
    CodeDMT(
        DMT_3010,
        "Return type is absent from the docstring.",
        family=3,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "check", "audit"}),
        fixable=True,
        granularity=PatchGranularity.SPAN,
    ),
    CodeDMT(
        "DMT-2125",
        "Documented parameter type is inconsistent with the annotation.",
        family=3,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-3011",
        "Documented return type is inconsistent with the annotation.",
        family=3,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_6201,
        "Unknown section.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6049,
        "Section is probably misspelled.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-6050",
        "Non-canonical section alias.",
        family=4,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-6047",
        "Duplicate section.",
        family=4,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-6048",
        "Section is invalid for this symbol type.",
        family=4,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_6202,
        "Section order is invalid.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6051,
        "Missing blank line.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6200,
        "Incorrect underline length.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6210,
        "Missing colon in a parameter entry.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6218,
        "Missing type for a parameter.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6211,
        "Empty parameter name.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6212,
        "Incorrect spacing after a colon.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6000,
        "Inconsistent indentation.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6220,
        "Returns type and description are reversed.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_4101,
        "Missing description for an exception in Raises.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_4102,
        "Invalid exception name in Raises.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_6240,
        "Raises type and description are on the same line.",
        family=4,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        DMT_0002,
        "Docstring cannot be parsed.",
        family=4,
        severity="error",
        confidence="high",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-0101",
        "Mixed style detected.",
        family=4,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_0102,
        "Style non-conformance (aggregate, pure fallback).",
        family=4,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_7001,
        "Missing or empty summary.",
        family=5,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"check", "audit"}),
    ),
    CodeDMT(
        "DMT-8001",
        "Missing Parameters section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8002",
        "Missing Returns section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8003",
        "Missing Yields section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8004",
        "Missing Raises section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8005",
        "Missing Attributes section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8010",
        "Missing Examples section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8011",
        "Missing Notes section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8012",
        "Missing See Also section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8013",
        "Missing References section.",
        family=5,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_7002,
        "Summary is too short.",
        family=6,
        severity="warning",
        confidence="high",
        default_enabled=False,
        status="emitted",
        emitter=frozenset({"audit"}),
    ),
    CodeDMT(
        "DMT-7003",
        "Summary is too generic.",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-7004",
        "Summary is identical to the symbol name.",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-7101",
        "Parameter description is too weak.",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-7102",
        "Return description is too weak.",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_7200,
        "Boilerplate documentation (including forbidden vocabulary).",
        family=6,
        severity="warning",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"verify", "audit"}),
    ),
    CodeDMT(
        "DMT-7301",
        "Description is inconsistent with detected behavior.",
        family=6,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-7401",
        "Over-interpretation or overclaim.",
        family=6,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-7501",
        "Semantic drift.",
        family=6,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_4201,
        "Exception exposed after a change is not aligned with Raises (DIA).",
        family=6,
        severity="error",
        confidence="high",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        DMT_4202,
        "Documented exception removed from behavior (DIA).",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        DMT_7302,
        "I/O effect changed without corresponding documentation (DIA).",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        DMT_7303,
        "Observable property changed without corresponding documentation (DIA).",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        DMT_5201,
        "Method origin or override changed without corresponding documentation (DIA).",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        DMT_5202,
        "Inheritance changed without corresponding documentation (DIA).",
        family=6,
        severity="warning",
        confidence="medium",
        default_enabled=True,
        status="emitted",
        emitter=frozenset({"check"}),
        fixable=True,
    ),
    CodeDMT(
        "DMT-8201",
        "Nonexistent symbolic reference (generic symbolic).",
        family=7,
        severity="error",
        confidence="high",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8101",
        "See Also item not found (specialization, takes precedence over 700).",
        family=7,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8301",
        "Invalid external link (independent category).",
        family=7,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8401",
        "Malformed bibliographic reference (independent category).",
        family=7,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8501",
        "Invalid Sphinx target (may take precedence over 700).",
        family=7,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-8502",
        "Invalid MkDocs target (may take precedence over 700).",
        family=7,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-9001",
        "Undocumented __all__ entry (Python).",
        family=8,
        severity="warning",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        "DMT-9002",
        "Public export is inconsistent with __all__ (Python).",
        family=8,
        severity="error",
        confidence="medium",
        default_enabled=False,
        status="reserved",
    ),
    CodeDMT(
        DMT_999,
        "Configuration pseudo-code (generic override), never emit-able.",
        family=9,
        severity="info",
        confidence="high",
        default_enabled=False,
        status="reserved",
    ),
)

_CODE_BY_CODE: dict[str, CodeDMT] = {entry.code: entry for entry in REGISTRY}

KNOWN_CODES: frozenset[str] = frozenset(_CODE_BY_CODE)

EMITTED_CODES: frozenset[str] = frozenset(entry.code for entry in REGISTRY if entry.status == "emitted")

DIA_CODE_BY_IMPACT_KIND: dict[str, str] = {
    "exposed_exception": DMT_4201,
    "removed_exception": DMT_4202,
    "io_effect": DMT_7302,
    "observable_property": DMT_7303,
    "override": DMT_5201,
    "heritage": DMT_5202,
}

DIA_IMPACT_KIND_BY_CODE: dict[str, str] = {code: impact_kind for impact_kind, code in DIA_CODE_BY_IMPACT_KIND.items()}
DIA_CODES: frozenset[str] = frozenset(DIA_IMPACT_KIND_BY_CODE)

UNDOCUMENTED_CODES: frozenset[str] = frozenset(
    entry.code for entry in REGISTRY if entry.family == 1 and entry.status == "emitted"
)

DOCSTRING_INSERTION_CODES: frozenset[str] = frozenset({DMT_1120, DMT_1220, DMT_1320, DMT_1130, DMT_1230, DMT_1330})

CODE_BY_WARNING_KIND: dict[str, str] = {
    "empty_summary": DMT_7001,
    "unknown_section": "DMT-6201",
    "misspelled_section": "DMT-6049",
    "section_order": "DMT-6202",
    "missing_blank_line": "DMT-6051",
    "underline_length": "DMT-6200",
    "param_missing_colon": "DMT-6210",
    "param_missing_type": "DMT-6218",
    "param_empty_name": "DMT-6211",
    "param_colon_spacing": "DMT-6212",
    "inconsistent_indentation": "DMT-6000",
    "return_type_and_desc_inverted": "DMT-6220",
    "raises_missing_description": "DMT-4101",
    "raises_invalid_name": "DMT-4102",
    "raises_type_and_desc_on_same_line": "DMT-6240",
}


def find_code(code: str) -> CodeDMT:
    """Return the registry entry for a DMT code.

    Parameters
    ----------
    code : str
        The DMT code to look up in the registry.

    Returns
    -------
    CodeDMT
        A CodeDMT object representing the registry entry for the given DMT code.

    Raises
    ------
    ValueError
        Explicitly raised.

    """
    try:
        return _CODE_BY_CODE[code]
    except KeyError as exc:
        msg = f"DMT code not found in registry: {code!r}"
        raise ValueError(msg) from exc


def technical_severity(code: str) -> TechnicalSeverity:
    """Return the transitional technical severity for the current check schema.

    `default_enabled: false` and `severity: info` map to `disabled` while the
    schema does not expose these two axes. Remove this during migration to the three-axis model.

    Parameters
    ----------
    code : str
        The check code whose transitional technical severity should be determined.

    Returns
    -------
    TechnicalSeverity
        Returns the transitional technical severity for the current check schema. A severity of 'disabled' is returned when the
        code entry is not default-enabled or has severity 'info'; otherwise, the entry's severity is returned as a
        TechnicalSeverity.

    """
    entry = find_code(code)
    if not entry.default_enabled or entry.severity == "info":
        return "disabled"
    return entry.severity
