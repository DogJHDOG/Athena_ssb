"""Language-specific rule interface for Change Set enrichment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class Rule(ABC):
    """Transforms raw changed-method rows into enriched ChangeSet entries.

    Implementations may add VIRTUAL entries (e.g., compiler-generated methods)
    or normalize identifiers (e.g., top-level functions to FileNameKt.func).
    """

    @abstractmethod
    def apply(self, raw_methods, software_repo) -> List:
        """Return a list of ChangeSetEntry given raw methods and a SoftwareRepo."""


def get_rule(lang: str) -> Rule:
    if lang == 'java':
        from .java import JavaRule
        return JavaRule()
    if lang == 'kotlin':
        from .kotlin import KotlinRule
        return KotlinRule()
    raise ValueError(f"unknown lang: {lang}")
