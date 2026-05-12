"""CSV adapter for raw changed-method datasets.

Handles both schemas:
- Alexandria (Java): repo, github_link, parent_commit, file_path, method_name
- kotlin_dataset:    repo, commit, parent_commit, file_path, method_name,
                     method_start, method_end, hunk_id, github_link
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


@dataclass(frozen=True)
class RawChangedMethod:
    repo: str
    parent_commit: str
    file_path: str
    method_name: str
    child_commit: Optional[str] = None
    hunk_id: Optional[str] = None
    method_start: Optional[int] = None
    method_end: Optional[int] = None


@dataclass
class ChangeSetLoader:
    csv_path: str
    rows: List[RawChangedMethod] = field(default_factory=list)

    def __post_init__(self) -> None:
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rows.append(self._normalize(row))

    @staticmethod
    def _normalize(row: dict) -> RawChangedMethod:
        def _opt_int(v):
            if v is None or v == '':
                return None
            try:
                return int(v)
            except ValueError:
                return None

        return RawChangedMethod(
            repo=row['repo'],
            parent_commit=row['parent_commit'],
            file_path=row['file_path'],
            method_name=row['method_name'],
            child_commit=row.get('commit') or None,
            hunk_id=row.get('hunk_id') or None,
            method_start=_opt_int(row.get('method_start')),
            method_end=_opt_int(row.get('method_end')),
        )

    def for_commit(self, repo: str, parent_commit: str) -> List[RawChangedMethod]:
        return [r for r in self.rows
                if r.repo == repo and r.parent_commit == parent_commit]

    def parent_commits(self, repo: Optional[str] = None) -> Iterator[tuple]:
        seen = set()
        for r in self.rows:
            if repo is not None and r.repo != repo:
                continue
            key = (r.repo, r.parent_commit)
            if key in seen:
                continue
            seen.add(key)
            yield key
