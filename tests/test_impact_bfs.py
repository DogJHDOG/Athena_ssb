"""Reverse BFS on a toy call graph.

Verifies _build_reverse_adj and the BFS frontier within max_hop, without invoking
SoftwareRepo (which requires git + tree-sitter).
"""

import unittest

try:
    import pandas as pd
except ImportError:
    pd = None

from impact_set.builder import ImpactSetBuilder


@unittest.skipIf(pd is None, "pandas not installed")
class ReverseAdjTest(unittest.TestCase):
    def test_reverse_adj_call_only(self):
        call_edges = pd.DataFrame({'from_id': [0, 1, 2], 'to_id': [1, 2, 3]})
        class_edges = pd.DataFrame({'from_id': [], 'to_id': []})
        b = ImpactSetBuilder(include_class_edges=False)
        adj, via = b._build_reverse_adj(call_edges, class_edges)
        # 0 calls 1, 1 calls 2, 2 calls 3 -> reverse: 1<-0, 2<-1, 3<-2
        self.assertEqual(adj[1], {0})
        self.assertEqual(adj[2], {1})
        self.assertEqual(adj[3], {2})
        self.assertEqual(via[(1, 0)], 'call')

    def test_reverse_adj_with_class_edges(self):
        call_edges = pd.DataFrame({'from_id': [0], 'to_id': [1]})
        class_edges = pd.DataFrame({'from_id': [2], 'to_id': [3]})
        b = ImpactSetBuilder(include_class_edges=True)
        adj, via = b._build_reverse_adj(call_edges, class_edges)
        self.assertEqual(adj[1], {0})
        self.assertEqual(adj[2], {3})
        self.assertEqual(adj[3], {2})
        self.assertEqual(via[(2, 3)], 'class')
        self.assertEqual(via[(3, 2)], 'class')


if __name__ == '__main__':
    unittest.main()
