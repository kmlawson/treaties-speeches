# Coordinator instructions (Japan-Manchoukuo Year Book 1934, Supplement III)

You are a COORDINATOR for one batch, named in your prompt as BATCH (jm01 ... jm04). You do not transcribe anything
yourself and never Read page images at reading size; you keep launching one worker sub-agent at a time until the
batch is finished.

Project root: /Users/kml/shell/projects/treaties-speeches. Read scripts/JM_BRIEF.md and the section "Writing in
small pieces, and resuming" of scripts/AGENT_BRIEF.md. Batch file: _work/batches/BATCH.json. Progress file:
texts/_reports/BATCH.progress. Report: texts/_reports/BATCH.md.

Workers on this job are often terminated by an API output filter ("Output blocked by content filtering policy")
the moment they start writing certain passages; the same passage stops every worker. The progress file then ends
with a PAGE line (page and column) for a text with START and no DONE; the next worker skips that column with a
placeholder and carries on. You then launch the next worker.

Loop:
1. Launch ONE worker (Agent tool, subagent_type "general-purpose", model "sonnet"), never more than one at a time,
   with this prompt (replace BATCH):

---
You are transcribing the texts of treaties, agreements, notes and statutes printed in a scanned 1934 English-language year book into Markdown files, by reading page images with your own eyes (no OCR, no PDF text layer, no pdftotext, no apple-vision/llmimage skills, no text from memory or the web — transcribe only what this book prints).
Project root: /Users/kml/shell/projects/treaties-speeches. First read scripts/AGENT_BRIEF.md and then scripts/JM_BRIEF.md in full and follow them exactly: two-column pages, one COLUMN per read-then-write cycle with a `PAGE <path> <page><L|R>` line appended to the progress file BEFORE each cycle, START / DONE lines per text, no transcribed text in chat.
Your batch: BATCH → _work/batches/BATCH.json. Progress file: texts/_reports/BATCH.progress; report: texts/_reports/BATCH.md.
Earlier workers may have done part of this batch and been cut off: read the progress file first (if it exists) and check which `out` files exist. A text with START and no DONE cut a worker off at its last PAGE line (page and column): do not transcribe that column — SKIPPAGE it with the placeholder as the brief says — and continue that text from the next column. There is no limit on skipped columns in this job: try every column once. Work through the texts in order. When every text is DONE, write the report and append `BATCH COMPLETE` to the progress file. Never run git. Do not delegate to sub-agents.
---

2. When the worker returns (finished or cut off), check the tail of the progress file. If it ends with
   `BATCH COMPLETE`, stop. Otherwise launch the next worker. If three workers in a row leave the progress file
   unchanged, stop and report why.
3. Safety valve: stop after 80 workers.

Never run git. Final message: workers launched, counts of DONE / SKIPPAGE lines, files with skipped columns,
unlisted texts added, anything illegible.
