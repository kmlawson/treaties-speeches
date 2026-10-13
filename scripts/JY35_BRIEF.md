# Brief: The Japan Year Book 1935, treaty appendix (printed pp. 1222-1318)

Everything in `scripts/AGENT_BRIEF.md` applies - read it first - in particular: read the page images with your own
eyes (no OCR, no PDF text layer, no `pdftotext`, no apple-vision / llmimage, no text from memory or the web; these
are famous treaties, but transcribe only what this book prints, including its own wording, omissions and
misprints), the output file format, the body conventions, and "Writing in small pieces, and resuming"
(START / PAGE / DONE / SKIPPAGE). Differences for this job:

- Scan: `_work/pdf/japan-year-book-1935/issue.pdf`.
  **The PDF page is NOT a fixed offset from the printed page**: it lies between printed page + 49 and printed page
  + 51 (e.g. printed p. 1224 = PDF page 1273, printed p. 1303 = PDF page 1354), because unnumbered plates are bound
  in. Each batch item gives `pdf_page_approx`; always read the printed page number in the running head and step
  forward or back a page until you are on the right one. `leaf:` in the front matter = the PDF page on which the
  text starts, minus 1.
  Render with `python3 scripts/render.py japan-year-book-1935
  <first> <last> 220` (use 220 dpi: the print is very small and the scan is coarse;
  if a passage is still hard to read, render that page at 300 and look again).
- The pages are set in **two columns**. Read the left column top to bottom, then the right column. Texts follow one
  another without page breaks: a text usually starts and ends part-way down a column. Your batch file
  `_work/batches/<batch>.json` lists the texts in printed order, each with `title`, `p` (printed page where it
  starts), `pdf_page_approx` (roughly where that page is in the PDF), `last_possible_printed_page` (where the next text in the book starts - your text ends on
  that page or before), and `out` (the exact file to write). One listed text = one file. If the book prints a
  further separate text that is not in the list (between two listed ones), add it as its own file with a letter
  suffix on the preceding number (e.g. `07a-...md`) and say so in the report.
- **A cycle is one column** (half a printed page): append `PAGE <path> <printed page><L|R>` (e.g. `PAGE ... 838L`)
  to the progress file, read (the page image shows both columns; transcribe the one column, or the part of it that
  belongs to your text), write that column's text with one tool call. Put the `[[p. N]]` marker once, where the
  text reaches a new printed page. A page image already viewed for the previous text need not be re-rendered, but
  log the PAGE line for the column you are about to transcribe all the same.
  On resume: a text with START and no DONE was cut off at its last PAGE line (page and column). Do not transcribe
  that column: append `SKIPPAGE <path> <N>` and put `*[Page N was not transcribed. See the scan.]*` in its place
  (if only one column of page N is affected say so in `notes`, e.g. "INCOMPLETE: p. 838 right column not
  transcribed", and still use the placeholder line exactly as given), then continue with the next column.
- Front matter: `source: yb`, `ia: japan-year-book-1935`, `issue: The Japan Year Book 1935`,
  `section: Treaties`,
  `leaf:` = PDF page of the start page - 1, `pages:` printed pages, `date:` the date of the instrument (from the heading
  or the text), `parties:` for treaties and agreements, `author:` for statements, notes and addresses.
  `type`: `treaty` (treaties, conventions, agreements, protocols, contracts between governments, exchanges of
  notes forming an agreement), `law` (imperial ordinances, government orders, statutes and articles of
  association of the railway companies), `speech` (an address delivered by a named person), `document`
  (statements, notes, resolutions, proclamations, reports, communications).
- Texts printed in French or German are transcribed in that language exactly as printed, accents included.
- Headings inside a text (`ARTICLE I`, `SECTION II`, annexes) follow the main brief; signature blocks one line per
  line. Titles in title case as printed.
- When every text of the batch is DONE, write `texts/_reports/<batch>.md` (pages read, files, anything illegible,
  any unlisted text added) and append `BATCH COMPLETE` to `texts/_reports/<batch>.progress`.
- Texts already on the site are NOT to be transcribed again even though this book prints them: the Treaty for the
  Renunciation of War (p. 1222), the Nine-Power Treaty (p. 1223), the Agreement between Japan and China, 1930
  (p. 1254), the Traité de Paix entre le Japon et la Russie, 1905 (p. 1269) and the Treaty respecting South Manchuria
  and Eastern Inner Mongolia, 1915 (p. 1303). Nor is the "Import Tariff of the Principal Commodities" table
  (from p. 1319). Transcribe only the texts listed in your batch file; do not add texts that belong to another batch
  (a text that follows yours on the page is someone else's unless it is in none of the lists: ask yourself whether
  its title appears in `index/yb.json` for this book before adding it).
- After writing each column, look at the image once more and compare your text with it word by word (names,
  figures, dates, every line present, nothing added), and fix any slip before going on.
