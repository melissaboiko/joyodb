import unittest
import doctest
import os
import sys

# "The parent dir of the directory of the full path of this file."
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import joyodb
import joyodb.model
import joyodb.convert
import regex as re

class TestLoadedData(unittest.TestCase):

    def setUp(self):
        joyodb.convert.parse()

    def test_okurigana_delimit(self):
        """Simple test to look for suspicious non-delimited readings."""

        for k in joyodb.loaded_data.kanjis:
            for r in filter(lambda r: r.kind == 'Kun', k.readings):
                examples = [e.example for e in r.examples]
                for e in examples:
                    match = re.search(k.kanji + "(\p{Hiragana}+)", e)
                    if match and re.search(match[1] + '$', r.reading):
                        self.assertIn('.', r.reading)


def load_tests(loader, tests, ignore):
    """Load doctests into unit tests suite.

    See Python's doctest.html for detail."""
    tests.addTests(doctest.DocTestSuite(joyodb.model))
    tests.addTests(doctest.DocTestSuite(joyodb.convert))
    return tests

if __name__ == '__main__':
    unittest.main()
