# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Public exports for module and attribute presence diagnostic codes."""

from docmethis_verify import dmt


def test_presence_codes_are_public_exports() -> None:
    """The canonical presence codes are importable by consumers."""
    assert dmt.DMT_1201 == "DMT-1201"
    assert dmt.DMT_1301 == "DMT-1301"
    assert dmt.DMT_1250 == "DMT-1250"
    assert dmt.DMT_4301 == "DMT-4301"
    assert {"DMT_1201", "DMT_1301", "DMT_1250", "DMT_4301"} <= set(dmt.__all__)
