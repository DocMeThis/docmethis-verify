# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Text line normalization utilities."""

from collections.abc import Sequence

__all__ = ["is_blank_line", "trim_outer_blank_lines"]


def is_blank_line(line: str) -> bool:
    """Return ``True`` if the line is blank, including spaces and tabs.

    Parameters
    ----------
    line : str
        The text line to check for blankness.

    Returns
    -------
    bool
        True if the line is blank, including spaces and tabs; False otherwise.

    """
    return not line.strip()


def trim_outer_blank_lines(lines: Sequence[str]) -> tuple[str, ...]:
    """Remove only blank lines at the edges.

    Parameters
    ----------
    lines : Sequence[str]
        The sequence of lines to process; only blank lines at the beginning and end are removed.

    Returns
    -------
    tuple[str, ...]
        A tuple containing the input lines with any leading and trailing blank lines removed.

    """
    start_index = 0
    end_index = len(lines)

    while start_index < end_index and is_blank_line(lines[start_index]):
        start_index += 1

    while end_index > start_index and is_blank_line(lines[end_index - 1]):
        end_index -= 1

    return tuple(lines[start_index:end_index])
