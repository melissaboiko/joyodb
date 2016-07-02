Introduction
============

Warning: This software is currently **alpha** and **untested**.  Don't use the
data blindly.

Kanji usage in Japan is regulated by the Jōyō Kanji table.  The latest, 2010
edition of the table is provided by the Ministry of Education in PDF format.

The original table is quite messy and hard to use in computer programs.  This
project extracts the data and converts it into popular formats: TSV, JSON, SQL
and HTML.  The data is extracted automatically as much as possible, in the
interests of minimizing human error.  The results will be tested to ensure
consistency.

Most users won't have to run the scripts to extract the data; in the future,
you'll be able to download the output directly from this repository, in your
favourite format.


Roadmap/TODO
============
Completed:

     everyone uses the former).
 - Old kanji
   - Handle 弁:[辨, 瓣, 辯]
   - Handle 亀/龜 as Unicode
 - On- and kun-readings
   - Romaji converter
   - Distinguish special readings (marked in the table as indented/1字下げ)
 - Example words
   - Use examples to delimit okurigana in kun-readings
 - Variant forms
   - Encode accepted variants (許容字体) as Unicode variation sequences
   - Handle problematic 叱 U+53F1 vs. 𠮟 U+20B9F situation (MEXT wants the
     latter, but everyone uses the former)
 - Notes
   - Save full note as text
     - Handle notes spanning multiple lines
 - TSV output

To do:
 - Examples:
   - Handle POS markers like 〔副〕
 - Notes
   - Distinguish kanji-scoped notes from reading-scoped (almost done; need to
     handle jukujikun better)
   - Structure the data from notes:
     - Alternative orthographies (同訓異字)
     - Pointers to reference section in text
       - Extract example images
     - Prefecture names
     - Exceptional readings.
       - Unbounded lists (with a "などは").
         - Complement with all available examples from edict.
       - Alternatives ("とも").
     - Jukujikun/appendix readings
       - Filter: only list them for kanji where the reading is not regular
     - One-off notes

 - Tests
   - old_kanji: against old dataset
   - readings: against Wikipedia table, kanjidic
   - examples: against edict
   - notes: write at least one test for each type of parsed data
   - write doctests for small functions

 - Reference images for variant glyphs (許容字体)
 - Parse appendix

 - Output types:
   - SQL
   - JSON
   - HTML table

How to recreate the files
=========================


     pip3 install ostruct
     pip3 install regex # newer version of 're'
     git clone # this repo
     cd joyodb
     make # (needs Internet)
     bin/convert_joyodb

Output will be in `output/` directory.Introduction
============

Warning: This software is currently **alpha** and **untested**.  Don't use the
data blindly.

Kanji usage in Japan is regulated by the Jōyō Kanji table.  The latest, 2010
edition of the table is provided by the Ministry of Education in PDF format.

The original table is quite messy and hard to use in computer programs.  This
project extracts the data and converts it into popular formats: TSV, JSON, SQL
and HTML.  The data is extracted automatically as much as possible, in the
interests of minimizing human error.  The results will be tested to ensure
consistency.

Most users don't have to run the scripts to extract the data; you can download
the output directly from this repository, in your favourite format.


Roadmap/TODO
============
Completed:

 - Old kanji
   - Handle 弁:[辨, 瓣, 辯]
   - Handle 亀/龜 as Unicode
 - On- and kun-readings
   - Romaji converter
   - Distinguish special readings (marked in the table as indented/1字下げ)
 - Example words
   - Use examples to delimit okurigana in kun-readings
 - Notes
   - Save full note as text
     - Handle notes spanning multiple lines
 - TSV output

To do:
 - Notes
   - Distinguish kanji-scoped notes from reading-scoped (almost done; need to
     handle jukujikun better)
   - Structure the data from notes:
     - Alternative orthographies (同訓異字)
     - Pointers to reference section in text
       - Extract example images
     - Prefecture names
     - Exceptional readings.
       - Unbounded lists (with a "などは").
         - Complement with all available examples from edict.
       - Alternatives ("とも").
     - Jukujikun/appendix readings
       - Filter: only list them for kanji where the reading is not regular
     - One-off notes

 - Tests
   - old_kanji: against old dataset
   - readings: against Wikipedia table, kanjidic
   - examples: against edict
   - notes: write at least one test for each type of parsed data
   - write doctests for small functions

 - Reference images for variant glyphs (許容字体)
 - Parse appendix

 - Output types:
   - SQL
   - JSON
   - HTML table

How to recreate the files
=========================


     pip3 install ostruct
     pip3 install regex # newer version of 're'
     git clone # this repo
     cd joyodb
     make # (needs Internet)
     bin/convert_joyodb

Output will be in `output/` directory.
