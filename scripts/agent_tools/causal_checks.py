"""Narrow diagnostics for an observed unsupported-probability failure.

This does not infer mental states, forbid equal priors, or replace authored review.
Only an explicit claim that ignorance establishes equal probabilities is rejected.
"""

import re


def unsupported_probability_claims(text):
    from .text_core import scan
    # Quoted source material is historical evidence, not the author's assertion.
    lines = [line for line in scan(text) if line.kind == 'prose']
    issues = []
    for line in lines:
        value = re.sub(r'`[^`]*`|«[^»]*»|"[^"\n]*"', ' ', line.raw)
        value = re.sub(r'\[[^\]]*\]\([^)]*\)', ' ', value)
        if re.search(r'(?i)\b(?:не\s+(?:означа\w*|доказыва\w*|устанавлива\w*|следу\w*)|does\s+not|cannot\s+(?:establish|prove|imply))\b', value):
            continue
        equality = re.search(r'(?i)равн\w*\s+(?:процент\w*|вероятност\w*|оценк\w*)|равновероят\w*|equal\s+(?:probabilit\w*|likelihood\w*)|50\s*[/—–:-]\s*50', value)
        ignorance = re.search(r'(?i)отсутств\w*\s+(?:доказатель\w*\s+)?(?:основан\w*|данн\w*|свидетельств\w*)|не\s+(?:зна\w*|нахожу\s+основан\w*)|lack\s+of\s+(?:evidence|information)|no\s+evidence', value)
        link = re.search(r'(?i)означа\w*|следоват\w*|поэтому|потому\s+что|поскольку|because|therefore|implies|means', value)
        if equality and ignorance and link:
            issues.append(f'CAUSAL-PROBABILITY:{line.no}: absence of discriminating evidence does not establish equal probabilities; state the prior/basis or leave the cause unresolved')
    return issues
