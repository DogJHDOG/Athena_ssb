"""ChangeSetLoader handles both Alexandria (Java) and kotlin_dataset schemas."""

import csv
import os
import tempfile
import unittest

from change_set.loader import ChangeSetLoader


def _write_csv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class LoaderTest(unittest.TestCase):
    def test_kotlin_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'k.csv')
            _write_csv(path,
                ['repo', 'commit', 'parent_commit', 'file_path', 'method_name',
                 'method_start', 'method_end', 'hunk_id', 'github_link'],
                [['Kotlin/x', 'cc', 'pc', 'a/b.kt', 'foo', '10', '20', 'h1', 'http://x']])
            loader = ChangeSetLoader(path)
            self.assertEqual(len(loader.rows), 1)
            r = loader.rows[0]
            self.assertEqual(r.repo, 'Kotlin/x')
            self.assertEqual(r.parent_commit, 'pc')
            self.assertEqual(r.child_commit, 'cc')
            self.assertEqual(r.hunk_id, 'h1')
            self.assertEqual(r.method_start, 10)
            self.assertEqual(r.method_end, 20)

    def test_alexandria_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'a.csv')
            _write_csv(path,
                ['repo', 'github_link', 'parent_commit', 'file_path', 'method_name'],
                [['org/proj', 'http://x', 'pc1', 'src/A.java', 'bar']])
            loader = ChangeSetLoader(path)
            self.assertEqual(len(loader.rows), 1)
            r = loader.rows[0]
            self.assertEqual(r.repo, 'org/proj')
            self.assertIsNone(r.child_commit)
            self.assertIsNone(r.hunk_id)
            self.assertIsNone(r.method_start)

    def test_for_commit_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'k.csv')
            _write_csv(path,
                ['repo', 'commit', 'parent_commit', 'file_path', 'method_name',
                 'method_start', 'method_end', 'hunk_id', 'github_link'],
                [['r', 'cc1', 'pc1', 'a.kt', 'm1', '1', '2', 'h', 'x'],
                 ['r', 'cc2', 'pc2', 'a.kt', 'm2', '3', '4', 'h', 'x']])
            loader = ChangeSetLoader(path)
            self.assertEqual(len(loader.for_commit('r', 'pc1')), 1)
            self.assertEqual(loader.for_commit('r', 'pc1')[0].method_name, 'm1')


if __name__ == '__main__':
    unittest.main()
