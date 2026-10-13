# Brief: transcribing verbatim official texts from scanned journal issues

Project root: `/Users/kml/shell/projects/treaties-speeches`. You are given a batch file
`_work/batches/<batch>.json`: a list of journal issues (Tokyo Gazette, 1937-42, or Contemporary Japan,
1941-45), each with its Internet Archive id (`ia`), date, and the table-of-contents entries taken from the
index site (`entries`: `d` = nesting depth, `title`, `attrib`, `p` = printed page, `n` = IA leaf number).
The scan of each issue is at `_work/pdf/<ia>/issue.pdf`. **PDF page = leaf `n` + 1** (check it on the first
page you open; say so in your report if an issue is offset differently).

## What to extract

Every text that the journal prints **verbatim** and that is one of:

- `treaty` - treaties, pacts, conventions, agreements, protocols, annexed terms of understanding,
  joint declarations, exchanges of notes/letters that constitute an agreement.
- `law` - laws, imperial ordinances, regulations, imperial rescripts, when the articles/text itself is
  printed (e.g. "Article 1. ...").
- `speech` - addresses, speeches, broadcasts, lectures, messages delivered by a named person
  (Diet ministerial addresses, radio addresses, banquet addresses, messages to the Diet).
- `summary` - an official summary or explanatory account of a law that does not print its articles (only when
  it is long enough to be worth taking; see below). `law` is reserved for the text of the law itself.
- `list` - see "Recently promulgated columns" below.
- `document` - other verbatim official texts: government/Foreign Office statements, diplomatic notes,
  protests, proclamations, announcements quoted in full, joint communiques.

Do **not** extract: commentary or explanatory articles about a law or treaty, summaries or paraphrases
(e.g. the Tokyo Gazette's "Laws and Ordinances Recently Promulgated" columns are mostly one-paragraph
*summaries* - skip those; but where that column or any other prints the actual articles of a treaty or
law, take it), narrative chronicles, academic articles, book reviews. A signed essay by a minister that
is an article rather than a delivered speech/statement is out; if the heading or a note says it was
delivered/broadcast/issued (e.g. "An Address Delivered at ...", "Broadcast on ..."), it is in.
Where an editorial introduction precedes a verbatim text, keep only the verbatim text, but record in
`notes` anything from the introduction needed to identify it (date, place, occasion).
If a multi-part item contains several separate texts (e.g. "Documents concerning the Panay Incident":
eleven notes and statements; a Diet session: several ministers' addresses), write **one file per text**.
In Contemporary Japan the relevant material is nearly all in the "Documentary Material" section at the
end of each issue: go through that whole section, from its first page to its last, and take every verbatim
text in it, whether or not the index lists it. Also check any other index entry whose title indicates a
verbatim speech or text. In the Tokyo Gazette, go by the index entries: check every entry that could be a
verbatim text (addresses, statements, documents, notes, treaties, pacts, rescripts, ordinances and laws
printed at length such as the "Income Tax Law" chapters or "Ordinance Pertaining to Control of Prices"),
including the "recently promulgated" columns, and the "Documents" sections.

## "Recently promulgated" columns (Tokyo Gazette)

The columns headed "Laws and Ordinances Recently Promulgated", "Ordinances Recently Promulgated", "Treaties
and Ordinances Recently Promulgated" etc. usually give each law a heading, a "(Law No. 57, Promulgated on
August 11, 1937)" line, and a short paragraph of summary; occasionally an entry is much fuller. Use a contact
sheet of the column to see which is which, then:

- Every such column gets **one `list` file per issue** recording every entry in it, whether or not you also
  extract it in full. Body: a Markdown table `| Title | Number | Promulgated | Page |` (title as printed;
  number as printed, e.g. "Law No. 57", "Imperial Ordinance No. 616", "Treaty No. 12"; promulgation date as
  printed, plus any "enforced since" date; printed page). No summaries. Front matter: `type: list`,
  `title: Laws and Ordinances Recently Promulgated` (the column heading as printed), `date:` blank.
  Read the pages at reading size for this - do not take titles or dates off the contact sheet or the index.
- An entry that prints the actual text (articles, treaty provisions), or whose account runs to about half a
  page or more, is **also** extracted in full as its own `law` / `treaty` file; if it is an official summary
  rather than the articles themselves, give it `type: summary`.

## Writing in small pieces, and resuming (important)

Agents on this job are regularly cut off by an output filter: on certain pages, the moment the agent starts
to emit the transcription, its whole run is terminated. The same page cuts off every agent that tries it.
So the work is organised so that a cut-off loses one page and tells the next agent exactly which page it was.

The progress file is `texts/_reports/<batch>.progress` (append-only; one line per event).

For every text (file):
1. Append `START <path of the file>` before you read its first page at reading size.
2. Work **one printed page at a time**: append `PAGE <path> <printed page number>`; Read that one page
   image; then write that page's transcription to the file in one tool call (create the file with the front
   matter and first page; append later pages with `cat >> file <<'EOF_TS' ... EOF_TS` or Edit). Never emit
   more than one printed page of transcription in a single tool call, never read ahead several pages before
   writing, and never repeat transcribed text in your messages or report. (Short `list` tables and texts
   under a page are a single cycle.)
3. When the text is complete append `DONE <path>`.

**Before starting**, read the progress file and list what exists in `texts/<src>/<ia>/` for your issues.
- Files marked DONE are finished: keep them, do not re-read their pages.
- A file with START and no DONE was being written when an agent was cut off. The page that cut it off is
  the last `PAGE` line for that path (if there are no PAGE lines for it: the printed page after the last
  `[[p. N]]` marker in the file, or the text's first page if the file does not exist). **Do not read that
  page.** Append `SKIPPAGE <path> <N>`, and put in the file, in that page's place:

  `[[p. N]]`

  `*[Page N was not transcribed. See the scan.]*`

  then continue with the following page, and finish the text normally (DONE). Add to the file's `notes:`
  "INCOMPLETE: p. N not transcribed". If a text already has three SKIPPAGE lines, stop work on it:
  append `BLOCKED <path>`, extend the note ("INCOMPLETE: not transcribed after p. N"), and move on.
- Your prompt may name further pages known to cut agents off: treat them the same way (SKIPPAGE, placeholder).
- Then carry on with whatever in the batch is not yet done. Keep file numbering (`NN`) unique within a folder.

## How to work

1. For each issue, pick candidate page ranges from the index, then make a **contact sheet** to see what is
   there and where each text starts and ends, rather than opening pages one by one:
   `python3 scripts/contact.py <ia> <first-pdf-page> <last-pdf-page> [cols]` (12 pages at 4 columns is
   readable enough to see headings; use fewer columns if not). Read the resulting PNG with the Read tool.
2. Render the pages you need at reading size: `python3 scripts/render.py <ia> <first> <last>` (130 dpi;
   pass a 4th argument such as 170 if print is hard to read) and Read each PNG.
3. **Read the page images with your own eyes and transcribe what you see.** Do not use OCR, `pdftotext`,
   the PDF's text layer, the Internet Archive's djvu text, the `apple-vision` or `llmimage` skills, or any
   image-description service, and do not paste text of these documents from memory or the web. If you
   delegate anything, the same rule applies. A word or figure you cannot read is `[illegible]` plus an
   entry in `notes`, never a guess.
4. Do not run any git command. Do not send any personal information anywhere; no network access is needed.
   Do not delete anything outside `_work/pages` and `_work/sheets` for your own issues.

## Output: one Markdown file per text

Path: `texts/<tg|cj>/<ia>/<NN>-<short-slug>.md` (`NN` = two-digit order of the text within the issue).

```
---
title: Treaty Concerning the Basic Relations between Japan and China
type: treaty
source: tg
ia: tokyo-gazette-4.1-12-1940.7-1941.6-Full
issue: January, 1941
leaf: 321
pages: 272-274
date: 1940-11-30
author: 
parties: Japan; China
section: Documents Concerning the Treaty between Japan and China
notes: 
---
(body)
```

- `title`: as printed (title case, not all caps); add what is needed to make it self-explanatory
  (e.g. "Address of the Prime Minister, Prince Fumimaro Konoe, at the 72nd Session of the Imperial Diet").
- `type`: `treaty` | `law` | `speech` | `document` | `summary` | `list`.
- Optional, for one text printed in instalments across issues: `series: <name of the whole text>` and `part: <n>`.
- `source`: `tg` or `cj`. `ia`, `issue`: from the batch file.
- `leaf`: IA leaf of the page where the text starts (= PDF page - 1). `pages`: printed page numbers.
- `date`: date of the text (signing, promulgation, delivery) as YYYY-MM-DD, or YYYY-MM / YYYY; blank if not given.
- `author`: speaker or issuing person/body with office (speech, document); `parties`: for treaties, `;`-separated.
- `section`: the index/section heading it appears under. `notes`: illegible spots, doubts, missing pages,
  "unofficial translation", totals that do not add up, etc. One line each key; no line breaks inside a value.

Body conventions:
- Faithful transcription: keep the original spelling, punctuation, capitalisation of words, and romanisation,
  including the source's errors (mark an obvious misprint with `[sic]` only if it could be mistaken for yours).
- Rejoin words hyphenated across line ends; one paragraph per printed paragraph, blank line between.
- Start of each printed page: a line by itself `[[p. 273]]` (printed page number), including the first.
- Internal headings (PREAMBLE, CHAPTER I, section titles): `### Heading`. Article labels as printed at the
  start of the paragraph in bold: `**Article 1.** ...`. Signature blocks: one line per line, ending with two spaces.
- Tables as Markdown tables; footnotes as `[^1]` with the note at the end. Omit running heads and page numbers.
- No commentary of your own in the body.

## Report

When finished write `texts/_reports/<batch>.md`: per issue, the PDF pages you read, the files written, every
index entry you checked and rejected with a one-phrase reason (summary only / commentary / not verbatim),
and every illegible spot. Your final message should be that report in brief (counts per issue + problems).
Work through the entire batch; do not stop early or sample.
