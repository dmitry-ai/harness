# Shared Client Text Procedure

This procedure is shared across `/df-article`, `/df-proposal`, and client letters.  
The respective skill defines document form; a separate five-stage analysis or prior article is not required to write a proposal.  
`python <agents>/scripts/df_text.py` executes shared operations; `df_article.py` and `df_proposal.py` invoke the same CLI with their format preset.  
Schemas and commands are in [operations.md](operations.md), substantive review rules in [review.md](review.md), and style diagnostics in [slop.md](slop.md).  
The shared [turn completion contract](../turn-completion.md#turn-begin) applies even when no client document is modified; the text operation `begin` scopes document edits and does not replace `turn-begin`.  

## Scope of the Current Instruction

1. Establish the exact project root, target document, language, goal, mode (`edit|propose|inspect`), and permitted change kind (`prose|links|renumber`).  
Record the verbatim current requests, permitted sections, and protected files via `begin` before drafting any revision.  
A request to suggest or propose an edit means `propose`; it does not authorize applying the change to the target file.  
1. Read the current target file from disk.  
The baseline is its exact bytes prior to the operation, including uncommitted user edits; `git HEAD` or a prior chat reply never substitutes for the on-disk file.  
`begin` records those bytes and creates the mandatory FILE-2 snapshot when `draft.md` exists.  
Never run `git checkout`, `git restore`, or file deletion to "protect" an authored file.  
1. Run `diagnose` for the specific root and platform whenever instruction bindings are uncertain or a conflict is reported.  
The presence of configuration files and hashes does not prove that a model read the instructions.  
Do not batch-migrate unrelated client projects because a single manifest is missing.  
1. If the user edits the target file while work is in progress, save your prepared candidate separately, read the new on-disk version, and reconcile changes in a new operation.  
`apply` refuses on any baseline mismatch; for an already registered document, a new operation accepts the current hash via `reconcile_sha256` only after reading and reconciling the user's edits.  
A protected source file from another editor is never modified when porting its changes into the target document.  

## Substance and Evidence

1. Select material that serves the reader's decision.  
Every paragraph must contribute an observation, justified inference, direct answer, or actionable step.  
Introduce each fact once; referencing it later does not replace verifying the downstream inference.  
Lexical similarity alone does not prove semantic repetition.  
1. Analyze the client's system using objective subjects: `the website`, the domain name, or the exact component.  
Do not use authored `your` when describing the system; code blocks and verbatim quotes remain untouched.  
Do not repeat the client's brief back as your own discovery.  
Do not attribute the user's portfolio history or results from a sample project to the current client.  
1. Record any new factual claim in the agent KB with primary grounds per [evidence contract v3](../../skills/upwork-init/references/evidence-contract.md) first.  
An existing project analysis registry may be reused directly.  
For standalone texts, `claims-save` maintains `ꘖ/KB/TextClaims.json`; there is no need to fabricate five analysis stages.  
An old draft, agent opinion, or client agreement does not become primary evidence upon import.  
1. Preserve essential distinctions: observation vs. explanation; platform capability vs. site configuration; client report vs. direct measurement; raw HTTP vs. post-execution DOM; historical capture vs. current state.  
For every specific claim, define the method, the property actually tested, and a counterexample that yields the same test output when the claim is false.  
Indirect compatibility leaves a claim qualified or unverified.  
1. Preserve modality, quantifiers, and scope.  
`"Often"` does not become `"never"`, a single URL does not become all routes, and absence of a trace does not become physical impossibility.  
Upgrading `"probably"` to an unqualified assertion requires new primary evidence.  
The utility of a recommendation, business harm, and developer intent must be verified separately from the presence of a technical property.  
1. Validate every link according to its role: target page, exact anchor, quote in context, product, version, and applicability.  
`sources` validates saved primary bytes and claim locators; `source-check` binds the quote and exact URL to the candidate bytes.  
Source receipts are mandatory for `check`, `apply`, and readiness verification even on mechanical edits.  
See the [source contract](sources.md#mandatory-source-clearance).  
`lint --network --project <root>` saves HTTP responses and checks the final URL and anchor, but a passing network probe does not replace a verified quote.  
A later failed probe blocks reuse of an older passing observation for the same URL.  
An anchor absent from raw HTML may require a DOM capture; an HTTP 200 redirect to a login page does not confirm a private report.  
Unavailability never grants `verified` status.  
Matching a keyword on a documentation page does not prove a claim about the client's site.  
Replacing an unavailable source requires independent verification of the new URL, quote, edition, and applicability; if grounds remain insufficient, report the claim as unverified rather than granting clearance.  
See the [replacement procedure](sources.md#unavailability-and-replacement).  
1. For every number, record the primary operands, units, formula, and rounding rule.  
For every console report, record the property, exact URL, filters, date range, metric, denominator, and pagination.  
Supported calculations are verified deterministically by the contract; other calculations require a reproducible primary artifact.  
Mentioning a number inside `essence` does not establish its provenance.  
1. `claims-save` preserves version history and marks dependent conclusions `stale` whenever a ground changes; adding a parent note does not restore their status.  
Locate all dependent KB conclusions and text blocks.  
Update permitted artifacts; for out-of-scope files, record the staleness and required follow-up without editing them uninvited.  
1. Map every substantive block to a stable key, exact text digest, role, contribution to the goal, new substance, and KB claim digests.  
A greeting, service offer, or clarifying question may use `nonfactual` with a concrete basis.  
That label never exempts embedded factual assertions from independent verification.  
Keep the block map in service storage outside the client text.  

## Preparation, Validation, and Writing

1. Write the candidate inside the service directory.  
`source` and `render` rebuild numbering while preserving code, URLs, and quotes; a reference to a deleted key fails rendering.  
`render --diff` prints the diff without overwriting a registered authored document.  
`apply` writes the target file only after verifying the exact baseline digest.  
1. Run the format-specific `lint` and fix all errors.  
Any retained warnings require a substantive disposition in `warning_dispositions`, and paragraph-necessity notes are evaluated against the document goal.  
Project-specific phrase bans live in `ꘖ/data/text-bans.json` (legacy `article-bans.json` remains readable for compatibility).  
Do not turn project-specific names or phrases into global rules.  
1. Execute new or modified commands via `check --run-replay`, capturing raw stdout, stderr, exit code, and the Bash binary used.  
On Windows, an installed Cygwin Bash is selected by default; `client_text.bash`, `DF_TEXT_BASH`, or `--shell` sets an explicit path.  
Validation requires coverage of the selected blocks and output comparison; missing quoted output is not a pass.  
Reader-facing output formatting is compared separately from raw capture bytes.  
Format short commands per `P.Bash.md`; use a four-space indent and an argument array when passing three or more parameters.  
Extract long parsing logic into a version-pinned helper script only within the scope of the instruction; permission to draft text does not authorize publishing code.  
1. `check` binds the candidate, scope, block map, KB, evidence, `source_checks`, and command replay.  
A mechanical edit verifies preservation of all other prose, literals, and line endings alongside external source checks.  
`propose` saves the candidate and diff while forbidding `apply`.  
A substantive edit requires independent review of the [specific version](review.md).  
1. Once approved, run `apply`.  
If `apply` refuses, never overwrite user text from Git; resolve the cause while preserving the current on-disk bytes.  
Standard response recording checks only documents linked to the exact current requests of the operation.  
Commit validation checks registered target files in the explicit commit list; an error in an unrelated draft does not authorize editing it.  
1. Lead your response with the result of the current instruction on the first line.  
Take changes and counts from the saved diff and actual files; verify any claims about removed text via `response --against`.  
Run [answer-prepare](../turn-completion.md#answer-preparation) with the exact final response and publish the returned `response_file`; never reply to a new question by pasting a stale report.  
Similarity between responses is a prompt to verify execution, not proof of non-execution.  

## Browser and Tool Limits

When inspecting Codex or Antigravity via CDP, follow the user's standing settings and use `Page.captureScreenshot` for visual captures.  
For a client browser, explicitly select a permitted session, profile, current target, and account when applicable.  
`browser-check` never infers a profile from a port number alone and never accepts hand-crafted JSON as native proof.  
`GuardedCDP` re-verifies the target before actions and serializes its own workers; active user tabs remain read-only.  
Never restart Antigravity or close the last or user-owned browser window.  
If profile proof is unavailable, this adapter remains inapplicable while standard HTTP collection and independent primary-source verification continue.  

This workflow provides an auditable preparation path.  
It does not sandbox an arbitrary shell and does not guarantee that the host OS prevents direct file writes outside the tools.  
`finalize --publication` certifies readiness only for registered texts holding a current substantive clearance; the command neither publishes nor sends text to a client.  
