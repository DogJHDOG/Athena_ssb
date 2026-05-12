"""CLI: `python -m change_set ...` — build a Change Set for one (repo, parent_commit)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .builder import ChangeSetBuilder


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True,
                   help="repo name as it appears in the CSV (e.g., Kotlin/kotlinx.coroutines)")
    p.add_argument('--repo-path', required=True,
                   help="local path to the cloned repo")
    p.add_argument('--parent-commit', required=True)
    p.add_argument('--csv', required=True, help="raw changed-method CSV path")
    p.add_argument('--lang', default='java', choices=['java', 'kotlin'])
    p.add_argument('--output', required=True, help="output JSON path")
    args = p.parse_args()

    builder = ChangeSetBuilder(lang=args.lang)
    entries = builder.build_from_csv(
        repo=args.repo,
        repo_path=Path(args.repo_path),
        parent_commit=args.parent_commit,
        csv_path=args.csv,
    )

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump([e.to_dict() for e in entries], f, ensure_ascii=False, indent=2)

    print(f"wrote {len(entries)} entries to {args.output}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
