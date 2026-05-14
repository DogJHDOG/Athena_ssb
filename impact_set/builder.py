"""Impact Set Builder — Athena ranking pipeline wrapper.

Calls `main_multi.generate_results` with a Change Set as the query list and
returns the ranked impact list (rank/RR/AP/hit@10 per query).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List


class ImpactSetBuilder:
    def __init__(self, lang: str,
                 pretrained_model_name: str = 'microsoft/graphcodebert-base',
                 finetuned_model_path: str = '',
                 weight: float = 0.5,
                 MAX: int = 10000,
                 nebr_num: int = 100,
                 nebr_order: int = 1,
                 version: str = 'baseline',
                 project_path: str = '.'):
        self.lang = lang
        self.pretrained_model_name = pretrained_model_name
        self.finetuned_model_path = finetuned_model_path
        self.weight = weight
        self.MAX = MAX
        self.nebr_num = nebr_num
        self.nebr_order = nebr_order
        self.version = version
        self.project_path = project_path

    def build(self, repo: str, repo_path: Path, parent_commit: str,
              change_set_entries: List[dict]) -> List[dict]:
        # Lazy imports: torch / tree_sitter / pandas are heavy.
        import extractor
        from data import SoftwareRepo
        from main_multi import generate_results

        path_lines = self._change_set_to_path_lines(change_set_entries)
        if not path_lines:
            return []

        software_repo = SoftwareRepo(repo_path, parent_commit, lang=self.lang)
        embed = self._build_embed(extractor)
        embed.load_finetuned_model()
        corpus_vecs = embed.extract_corpus_vecs(software_repo.method_df.method.values)

        args = self._make_args_namespace()
        results = generate_results(
            (repo, parent_commit, path_lines, software_repo, corpus_vecs, args)
        )
        return results[0]

    def _change_set_to_path_lines(self, entries: List[dict]) -> List[str]:
        out: List[str] = []
        for e in entries:
            if e.get('kind', 'MODIFIED') != 'MODIFIED':
                # VIRTUAL entries (Kotlin auto-generated methods) have no node in
                # method_df; skip — see Phase 5 follow-ups in the plan file.
                continue
            file_path = e['file_path']
            simple_name = str(e['identifier']).split('.')[-1]
            out.append(f"{file_path}<sep>{simple_name}")
        return out

    def _build_embed(self, extractor):
        name = self.pretrained_model_name
        if name == 'microsoft/codebert-base':
            return extractor.EmbedCodebert(name, self.finetuned_model_path, lang=self.lang)
        if name == 'microsoft/graphcodebert-base':
            return extractor.EmbedGraphcodebert(name, self.finetuned_model_path, lang=self.lang)
        if 'qwen' in name.lower():
            return extractor.EmbedQwen(name, self.finetuned_model_path, lang=self.lang)
        return extractor.EmbedUnixcoder(name, self.finetuned_model_path, lang=self.lang)

    def _make_args_namespace(self) -> argparse.Namespace:
        return argparse.Namespace(
            project_path=self.project_path,
            lang=self.lang,
            weight=self.weight,
            MAX=self.MAX,
            nebr_num=self.nebr_num,
            nebr_order=max(1, self.nebr_order),
            version=self.version,
            pretrained_model_name=self.pretrained_model_name,
            finetuned_model_path=self.finetuned_model_path,
        )
