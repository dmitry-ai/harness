---
trigger: always_on
description: "KB ownership, knowledge types, stable IDs, and full context export"
---
# Knowledge Base
## KB-1
`KB/` belongs to the user; the agent creates `KB/Project.md` once during initial analysis (and synchronizes the `# 2. Current Client Project` section during `sync-attachments`), and thereafter does not modify it or other manual KB files without a new direct instruction.  
Immediately port the complete initial document into `ꘖ/KB/Project.md` (as well as `ꘖ/KB/Projects.md` and `ꘖ/KB/Evidence.md`), including verbatim and in full all attached text files (including PDF and DOCX) with Markdown formatting, complete transcripts of client videos (`# Video:`, `# Key Spoken Commentary Points (Additions to Document Text):`, `# Full Audio Transcript:` with `[MM:SS]` timestamps), and complete descriptions of images (verbatim text and UI labels in `«»`, confirmations and contradictions against client statements with `%` scores); store all further research exclusively in `ꘖ/KB`.  
External `http(s)://` links in a project response must be backed by entries in `ꘖ/KB` (modules, `Analysis.json`, or `Project.md`) and saved primary observations; adding external URLs to a response while bypassing `ꘖ/KB` is blocked.  
Re-running `init` does not regenerate user-authored or agent-enriched documents.  
## KB-2
The KB consists of compact topical modules, primary evidence, and a relationship registry; each fact is stored once.  
Use stable IDs: F for observation/quoted client report, H for hypothesis, M for method; a heading with the ID serves as the target anchor without HTML tags.  
An F entry contains the claim, exact quote, source, and observation date/scope; client statements do not become independent facts.  
For new analyses, structured F claims live in the analysis registry while topical Markdown modules expand their primary grounds via stable IDs.  
References to derived F/H/M items carry verifiable digests; a changed ground requires re-evaluating the dependent conclusion rather than keeping the old percentage.  
H and M conform to [DOC-2](04-statement-structure.md#doc-2) and [DOC-3](04-statement-structure.md#doc-3); link causes to concerns and methods to causes or tasks.  
A mentioned domain, a name in a review, a prior contract, or a folder name does not establish identity, website ownership, or that all jobs belong to one business.  
## KB-3
Read the overview and relevant topical modules before investigating; save new verified findings and corrections before responding, updating dependencies and the glossary.  
Internal agents of both platforms work with their own agent KB (`ꘖ/KB`), primary evidence, and its `Progress.md` navigation.  
Keep the KB current and self-consistent at all times: after new data arrives, audit dependent claims, update permitted modules, and explicitly mark anything unverified or stale.  
After an interruption and a `"Continue analysis"` request in the current chat, restore the next step from the KB and service receipts; the mere presence of an old file does not prove stage completion.  
A project may be continued in the other platform and in a new chat using the same root on disk, including semi-manual proposal preparation after initial analysis.  
Also read the exact journal and existing `result/**/draft.md`/`final.md`; do not carry over a conversation from one platform to another via fabricated history.  
Record the current instruction, working files, open questions, and next step in `ꘖ/data/continuation.md` with links to real artifacts.  
Completion of initial analysis and readiness of a proposal are distinct; a new instruction regarding a draft does not by itself require re-collection or all five analysis stages.  
H percentages change with evidence; promotion to a fact requires a separate observation rather than a high score.  
Preserve provenance of prior versions and material sources; handle temporary files per [FILE-5](01-file-boundaries.md#file-5).  
Perform network HTTP(S) and browser DOM observations through `harness.py collect`, `collect-http`, or `collect-browser` (with `upwork_project.py` retained as a compatibility alias), saving into `ꘖ/KB/Evidence/HTTP` and `ꘖ/data/http-index.json`; ad-hoc network calls in the shell that bypass evidence storage are prohibited.  
If context compaction (`CHECKPOINT`/`compaction`) occurs after tool calls before publishing the response, restore pre-compaction results via `recover-checkpoint` or by reading the full transcript.  
## KB-4
`ꙮ/0/Context.md` assembles sources in full: task, constraints, manual/agent KB, and chronological `req/res` pairs with authors.  
It is the unified export for external agents, primarily Gemini DeepThink in the web UI at `https://gemini.google.com`; the user submits it manually.  
Internal agents do not use `Context.md` as their working KB; build the external export after reconciling the KB and journal or when requested by the user.  
Do not truncate sources or replace them with summaries; flag an incomplete pair as a build error and preserve the previous context file.  
In correspondence, `final.md` takes priority over `draft.md`; an empty `final.md` is an error rather than permission to substitute `draft.md`.  
