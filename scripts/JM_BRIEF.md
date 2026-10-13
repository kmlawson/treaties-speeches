# Brief: Japan-Manchoukuo Year Book 1934, Supplement III (texts of treaties, agreements, notes and statutes)

Everything in `scripts/AGENT_BRIEF.md` applies - read it first - in particular: read the page images with your own
eyes (no OCR, no PDF text layer, no `pdftotext`, no apple-vision / llmimage, no text from memory or the web; these
are famous treaties, but transcribe only what this book prints, including its own wording, omissions and
misprints), the output file format, the body conventions, and "Writing in small pieces, and resuming"
(START / PAGE / DONE / SKIPPAGE). Differences for this job:

- Scan: `_work/pdf/japan-manchoukuo-year-book-1934/issue.pdf` (second file of the Internet Archive item).
  **PDF page = printed page - 564**, i.e. IA leaf n = printed page - 565 (printed p. 829 = leaf 264 = PDF page 265).
  Check it on the first page you open. Render with `python3 scripts/render.py japan-manchoukuo-year-book-1934
  <first> <last> 170` (use 170 dpi; the print is small and there is show-through from the reverse of the leaf:
  ignore the faint mirrored text).
- The pages are set in **two columns**. Read the left column top to bottom, then the right column. Texts follow one
  another without page breaks: a text usually starts and ends part-way down a column. Your batch file
  `_work/batches/<batch>.json` lists the texts in printed order, each with `title`, `p` (printed page where it
  starts), `n` (leaf of that page), `n_last_possible` (leaf where the next listed text starts - your text ends on
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
- Front matter: `source: yb`, `ia: japan-manchoukuo-year-book-1934`, `issue: Japan-Manchoukuo Year Book 1934`,
  `section: Supplement III. Texts of Treaties, Agreements, Notes and Statutes of the Powers Concerning Manchuria`,
  `leaf:` = printed start page - 565, `pages:` printed pages, `date:` the date of the instrument (from the heading
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
