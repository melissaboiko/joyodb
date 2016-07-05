import unittest
import doctest
import os
import sys
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')
from collections import defaultdict

from bs4 import BeautifulSoup
from lxml import etree
import romkan
import MeCab
mecab_tagger = MeCab.Tagger('-Ounidic')

# "The parent dir of the directory of the full path of this file."
basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(basedir)
os.chdir(basedir)

wikipedia_file = basedir + '/cache/List_of_joyo_kanji.html'
shin2kyuu_file = basedir + '/data/old_shin2kyuu.tsv'
kanjidic_file = basedir + '/cache/kanjidic_comb_utf8'
jmdict_file = basedir + '/cache/JMdict'
jmdict_missing_examples_file = basedir + '/data/examples_not_in_jmdict.tsv'

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
    ('中', 'ジュウ'), # example: ○○中
    ('丼', 'どん'), # example: 牛丼
    ('務', 'つと.まる'), # example: 務まる
    ('塞', 'ふさ.がる'), # example: 塞がる
    ('守', 'も.り'), # example: お守り
    ('惧', 'グ'), # example: 危惧
    ('振', 'ふ.れる'), # example: 振れる
    ('曽', 'ゾ'), # example: 未曽有
    ('植', 'うえ.る'), # example: 植木
    ('漬', 'つけ.る'), # example: 漬物
    ('籠', 'こ.もる'), # example: 籠もる
    ('絡', 'から.める'), # example: 絡める
    ('羨', 'うらや.ましい'), # example: 羨ましい
    ('詣', 'もうで.る'), # example: 初詣
    ('謡', 'うたい'), # example: 謡, 素謡
    ('貪', 'ドン'), # example: 貪欲
    ('速', 'はや.まる'), # example: 速まる

    # these are more limitations from this code
    ('受', 'うけ.る'), # example: 受付
    ('宛', 'あて.る'), # example: 宛先
    ('建', 'たて.る'), # example: 建物
    ('替', 'かえ.る'), # example: 両替
    ('請', 'うけ.る'), # example: 請負

    # redundant inflection; there's already おど.る
    ('踊', 'おど.り'), # example: 踊り

]

JMDICT_MISSING_EXAMPLES = []
with open(jmdict_missing_examples_file, 'rt') as f:
    f.readline() # discard header
    for line in f:
        kanji, reading, example, furigana = line.strip().split("\t")
        JMDICT_MISSING_EXAMPLES.append((kanji, reading, example))

jmdict_index = defaultdict(list)
class JMdictEntry():

    def __init__(self, entry):
        self.kanji_expressions = []
        for k_ele in entry.iter('k_ele'):
            keb = k_ele.find('keb')
            self.kanji_expressions.append(keb.text)
            jmdict_index[keb.text].append(self)

        self.readings = []
        for r_ele in entry.iter('r_ele'):
            reb = r_ele.find('reb')
            self.readings.append(reb.text)

        self.parts_of_speech = []
        for pos in entry.iter('pos'):
            for entity in pos.iter(tag=etree.Entity):
                self.parts_of_speech.append(str(entity))

def jmdict_is_kanji_entry(entry):
    if entry.find('k_ele') is not None:
        return True

def lemmatize_with_mecab(expression, kanji):
    '''Find the first word containing kanji; return (lemma, reading).'''
    nodes = mecab_tagger.parseToNode(expression)
    while nodes:
        features = nodes.feature.split(',')
        if kanji in features[10]:
            lemma = features[10]
            reading = romkan.to_hiragana(romkan.to_roma(features[6]))
            return((lemma, reading))
        nodes = nodes.next
    raise(ValueError("Mecab failed: %s, %s" % (expression, kanji)))


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
                self.assertEqual(TestLoadedData.kanjis[joyodb.popular_alternatives[w_kanji]].standard_character,
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

    def test_reading_variations(self):
        for k in joyodb.loaded_data.kanjis:
            for r in k.readings:
                base = r.variation_of
                if base:
                    matches = [r for r in k.readings
                               if r.reading == base]
                    self.assertEqual(len(matches), 1)

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
                if reading.variation_of:
                    continue # variations are not in kanjidic
                if (kanji.kanji, reading.reading) not in KANJIDIC_MISSING_READINGS:
                    self.assertIn(reading.reading, kanjidic_data[kanji.kanji])

    def test_against_edict(self):
        # list of EdictEntry objects
        jmdict_data = []

        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(jmdict_file, parser)
        for entry in  tree.getroot().iter('entry'):
            if jmdict_is_kanji_entry(entry):
                jmdict_entry = JMdictEntry(entry)
                jmdict_data.append(jmdict_entry)

        for k in joyodb.loaded_data.kanjis:
            for r in k.readings:
                for e in r.examples:

                    jmdict_entries = None

                    if e.example in jmdict_index.keys():
                        jmdict_entries = jmdict_index[e.example]
                    elif (k.kanji, r.reading, e.example) in JMDICT_MISSING_EXAMPLES:
                        continue
                    else:
                        lemma, lemma_reading = lemmatize_with_mecab(e.example, k.kanji)
                        if lemma in jmdict_index.keys():
                            jmdict_entries = jmdict_index[lemma]
                            jmdict_entries = [je for je in jmdict_entries
                                              if lemma_reading in je.readings]
                            if not jmdict_entries:
                                raise(RuntimeError(
                                    "Could not find example: %s (lemma: %s,%s)" %
                                    (e.example, lemma, lemma_reading)))
                            else:
                                logging.warning("Could only find lemmatized example: %s, %s" %
                                                (e.example, lemma))

                    if not jmdict_entries:
                        raise(RuntimeError("Could not find example: %s"
                              % e.example))

    def test_alternate_orthographies(self):
        for k in joyodb.loaded_data.kanjis:
            for r in k.readings:
                for a in r.alternate_orthographies:
                    looks_like_alternate = re.match("^(\p{Han})\p{Hiragana}*$", a)
                    assert(looks_like_alternate)
                    alt_kanji_ch = looks_like_alternate[1]
                    assert(alt_kanji_ch)

                    alt_kanji_list = [obj for obj in joyodb.loaded_data.kanjis
                                      if obj.kanji == alt_kanji_ch]
                    assert(len(alt_kanji_list) == 1)
                    alt_kanji = alt_kanji_list[0]

                    found=False
                    for their_readings in alt_kanji.readings:
                        for their_alternates in their_readings.alternate_orthographies:
                            if k.kanji in their_alternates:
                                found=True
                    assert(found)



def load_tests(loader, tests, ignore):
    """Load doctests into unit tests suite.

    See Python's doctest.html for detail."""
    tests.addTests(doctest.DocTestSuite(joyodb))
    tests.addTests(doctest.DocTestSuite(joyodb.model))
    tests.addTests(doctest.DocTestSuite(joyodb.convert))
    return tests

if __name__ == '__main__':
    unittest.main()
