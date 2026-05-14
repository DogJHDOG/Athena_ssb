"""Smoke test: ImpactSetBuilder.build wraps main_multi.generate_results.

Mocks the heavy dependencies (SoftwareRepo, Embed*, generate_results) so the
test runs without torch / tree-sitter / pandas-on-disk.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock


def _install_stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class WrapsAthenaTest(unittest.TestCase):
    def setUp(self):
        # Stub heavy modules before ImpactSetBuilder.build imports them.
        self._stubbed = []

        software_repo_obj = MagicMock(name='SoftwareRepo')
        software_repo_obj.method_df.method.values = ['m0', 'm1', 'm2']
        SoftwareRepoCls = MagicMock(return_value=software_repo_obj)
        self._stubbed.append(('data', sys.modules.get('data')))
        _install_stub_module('data', SoftwareRepo=SoftwareRepoCls)

        embed_instance = MagicMock(name='EmbedGraphcodebert')
        embed_instance.extract_corpus_vecs.return_value = [[0.0]] * 3
        EmbedCls = MagicMock(return_value=embed_instance)
        self._stubbed.append(('extractor', sys.modules.get('extractor')))
        _install_stub_module(
            'extractor',
            EmbedCodebert=EmbedCls,
            EmbedGraphcodebert=EmbedCls,
            EmbedUnixcoder=EmbedCls,
            EmbedQwen=EmbedCls,
        )

        # generate_results returns the documented Athena output shape:
        # results[level] is a list of per-query dicts.
        sentinel_row = {'method path': 'X.kt/foo', 'rank': 1, 'RR': 1.0,
                        'AP': 1.0, 'hit@10': 1}
        self.generate_results = MagicMock(return_value=[[sentinel_row]])
        self._stubbed.append(('main_multi', sys.modules.get('main_multi')))
        _install_stub_module('main_multi', generate_results=self.generate_results)

        # Save references for assertions.
        self.SoftwareRepoCls = SoftwareRepoCls
        self.EmbedCls = EmbedCls
        self.embed_instance = embed_instance
        self.sentinel_row = sentinel_row

        # Make sure builder is freshly imported so its lazy imports pick up stubs.
        for mod_name in list(sys.modules):
            if mod_name.startswith('impact_set'):
                del sys.modules[mod_name]

    def tearDown(self):
        for name, original in self._stubbed:
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_modified_entries_become_path_lines_and_virtual_skipped(self):
        from impact_set.builder import ImpactSetBuilder

        change_set = [
            {'file_path': 'a/A.kt', 'identifier': 'A.foo', 'kind': 'MODIFIED'},
            {'file_path': 'a/A.kt', 'identifier': 'A.copy', 'kind': 'VIRTUAL'},
            {'file_path': 'b/B.kt', 'identifier': 'B.bar', 'kind': 'MODIFIED'},
        ]
        builder = ImpactSetBuilder(
            lang='kotlin',
            pretrained_model_name='microsoft/graphcodebert-base',
            finetuned_model_path='/tmp/model.bin',
            project_path='/tmp/proj',
        )
        out = builder.build(
            repo='Kotlin/x',
            repo_path=Path('/tmp/proj/Kotlin/x'),
            parent_commit='abc',
            change_set_entries=change_set,
        )

        # generate_results was called once with our expected payload.
        self.generate_results.assert_called_once()
        (item,), _ = self.generate_results.call_args
        repo, parent_commit, path_lines, software_repo, corpus_vecs, args = item

        self.assertEqual(repo, 'Kotlin/x')
        self.assertEqual(parent_commit, 'abc')
        self.assertEqual(path_lines, ['a/A.kt<sep>foo', 'b/B.kt<sep>bar'])
        self.assertEqual(args.lang, 'kotlin')
        self.assertEqual(args.project_path, '/tmp/proj')
        self.assertGreaterEqual(args.nebr_order, 1)

        # Embed dispatch picked the GraphCodeBERT branch and was loaded.
        self.EmbedCls.assert_called_with(
            'microsoft/graphcodebert-base', '/tmp/model.bin', lang='kotlin')
        self.embed_instance.load_finetuned_model.assert_called_once()

        # The first level of the results was forwarded.
        self.assertEqual(out, [self.sentinel_row])

    def test_no_modified_entries_returns_empty_without_loading_model(self):
        from impact_set.builder import ImpactSetBuilder

        change_set = [
            {'file_path': 'a/A.kt', 'identifier': 'A.copy', 'kind': 'VIRTUAL'},
        ]
        builder = ImpactSetBuilder(
            lang='kotlin',
            finetuned_model_path='/tmp/model.bin',
        )
        out = builder.build(
            repo='Kotlin/x',
            repo_path=Path('/tmp/proj/Kotlin/x'),
            parent_commit='abc',
            change_set_entries=change_set,
        )
        self.assertEqual(out, [])
        self.generate_results.assert_not_called()
        self.embed_instance.load_finetuned_model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
