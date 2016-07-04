# as of this writing, we need the new regex library to get support for kanji and kana matching:
# \p{Han}, \p{Hiragana}, \p{Katakana}
import regex as re

from joyodb import *
from joyodb.model import *

def convert():
    "Main function which converts the Joyo table to multiple formats."
    parse()
    convert_to_tsv()
    convert_to_html()
    convert_to_sql()

def parse():
    "Main function to load data from the Joyo table."
    open_joyo_txt_file()
    find_main_table()
    parse_main_table()
    parse_appendix_table()

def open_joyo_txt_file():
    "Open the Joyo .txt file, storing a pointer in loaded_data."
    import os.path

    loaded_data.joyotxt = open(JOYOHYO_TXT, 'rt')

def find_main_table():
    "Moves up in the Joyo file until the start of the main table (本表)."
    for line in loaded_data.joyotxt:
        line = line.strip()
        if re.match(r'本\s*表$', line):
            break

def parse_main_table():
    "Reads data from main table (本表) into memory."

    # store the parsed data here
    loaded_data.kanjis = []
    # we use this to skip the first content line, which is the header
    header_skipped = False

    for line in loaded_data.joyotxt:

        # skip page numbers and index headers
        if is_empty(line) or is_page_index(line) or is_sound_index(line):
            continue
        # stop when we reach the appendix
        elif is_appendix_start(line):
            break
        else:
            if not header_skipped:
                # throw away header line
                header_skipped = True
            else:
                parse_main_table_row(line)

def is_empty(line):
    # 'r' raw string so that doctest works with these special characters.
    r"""Detects blank lines.

    In the pdfbox conversion of the main table, blank lines seem to separate
    kanji entries.  But we can already detect the start of each kanji entry by
    the presence of the kanji itself, so we just skip blank lines.

    >>> is_empty('')
    True
    >>> is_empty("\n")
    True
    >>> is_empty(" \t  \n")
    True
    >>> is_empty("\u3000") # IDEOGRAPHIC SPACE
    True
    >>> is_empty("\u3000漢\t\n")
    False
    """

    line = line.strip()
    return re.match('^$', line) != None

def is_page_index(line):
    r"""Detects the page indices from the Joyo document.

    They usually look like this:

    >>> is_page_index('03初_改定常用漢字表_本表NN.indd   107 2010/11/12   13:10:23')
    True

    Pdfbox also generated a single page number (?) like this:

    >>> is_page_index('163')
    True

    Content lines won't match:
    >>> is_page_index('\t \t \t なつける\t 懐ける\t')
    False
    """

    line = line.strip()

    # We just test whether it starts with a number.
    if re.match(r'^[0-9]', line):
        return(True)
    else:
        return(False)

def is_sound_index(line):
    r"""Detects the sound indices present in every page of the Joyo PDF.

    They can be single:

    >>> is_sound_index('カン')
    True

    Or a range, with a U+FF0D FULLWIDTH HYPHEN-MINUS:
    >>> is_sound_index('キ－キツ')
    True

    Or also with hiragana:
    >>> is_sound_index('オウ－おそれ')
    True

    Content lines won't match:
    >>> is_page_index('\t \t \t なつける\t 懐ける\t')
    False
    """

    line = line.strip()
    if re.match(r'^[\p{Katakana}\p{Hiragana}－]+$', line):
        return(True)
    else:
        return(False)

def is_appendix_start(line):
    "Return true if this line starts the appendix table (付表)."
    line = line.strip()
    if re.match(r'付\s*表$', line):
        return(True)
    else:
        return(False)


def parse_main_table_row(line):
    """Intelligently parse a line from the Joyo table, in pdfbox .txt format.

    Entry-point function; most of work is done by others.
    """
    fields = main_table_row_fields(line)

    if 'kanji' in fields.keys():
        add_kanji(fields['kanji'])

    current = current_kanji()

    if 'old_kanji' in fields.keys():
        current.add_old_kanji(fields['old_kanji'])

    if 'reading' in fields.keys():
        current.add_reading(fields['reading'])

    if 'examples' in fields.keys():
        current.add_examples(fields['examples'])

    if 'notes' in fields.keys():
        current.append_to_notes(fields['notes'])


def main_table_row_fields(line):
    r"""Interprets the fields in a Joyo table row, ain pdftoolbox .txt format.

    The txt conversion generates a huge mess of different line types, which are
    documented below and grouped by number of fields:

    1 field
    =======

    Sometimes pdfbox leaves a dangling field alone in a line.  These are
    almost aways additions to the "notes" field of the previous line:

    >>> f = main_table_row_fields("「春雨」，「小雨」，「霧雨」などは，\n")
    >>> f['notes']
    '「春雨」，「小雨」，「霧雨」などは，'

    Exceptions:

    - 弁 leaves a lone field for two out of its three old forms, namely '瓣' and '辯'.

    >>> f = main_table_row_fields('瓣')
    >>> 'old_kanji' in f.keys()
    True

    - The following three lone columns are examples:

    >>> f = main_table_row_fields("\t \t \t \t 極めて〔副〕\n")
    >>> 'examples' in f.keys()
    True

    >>> f = main_table_row_fields("\t \t \t \t 慌ただしげだ\n")
    >>> 'examples' in f.keys()
    True

    >>> f = main_table_row_fields("\t \t \t \t 四月目\n")
    >>> 'examples' in f.keys()
    True


    2 fields
    ========

    There are four kinds of lines with 2 fields:

    - 2.a: kanji, reading:
    >>> f = main_table_row_fields("升\t\t \t \t\t \t \t ショウ\t \t\n")
    >>> f['kanji']
    '升'
    >>> f['reading']
    'ショウ'

    - 2.b: reading, examples:
    >>> f = main_table_row_fields("\t \t \t あわれ\t 哀れ，哀れな話，哀れがる\t\n")
    >>> f['reading']
    'あわれ'
    >>> f['examples']
    '哀れ，哀れな話，哀れがる'

    - 2.c: reading, notes:
    >>> f = main_table_row_fields("\t \t \t 　ク\t \t 「宮内庁」などと使う。\n")
    >>> f['reading']
    '　ク'
    >>> f['notes']
    '「宮内庁」などと使う。'

    - 2.d: examples, notes
    >>> f = main_table_row_fields("\t \t \t \t 真ん中\t 真っ赤（まっか）\n")
    >>> f['examples']
    '真ん中'
    >>> f['notes']
    '真っ赤（まっか）'


    3 fields
    ========

    Two kinds of lines:

    - 3.a: kanji, reading, examples:
    >>> f = main_table_row_fields("\t哀\t \t \t \t\t \t \t アイ\t 哀愁，哀願，悲哀\t\n")
    >>> for column in ('kanji', 'reading', 'examples'):
    ...     assert(column in f.keys())

    - 3.b: reading, examples, notes:
    >>> f = main_table_row_fields("\t \t \t 　ユイ\t 遺言\t 「遺言」は，「イゴン」とも。\n")
    >>> for column in ('reading', 'examples', 'notes'):
    ...     assert(column in f.keys())

    They can be distinguished by the first field being a single kanji.

    4 fields
    ========

    Four kinds of lines with four fields, with one exception:

    - 4.a: kanji, old_kanji, reading, examples:
    >>> f = main_table_row_fields("涙\t（淚）\t \t \t\t \t \t ルイ\t 感涙，声涙，落涙\t\n")
    >>> for column in ('kanji', 'old_kanji', 'reading', 'examples'):
    ...     assert(column in f.keys())

    Old kanji is between wide-char parenthesis, （）.

    - 4.a exception: kanji, old_kanji, reading, notes

    >>> f = main_table_row_fields("弥\t（彌）\t \t \t\t \t \t や\t \t 弥生（やよい）\n")
    >>> for column in ('kanji', 'old_kanji', 'reading', 'notes'):
    ...     assert(column in f.keys())

    Only in this kanji has this format, with no examples in this line but notes instead.

    - 4.b: kanji, reading, examples, notes:
    >>> f = main_table_row_fields("和\t\t \t \t\t \t \t ワ\t 和解，和服，柔和\t 日和（ひより）\n")
    >>> for column in ('kanji', 'reading', 'examples', 'notes'):
    ...     assert(column in f.keys())

    Reading is a kana string.

    - 4.c: old_kanji, reading, examples, notes:
    >>> f = main_table_row_fields("\t \t（餠）\t もち\t 餅屋，尻餅\t ＊［（付）第２の３【餌】参照］\t \t \t \t \t\n")
    >>> for column in ('old_kanji', 'reading', 'examples', 'notes'):
    ...     assert(column in f.keys())

    Only the line above is of this type.  Old kanji in parenthesis leads the
    line.

    - 4.d: kanji, old_kanji, reading, examples:
    >>> f = main_table_row_fields("弁\t\t\t辨\t \t \t\t \t \t ベン\t 弁償，花弁，雄弁\t\n")
    >>> for column in ('kanji', 'old_kanji', 'reading', 'examples'):
    ...     assert(column in f.keys())

    Only the line above is of this type.  Old kanji without parenthesis.


    5 fields
    ========

    Three kinds of lines:

    - 5.a: kanji with old form:
    >>> f = main_table_row_fields("為\t（爲）\t \t \t\t \t \t イ\t 為政者，行為，作為\t 為替（かわせ）\n")
    >>> for column in ('kanji', 'old_kanji', 'reading', 'examples', 'notes'):
    ...     assert(column in f.keys())

    - 5.b: kanji with accepted variant form (許容字体):
    >>> f = main_table_row_fields("遡\t［遡］\t \t \t\t \t \t ソ\t 遡及，遡上\t ［遡］＝許容字体，\n")
    >>> for column in ('kanji', 'reading', 'examples', 'notes'):
    ...     assert(column in f.keys())

    The encoding of the variant form is lost in the pdftoolbox conversion, so
    the second field here is useless.  The information is restored by class
    Kanji.

    - 5.c: kanji with unencoded old form:
    >>> f = main_table_row_fields("亀\t（ ）\t \t \t\t \t \t キ\t 亀裂\t\n")
    >>> for column in ('kanji', 'old_kanji', 'reading', 'examples'):
    ...     assert(column in f.keys())

    Old form is encoded as image, generating trash parenthesis here.  We
    discard them and substitute a hardcoded Unicode '龜'.
    """

    #       TODO: can examples, like notes, be append to previous line?
    fields = split_main_table_row(line)
    dfields = dict()

    if len(fields) == 1:
        if fields[0] in ('瓣', '辯'):
            # Exception: old forms of 弁
            dfields['old_kanji'] = fields[0]

        elif is_examples(fields[0]):
            assert(fields[0][0] in ('極', '慌', '四'))
            dfields['examples'] = fields[0]

        else:
            # Everything else is notes
            dfields['notes'] = fields[0]

    elif len(fields) == 2:
        if is_kanji(fields[0]):
            # 2.a: kanji leads
            dfields['kanji'] = fields[0]
            dfields['reading'] = fields[1]
        elif is_reading(fields[0]):
            # 2.b or 2.c: reading leads
            dfields['reading'] = fields[0]
            if is_examples(fields[1]):
                dfields['examples'] = fields[1]
            else:
                dfields['notes'] = fields[1]
        else:
            # 2.d
            dfields['examples'] = fields[0]
            dfields['notes'] = fields[1]

    elif len(fields) == 3:
        if is_kanji(fields[0]):
            # 3.a: kanji leads
            dfields['kanji'] = fields[0]
            dfields['reading'] = fields[1]
            dfields['examples'] = fields[2]
        else:
            # 3.b: reading leads
            dfields['reading'] = fields[0]
            dfields['examples'] = fields[1]
            dfields['notes'] = fields[2]


    elif len(fields) == 4:
        old_kanji = extract_old_kanji(fields[1])
        if old_kanji:
            # 4.a: old_kanji line.
            dfields['kanji'] = fields[0]
            dfields['old_kanji'] = old_kanji
            dfields['reading'] = fields[2]
            if dfields['kanji'] == '弥':
                # exceptionally without examples in this line
                dfields['notes'] = fields[3]
            else:
                dfields['examples'] = fields[3]

        elif is_kanji(fields[0]):
            if fields[0] == '弁':
                # 4.d exception: old kanji without parenthesis.
                dfields['kanji'] = fields[0]
                dfields['old_kanji'] = fields[1]
                dfields['reading'] = fields[2]
                dfields['examples'] = fields[3]
            else:
                # 4.b.
                dfields['kanji'] = fields[0]
                dfields['reading'] = fields[1]
                dfields['examples'] = fields[2]
                dfields['notes'] = fields[3]
        else:
            # must be 4.c exception.
            assert(fields[0] == '（餠）')
            dfields['old_kanji'] = '餠'
            dfields['reading'] = fields[1]
            dfields['examples'] = fields[2]
            dfields['notes'] = fields[3]

    elif len(fields) == 5:
        old_kanji = extract_old_kanji(fields[1])
        if old_kanji:
            # 5.a: kanji with old form, examples, notes
            dfields['kanji'] = fields[0]
            dfields['old_kanji'] = old_kanji
            dfields['reading'] = fields[2]
            dfields['examples'] = fields[3]
            dfields['notes'] = fields[4]

        elif fields[0] == '亀':
            # 5.c: exception: unencoded old form
            dfields['kanji'] = fields[0]
            dfields['old_kanji'] = '龜'
            dfields['reading'] = fields[3]
            dfields['examples'] = fields[4]

        else:
            # must be type 5.b: kanji with variant
            match = re.match("［(.)］$", fields[1])
            assert(match)
            dfields['kanji'] = fields[0]

            # throw away match[1]; it's bogus in the .txt, and will be
            # identical to fields[0].

            dfields['reading'] = fields[2]
            dfields['examples'] = fields[3]
            dfields['notes'] = fields[4]

    if 'kanji' in dfields.keys():
        assert(is_kanji(dfields['kanji']))
    if 'old_kanji' in dfields.keys():
        assert(is_kanji(dfields['old_kanji']))
    if 'reading' in dfields.keys():
        assert(is_reading(dfields['reading']))
    if 'examples' in dfields.keys():
        assert(is_examples(dfields['examples']))
    if 'notes' in dfields.keys():
        assert(is_notes(dfields['notes']))
    return(dfields)


def split_main_table_row(line):
    r"""Splits a Joyo table row, in pdftoolbox .txt format, into fields.

    The pdftoolbox output seems to end up separating fields by an arbitrary
    amount of spaces and tabs.  As well-behaved Python programmers, we want to
    strip that random spacing and convert the fields to a list:

    >>> split_main_table_row("壱\t（壹）\t \t \t\t \t \t イチ\t 壱万円\t\n")
    ['壱', '（壹）', 'イチ', '壱万円']

    >>> split_main_table_row("咽\t \t \t \t\t \t \t イン\t 咽喉\t\n")
    ['咽', 'イン', '咽喉']

    However, there's a complication: the Jōyō Kanji table highlights certain
    readings by indenting them with a space ("1字下げ").  Distinguishing those
    meaningful spaces from the column-separating spaces/tabs could be a lot of
    trouble.  Luckly, the original indenting space is always a wide-char U+3000
    IDEOGRAPHIC SPACE ("\u3000").  So this code strips all spaces _except_
    U+3000:

    >>> split_main_table_row("\t \t \t \u3000あま\t 雨雲，雨戸，雨具\t\n")
    ['\u3000あま', '雨雲，雨戸，雨具']

    We also preserve the space that follows a '⇔' in the Notes column (though
    this isn't very important...):

    >>> split_main_table_row("\t \t \t おそれる\t 畏れる，畏れ\t ⇔ 恐れる\n")
    ['おそれる', '畏れる，畏れ', '⇔ 恐れる']
    """


    # We can't use Python strip() as-is, because it would eat the U+3000
    # wide-space.  To clean the left side of the line, we remove strictly
    # regular spaces and tabs.
    line = re.sub("^[ \t]+", '', line)
    # But trailing whitespace to the right side is fair game.
    line = line.rstrip()

    # The "Notes" column uses a regular space after '⇔'; we replace it with a
    # special char, to simplify splitting.  The special char is from Unicode
    # private-use area, which isn't used by the Joyo table.
    line = line.replace('⇔ ', "⇔\ue000")

    # We can't use the defalt split() algorithm either.  So we first compress
    # sequences of spaces and tabs into another private char, as a separator...
    line = line.replace("\t", "\ue001")
    line = re.sub("[ \ue001]+", "\ue001", line)
    # Then give '⇔' its space back...
    line = line.replace("\ue000", ' ')
    # And, finally, split on the separator-char.
    fields = line.split("\ue001")

    return(fields)


kanji_regexp = re.compile(r"^\p{Han}$")
def is_kanji(field):
    return(re.match(kanji_regexp, field))

def extract_old_kanji(field):
    """Return None if it isn't an old kanji field."""
    match = re.match(r"^（(\p{Han})）$", field)
    if match:
        return(match[1])
    else:
        return None

reading_regexp = re.compile(r"^[\u3000\p{Hiragana}\p{Katakana}]+$")
def is_reading(field):
    return(re.match(reading_regexp, field))

# found experimentally; it doesn't match glossed examples, which are
# indistinguishable from notes.
examples_regexp = re.compile(r"[\p{Han}\p{Hiragana}\p{Katakana}，〔〕…○Ａ]+$")
glossed_examples = [
    '一羽（わ）',
    '六羽（ぱ）',
    '三日（みっか）',
    '四日（よっか）',
    '一把（ワ）',
    '三把（バ）',
    '十把（パ）',
]

def is_examples(field):
    if re.match(examples_regexp, field):
        return True
    else:
        parts = field.split('，')
        for part in parts:
            if part in glossed_examples:
                return True

    return False

def is_notes(field):
    return(not is_kanji(field)
           and not is_reading(field)
           and not is_examples(field))

def add_kanji(string):
    "Add a kanji object to loaded_data."
    loaded_data.kanjis.append(Kanji(string))

def current_kanji():
    "Access the kanji object currently under construction."
    return(loaded_data.kanjis[-1])

def parse_appendix_table():
    # TODO
    loaded_data.joyotxt.close()

def convert_to_tsv():
    with open(outputdir + '/readings.tsv', 'wt') as f:
        f.write("Kanji\tReading\tRomaji\tType\tUncommon?\tVariation of\n")
        for k in loaded_data.kanjis:
            for r in k.readings:
                f.write(k.kanji + "\t")
                f.write(r.reading + "\t")
                f.write(r.romaji() + "\t")
                f.write(r.kind + "\t")
                if r.uncommon:
                    f.write("Y\t")
                if r.variation_of:
                    f.write(r.variation_of)
                f.write("\n")

    with open(outputdir + '/old_kanji.tsv', 'wt') as f:
        for k in loaded_data.kanjis:
            if type(k.old_kanji) is list:
                for old in k.old_kanji:
                    f.write("%s\t%s\n" % (k.kanji, old))
            elif k.old_kanji:
                f.write("%s\t%s\n" %( k.kanji, k.old_kanji))

    with open(outputdir + '/examples.tsv', 'wt') as f:
        f.write("Kanji\tReading\tUncommon reading?\tExample\tPOS of example\n")
        for k in loaded_data.kanjis:
            for r in k.readings:
                if r.uncommon:
                    uncommon = 'Y'
                else:
                    uncommon = ''

                for e in r.examples:
                    if e.pos:
                        pos = e.pos
                    else:
                        pos = ''

                    f.write("%s\t%s\t%s\t%s\t%s\n" % (k.kanji, r.reading, uncommon, e.example, pos))

    with open(outputdir + '/notes_for_readings.tsv', 'wt') as f:
        f.write("Kanji\tNote\n")
        for k in loaded_data.kanjis:
            if k.notes:
                f.write("%s\t%s\n" % (k.kanji, k.notes))

    with open(outputdir + '/notes_for_kanjis.tsv', 'wt') as f:
        f.write("Kanji\tReading\tUncommon?\tNote\n")
        for k in loaded_data.kanjis:
            for r in k.readings:
                if r.uncommon:
                    uncommon = 'Y'
                else:
                    uncommon = ''

                if r.notes:
                    f.write("%s\t%s\t%s\t%s\n" %
                            (k.kanji,
                            r.reading,
                            uncommon,
                            r.notes))

def convert_to_sql():
    pass
def convert_to_html():
    pass

# With this, one can test with: env PYTHONPATH=. python3 convert.py
if __name__ == "__main__":
    import doctest
    doctest.testmod()

