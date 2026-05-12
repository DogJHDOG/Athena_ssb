"""Output dataclass for the Change Set Builder."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class ChangeSetEntry:
    repo: str
    parent_commit: str
    file_path: str
    identifier: str            # method name or qualified (e.g., FooKt.bar, User.copy)
    kind: str                  # MODIFIED | VIRTUAL
    source: str                # real | implicit
    class_name: Optional[str] = None
    child_commit: Optional[str] = None
    hunk_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
