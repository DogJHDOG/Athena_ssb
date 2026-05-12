"""Java rule is a passthrough — identifiers preserved, kind=MODIFIED, source=real."""

import unittest

from change_set.loader import RawChangedMethod
from change_set.rules.java import JavaRule


class JavaRuleTest(unittest.TestCase):
    def test_passthrough(self):
        raw = [
            RawChangedMethod(repo='r', parent_commit='pc',
                             file_path='src/A.java', method_name='foo'),
            RawChangedMethod(repo='r', parent_commit='pc',
                             file_path='src/B.java', method_name='bar'),
        ]
        entries = JavaRule().apply(raw, software_repo=None)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].identifier, 'foo')
        self.assertEqual(entries[0].kind, 'MODIFIED')
        self.assertEqual(entries[0].source, 'real')
        self.assertIsNone(entries[0].class_name)


if __name__ == '__main__':
    unittest.main()
