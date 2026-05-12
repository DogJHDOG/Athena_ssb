"""Change Set orchestrator: load CSV, build SoftwareRepo at parent_commit, apply rule."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .entry import ChangeSetEntry
from .loader import ChangeSetLoader, RawChangedMethod
from .rules import get_rule


class ChangeSetBuilder:
    def __init__(self, lang: str = 'java'):
        self.lang = lang
        self.rule = get_rule(lang)

    def build(self, repo_path: Path, parent_commit: str,
              raw_methods: List[RawChangedMethod]) -> List[ChangeSetEntry]:
        from data import SoftwareRepo

        software_repo = SoftwareRepo(repo_path, parent_commit, lang=self.lang)
        return self.rule.apply(raw_methods, software_repo)

    def build_from_csv(self, repo: str, repo_path: Path, parent_commit: str,
                       csv_path: str) -> List[ChangeSetEntry]:
        loader = ChangeSetLoader(csv_path)
        raw = loader.for_commit(repo, parent_commit)
        if not raw:
            return []
        return self.build(repo_path, parent_commit, raw)
