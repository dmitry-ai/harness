# Commands and Service Data

All commands below are executed by the agent.  
`<scripts>` denotes `AI/harness/code/scripts`, and `<root>` denotes the exact root of the instruction.  
`df_text.py`, `df_article.py`, and `df_proposal.py` import the same CLI; the latter two select their default format.  
UTF-8 JSON/Markdown may be piped via `-` on stdin (subject to the UTF-8 file rule on Windows PowerShell).  
Exit code `0` means the check passed, `1` indicates substantive findings, and `2` indicates invalid input or an operation refusal.  

## Diagnostics and Format

```text
python <scripts>/df_text.py diagnose <root> --platform codex --profile C1
python <scripts>/df_article.py lint <file> --kind article --json
python <scripts>/df_proposal.py lint <file> --profile <profile.json>
python <scripts>/df_text.py lint <letter> --kind letter
python <scripts>/df_article.py lint <file> --network --project <root>
python <scripts>/df_article.py source <file> -o <separate-source>
python <scripts>/df_article.py render <source> --previous <file> --diff
python <scripts>/df_proposal.py render <source> -o <separate-candidate>
python <scripts>/df_proposal.py fields --fields <fields.json> --limits <limits.json>
```

Proposal profile: `numbering: nested|flat`, `voice: technical|offer`; extra parameters do not override the requirements of the current task.  
`fields.json` maps exact field names to the text being submitted, and `limits.json` maps them to each field's verified character limit.  
By default, length is counted as UTF-16 code units as in a browser; `--count-mode unicode` is used only when a different counter is verified.  
An article accepts the `link_style: markdown` profile for explicit checking of bare URLs.  
The `formatted` profile verifies that the domain, path, query, and fragment match between the visible label and target URL; a technical URL in the label does not create standalone numeric claims.  
See the [link contract](sources.md#link-labels-and-numbers).  
An external section reference is identified by an explicitly named document: `11 CCR §7025`, `RFC 9110 §15.4.3`, `ISO 27001:2022 §5.1`.  
Shared parsing supports RFC/ISO/IEC/IEEE/EN and numeric CCR/CFR/USC citations; internal references resolve against the item map.  
Rendering preserves the external section number, removes spaces after `§` in authored prose, and records the normalization in `external_references_normalized`; code and verbatim quotes are preserved untouched.  
`source/render -o` write a separate candidate file.  
An existing output file requires its current `--expected-sha256`; prior bytes are archived in history.  
These commands never overwrite a registered target or protected document.  

## Edit Contract

`begin <root> --spec <operation.json>` (alias `guard`) records the exact baseline bytes; JSON format:  

```json
{
  "kind": "proposal",
  "target": "result/EN/draft.md",
  "mode": "propose",
  "changes": "prose",
  "goal": "Explain the established tracking defect and the applicable repair.",
  "requests": ["Verbatim current user request"],
  "allow_sections": [],
  "protected": ["result/EN/draft.working.md"]
}
```

`kind`: `article|proposal|letter`; `mode`: `edit|propose|inspect`; `changes`: `prose|links|renumber`.  
An empty `allow_sections` array covers the entire target document; a non-empty array restricts edits to the exact items and their descendants or an inclusive range such as `I.16-I.20` or `2-4`.  
A scoped edit also verifies headings, groupings, anchors, and unchanged line endings.  
`protected` lists only explicitly protected documents; their absence on disk is also recorded.  
Do not list the target file itself in `protected`.  
To reconcile an external edit to an already registered document, pass `reconcile_sha256` of its actually read current version; this resets prior clearance without rolling back authored bytes.  
`shell` specifies an explicit Bash binary for the operation; `profile` specifies the format profile.  

## KB and Paragraph Map

```text
python <scripts>/df_text.py claims-save <root> --candidate <registry.json>
python <scripts>/df_text.py claims-save <root> --candidate <revision.json> --expected-sha256 <current-registry-hash>
python <scripts>/df_text.py sources <root> --claim <claim-id> --claim <other-id>
python <scripts>/df_text.py source-check <root> --candidate <candidate> --spec <source.json>
```

The default registry is `ꘖ/KB/TextClaims.json`.  
`--registry` selects a different explicit JSON file inside the agent KB.  
Schema v3, claim types, provenance, and locators follow the [existing evidence contract](../../skills/upwork-init/references/evidence-contract.md).  
For a standalone text, `{"schema_version":3,"facts":[…]}` suffices; hypotheses and recommendations are placed in their respective contract sections when needed.  
Required links and quotes obtain observations via the shared collector `upwork_project.py collect`, `capture-dom`, registered intake, or the experiment contract.  
Never populate `observation` with a fabricated report.  
`sources` verifies the exact closure of the listed claims; a mismatched quote, hash, or locator fails validation.  
A.A evaluates semantic applicability.  
For external URLs in the candidate, `source-check` writes separate mandatory receipts whose paths are listed in `manifest.source_checks`.  
The specification schema, expiration window, DOM fallback, failed probes, and source replacement are detailed in the [source contract](sources.md#observation-and-receipt).  

The candidate map uses schema v1:  

```json
{
  "schema_version": 1,
  "registry": "ꘖ/KB/TextClaims.json",
  "blocks": [{
    "key": "form-observation",
    "section": "1",
    "text_sha256": "SHA256 of the exact text bytes of this block",
    "role": "observation",
    "goal_basis": "What reader question this item resolves",
    "new_content": "What new substance it adds",
    "claim_ids": ["F-FORM-1"]
  }]
}
```

`text_claims.blocks(candidate, kind)` returns the exact `section`, `text`, `prose`, and `line` for computing hashes; an article does not duplicate child evidence inside a grouping parent, while a proposal includes item continuations and any separate preface.  
For a letter, blocks are paragraphs numbered `1`, `2`, and so on.  
The block key persists across renumbering and prose edits; substance, hash, and role are re-verified.  
Roles: `observation|documented|inference|recommendation|context|nonfactual`.  
A `nonfactual` block requires an empty `claim_ids` list and a specific `nonfactual_basis`; this is valid for a service offer or greeting, never for claims about a system.  
A qualified claim requires a `qualification` string present verbatim in the block text; re-introducing a fact requires a substantive `reuse_basis` evaluated by the reviewer.  
`commands` maps a fenced command line to explicit `exit`, `stdout`, and optional `stderr`; omitting the contract implies expected exit code `0` and comparison against the output quoted in the document.  

## Validation and Review

```text
python <scripts>/df_text.py check <root> --operation <ID> --candidate <candidate> --manifest <map.json> --run-replay
python <scripts>/df_text.py review-prepare <root> --check <check-path> --parent <native-parent-id> --spec <risk.json>
python <scripts>/df_text.py review-input <root> --package <package-path>
python <scripts>/upwork_project.py native-review-proof <root> --platform codex --reviewer <native-child-id> --parent <native-parent-id>
python <scripts>/df_text.py review-record <root> --report <authored-report> --parent <native-parent-id> --reviewer <native-child-id> --native-evidence <proof-path>
python <scripts>/df_text.py review-status <root> --check <check-path>
python <scripts>/df_text.py apply <root> --check <check-path>
```

Check, package, and proof paths are relative to `<root>` and taken from actual command outputs.  
`risk.json` specifies `risk: routine|significant`, a substantive `basis`, and `task_flags` for the current instruction; an actual material claim escalates risk regardless of a `routine` label.  
A native review is launched via the native subagent tool of the active platform.  
Pass the package path in the parent prompt; the child agent first executes `review-input` and then returns its authored JSON in its final message.  
`review-input` provides the exact report schema, including `claim_reviews[].test_alignment`, `text_checks`, and `source_reviews`, in `report_contract`; do not rewrite that contract in a custom schema.  
The parent generates a separate native proof receipt and submits the report via `review-record`.  
Forged or self-authored reports do not grant clearance to the text.  
Pass `--platform antigravity` on Antigravity; Codex C1/C2 is resolved from the active `CODEX_HOME` or an explicit `--codex-profile` on the shared tool.  
History from another profile may be read only when explicitly instructed by the user.  

For a purely mechanical edit, a passing `check` does not require a block map or new substantive approval, though external source checks remain mandatory.  
A mechanical check does not confer semantic readiness for submission.  
`--warnings` accepts JSON `{"RULE:line":"Substantive disposition of the warning"}`.  
Re-running `check` reuses an immutable saved replay via `--replay-record`; substituting a replay receipt from a different candidate is prohibited.  
`propose` and `inspect` modes do not permit `apply`.  

## Response and Completion

```text
python <scripts>/df_text.py response <answer> --against <target> --journal <journal>
python <scripts>/upwork_project.py answer-prepare <root> --response-file <answer> --platform codex
python <scripts>/df_text.py finalize <root>
python <scripts>/df_text.py finalize <root> --publication
```

`answer-prepare` fetches the exact requests from the active native turn, records the response, and verifies linked clearances; Antigravity passes `--platform antigravity --conversation <native-uuid>`.  
Turn initialization and independent delivery verification are documented in the [shared turn completion contract](../turn-completion.md#native-verification).  
Low-level `df_text.py record-answer <root> --journal <journal> --request-file <request> --response-file <answer> --turn <stable-turn-id>` remains available for compatibility and recovery; multiple `--request-file` flags bind several requests to one response, and retries are allowed only with identical bytes.  
Standard `record_step`, `record-answer`, analysis `finalize`, and `safe_commit` invoke the same gates for target files linked to the current instruction or explicit commit list.  
`finalize` validates registered documents in the explicitly selected text root; `--publication` additionally requires an active substantive clearance.  
This is a readiness check, not external submission.  
State is stored in `ꘖ/data/texts`: immutable baseline, operation, candidate, check/replay/apply receipts, review versions, and index.  
Primary evidence remains in `KB/Evidence`; temporary inputs may be deleted once durable receipts are saved.  

## CDP

`browser-check <root> --spec <session.json>` reads live `/json/version` and `/json/list` endpoints, verifies the profile and target via native CDP, and returns `unknown` when proof is unavailable.  
Specification fields: `session_id`, current `target_id`, and optional exact `target_url`.  
Permitted sessions are defined exclusively in `runtime.json → text.browser.sessions`; each entry specifies surface (`browser|codex|antigravity`), loopback endpoint or Antigravity `devtools_active_port`, profile with an observable command-line argument, and `target_url_patterns`.  
The client window and account are selected according to the instruction and live observation; this document never authorizes picking an arbitrary profile.  
Profiles C1/C2 use the reference `profile: {platform: codex, name: C1|C2, argument: --codex-home}` only when that exact argument is observable in the running build; otherwise the status remains `unknown`.  
`GuardedCDP` is a cooperative adapter rather than a global lock across external tools.  
Do not use native Codex/Antigravity UI automation as a workaround for a rejected CDP check.  
