"""CLI: `python -m impact_set ...` — Athena ranking over a Change Set."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .builder import ImpactSetBuilder


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True,
                   help="repo identifier as it appears in the CSV (e.g., apache/ant-ivy)")
    p.add_argument('--repo-path', required=True,
                   help="local path to the cloned repo")
    p.add_argument('--parent-commit', required=True)
    p.add_argument('--change-set', required=True, help="Change Set JSON path")
    p.add_argument('--lang', default='java', choices=['java', 'kotlin'])
    p.add_argument('--pretrained-model-name', default='microsoft/graphcodebert-base')
    p.add_argument('--finetuned-model-path', required=True)
    p.add_argument('--weight', type=float, default=0.5)
    p.add_argument('--MAX', type=int, default=10000)
    p.add_argument('--nebr-num', type=int, default=100)
    p.add_argument('--nebr-order', type=int, default=1)
    p.add_argument('--version', default='baseline')
    p.add_argument('--project-path', default='.',
                   help="root such that <project-path>/<repo> == <repo-path>")
    p.add_argument('--output', required=True)
    args = p.parse_args()

    with open(args.change_set, encoding='utf-8') as f:
        change_set = json.load(f)

    builder = ImpactSetBuilder(
        lang=args.lang,
        pretrained_model_name=args.pretrained_model_name,
        finetuned_model_path=args.finetuned_model_path,
        weight=args.weight,
        MAX=args.MAX,
        nebr_num=args.nebr_num,
        nebr_order=args.nebr_order,
        version=args.version,
        project_path=args.project_path,
    )
    results = builder.build(
        repo=args.repo,
        repo_path=Path(args.repo_path),
        parent_commit=args.parent_commit,
        change_set_entries=change_set,
    )

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=_json_default)

    print(f"wrote {len(results)} impact entries to {args.output}", file=sys.stderr)
    return 0


def _json_default(obj):
    # numpy scalars / arrays from generate_results' output.
    try:
        import numpy as np
    except ImportError:
        raise TypeError(f"unserializable type {type(obj)!r}")
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"unserializable type {type(obj)!r}")


if __name__ == '__main__':
    raise SystemExit(main())
