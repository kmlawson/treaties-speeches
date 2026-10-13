# Brief: proofreading transcriptions against the scan

You compare existing transcriptions with the page images and correct them. You do NOT re-transcribe: you never
write out a passage of the text, in a file or in chat, beyond the few words needed for a correction.

Project root: /Users/kml/shell/projects/treaties-speeches. Your prompt gives you a list file (one job per line:
`<text file>\t<printed pages to check>`), a progress file and a report file.

Rules
- Read the page images with your own eyes (render with `python3 scripts/render.py <ia> <pdf-page> <pdf-page> 170`;
  `<ia>` is the name of the folder the text file is in; the scan is `_work/pdf/<ia>/issue.pdf`). No OCR, no PDF text
  layer, no pdftotext, no apple-vision / llmimage, no text from memory or the web.
- Finding the page: the file's front matter has `leaf:` (IA leaf of its first page; PDF page = leaf + 1) and the
  body has `[[p. N]]` markers. For the Japan-Manchoukuo Year Book, PDF page = printed page - 564, two columns per
  page. Some 1941-42 Tokyo Gazette issues are two-page spreads (one PDF page = two printed pages). Check the
  printed page number on the image before comparing.
- For each job: append `CHECK <file> <page>` to the progress file, Read the page image, Read the corresponding part
  of the text file (Read with offset/limit around the `[[p. N]]` marker), and compare word by word: dropped or
  repeated words, lines or sentences; wrong words; names and place names (letter by letter - the transcription
  must keep the book's spelling, even where it looks wrong or old-fashioned, e.g. "Yunting" must not have become
  "Yungting"); figures and dates; paragraph breaks; text belonging to a neighbouring item wrongly included.
- Fix each discrepancy with a small Edit whose old_string and new_string are only a few words long (just enough
  context to be unique). If a whole line or sentence is missing, add it with an Edit that anchors on the few words
  before it. Never rewrite a paragraph wholesale. If you cannot read a word on the scan, do not change it.
- Do not touch front matter, page markers, or lines of the form `*[Page N was transcribed with ...]*`.
- After each page append `OK <file> <page> <number of corrections>` to the progress file. If the progress file
  already has an OK line for a job, skip it (an earlier checker did it). If it has a CHECK line with no OK line,
  that page cut the previous checker off: append `SKIP <file> <page>` and move on without reading it.
- Report file: one line per correction (file, page, what was wrong -> what the scan has, in a few words), and a
  final count. Your final message: pages checked, corrections made, pages skipped.
- Never run git. Do not delegate to sub-agents.
