# Brief: second pass — transcribing whole articles (programmes, reports, reviews, statistics, profiles)

This pass adds further kinds of content to the collection. Everything in `scripts/AGENT_BRIEF.md` applies —
read it first — in particular: read the page images with your own eyes (no OCR, no PDF text layer, no
`pdftotext`, no apple-vision / llmimage, no text from memory or the web), the output file format and body
conventions, and the whole section "Writing in small pieces, and resuming" (START / PAGE / DONE / SKIPPAGE /
BLOCKED; one printed page per read-then-write cycle; a PAGE line before each Read; no transcribed text in chat).
Differences for this pass:

## What you are given

A batch file `_work/batches/<batch>.json`: a list of items, each one article to transcribe **in full**:
`source`, `ia`, `issue`, `title`, `attrib`, `category`, `series`, `part`, `n` (IA leaf of the first page; PDF page
= n + 1), `n_next` (leaf where the next article in the index starts — your article ends on or before that page;
find the true end with a contact sheet), and `out` (the exact path of the file to write). One item = one file.
A few late Tokyo Gazette issues are scanned as two-page spreads (one PDF page = two printed pages): then a
"cycle" is still one printed page, written with its own `[[p. N]]` marker.

## Front matter

Same keys as the main brief, with `type` set from the item's category:
`programme` → `type: programme`; `situation` and `empire` → `type: report`; `review` → `type: review`;
`statistics` → `type: statistics`; `profile` → `type: profile`.
Add `series:` and `part:` lines after `type:` when the item has a series. `author:` = the issuing department
(`attrib`) or, for a signed article, the author; for a `profile` put the person profiled in a `subject:` line.
`date:` = date of the document if the article gives one, otherwise blank (the issue date is used).

## Body

- The whole article, from its title to its end, including sub-headings (`###`, `####` for lower levels),
  numbered lists, footnotes, and every table.
- **Tables**: Markdown tables, every row and column, figures exactly as printed (keep thousands separators and
  units). A cell you cannot read is left empty and listed in `notes` — never a guess. **Where a total is
  printed, add up the parts**: if they do not reconcile with the printed total, keep the printed figures and
  say so in `notes` (which table, printed total, your sum). Do not correct the source. A very wide table may be
  split into two tables with the stub column repeated; say so in `notes`.
- Maps, charts and photographs: one line `*[Map: caption as printed]*` / `*[Chart: ...]*` / `*[Photograph: ...]*`.
- `notes:` must list the printed pages read and every cell or word you could not make out.

## Report

Append to `texts/_reports/<batch>.md`: per item, the PDF pages read, the file written, table totals that did not
reconcile, illegible cells. When every item of the batch is DONE (or BLOCKED), append `BATCH COMPLETE` to the
progress file `texts/_reports/<batch>.progress`.
