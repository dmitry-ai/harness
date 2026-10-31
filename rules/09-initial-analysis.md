---
trigger: always_on
description: "Initial Upwork analysis: workspace creation, five stages, and evidence"
---
# Initial Analysis
## INIT-1
The user invokes `/upwork-init <URL>` (in Codex also `$upwork-init <URL>`); the procedure and internal tools reside in the same-named skill.  
After an interruption, the user writes `"Continue analysis"` in the same chat; re-running `/upwork-init` is not required.  
First read the current agent KB and stage status of the project; resume unfinished work while preserving completed checks and source files.  
Create `proposals/daily/YYYY/MM/DD/N - domain_or_topic`: use the initial request date in `Europe/Istanbul`, allocate the number under a lock, and name the folder without unproven website attribution.  
Structure: `.md`, root `source/` folder (all client-attached files), local `.agents` with native settings, `.codex/config.toml` loader, `KB/Project.md`, `ꘖ/{KB,data}`, `ꙮ/1 - Analysis/{req,res}`, and `ꙮ/0/Context.md`.  
## INIT-2
Single capture → identity and completeness verification → `init` from saved JSON; re-capturing the page is not needed for formatting.  
Save the original job post text, actually available client history, coverage errors/boundaries, and all client-attached files simultaneously in the root `source/` folder of the project and in `ꘖ/KB/Evidence/Attachments/<sha256>/` with hash verification.  
Include all attached text documents (including PDF, DOCX, TXT, MD, etc.) verbatim and in full in both knowledge bases (`KB/Project.md` and `ꘖ/KB/{Project,Projects,Evidence}.md`) with proper Markdown formatting; transcribe all client-referenced videos (including Loom links inside the job description or attachments) in full with `[MM:SS]` timestamps; transcribe all attached images in full (verbatim text in `«»`, exhaustive UI description, confirmations and contradictions against client statements with arguments for/against and `%` scores).  
Maintain the KB per [KB-1](06-knowledge-base.md#kb-1); `init` preserves existing files and third-party structure.  
## INIT-3
The initial analysis comprises five connected stages:  
1. Identification of the client and their website, with evaluation of alternatives.  
1. What concerns the client and what they intend to achieve with the project.  
1. What misconceptions are supported by the description; `"none established"` is valid.  
1. Hypotheses for the causes of these problems in the specific client's system.  
1. Solution methods linked to the causes or task.  
Frame H per [DOC-2](04-statement-structure.md#doc-2) and M per [DOC-3](04-statement-structure.md#doc-3); back all evidence per [LINK-1](02-link-standards.md#link-1).  
During a technical/SEO website audit, sample all primary templates from `sitemap.xml`, check cross-page uniqueness and length of `<title>`/`<meta description>`, verify the presence of exactly one `<h1>` per page, inspect the `URL`/`title`/`image` structure in `sitemap.xml`, and check for tracking codes (`GA4`/`GTM`/`GSC`).  
## INIT-4
Populate the KB and evidence first, then the exact journal, link/analysis validations, and full context export.  
`Context.md` is the external export per KB-4; internal continuation and delegation use the agent KB.  
Before finalizing, address findings from the A.A substantive review and verify KB consistency; engage independent auditors per REVIEW-3, as a green schema check does not replace substantive evaluation.  
New publications must pass the current evidence contract and exact-response review; reading a legacy format does not grant clearance for a new publication.  
The final response in chat and `res/<N>.md` includes the complete five-stage breakdown with clickable links to primary evidence and verbatim quotes, without internal service notes about file generation; client identity established in `identity` is synchronized to `KB/Project.md`.  
A generated scaffold is not a completed analysis; do not report model selection, delegation launch, or rule loading as verified without observation.  
## INIT-5
Client intermediation and an unidentified target website are distinct Red Flags; criteria and the contract reside in the `/upwork-init` skill.  
Display any identified flags in a prominent block at the very beginning of the report/response and duplicate them at the end of the project's root `.md` inside a dedicated level-1 `# Red Flags` section, placing both service markers after its heading; highlight the combination of both flags as a high likelihood that the user will decline the project.  
If `red_flags` is empty after evaluating both risks, do not output a `Red Flags` heading or section either at the beginning of the response/report or at the end of the root `.md`.  
In the root `.md`, maintain the managed Red Flags and client/target website blocks with URL, score, and link to the identity claim while preserving all other authored text; do not present unknowns or hypotheses as confirmed facts.  
