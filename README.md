Introduction
============

Warning: This software is currently **alpha**.  Don't use the data blindly.

Kanji usage in Japan is regulated by the Jōyō Kanji table.  The latest, 2010
edition of the table is provided by the Ministry of Education in PDF format:
http://kokugo.bunka.go.jp/kokugo_nihongo/joho/kijun/naikaku/pdf/joyokanjihyo_20101130.pdf

The original table is quite messy and hard to use in computer programs.  This
project includes code to extract the data and convert it into popular formats:
TSV, JSON, SQL and HTML.  To minimize human error, the data is parsed
automatically as much as possible.  The results will be tested to ensure
consistency.

Most users won't have to run the scripts to extract the data; in the future,
you'll be able to download the output directly from this repository, in your
favourite format.


Roadmap/TODO
============

## Completed

 - On- and kun-readings
   - Romaji converter.
   - Distinguish uncommon readings (marked in the table as indented/1字下げ).
 - Example words
   - Use examples to delimit okurigana in kun-readings
     - Including inflected examples, and "double okurigana" (like 成り立ち)
   - Handle POS markers :〔副〕,〔接〕, '……',
   - Treat glossed variations as different, special readings
   - Handle examples with explicative text and 「」

 - Old kanji
   - Handle 弁:[辨, 瓣, 辯].
   - Handle 亀/龜 as Unicode.
 - Variant forms
   - Encode accepted variants (許容字体) as Unicode variation sequences.
   - Convert little-used codepoints to popular use alternatives (通用字体:
     塡 剝 頰 → 填 剥 頬).
   - Convert 叱 U+53F1 into common alternate (異体字) 𠮟 U+20B9F.
 - Notes (参考)
   - Save full note as text
     - Handle notes spanning multiple lines
 - Output formats
   - TSV
 - Tests
   - doctests for functions
   - old_kanji: against wikipedia, old dataset
   - readings: against kanjidic
   - examples: against JMdict (edict)

## Yet to be done

 - Decide how to mark 恐らく as special

 - Notes (参考)
   - Distinguish kanji-scoped notes from reading-scoped (almost done; need to
     handle jukujikun better).
   - Parse and structure the data from notes
     - Alternative orthographies (同訓異字).
     - Pointers to reference section in text.
       - Extract example images.
     - Prefecture names.
     - Exceptional readings..
       - Unbounded lists (with a "などは").
         - Complement with all available examples from edict.
       - Alternatives ("とも").
     - Jukujikun/appendix readings.
       - Filter: only list them for kanji where the reading is not regular.
     - One-off types of notes.

 - Tests
   - notes: write at least one test for each type of parsed note

 - Reference images for variant glyphs (許容字体)

 - Parse appendix

 - Output types:
   - SQL
   - JSON
   - HTML table

 - XTSU in output

How to recreate the files
=========================

     pip3 install romkan
     pip3 install ostruct
     pip3 install regex # newer version of 're'
     git clone https://github.com/leoboiko/joyodb.git
     cd joyodb
     make # (needs Internet)
     bin/convert_joyodb

Output will be in `output/` directory.

How to test
===========

    apt-get install rsync python3-lxml python3-bs4 mecab unidic-mecab
    pip3 install mecab-python3
    make test # (needs Internet)
