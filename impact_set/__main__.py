"""CLI: `python -m impact_set ...` — run reverse BFS over Change Set seeds."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .builder import ImpactSetBuilder


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--repo-path', required=True)
    p.add_argument('--parent-commit', required=True)
    p.add_argument('--change-set', required=True, help="Change Set JSON path")
    p.add_argument('--lang', default='java', choices=['java', 'kotlin'])
    p.add_argument('--max-hop', type=int, default=3)
    p.add_argument('--no-class-edges', action='store_true',
                   help="exclude class_edge_df (same-file membership) from traversal")
    p.add_argument('--output', required=True)
    args = p.parse_args()

    with open(args.change_set, encoding='utf-8') as f:
        change_set = json.load(f)

    builder = ImpactSetBuilder(
        lang=args.lang,
        max_hop=args.max_hop,
        include_class_edges=not args.no_class_edges,
    )
    impacts = builder.build(
        repo_path=Path(args.repo_path),
        parent_commit=args.parent_commit,
        change_set=change_set,
    )

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump([e.to_dict() for e in impacts], f, ensure_ascii=False, indent=2)

    print(f"wrote {len(impacts)} impact entries to {args.output}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
