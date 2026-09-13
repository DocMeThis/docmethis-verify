# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""NumPy docstring format warning model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FormatWarningSpan:
    """Half-open character bounds in the normalized docstring body."""

    start: int
    end: int

    def __post_init__(self) -> None:
        """Validate non-negative, ordered character offsets."""
        if type(self.start) is not int or self.start < 0:
            msg = "Format warning span start must be a non-negative integer."
            raise ValueError(msg)
        if type(self.end) is not int or self.end < self.start:
            msg = "Format warning span end must be an ordered integer."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FormatWarning:
    """Format warning detected by the docstring validator.

    Attributes
    ----------
    section : str
        Docstring section the warning applies to.
    kind : str
        Kind of format warning.
    detail : str
        Human-readable description of the warning.
    line : int | None
        Line number the warning applies to, when known.
    discriminator : str | None
        Discriminator used to deduplicate identical warnings, when needed.
    expected : str | None
        Structured expected value used by a deterministic correction, when known.
    span : FormatWarningSpan | None
        Warning-local half-open character span in the normalized docstring body.

    """

    section: str
    kind: str
    detail: str
    line: int | None = None
    discriminator: str | None = None
    expected: str | None = None
    span: FormatWarningSpan | None = None
