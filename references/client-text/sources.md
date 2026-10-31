# External Source Clearance for Client Text

## Mandatory Source Clearance

`check` requires a `source-check` receipt for every external HTTP(S) URL in authored prose and headings of a candidate.  
This requirement also applies to mechanical link edits and `inspect` mode; fenced code blocks and blockquotes do not count as authored links.  
Exact addresses are verified, including significant query parameters and fragments, with readable Unicode normalized to a canonical form.  

Each receipt is bound to the SHA256 of the candidate's exact UTF-8 bytes, the URL, the saved HTTP/DOM observation, and the hashes of primary evidence files.  
An arbitrary `{"valid":true}` object cannot substitute for a receipt.  
Modifying the candidate text requires new receipts, and modifying primary evidence bytes invalidates any prior receipt.  

`apply`, review validation, and `finalize` re-verify these grounds without making new network requests.  
Legacy apply receipts that contain external links without source checks no longer certify document readiness.  
This contract is enforced across the standard tools; it does not sandbox arbitrary shell writes outside the toolkit.  

## Observation and Receipt

Explicit network diagnostics save primary responses, including HTTP errors and redirects:  

```text
python <scripts>/df_article.py lint <candidate> --network --project <root>
```

The candidate must reside inside the specified project root.  
A single invocation performs one GET per base URL even when multiple links differ only by `#fragment`.  
`*-probe.json` receipts are stored in `ꘖ/data/texts/sources`, while raw response bytes and metadata are stored in `KB/Evidence`.  
HTTP 200 alone does not grant substantive clearance.  
Standard `lint` without `--network` remains a local format check.  

After reading the primary source, prepare the specification and run:  

```text
python <scripts>/df_text.py source-check <root> --candidate <candidate> --spec <source.json>
```

The example schema below is synthetic; take paths and hashes from actual `collect` or `capture-dom` outputs:  

```json
{
  "url": "https://example.org/manual#limits",
  "currency": "current",
  "currency_basis": "Why this page applies to the current claim and version",
  "evidence": {
    "source": "https://example.org/manual#limits",
    "observation": "Evidence/HTTP/<capture>/observation.json",
    "source_sha256": "<SHA256 of saved response.bin>",
    "documentation": true,
    "locator": {"type": "anchor", "value": "limits"},
    "quote": "Verbatim quote from the verified section"
  }
}
```

`observation` resolves relative to `ꘖ/KB`; `source_check` in the command output resolves relative to the project root.  
List the exact receipt paths returned by the command in the candidate manifest:  

```json
{"source_checks": ["ꘖ/data/texts/sources/<hash>-source.json"]}
```

For a substantive edit, this field supplements the block map; for a mechanical edit, it is required even without a block map.  
A failed `source-check` also writes an immutable receipt, but returns `valid: false` and exit code `1`; such a receipt never clears the text.  

Validation checks the requested and final URLs, HTTP status, saved bytes, their SHA256 digest, existence and uniqueness of the anchor, and containment of the quote within that fragment.  
An unexpected final URL after redirection is rejected.  
For a verified redirect, specify `expected_final_url` explicitly; quote and anchor checks still apply.  
A shortened URL is permissible only after verifying that it resolves to the same resource and fragment, never from path similarity alone.  

For documentation, an existing anchor must appear in the cited URL itself.  
If no suitable anchor exists on the page, use `locator.type: text`, an exact quote, and `anchor_exception: {"section":"Section Title","observation":"Same observation path"}` inside `evidence`.  
The collector must confirm that the section title is unique and that neither the heading nor its ancestors carry an anchor; a prose note from the author does not replace this check.  

`currency: current` requires an observation no older than 24 hours.  
That window defines receipt freshness rather than automatic proof that a standard is still in force.  
`currency: historical` requires non-empty `edition` and `currency_basis` fields; applicability of a historical edition to the claim is evaluated during review.  
An archived edition cannot be relabeled `current` merely by changing the field value.  

## Unavailability and Replacement

A later failed or contradicting check of the same URL within the project blocks reuse of an earlier passing check.  
Editing the candidate text does not erase that failure record.  
A new successful observation, sufficient quote, and fresh receipt resolve the conflict; independently collected later bytes of the same resource with an identical hash do not invalidate the author's check.  

An HTTP error or bot-protection page may be resolved via a DOM snapshot captured from a permitted CDP session.  
`capture-dom` returns the observation and `cdp_identity`; pass both in the `source-check` specification.  
Validation verifies the binding between the observation, exact session, target, `READ_DOM` method, and immutable identity receipt.  
An unverified browser profile or arbitrary local DOM file cannot substitute for this path.  

A replacement official source is validated as a brand-new URL: quote, fragment, edition, and applicability.  
Update the candidate text first and then generate its new receipts.  
A snapshot of a different page never validates a broken URL left inside the text.  
If sufficient primary evidence is unavailable, record the gap in the report; a candidate containing an unverified external URL cannot receive positive clearance.  

## Link Labels and Numbers

In the `link_style: formatted` article profile, the visible link label must preserve the domain, path, query, and fragment of the target URL; `www.` and the scheme may be omitted.  
Stripping only the visible `#anchor` triggers `LINK-LABEL`.  
Named link labels are permitted in other profiles; code blocks and verbatim quotes remain untouched.  

Standalone number extraction parses Markdown links, including reference links and balanced parentheses.  
Numbers inside a technical URL label pointing to the same domain are treated as address identifiers.  
Quantitative prose inside a link label, such as `[The limit is 15.3 volts.](https://example.org/)`, still requires numeric evidence.  

## Review and Limits

To approve each external URL, the reviewer populates `source_reviews`:  

```json
{
  "url": "https://example.org/manual#limits",
  "receipt": "ꘖ/data/texts/sources/<hash>-source.json",
  "assessment": "What the quote establishes for this specific claim, version, and condition",
  "outcome": "supported"
}
```

Valid outcomes are `supported` and `unsupported`; an `approved` verdict requires complete coverage and `supported` for every cited URL.  
When returning `needs_changes`, the reviewer lists defects in `findings`, including any missing or insufficient receipt.  
The reviewer may collect its own observation and receipt for the same candidate.  
`review-record` stores the hashes of receipts and primary bytes in the proof, including independently gathered grounds.  

Mechanical validation confirms provenance, addressing, and quote presence.  
The strings in `currency_basis`, `assessment`, and a matching quote do not by themselves prove logical entailment, regulatory currency, or applicability to the client's system.  
Evaluating those remains the responsibility of [substantive review](review.md#independent-review-of-a-specific-text-version); native authorship of the verdict is enforced by the review provenance contract.  
