"""Aggregate per-commit Impact Set JSON outputs into a single ranked CSV report.

Output columns mirror `main_multi.py`'s `results_<level>.csv`
(repo, parent commit, method path, rank, RR, AP, hit@10, ...).

stdout summary: queries, mean RR, mean AP, mean hit@10.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import List

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--impact-dir', required=True,
                   help="directory containing impact_set_*.json files")
    p.add_argument('--report', required=True, help="output CSV path")
    args = p.parse_args()

    rows: List[dict] = []
    for path in sorted(glob.glob(os.path.join(args.impact_dir, '*.json'))):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        rows.extend(data)

    os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.report, index=False)

    summary: dict = {'queries': len(df)}
    if not df.empty:
        for col in ('RR', 'AP', 'hit@10'):
            if col in df.columns:
                summary[f'mean_{col}'] = float(df[col].mean())
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
