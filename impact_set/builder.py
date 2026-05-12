"""Impact Set Builder: reverse BFS over the call graph from Change Set seeds."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ImpactEntry:
    seed_identifier: str
    seed_file_path: str
    impacted_identifier: str
    impacted_file_path: str
    hop_distance: int
    via: str   # 'call' | 'class' | 'mixed'

    def to_dict(self) -> dict:
        return asdict(self)


def _match_method_indices(file_path: str, method_name: str,
                          method_df, lang: str) -> List[int]:
    """Adapter around main_multi.search_query that returns matching indices.

    Compares the last token before '(' on the first non-annotation line of each
    method body, mirroring main_multi.search_query.
    """
    from parser import remove_comments_and_docstrings

    candidates = method_df.index[method_df.path == str(file_path)].tolist()
    matches: List[int] = []
    for idx in candidates:
        mtd = remove_comments_and_docstrings(method_df.method[idx], lang).split('\n')
        for i in range(len(mtd)):
            line = mtd[i]
            if line.lstrip().startswith('@') or not line.strip():
                continue
            if '(' not in line and i + 1 < len(mtd):
                line = line + mtd[i + 1]
            if '(' not in line:
                break
            head = line.split('(')[0].split()
            if not head:
                break
            token = head[-1].split('*/')[-1].split('.')[-1]
            if token == method_name:
                matches.append(idx)
            break
    return matches


def _simple_method_name(identifier: str) -> str:
    return identifier.split('.')[-1]


class ImpactSetBuilder:
    def __init__(self, lang: str = 'java',
                 max_hop: int = 3,
                 include_class_edges: bool = True):
        self.lang = lang
        self.max_hop = max_hop
        self.include_class_edges = include_class_edges

    def build(self, repo_path: Path, parent_commit: str,
              change_set: List[dict]) -> List[ImpactEntry]:
        from data import SoftwareRepo

        sw = SoftwareRepo(repo_path, parent_commit, lang=self.lang)
        method_df = sw.method_df
        call_edges = sw.call_edge_df
        class_edges = sw.class_edge_df

        reverse_adj, via_kind = self._build_reverse_adj(call_edges, class_edges)
        results: List[ImpactEntry] = []

        for entry in change_set:
            identifier = entry['identifier']
            file_path = entry['file_path']
            seeds = self._resolve_seeds(entry, method_df)
            if not seeds:
                continue

            visited: Dict[int, Tuple[int, str]] = {}
            queue: deque = deque()
            for s in seeds:
                visited[s] = (0, 'seed')
                queue.append((s, 0))

            while queue:
                node, hop = queue.popleft()
                if hop >= self.max_hop:
                    continue
                for nbr in reverse_adj.get(node, ()):
                    if nbr in visited:
                        continue
                    via = via_kind.get((node, nbr), 'call')
                    visited[nbr] = (hop + 1, via)
                    queue.append((nbr, hop + 1))

            for impacted_idx, (hop, via) in visited.items():
                if impacted_idx in seeds:
                    continue
                results.append(ImpactEntry(
                    seed_identifier=identifier,
                    seed_file_path=file_path,
                    impacted_identifier=self._df_method_signature(method_df, impacted_idx),
                    impacted_file_path=method_df.path[impacted_idx],
                    hop_distance=hop,
                    via=via,
                ))

        return results

    def _build_reverse_adj(self, call_edges, class_edges):
        reverse_adj: Dict[int, Set[int]] = defaultdict(set)
        via_kind: Dict[Tuple[int, int], str] = {}

        for _, row in call_edges.iterrows():
            caller, called = int(row['from_id']), int(row['to_id'])
            reverse_adj[called].add(caller)
            via_kind[(called, caller)] = 'call'

        if self.include_class_edges:
            for _, row in class_edges.iterrows():
                a, b = int(row['from_id']), int(row['to_id'])
                reverse_adj[a].add(b)
                reverse_adj[b].add(a)
                via_kind.setdefault((a, b), 'class')
                via_kind.setdefault((b, a), 'class')

        return reverse_adj, via_kind

    def _resolve_seeds(self, entry: dict, method_df) -> List[int]:
        identifier = entry['identifier']
        file_path = entry['file_path']
        kind = entry.get('kind', 'MODIFIED')

        if kind == 'VIRTUAL':
            return method_df.index[method_df.path == str(file_path)].tolist()

        return _match_method_indices(file_path, _simple_method_name(identifier),
                                     method_df, self.lang)

    @staticmethod
    def _df_method_signature(method_df, idx: int) -> str:
        # Take the first non-annotation line as a human-readable signature stub.
        body = method_df.method[idx]
        for line in body.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('@') and not stripped.startswith('//'):
                return stripped[:200]
        return body[:200]
