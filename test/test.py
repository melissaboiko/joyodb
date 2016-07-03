import unittest
import doctest
import os
import sys

from bs4 import BeautifulSoup

# "The parent dir of the directory of the full path of this file."
basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(basedir)
os.chdir(basedir)

wikipedia_file = basedir + '/cache/List_of_joyo_kanji.html'
shin2kyuu_file = basedir + '/data/old_shin2kyuu.tsv'

import joyodb
import joyodb.model
import joyodb.convert
import regex as re


# These kanji are listed in Wikipedia, but I carefully confirmed that they are
# not in the Joyo table.
WIKIPEDIA_ONLY_OLDKANJI = [
    '銳',
    '沒',
    '內',
    '攜',
    '歲',
    '啟',
    '悅',
]

class TestLoadedData(unittest.TestCase):

    def setUp(self):
        joyodb.convert.parse()
        self.kanjis = {}

        # convenience mapping by string
        for k in joyodb.loaded_data.kanjis:
            self.kanjis[k.kanji] = k

    def test_okurigana_delimit(self):
        """Simple test to look for suspicious non-delimited readings."""

        for k in joyodb.loaded_data.kanjis:
            for r in filter(lambda r: r.kind == 'Kun', k.readings):
                examples = [e.example for e in r.examples]
                for e in examples:
                    match = re.search(k.kanji + "(\p{Hiragana}+)", e)
                    if match and re.search(match[1] + '$', r.reading):
                        self.assertIn('.', r.reading)


    def test_against_wikipedia(self):
        with open(wikipedia_file, 'rt') as f:
            w = BeautifulSoup(f)
        table = w.find_all("table", class_="wikitable")
        if len(list(table)) != 1:
            raise(RuntimeError("Wikipedia changed too much! Can't test against it!"))

        table = table[0]

        wikipedia_kanjis = {}
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')

            new = tds[1].find('a').text
            old = None
            a = tds[2].find('a')
            if a:
                old = a.text

            readings = tds[7]

            wikipedia_kanjis[new] = (old, readings)

        self.assertEqual(len(self.kanjis.keys()), len(wikipedia_kanjis.keys()))

        for w_kanji in wikipedia_kanjis.keys():
            if w_kanji in joyodb.popular_alternatives.keys():
                self.assertEqual(self.kanjis[joyodb.popular_alternatives[w_kanji]].default_variant,
                                 w_kanji)
            else:
                self.assertEqual(self.kanjis[w_kanji].kanji, w_kanji)

            w_old, readings = wikipedia_kanjis[w_kanji]
            if (w_old not in WIKIPEDIA_ONLY_OLDKANJI
                and w_kanji != '弁'): # confirmed by hand

                loaded_kanji = self.kanjis[joyodb.popularize(w_kanji)]
                self.assertEqual(loaded_kanji.old_kanji, w_old)

        for kanji in joyodb.loaded_data.kanjis:
            if kanji.old_kanji and len(kanji.old_kanji) == 1:
                self.assertEqual(kanji.old_kanji, wikipedia_kanjis[kanji.kanji][0])

    def test_against_old_shin2kyuu(self):
        old_data = {}
        with open(shin2kyuu_file, 'rt') as f:
            for line in f:
                shin, kyuu = line.strip().split("\t")
                old_data[shin] = kyuu

        kanjis_with_old = list(filter(lambda k: k.old_kanji, joyodb.loaded_data.kanjis))
        self.assertEqual(len(kanjis_with_old), len(old_data))
        for shin, kyuu in old_data.items():
            if shin != '弁':
                self.assertEqual(kyuu, self.kanjis[shin].old_kanji)
        for kanji in kanjis_with_old:
            if kanji.kanji != '弁':
                self.assertEqual(kanji.old_kanji, old_data[kanji.kanji])


def load_tests(loader, tests, ignore):
    """Load doctests into unit tests suite.

    See Python's doctest.html for detail."""
    tests.addTests(doctest.DocTestSuite(joyodb))
    tests.addTests(doctest.DocTestSuite(joyodb.model))
    tests.addTests(doctest.DocTestSuite(joyodb.convert))
    return tests

if __name__ == '__main__':
    unittest.main()
