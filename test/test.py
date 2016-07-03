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
kanjidic_file = basedir + '/cache/kanjidic_comb_utf8'
edict_file = basedir + '/cache/edict_utf8'

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

KANJIDIC_MISSING_READINGS = [
    ('惧', 'グ'), # example: 危惧
    ('塞', 'ふさ.がる'), # example: 塞がる
    ('守', 'も.り'), # example: お守り
    ('振', 'ふ.れる'), # example: 振れる
    ('羨', 'うらや.ましい'), # example: 羨ましい
    ('曽', 'ゾ'), # example: 未曽有
    ('速', 'はや.まる'), # example: 速まる
    ('中', 'ジュウ'), # example: ○○中
    ('貪', 'ドン'), # example: 貪欲
    ('丼', 'どん'), # example: 牛丼
    ('務', 'つと.まる'), # example: 務まる
    ('踊', 'おど.り'), # example: 踊り # clean redundant inflections like this?
    ('謡', 'うたい'), # example: 謡, 素謡
    ('絡', 'から.める'), # example: 絡める
    ('籠', 'こ.もる'), # example: 籠もる
    ('宛', 'あて.る'), # example: 宛先
    ('詣', 'もうで.る'), # example: 初詣
    ('建', 'たて.る'), # example: 建物
    ('受', 'うけ.る'), # example: 受付
    ('植', 'うえ.る'), # example: 植木
    ('請', 'うけ.る'), # example: 請負
    ('替', 'かえ.る'), # example: 両替
    ('漬', 'つけ.る'), # example: 漬物

    # this one was added by ours; on the table it's listed as an example of
    # 恐れる
    ('恐', 'おそ.らく'), # example: 恐らく
]

class TestLoadedData(unittest.TestCase):

    def setUpClass():
        joyodb.convert.parse()
        TestLoadedData.kanjis = {}

        # convenience mapping by string
        for k in joyodb.loaded_data.kanjis:
            TestLoadedData.kanjis[k.kanji] = k

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

        self.assertEqual(len(TestLoadedData.kanjis.keys()), len(wikipedia_kanjis.keys()))

        for w_kanji in wikipedia_kanjis.keys():
            if w_kanji in joyodb.popular_alternatives.keys():
                self.assertEqual(TestLoadedData.kanjis[joyodb.popular_alternatives[w_kanji]].default_variant,
                                 w_kanji)
            else:
                self.assertEqual(TestLoadedData.kanjis[w_kanji].kanji, w_kanji)

            w_old, readings = wikipedia_kanjis[w_kanji]
            if (w_old not in WIKIPEDIA_ONLY_OLDKANJI
                and w_kanji != '弁'): # confirmed by hand

                loaded_kanji = TestLoadedData.kanjis[joyodb.popularize(w_kanji)]
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
                self.assertEqual(kyuu, TestLoadedData.kanjis[shin].old_kanji)
        for kanji in kanjis_with_old:
            if kanji.kanji != '弁':
                self.assertEqual(kanji.old_kanji, old_data[kanji.kanji])

    def test_against_kanjidic(self):
        kanjidic_data = {}
        with open(kanjidic_file, 'rt') as f:
            for line in f:
                kanji, *fields = line.strip().split()

                if kanji in TestLoadedData.kanjis.keys():
                    # kanjidic marks bound affixes with '-', but we don't
                    fields = [re.sub('-$', '', f) for f in fields]
                    fields = [re.sub('^-', '', f) for f in fields]

                    kanjidic_data[kanji] = fields

        for kanji in joyodb.loaded_data.kanjis:
            for reading in kanji.readings:
                if (kanji.kanji, reading.reading) not in KANJIDIC_MISSING_READINGS:
                    self.assertIn(reading.reading, kanjidic_data[kanji.kanji])

    def test_against_edict(self):
        edict_data = {}
        with open(edict_file, 'rt') as f:
            for line in f:
                fields = line.split()
                if fields[1][0] == '[':
                    # it's a kanji entry
                    expression = fields[0]
                    # strip surrounding []
                    reading = fields[1][1:-2]

                    if expression not in edict_data.keys():
                        edict_data[expression] = list()
                    edict_data[expression].append(reading)


def load_tests(loader, tests, ignore):
    """Load doctests into unit tests suite.

    See Python's doctest.html for detail."""
    tests.addTests(doctest.DocTestSuite(joyodb))
    tests.addTests(doctest.DocTestSuite(joyodb.model))
    tests.addTests(doctest.DocTestSuite(joyodb.convert))
    return tests

if __name__ == '__main__':
    unittest.main()
