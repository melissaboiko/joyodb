# database/ORM models

import logging
logging.basicConfig(format='%(levelname)s: %(message)s')

import romkan
import regex as re
from joyodb import *

class Kanji:
    """A kanji with its associated Jōyō information:

        - kanji: The kanji, as a Unicode character.

          The Unicode encoding of this field may differ from that of the
          standard document; cf. self.standard_character,
          self.acceptable_variant.

        - old_kanji: The old version (if any) as a Unicode character, OR a list
          of character, where applicable (in Joyo 2010, only for 弁).

        - readings: Associated readings, as a list of Reading objects.

        - notes: Associated notes (参考), when they're kanji-scoped.  The
          original Japanese text as a string.  Notes pertaining to specific
          readings go into their Reading objects.

        - standard_character: In four cases, the Unicode character favored by
          the Joyo standard is not normally used; rather, current practice
          favors alternate characters.  These are called "popular-use character
          forms" 通用字体 (see Joyo p. 3, and data/popular_alternatives.tsv).
          In those cases, self.kanji stores the popular character, and
          self.standard_kanji the Joyo-favored one.

        - accepted_variant: In five cases, the same Unicode character may
          display graphical variation in glyphs. The choice of variant is left
          to the font rendering system, unless selected explicitly by variation
          selector characters. The Joyo standard lists "acceptable" variants
          (許容字体) between brackets ［］; typically they're more common than
          the standard's favoured form.

          This field, if available, is a Unicode variation sequence for the
          graphical variant listed as "accepted".

        - standard_variant: If the character has variant glyphs, this is an
          Unicode variation sequence to select the graphical variant listed as
          default (cf. self.accepted_variant).

        - acceped_variant_image: If the character has variant glyphs, this is a
          file object pointing to a reference png image of the "acceptable"
          variant (see self.accepted_variant).

        - standard_variant_image: If the character has variant glyphs, this is a
          file object pointing to a reference png image of the default variant
          (see self.standard_variant).

    """

    def __init__(self, kanji):
        if kanji in popular_alternatives.keys():
            self.kanji = popular_alternatives[kanji]
            self.standard_character = kanji
        else:
            self.kanji = kanji
            self.standard_character = None

        if kanji in variants.keys():
            self.standard_variant, self.accepted_variant = variants[kanji]

            codepoint = '%x' % ord(kanji)
            file_prefix = datadir + '/variants_img/' + codepoint.lower()
            self.standard_variant_image = open(file_prefix + '-standard.png', 'rb')
            self.accepted_variant_image = open(file_prefix + '-accepted.png', 'rb')

        else:
            self.standard_variant = None
            self.accepted_variant = None
            self.standard_variant_image = None
            self.accepted_variant_image = None

        self.old_kanji = None
        self.readings = list()
        self.notes = ''

        # if true, next note line should be appended to current note
        self.pending_note = False

    # prettier representations; useful when debugging
    def __str__(self):
        s = self.kanji
        if self.old_kanji:
            if type(self.old_kanji) == list:
                s += ' (%s)' % ','.join(self.old_kanji)
            else:
                s += ' (%s)' % self.old_kanji
        s += ' [%s]' % ','.join([r.reading for r in self.readings])
        return(s)

    def add_reading(self, reading, kind=None, variation_of=None):
        """See class Reading for arguments."""

        self.readings.append(Reading(self, reading,
                                     kind=kind,
                                     variation_of=variation_of))


    def add_examples(self, examples):
        """Call Reading.add_examples for current reading."""

        self.readings[-1].add_examples(examples)

    def add_old_kanji(self, string):
        """Sets self.old_kanji intelligently.

        Handles the case of multiple old forms for 弁."""
        if self.old_kanji:
        # If there's already an old kanji, it must be 弁.
        # We handle it by creating a list.
            assert(self.kanji == '弁')
            if not self.old_kanji is list:
                self.old_kanji = list(self.old_kanji)
            self.old_kanji.append(string)
        else:
            self.old_kanji = string

    def append_to_notes(self, string):
        """Intelligently add a line from the "notes" (参考) column.

        This call Reading.append_to_notes() function for current reading.
        Reading.append_to_notes() will check whether the notes is
        reading-scoped, or kanji-scoped.  If kanji-scoped, it will forward the
        note to Kanji.append_to_kanji_notes().

        These functions also deal with notes fields being continuations of
        previous lines."""
        self.readings[-1].append_to_notes(string)

    def append_to_kanji_notes(self, string):
        """Intelligently add a kanji-scoped note.

        - .+[府県]: prefecture-name uncommon reading.


        - ［漢］＝許容字体，\n *[(付).+]: reference for variant forms, encoded as
        [] in kanji column.

        - *[(付).*]: reference for documentation about minor graphical
        variation.

        """

        m = re.match(r'(\p{Han}+)（(\p{Hiragana}+)）[府県]$', string)
        if m:
            self.notes = string

            # TODO:
            # self.prefecture_reading = (m[1], m[2])
            return

        m = re.match(r'［(\p{Han})］＝許容字体，', string)
        if m:
            self.notes = string
            self.pending_note = True

            # TODO: data structure
            return

        m = re.match(r'＊［(（付）.*)］', string)
        if m:
            if self.pending_note:
                self.notes += m[1]
                self.pending_note = False
            else:
                self.notes = m[1]
            return

        raise(ValueError("BUG: unknown note format: '%s'" % string))

def all_suffixes(string):
    """Return a list of all possible suffixes, in decreasing order.

    >>> all_suffixes('abcde')
    ['abcde', 'bcde', 'cde', 'de', 'e']

    >>> all_suffixes('a')
    ['a']
    """

    suffixes = []
    for suffix_length in range(len(string), 0, -1):
        suffixes.append(string[-suffix_length:])
    return(suffixes)

# Used to lemmatize (de-inflect) verbs in okurigana processing.
#
# Luckly, no actual example uses a te-form or ta-form, so we don't need to
# handle them.
GODAN_INFLECTION = {
    'う': '[わえいおう]',
    'く': '[かけきこく]',
    'ぐ': '[がげぎごぐ]',
    'す': '[させしそす]',
    'ず': '[ざぜじぞず]',
    'つ': '[たてちとつ]',
    'づ': '[だでぢどづ]',
    'ぬ': '[なねにのぬ]',
    'ふ': '[はへひほふ]',
    'ぶ': '[ばべびぼぶ]',
    'ぷ': '[ぱぺぴぽぷ]',
    'む': '[まめみもむ]',
    'る': '[られりろる]',
}

ICHIDAN_BASE_ENDING = '[えけげせぜてでねへべぺめれいきぎしじちぢにひびぴみり]'
ICHIDAN_EXCEPTIONS = [
    '昼',
    '汁',
]

def is_ichidan_verb(kanji, canonical_reading):
    """

    >>> is_ichidan_verb('食', 'たべる')
    True

    >>> is_ichidan_verb('飲', 'のむ')
    False

    >>> is_ichidan_verb('干', 'ひる')
    True

    >>> is_ichidan_verb('昼', 'ひる')
    False
    """

    if kanji in ICHIDAN_EXCEPTIONS:
        return False
    elif re.search(ICHIDAN_BASE_ENDING + 'る$', canonical_reading):
        return True
    else:
        return False


def delimit_okurigana(kanji, canonical_reading, example):
    """Find where to delimit okurigana, based on the example.

    >>> delimit_okurigana('頼', 'たよる', '頼る')
    'たよ.る'

    It can handle verbal inflections:
    >>> delimit_okurigana('頼', 'たよる', '頼り')
    'たよ.る'

    >>> delimit_okurigana('初', 'そめる', '初める')
    'そ.める'

    >>> delimit_okurigana('干', 'ひる', '干物')
    'ひ.る'

    And intra-word okurigana:
    >>> delimit_okurigana('八', 'やつ', '八つ当たり')
    'や.つ'

    And the two combined:
    >>> delimit_okurigana('揺', 'ゆる', '揺り返し')
    'ゆ.る'

    >>> delimit_okurigana('初', 'そめる', '出初め式')
    'そ.める'

    >>> delimit_okurigana('干', 'ひる', '潮干狩り')
    'ひ.る'


    It ignores a trailing だ in the example, for na-adjectives:
    >>> delimit_okurigana('静', 'しずか', '静かだ')
    'しず.か'

    It can find the kanji if it's in the middle:
    >>> delimit_okurigana('古', 'ふるす', '使い古す')
    'ふる.す'

    It does nothing if the example isn't okurigana:
    >>> delimit_okurigana('本', 'ほん', '本')
    'ほん'

    >>> delimit_okurigana('唇', 'くちびる', '唇')
    'くちびる'

    This is tricker, because it looks like an ichidan verb; it's
    indistinguishable from 干=ひ.る except by explicit listing.

    >>> delimit_okurigana('昼', 'ひる', '真昼')
    'ひる'

    """

    if example == kanji:
        return(canonical_reading)

    for suffix in all_suffixes(canonical_reading):
        prefix = canonical_reading[0:-len(suffix)]
        ok_regex = kanji + suffix
        match = re.search(ok_regex, example)
        if match:
            return(prefix + '.' + suffix)

        if is_ichidan_verb(kanji, canonical_reading):
            ok_regex = ok_regex[:-1] # lose the る
            match = re.search(ok_regex, example)
            if match:
                return(prefix + '.' + suffix)

        last = ok_regex[-1]
        if last in GODAN_INFLECTION.keys():
            ok_regex = re.sub('.$', GODAN_INFLECTION[last], ok_regex)
            match = re.search(ok_regex, example)
            if match:
                return(prefix + '.' + suffix)

        ok_regex += 'だ'

    return(canonical_reading)

class Reading:
    """A kanji reading.

        - kanji: The kanji that this is a reading of (pointer to parent Kanji
                 object).
        - reading: The reading in kana (hiragana or katakana).  Kun-readings
                   will have okurigana delimited by a dot '.'.  Uncommon readings,
                   indented on table, will lose the indentation and be marked with
                   self.uncommon=True.
        - kind: one of On, Kun, TODO: jukujikun/exceptional readings.  If not
                passed, will autodetect as On for katakana and Kun otherwise.

        >>> k = Kanji('成')
        >>> r1 = Reading(k, reading='セイ')
        >>> r1.kind
        'On'

        >>> r2 = Reading(k, reading='なる')
        >>> r2.kind
        'Kun'

        >>> r3 = Reading(k, reading='　ジョウ') # wide space == "\u3000"
        >>> r3.kind
        'On'
        >>> r3.uncommon # indent = uncommon
        True
        >>> r3.reading # this field loses the indent spacing
        'ジョウ'

        >>> r1.uncommon == r2.uncommon == False # no indent = not uncommon
        True

        - examples: Example words from the Jōyō table; a list of strings.
        - uncommon: If true, this is a rarely-used reading, or a prefecture-name
                   reading.  This is equivalento to readings indented
                   ("1字下げ) in the PDF table.
        - variation_of: If true, this isn't listed as a separate reading in the
                        Joyo table, but as a variant of another reading (which
                        is given as a string).
        - notes: The "notes" (参考) column, when it's reading-scoped.
    """

    def __init__(self, kanji, reading, variation_of=None, kind=None):
        self.kanji = kanji
        if reading[0] == "\u3000":
            self.reading = reading[1:]
            self.uncommon = True
        else:
            self.reading = reading
            self.uncommon = False

        self.examples = list()

        if kind:
            self.kind = kind
        else:
            if re.match("\p{Katakana}", self.reading):
                self.kind = 'On'
            else:
                self.kind = 'Kun'

        self.variation_of = variation_of
        self.notes = ''

    def add_examples(self, examples_str):
        """Add an example to the list.

        Will convert codepoints to popular variants:
        >>> k = Kanji('𠮟')
        >>> r = Reading(k, reading='シツ')
        >>> r.add_examples('𠮟責') # in goes U+20B9F
        >>> r.examples[0].example # out comes U+53F1
        '叱責'

        Also use the example to delimit trailing okurigana in kun-readings,
        where applicable.

        >>> k = Kanji('成')
        >>> r = Reading(k, reading='なる')
        >>> r.reading
        'なる'
        >>> r.add_examples('成る')
        >>> r.reading
        'な.る'
        >>> r.examples[0].example
        '成る'

        Na-adjectives are listed with an extra だ, which we process:

        >>> k = Kanji('爽')
        >>> r = Reading(k, reading='さわやか')
        >>> r.add_examples('爽やかだ')
        >>> r.reading
        'さわ.やか'
        >>> r.examples[0].example
        '爽やかだ'

        >>> k = Kanji('嫌')
        >>> r = Reading(k, reading='いや')
        >>> r.add_examples('嫌だ')
        >>> r.reading
        'いや'
        >>> r.examples[0].example
        '嫌だ'

        The function is able to handle "double okurigana":
        >>> k = Kanji('六')
        >>> r = Reading(k, reading='むつ')
        >>> r.add_examples('六つ切り')
        >>> r.reading
        'む.つ'

        Even for verbs:
        >>> k = Kanji('生')
        >>> r = Reading(k, reading='おう')
        >>> r.add_examples('生い立ち')
        >>> r.reading
        'お.う'

        But it won't generate spurious okurigana from partial matches:
        >>> k = Kanji('恥')
        >>> r = Reading(k, reading='はじる')
        >>> r.add_examples('恥じる')
        >>> r.add_examples('恥じ入る')
        >>> r.reading
        'は.じる'

        >>> k = Kanji('汁')
        >>> r = Reading(k, reading='しる')
        >>> r.add_examples('汁')
        >>> r.add_examples('汁粉')
        >>> r.reading
        'しる'

        The single non–na-adjective trailed だ is handled just fine:
        >>> k = Kanji('甚')
        >>> r = Reading(k, reading='はなはだ')
        >>> r.add_examples('甚だ')
        >>> r.reading
        'はなは.だ'
        >>> r.examples[0].example
        '甚だ'

        We're not confused by multiple or weird examples:
        >>> k = Kanji('慌')
        >>> r = Reading(k, reading='あわただしい')
        >>> r.add_examples('慌ただしい')
        >>> r.add_examples('慌ただしさ')
        >>> r.add_examples('慌だだしげだ')
        >>> len(r.examples)
        3
        >>> r.reading
        'あわ.ただしい'


        """
        if '「' in examples_str:
            examples_str = re.sub(r'「|」|などと使う。', '', examples_str)

        examples_str = popularize(examples_str)
        examples = examples_str.split('，')
        examples = list(filter(None, examples))

        for example in examples:

            gloss_match = re.match('(.*)（(.*)）$', example)
            if gloss_match:
                # we treat the glossed variations in the examples list as their
                # own entries.

                example = gloss_match[1]
                gloss = gloss_match[2]

                if 'っ' in gloss:
                    # joyodb considers e.g. 三日 みっか to be a variation
                    # of the reading み.  we add みっ as a distinct
                    # reading.
                    gloss = re.sub(r'っ.*', 'っ', gloss)

                logging.info("Adding reading variation for example: %s, %s: %s, %s" %
                             (self.kanji.kanji, self.reading, gloss, example))
                self.kanji.add_reading(gloss,
                                       variation_of=self.reading)
                self.kanji.add_examples(example)

                # tuck new reading below, because the last reading in the list
                # is the one that will get new examples from the table.
                self.kanji.readings[-1], self.kanji.readings[-2] = (
                    self.kanji.readings[-2], self.kanji.readings[-1]
                )

            else:
                # normal example, without glosses

                # creating Example objects also clean up part-of-speech markers
                self.examples.append(Example(example))

        if self.kind == 'Kun':
            clean_reading = self.reading.replace('.', '')

            for example_obj in self.examples:
                example = example_obj.example
                new_reading = delimit_okurigana(self.kanji.kanji, clean_reading, example)

                if '.' in new_reading:
                    if clean_reading == self.reading:
                        # This is the first time we calculated a dotted reading.
                        self.reading = new_reading
                    else:
                        # We already had a dotted reading calculated;
                        # let's check whether it's the same.
                        if not self.reading == new_reading:
                            self.examples.remove(example_obj)

                            # 恐らく mess the algorith because it's listed as
                            # an example of おそ.れる – this only makes sense if
                            # you assume Classical grammar.  We handle it
                            # as a reading variation.
                            if example == '恐らく':
                                clean_reading = 'おそらく'
                                variation_of='おそ.れる'
                            else:
                                variation_of=None

                            self.kanji.add_reading(clean_reading, variation_of=variation_of)
                            self.kanji.add_examples(example)
                            self.kanji.readings[-1], self.kanji.readings[-2] = (
                                self.kanji.readings[-2], self.kanji.readings[-1]
                            )


    def romaji(self):
        """Returns the reading as rōmaji (romanized transcription).

        Uses lowercase for kun readings, uppercase for on, and titlecase for
        exceptional readings (TODO):

        >>> k = Kanji('嫌')
        >>> r1 = Reading(k, reading='ケン')
        >>> r1.romaji()
        'KEN'
        >>> r2 = Reading(k, reading='　ゲン')
        >>> r2.romaji() # self.uncommon isn't marked in romaji
        'GEN'
        >>> r3 = Reading(k, reading='いや')
        >>> r3.romaji()
        'iya'
        """

        hepburn = romkan.to_hepburn(self.reading)
        if self.kind == 'On':
            return(hepburn.upper())
        elif self.kind == 'Kun':
            return(hepburn)
        else:
            return(hepburn.title())

    def to_hiragana(self):
        """Return the reading as hiragana, even if it's On.

        >>> k = Kanji('柔')
        >>> r = Reading(k, 'ニュウ')
        >>> r.to_hiragana()
        'にゅう'


        If it's not On, it's imdepotent.
        >>> k = Kanji('最')
        >>> r = Reading(k, 'もっとも')
        >>> r.add_examples('最も')
        >>> r.reading
        'もっと.も'
        >>> r.to_hiragana()
        'もっと.も'

        """

        if self.kind == 'On':
            return(romkan.to_hiragana(romkan.to_roma(self.reading)))
        else:
            return(self.reading)

    def append_to_notes(self, string):
        """Intelligently add data from the "notes" column.

        Notes field can have two kinds of scope: per-reading, or whole-kanji.
        This function only handles reading-scoped notes; it calls
        Kanji.__append_to_kanji_notes() if needed.

        - ↔ (.+,?)+:  same-reading different-kanji

        - (漢+か*・?)+(か+)か+?: multiple-kanji special reading.  Sometimes it's a
        regular reading for _this_ kanji, but special reading for the other
        (compounds are listed for all kanji involved, even if they're regular).

        - (「漢+」,?)+(など)?は,.*。
        reading (always?); can span multiple lines.

        - (「[漢かカ]+」,?)+とも(書く)?。
        same meaning as above, but without the は.

        - 「猟」の字音の転用。
        only this line; a "diverted use" 転用.

        - 「山頂」の意。
        only this line; specify the intended meaning.

        - 多く文語の「亡き」で使う。
        only this line; literary usage.

        """

        string = string.strip()

        m = re.match(r'⇔ *(.+)', string)
        if m:
            self.notes = string
            # TODO: data structure
            # TODO: split on ','
            return

        m = re.match(r'(お?\p{Han}+\p{Hiragana}*・?)+（(\p{Hiragana}+)）(\p{Hiragana}*)', string)
        if m:
            self.notes = string
            # TODO: data structre
            return

        m = re.match(r'(「(.*)」，?)+(など)?は，', string)
        if m:
            self.notes = string
            # TODO:
            # self.other = m[1]
            if not re.search('。$', string):
                self.kanji.pending_note = True
            return

        m = re.match(r'(「(.*)」，?)+などと使う。$', string)
        if m:
            self.notes = string
            # TODO:
            # self.other = m[1]
            return

        if self.kanji.pending_note == True:
            m = re.search('。$', string)
            if m:

                # previous half of note could have been in this reading...
                if self.notes:
                    self.notes += string
                # or the previous one.
                elif self.kanji.readings[-2].notes:
                    self.kanji.readings[-2].notes += string
                else:
                    raise(ValueError("BUG: can't find where to attach half-note."))

                self.kanji.pending_note = False
                return

        m = re.match(r'(「[\p{Han}\p{Hiragana}\p{Katakana}]+」,?)+とも(書く)?。', string)
        if m:
            self.notes = string
            return

        m = re.match(r'「(\p{Han})」.*転用。', string)
        if m:
            self.notes = string
            return

        m = re.match(r'「(.*)」.*の意。', string)
        if m:
            self.notes = string
            return

        m = re.match(r'.*文語.*「(.*)」で使う。', string)
        if m:
            self.notes = string
            return

        # no match; let's try it as a kanji-scoped note
        self.kanji.append_to_kanji_notes(string)

    # pretty representation; useful when debugging
    def __str__(self):
        s = self.romaji()
        if self.uncommon:
            s += ' (特)'
        if self.examples:
            s += (', examples: [%s]' % ','.join([str(e) for e in self.examples]))
        return(s)

class Example:
    def __init__(self, example):
        """Model for each item in a list of examples (例 column).

         - self.reading: The parent Reading object.
         - self.example: The cleaned text string.
         - self.pos: If a part-of-speech marker is given, this is set to one of
          'Adverb', 'Conjunction' or 'Suffix'.
      """

        if '〔副〕' in example:
            self.example = example.replace('〔副〕', '')
            self.pos = 'Adverb'
        elif '〔接〕' in example:
            self.example = example.replace('〔接〕', '')
            self.pos = 'Conjunction'
        elif re.match('^……', example):
            self.example = example.replace('……', '')
            self.pos = 'Suffix'
        else:
            self.example = example
            self.pos = None

    def __str__(self):
        return self.example

# With this, one can test with: python3 model.py -v
if __name__ == "__main__":
    import doctest
    doctest.testmod()

