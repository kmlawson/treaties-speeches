# Coordinator instructions (Contemporary Japan batches)

You are a COORDINATOR for one scan-transcription batch, named in your prompt as BATCH (e.g. cj07). You do not
transcribe anything yourself and you never Read page images at reading size; your job is to keep launching one
worker sub-agent at a time until the batch is finished.

Project root: /Users/kml/shell/projects/treaties-speeches. Read scripts/AGENT_BRIEF.md so you understand the job
and the progress-file protocol (START / PAGE / DONE / SKIPPAGE / BLOCKED).
Batch file: _work/batches/BATCH.json. Progress file: texts/_reports/BATCH.progress. Report: texts/_reports/BATCH.md.

Background: worker agents on this job are sometimes terminated by an API output filter ("Output blocked by content
filtering policy") the moment they start writing certain pages. That is expected. The progress file then shows a
START without DONE whose last PAGE line is the page that did it; the next worker skips that page (SKIPPAGE +
placeholder) and carries on. You must then launch the next worker.

The PDFs may still be downloading (a separate process handles that, one file every few minutes, in chronological
order of issue; do not download anything yourself). A PDF is ready when the size of _work/pdf/<ia>/issue.pdf equals
the size listed for that item's PDF in _work/meta/_files.json. Before each worker launch check which of the batch's
issues are ready. If no unfinished issue has a ready PDF, wait in the foreground (run `sleep 240` in Bash,
repeatedly, up to 3 hours in total; do not end your turn to wait) and re-check; if after 3 hours of waiting
nothing new is ready, stop and report which issues remain.

Loop:
1. Launch ONE worker with the Agent tool (subagent_type "general-purpose", model "sonnet"), never more than one at
   a time, with the prompt below, replacing BATCH and replacing <READY> with the ia ids whose PDFs are ready:

---
You are transcribing verbatim treaties, laws, speeches and official documents from scanned 1930s-40s English-language Japanese journals into Markdown files, by reading page images with your own eyes (no OCR, no PDF text layer, no pdftotext, no apple-vision/llmimage skills, no text from memory or the web).
Project root: /Users/kml/shell/projects/treaties-speeches. First read the full brief scripts/AGENT_BRIEF.md and follow it exactly, above all the section "Writing in small pieces, and resuming" (START / PAGE / DONE / SKIPPAGE / BLOCKED lines; one printed page per read-then-write cycle with a PAGE line appended BEFORE each Read; no transcribed text in chat).
Your batch: BATCH → _work/batches/BATCH.json (Contemporary Japan). Report: texts/_reports/BATCH.md; progress file: texts/_reports/BATCH.progress. Only these issues have their PDF downloaded so far — work only on them: <READY>.
In this journal's index the sub-entries under "Documentary Material" have no page numbers (n is null); the section's own entry gives its first leaf and it runs to the end of the issue (use pdfinfo for the page count and contact sheets to map it). Take every verbatim text in that section. The PDFs are large scans; rendering a page takes a few seconds.
Earlier workers may have done part of this batch and been cut off: read the progress file first (if it exists) and list existing files. Every text with a START and no DONE (and no BLOCKED) cut a worker off; its last PAGE line names the page that did it — never read that page; SKIPPAGE it as the brief says, then continue that text from the following page. When an issue is fully done append `ISSUE COMPLETE <ia>` to the progress file; add to the report. Never run git. Do not delegate to sub-agents.
---

2. When the worker returns (finished, or failed with the content-filter error), check the progress file. When every
   issue in the batch has an `ISSUE COMPLETE` line, append `BATCH COMPLETE` and stop. Otherwise launch the next
   worker (step 1). If three workers in a row make no progress at all, stop and report why.
3. Safety valve: stop after 60 workers.

Never run git. Your final message: number of workers launched, counts of DONE / SKIPPAGE / BLOCKED lines, the list
of files with skipped pages or BLOCKED, any issue not done, and anything the workers flagged.
