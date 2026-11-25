---
trigger: model_decision
description: "Read when maintaining project knowledge bases (🕮/Project.md, ꘖ/KB), saving primary evidence, continuing interrupted analyses, or exporting Context.md"
---
# Knowledge Base
## KB-1
`🕮/` belongs to the user; the agent creates `🕮/Project.md` once during initial analysis (synchronizing `# 2. Current Client Project` during `sync-attachments`) and thereafter never modifies manual KB files without explicit instruction (for `fs_version: 1` paths, see [legacy-v1-compatibility.md](../references/legacy-v1-compatibility.md)).  
Immediately port the complete initial document into `ꘖ/KB/Project.md` (`Projects.md`, `Evidence.md`), including verbatim attached text documents (PDF/DOCX/TXT/MD with Markdown formatting), full timestamped `[MM:SS]` video transcripts (`# Video:`, `# Key Spoken Commentary Points (Additions to Document Text):`, `# Full Audio Transcript:`), and full image descriptions (verbatim text/UI labels in `«»`, confirmations/contradictions with `%` scores); store all further research exclusively in `ꘖ/KB`.  
External `http(s)://` links in project responses must be backed by `ꘖ/KB` entries and saved primary observations; re-running `init` preserves user-authored and agent-enriched documents.  
## KB-2
Organize `ꘖ/KB` into compact topical modules, primary evidence, and a relationship registry so each fact is stored once under stable IDs (`F` observation/client report, `H` hypothesis, `M` method; headings act as anchors without HTML tags).  
Record claim, verbatim quote, source, date, and scope on `F` entries; derived F/H/M references carry verifiable digests, and changed grounds require re-evaluating dependent conclusions rather than preserving old scores.  
Frame `H` per [DOC-2](04-statement-structure.md#doc-2) and `M` per [DOC-3](04-statement-structure.md#doc-3); a mentioned domain, review name, prior contract, or folder name never proves identity or website ownership.  
## KB-3
Read the overview and relevant topical modules before investigating; save verified findings and audit dependent claims before responding.  
On continuation (`"Continue analysis"` or cross-platform handoff on the same disk root), restore state from `ꘖ/KB`, receipts, exact journal, existing deliverables, and `ꘖ/data/continuation.md` without fabricating chat history or re-running finished stages.  
Run HTTP(S) and browser DOM observations exclusively through `harness.py collect`, `collect-http`, or `collect-browser`, saving under `ꘖ/KB/Evidence/HTTP`; after context compaction (`CHECKPOINT`), restore pre-compaction reads via `recover-checkpoint` or `transcript_full.jsonl`.  
Preserve provenance of prior versions and handle temporary files per [FILE-5](01-file-boundaries.md#file-5).  
## KB-4
`Ⰿ/≻/♙/Context/output/Context.md` exports the generation timestamp and `ꘖ/KB/*.md` (strictly excluding `Evidence/`) for manual submission to external agents (primarily Gemini DeepThink).  
Build `Context.md` only when explicitly requested by the user; internal agents work directly with `ꘖ/KB` and never overwrite source files.  
