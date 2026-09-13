# Copyright (c) 2026 DocMeThis SAS. All rights reserved.

"""Helpers for explicit forbidden-vocabulary policies."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

__all__ = ["compile_forbidden_patterns", "load_forbidden_terms"]


def compile_forbidden_patterns(terms: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    """Compile one request-local pattern per forbidden term.

    Parameters
    ----------
    terms : Iterable[str]
        An iterable of forbidden terms to compile into regex patterns.

    Returns
    -------
    tuple[re.Pattern[str], ...]
        A tuple of compiled regular expression patterns, one for each forbidden term, each matching the term as a whole word in a
        case-insensitive manner.

    """
    return tuple(re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE) for term in terms)


def load_forbidden_terms(path: Path) -> tuple[str, ...]:
    """Load a project vocabulary file without retaining global state.

    Parameters
    ----------
    path : Path
        Path to the project vocabulary file to load.

    Returns
    -------
    tuple[str, ...]
        A tuple of strings containing the unique non-empty vocabulary terms in the order they appeared in the file, excluding
        blank lines and lines starting with '#'. Duplicate terms are removed.

    """
    terms: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if term and not term.startswith("#") and term not in terms:
            terms.append(term)
    return tuple(terms)
