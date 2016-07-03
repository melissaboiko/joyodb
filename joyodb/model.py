# database/ORM models

import romkan
import regex as re
from joyodb import variants

class Kanji:
    """A kanji with its associated Jōyō information:

        - kanji: The kanji, as a Unicode character.

        A special case are these characters:
            - 叱 U+53F1 KA
            - 𠮟 U+20B9F, SHITSU/shikaru, "to scold" (mandarin: chì).

        These look pretty much the same, but MEXT says they're different
        characters (cf. 付 3.4 in the PDF).  According to the Joyo document,
        U+20B9F is the actual Joyo character (SHITSU/shikaru "to scold"), and
        U+53F1 is a separate one altogether (apparently pronounced
        KA[1]separate one altogether (apparently pronounced KA; cf.
        https://hydrocul.github.io/wiki/blog/2014/1201-shikaru.html ).  The PDF
        table uses U+20B9F.

        However, U+20B9F is a newer codepoint, outside the Basic Multilingual
        Plane; and in fact Unicode's Unihan list SHITSU/shikaru for U+53F1. A
        search on Google Books in July/2016 found ~56000 hits for 叱る encoded
        as U+53F1, and only 1 hit for 𠮟る with U+20B9F.  In my console, as I
        type this, U+20B9F shows in a different, distressingly small font.  And
        the PDF itself says that, given current usage, U+53F1 is to be accepted
        as a variant character (異体字) for SHITSU/shikaru.

        Given this reality, I've reluctantly encoded self.kanji as U+53F1 for
        this character, because I think this will match most user's
        expectations.  U+20B9F is available in self.default_variant.

        - old_kanji: The old version (if any) as a Unicode string, OR a list of
          strings, where applicable (in Joyo 2010, only for 弁).

        - acceptable_variant: The alternative form (許容自体), as a Unicode
          string using variation selection characters.

        - default_variant: The standard glyph in the table, specifically
          encoded as a Unicode string using variation selection characters.  Only
          defined if acceptable_variant exists; and in the case of 叱 U+53F1,
          where it lists 𠮟 U+20B9F, MEXT's favoured codepoint.

        - readings: Associated readings, as a list of Reading objects.

        - notes: Associated notes (参考), when they're kanji-scoped.  Notes
          pertaining to specific readings go into their Reading objects.
    """

    def __init__(self, kanji):
        if kanji == '𠮟':
            self.kanji = '叱' # U+53F1
            self.default_variant = '𠮟' # U+20B9F
        else:
            self.kanji = kanji

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

    def add_reading(self, reading, kind=None):
        """See class Reading for arguments."""
        # TODO: cf. case 羽

        self.readings.append(Reading(self, reading, kind))

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

    def add_variant(self):
        """Sets self.acceptable_variant, self.default_variant.

        Pulls from bundled data, because we lose the variants in the .txt
        conversion..
        """
        default, acceptable = variants[self.kanji]
        self.default_variant = default
        self.acceptable_variant = acceptable

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

        - .+[府県]: prefecture-name special reading.


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
    ['bcde', 'cde', 'de', 'e']

    >>> all_suffixes('a')
    []
    """

    suffixes = []
    for suffix_length in range(len(string)-1, 0, -1):
        suffixes.append(string[-suffix_length:])
    return(suffixes)

# Used to lemmatize (de-inflect) verbs in okurigana processing.
#
# Luckly, no actual example uses a te-form or ta-form, so we don't need to
# handle them.
INFLECTION = {
    'う': '[わえいおう]',
    'く': '[かけきこく]',
    'す': '[させしそす]',
    'つ': '[たてちとつ]',
    'ぬ': '[なねにのぬ]',
    'ふ': '[はへひほふ]',
    'む': '[まめみもむ]',
    'る': '[られりろる]',
}

def delimit_okurigana(canonical_reading, example):
    """Find where to delimit okurigana, based on the example.

    >>> delimit_okurigana('たよる', '頼る')
    'たよ.る'

    It can handle verbal inflections:
    >>> delimit_okurigana('たよる', '頼り')
    'たよ.る'

    And intra-word okurigana:
    >>> delimit_okurigana('やつ', '八つ当たり')
    'や.つ'

    And the two combined:
    >>> delimit_okurigana('ゆる', '揺り返し')
    'ゆ.る'

    It ignores a trailing だ in the example, for na-adjectives:
    >>> delimit_okurigana('しずか', '静かだ')
    'しず.か'

    It does nothing if the example isn't okurigana:
    >>> delimit_okurigana('ほん', '本')
    'ほん'
    """

    kanji = example[0]

    for suffix in all_suffixes(canonical_reading):
        ok_regex = kanji + suffix
        last = ok_regex[-1]
        if last in INFLECTION.keys():
            ok_regex = re.sub('.$', INFLECTION[last], ok_regex)
        ok_regex += 'だ?'

        match = re.match(ok_regex, example)
        if match:
            prefix = canonical_reading[0:-len(suffix)]
            return(prefix + '.' + suffix)
    return(canonical_reading)

class Reading:
    """A kanji reading.

        - kanji: The kanji that this is a reading of (pointer to parent Kanji
                 object).
        - reading: The reading in kana (hiragana or katakana).  Kun-readings
                   will have okurigana delimited by a dot '.'.  Special readings,
                   indented on table, will lose the indentation and be marked with
                   self.special=True.
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
        >>> r3.special # indent = special
        True
        >>> r3.reading # this field loses the indent spacing
        'ジョウ'

        >>> r1.special == r2.special == False # no indent = not special
        True

        - examples: Example words from the Jōyō table; a list of strings.
        - special: If true, this is a rarely-used reading, or a prefecture-name
                   reading.  This is equivalento to readings indented
                   ("1字下げ) in the PDF table.
        - notes: The "notes" (参考) column, when it's reading-scoped.
    """

    def __init__(self, kanji, reading, kind=None):
        self.kanji = kanji
        if reading[0] == "\u3000":
            self.reading = reading[1:]
            self.special = True
        else:
            self.reading = reading
            self.special = False

        self.examples = list()

        if kind:
            self.kind = kind
        else:
            if re.match("\p{Katakana}", self.reading):
                self.kind = 'On'
            else:
                self.kind = 'Kun'

        self.notes = ''

    def add_examples(self, examples_str):
        """Add an example to the list.

        Will convert the codepoint for 𠮟 (see documentation for class Kanji):
        >>> k = Kanji('𠮟')
        >>> r = Reading(k, reading='シツ')
        >>> r.add_examples('𠮟責') # in goes U+20B9F
        >>> r.examples[0].example
        '叱' # out comes U+53F1

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
        if '（' in examples_str:
            print("TODO: skipping complex example list: %s" % examples_str)
            return

        if '𠮟' in examples_str:
            examples_str = examples_str.replace('𠮟', '叱')
        examples = examples_str.split('，')
        examples = filter(None, examples)
        # creating Example objects also clean up part-of-speech markers
        examples = [Example(e) for e in examples]

        if self.kind == 'Kun':
            clean_reading = self.reading.replace('.', '')
            for example_obj in examples:
                example = example_obj.example
                new_reading = delimit_okurigana(clean_reading, example)

                if '.' in new_reading:
                    if clean_reading == self.reading:
                        # This is the first time we calculated a dotted reading.
                        self.reading = new_reading
                    else:
                        # We already had a dotted reading calculated;
                        # let's ensure it's the same.
                        if not self.reading == new_reading:
                            raise(ValueError("\n".join([
                                "Example generated different okurigana:",
                                "old: " + self.reading,
                                "new: " + new_reading,
                                "example: " + example,
                            ])))
                    break

        self.examples += examples


    def romaji(self):
        """Returns the reading as rōmaji (romanized transcription).

        Uses lowercase for kun readings, uppercase for on, and titlecase for
        exceptional readings (TODO):

        >>> k = Kanji('嫌')
        >>> r1 = Reading(k, reading='ケン')
        >>> r1.romaji()
        'KEN'
        >>> r2 = Reading(k, reading='　ゲン')
        >>> r2.romaji() # self.special isn't marked in romaji
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
        if self.special:
            s += ' (特)'
        if self.examples:
            s += (', examples: [%s]' % ','.join(self.examples))
        return(s)

class Example:
    def __init__(self, example):
        """Model for each item in a list of examples (例 column).

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

# With this, one can test with: python3 model.py -v
if __name__ == "__main__":
    import doctest
    doctest.testmod()

