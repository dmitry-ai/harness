"""Source-byte checks reuse the evidence contract; network reachability is separate."""

import json

from .claims import contract_issues, evidence_contract_issues
from .links import check_network, references
from .text_claims import registry_path, subset, evidence_inputs
from .text_core import Finding, scan


def check_claim_sources(root, identifiers, *, reference='ꘖ/KB/TextClaims.json'):
    path = registry_path(root, reference)
    selected = subset(json.loads(path.read_text(encoding='utf-8-sig')), identifiers)
    issues = contract_issues(selected)
    if not issues:
        issues.extend(evidence_contract_issues(root, selected))
    return {'valid': not issues, 'issues': issues, 'inputs': evidence_inputs(root, selected) if not issues else {},
            'coverage': 'Saved primary bytes, quotes, locators and declared method contracts; source applicability and entailment require authored review.'}


def check_links(text, *, fetcher=None):
    # Include URL literals used as source references; exclude fenced commands and quotations.
    prose = '\n'.join(line.raw for line in scan(text) if line.kind == 'prose')
    urls = references(prose)[0]
    urls = list(dict.fromkeys(url.rstrip('.,;') for url in urls if url.startswith(('https://', 'http://'))))
    results = check_network(urls, fetcher=fetcher)
    results += check_network(urls, anchors=True, fetcher=fetcher)
    allowed = {'http-ok', 'found-in-source'}
    return [Finding('error', 'SOURCE-UNVERIFIED', 1,
                    f"{result['url']}: {result['status']}; save an authorized DOM/console observation if the HTML cannot establish the target")
            for result in results if result['status'] not in allowed]
