"""Evaluate Impact Set outputs against the CSV's hunk_id / parent_commit ground truth.

Metrics: Precision@k, Recall@k, MRR.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

import pandas as pd

from change_set.loader import ChangeSetLoader, RawChangedMethod


def _simple_name_from_signature(sig: str) -> str:
    """Extract the method name token from a signature stub (last token before '(')."""
    if '(' not in sig:
        tokens = sig.split()
        return tokens[-1] if tokens else sig
    head = sig.split('(')[0].split()
    if not head:
        return ''
    return head[-1].split('*/')[-1].split('.')[-1]


def _simple_name_from_identifier(identifier: str) -> str:
    return identifier.split('.')[-1]


def _ground_truth_groups(rows: List[RawChangedMethod]) -> Dict[Tuple, List[RawChangedMethod]]:
    """Group rows into co-change sets.

    Kotlin schema (with hunk_id): key = (repo, child_commit, hunk_id).
    Java schema:                  key = (repo, parent_commit).
    """
    groups: Dict[Tuple, List[RawChangedMethod]] = defaultdict(list)
    for r in rows:
        if r.hunk_id is not None and r.child_commit is not None:
            key = (r.repo, r.child_commit, r.hunk_id)
        else:
            key = (r.repo, r.parent_commit)
        groups[key].append(r)
    return groups


def _evaluate(impact_entries: List[dict], rows: List[RawChangedMethod],
              ks: List[int]) -> List[dict]:
    groups = _ground_truth_groups(rows)
    # Index rows by (repo, parent_commit, file_path, method_name) for seed → group lookup.
    row_index: Dict[Tuple, List[RawChangedMethod]] = defaultdict(list)
    for r in rows:
        row_index[(r.repo, r.parent_commit, r.file_path, r.method_name)].append(r)

    per_seed = defaultdict(list)
    for e in impact_entries:
        per_seed[(e['seed_file_path'], e['seed_identifier'])].append(e)

    out: List[dict] = []
    for (seed_path, seed_id), impacts in per_seed.items():
        seed_simple = _simple_name_from_identifier(seed_id)
        # Find any raw row matching this seed to identify its ground-truth group.
        candidates = [r for key, rs in row_index.items() if key[2] == seed_path
                      and key[3] == seed_simple for r in rs]
        if not candidates:
            continue
        seed_row = candidates[0]
        gt_groups = [g for g in groups.values() if seed_row in g]
        if not gt_groups:
            continue
        gt = {(g_row.file_path, g_row.method_name) for grp in gt_groups for g_row in grp
              if (g_row.file_path, g_row.method_name) != (seed_path, seed_simple)}
        if not gt:
            continue

        ranked = sorted(impacts, key=lambda x: (x['hop_distance'], x['impacted_file_path']))
        ranked_pairs = [(ie['impacted_file_path'],
                         _simple_name_from_signature(ie['impacted_identifier']))
                        for ie in ranked]

        first_hit_rank = next((i + 1 for i, p in enumerate(ranked_pairs) if p in gt), None)
        mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0

        row = {
            'seed_file_path': seed_path,
            'seed_identifier': seed_id,
            'gt_size': len(gt),
            'impact_size': len(ranked_pairs),
            'mrr': mrr,
        }
        for k in ks:
            top_k = ranked_pairs[:k]
            hits = sum(1 for p in top_k if p in gt)
            row[f'precision@{k}'] = hits / k if k else 0.0
            row[f'recall@{k}'] = hits / len(gt) if gt else 0.0
        out.append(row)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--impact-dir', required=True,
                   help="directory containing impact_set_*.json files")
    p.add_argument('--csv', required=True, help="raw changed-method CSV path")
    p.add_argument('--report', required=True, help="output CSV path")
    p.add_argument('--ks', default='1,5,10', help="comma-separated k values")
    args = p.parse_args()

    ks = [int(x) for x in args.ks.split(',') if x.strip()]

    loader = ChangeSetLoader(args.csv)

    all_impacts: List[dict] = []
    for path in sorted(glob.glob(os.path.join(args.impact_dir, '*.json'))):
        with open(path, encoding='utf-8') as f:
            all_impacts.extend(json.load(f))

    rows = _evaluate(all_impacts, loader.rows, ks)
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
    df.to_csv(args.report, index=False)

    if not df.empty:
        summary = {'queries': len(df), 'mean_mrr': float(df['mrr'].mean())}
        for k in ks:
            summary[f'mean_precision@{k}'] = float(df[f'precision@{k}'].mean())
            summary[f'mean_recall@{k}'] = float(df[f'recall@{k}'].mean())
        print(json.dumps(summary, indent=2))
    else:
        print('{"queries": 0}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
