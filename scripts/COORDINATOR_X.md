# Coordinator instructions (second pass: whole articles)

You are a COORDINATOR for one batch of the second transcription pass, named in your prompt as BATCH (e.g. x03).
You do not transcribe anything yourself and you never Read page images at reading size; your job is to keep
launching one worker sub-agent at a time until the batch is finished.

Project root: /Users/kml/shell/projects/treaties-speeches. Read scripts/ARTICLE_BRIEF.md and the section "Writing
in small pieces, and resuming" of scripts/AGENT_BRIEF.md so you understand the job and the progress protocol.
Batch file: _work/batches/BATCH.json (a list of articles, each with an `out` path). Progress file:
texts/_reports/BATCH.progress. Report: texts/_reports/BATCH.md.

Background: worker agents on this job are often terminated by an API output filter ("Output blocked by content
filtering policy") the moment they start writing certain pages; the same page stops every worker. The progress
file then shows a START without DONE whose last PAGE line is the page that did it; the next worker skips that page
(SKIPPAGE + placeholder) and carries on. You must then launch the next worker.

Loop:
1. Launch ONE worker with the Agent tool (subagent_type "general-purpose", model "sonnet"), never more than one at
   a time, with this prompt (replace BATCH):

---
You are transcribing whole articles (government programmes, reports, reviews, statistical tables, profiles) from scanned 1930s-40s English-language Japanese journals into Markdown files, by reading page images with your own eyes (no OCR, no PDF text layer, no pdftotext, no apple-vision/llmimage skills, no text from memory or the web).
Project root: /Users/kml/shell/projects/treaties-speeches. First read scripts/AGENT_BRIEF.md and then scripts/ARTICLE_BRIEF.md in full and follow them exactly, above all "Writing in small pieces, and resuming" (START / PAGE / DONE / SKIPPAGE / BLOCKED lines; one printed page per read-then-write cycle with a PAGE line appended BEFORE each Read; no transcribed text in chat) and the rules for tables (every cell as printed; empty cell plus a note for anything unreadable; add up printed totals and note any that do not reconcile).
Your batch: BATCH → _work/batches/BATCH.json. Report: texts/_reports/BATCH.md; progress file: texts/_reports/BATCH.progress.
Earlier workers may have done part of this batch and been cut off: read the progress file first (if it exists) and check which `out` files exist. Every text with a START and no DONE (and no BLOCKED) cut a worker off; its last PAGE line names the page that did it — never read that page; SKIPPAGE it as the brief says, then continue that text from the following page. In this pass the three-SKIPPAGE limit is raised: only mark a text BLOCKED after six skipped pages. Work through the items in order. When every item is DONE or BLOCKED, append `BATCH COMPLETE` to the progress file. Never run git. Do not delegate to sub-agents.
---

2. When the worker returns (finished, or failed with the content-filter error), check the tail of the progress
   file. If it ends with `BATCH COMPLETE`, stop. Otherwise launch the next worker. If three workers in a row leave
   the progress file unchanged, stop and report why.
3. Safety valve: stop after 80 workers.

Never run git. Your final message: number of workers launched, counts of DONE / SKIPPAGE / BLOCKED lines, the files
with skipped pages or BLOCKED, table totals that did not reconcile, and anything else the workers flagged.
