"""Java rule: passthrough — Java's CSV already lists all explicitly changed methods."""

from __future__ import annotations

from typing import List

from ..entry import ChangeSetEntry
from .base import Rule


class JavaRule(Rule):
    def apply(self, raw_methods, software_repo) -> List[ChangeSetEntry]:
        out: List[ChangeSetEntry] = []
        for r in raw_methods:
            out.append(ChangeSetEntry(
                repo=r.repo,
                parent_commit=r.parent_commit,
                file_path=r.file_path,
                identifier=r.method_name,
                kind='MODIFIED',
                source='real',
                class_name=None,
                child_commit=r.child_commit,
                hunk_id=r.hunk_id,
            ))
        return out
