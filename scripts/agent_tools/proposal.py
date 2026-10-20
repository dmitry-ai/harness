"""Plain numbered Upwork proposal format; common prose/evidence mechanics live elsewhere.

Pure transforms intentionally do not write files. The shared client-text transaction
is responsible for version checks, permissions, reviews and atomic replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

from .text_core import (Finding, Line, author_text, check_code, check_prose,
                        detect_language, find_bans, load_lexicon, scan,
                        transform_prose, external_section_ref, normalize_external_refs)


PREFIX = r'(?P<prefix>(?:[^\w\s@#]+\s+)?)'
NUMBERED = re.compile(PREFIX + r'(?P<number>\d+(?:\.\d+)*)\.(?P<gap>[ \t]+)(?P<body>.*)$')
KEYED = re.compile(PREFIX + r'@(?P<name>[\w]+(?:[.\-][\w]+)*)(?P<gap>[ \t]+)(?P<body>.*)$')
REF = re.compile(r'(?<![\w§])(?P<marks>§§?)(?P<space>[ \t]*)(?P<start>\d+(?:\.\d+)*)(?:[ \t]*(?P<dash>[-–—])[ \t]*§?(?P<end>\d+(?:\.\d+)*))?(?!\w|\.\d)')
KEY_REF = re.compile(r'(?<![\w§])(?P<marks>§§?)@(?P<start>[\w.\-]+?)(?:-@(?P<end>[\w.\-]+?))?(?=[^\w.\-]|\.(?:\s|$)|$)')
MARKDOWN_LINK = re.compile(r'!?\[[^\]\n]*\]\(<?(?:https?://|#)[^\n]*?\)')
URL = re.compile(r'https?://[^\s<>`]+')


@dataclass
class ProposalBlock:
    name: str
    number: tuple[int, ...]
    line: int
    end: int
    prefix: str = ''
    body: str = ''
    parent: 'ProposalBlock | None' = None
    gap: str = ' '

    @property
    def key(self) -> str:
        return '.'.join(map(str, self.number)) if self.number else self.name

    @property
    def dotted(self) -> str:
        return self.key


def _lines(value: str | list[Line]) -> list[Line]:
    return scan(value) if isinstance(value, str) else value


def _parent_name(name: str, known: Mapping[str, ProposalBlock]) -> str | None:
    """Only absent zero-prefaces may be implicit, as in 21.0.1 of the exemplar."""
    segments = name.split('.')
    if len(segments) == 1:
        return None
    parent = '.'.join(segments[:-1])
    if parent in known:
        return parent
    if segments[-2] == '0' and '.'.join(segments[:-2]) in known:
        return '.'.join(segments[:-2])
    return parent


def parse_blocks(value: str | list[Line], findings: list[Finding] | None = None,
                 *, keyed: bool = False) -> list[ProposalBlock]:
    """Parse plain numbered/keyed blocks, preserving editorial zero-prefaces."""
    lines = _lines(value)
    findings = findings if findings is not None else []
    blocks, known = [], {}
    pattern = KEYED if keyed else NUMBERED
    for line in lines:
        if line.kind != 'prose':
            continue
        match = pattern.fullmatch(line.raw)
        if match is None:
            if keyed and NUMBERED.fullmatch(line.raw):
                findings.append(Finding('error', 'KEY-NUMBERED', line.no,
                                        'use @key in the keyed view', line.raw))
            continue
        name = match.group('name' if keyed else 'number')
        number = () if keyed else tuple(int(n) for n in name.split('.'))
        block = ProposalBlock(name, number, line.no, len(lines),
                              match.group('prefix'), match.group('body'))
        block.gap = match.group('gap')
        if name in known:
            findings.append(Finding('error', 'KEY-DUP' if keyed else 'PROPOSAL-DUP',
                                    line.no, f'duplicate {"@" if keyed else "§"}{name}', line.raw))
        parent = _parent_name(name, known)
        if parent is not None:
            block.parent = known.get(parent)
            if block.parent is None:
                findings.append(Finding('error', 'KEY-PARENT' if keyed else 'PROPOSAL-PARENT',
                                        line.no, f'no preceding parent {parent}', line.raw))
        known[name] = block
        blocks.append(block)
    for index, block in enumerate(blocks):
        block.end = blocks[index + 1].line - 1 if index + 1 < len(blocks) else len(lines)
    return blocks


parse_sections = parse_blocks
parse = parse_blocks


def _number_refs(raw: str):
    author = author_text(raw)
    return (match for match in REF.finditer(author) if not external_section_ref(author, match))


def _reassemble(template: str, lines: list[Line], values: list[str]) -> str:
    """Keep each original newline, including CRLF and a missing final newline."""
    chunks = template.splitlines(keepends=True)
    return ''.join(value + chunk[len(line.raw):]
                   for line, value, chunk in zip(lines, values, chunks))


def _check_sequence(blocks, findings, profile):
    groups = {}
    for block in blocks:
        number = block.number
        if not number:
            continue
        if re.search(r'(?<!\s)' + re.escape(block.key) + r'\.\s+', author_text(block.body)):
            findings.append(Finding('error', 'PROPOSAL-CONCAT', block.line,
                                    f'a second {block.key}. point is joined onto the same line; remove the duplicate or separate it', block.body))
        if profile.get('numbering') == 'flat' and len(number) > 1:
            findings.append(Finding('error', 'PROPOSAL-FLAT', block.line,
                                    'nested point in the selected flat profile', block.key))
        prefix, ordinal = number[:-1], number[-1]
        siblings = groups.setdefault(prefix, [])
        # Zero is a marked preface, not the first positive sibling.
        if ordinal == 0 and prefix:
            siblings.append(ordinal)
            continue
        positives = [n for n in siblings if n > 0]
        expected = (int(profile.get('start', 1)) if not prefix else 1) + len(positives)
        if ordinal != expected:
            findings.append(Finding('error', 'PROPOSAL-SEQ', block.line,
                                    f'§{block.key} breaks the sequence (expected {expected} at this level)'))
        siblings.append(ordinal)


def _check_references(lines, blocks, findings, profile):
    known = {block.key for block in blocks} | {str(n) for n in profile.get('reference_targets', [])}
    for line in lines:
        if line.kind not in ('prose', 'heading'):
            continue
        for match in _number_refs(line.raw):
            marks, start, dash, end = match.group('marks', 'start', 'dash', 'end')
            if match.group('space'):
                findings.append(Finding('error', 'PROPOSAL-REF-SPACE', line.no,
                                        'write the point number immediately after §', match.group(0)))
            if (end and (marks != '§§' or dash != '-')) or (not end and marks == '§§'):
                findings.append(Finding('error', 'PROPOSAL-RANGE', line.no,
                                        'use §N for one point and §§N-M for a range', match.group(0)))
            for endpoint in (start, end):
                if endpoint and endpoint not in known:
                    findings.append(Finding('error', 'REF-DANGLING', line.no,
                                            f'§{endpoint} does not exist', match.group(0)))
            if end and start in known and end in known:
                left, right = tuple(map(int, start.split('.'))), tuple(map(int, end.split('.')))
                if left >= right:
                    findings.append(Finding('error', 'PROPOSAL-RANGE-ORDER', line.no,
                                            'range endpoints must be in document order', match.group(0)))
                elif left[:-1] == right[:-1]:
                    for ordinal in range(left[-1], right[-1] + 1):
                        key = '.'.join(map(str, (*left[:-1], ordinal)))
                        if key not in known:
                            findings.append(Finding('error', 'REF-DANGLING', line.no,
                                                    f'§{key} inside the range does not exist', match.group(0)))
        if KEY_REF.search(author_text(line.raw)):
            findings.append(Finding('error', 'KEY-UNRENDERED', line.no,
                                    'render keyed references before using the proposal', line.raw))


def _format_checks(lines, findings, profile):
    seen_urls = {}
    for line in lines:
        if line.kind in ('code', 'quote', 'comment'):
            continue
        raw = line.raw
        author = author_text(raw)
        if line.kind == 'heading':
            findings.append(Finding('error', 'PROPOSAL-HEADING', line.no,
                                    'use plain numbered points in the Upwork proposal', raw))
        elif line.kind == 'anchor':
            findings.append(Finding('error', 'PROPOSAL-ANCHOR', line.no,
                                    'HTML anchors belong to article format; use §N in the proposal', raw))
        if line.kind == 'fence' and raw[:1].isspace():
            findings.append(Finding('error', 'PROPOSAL-CODE-INDENT', line.no,
                                    'place the code fence at the left margin', raw))
        if line.kind != 'prose':
            continue
        if MARKDOWN_LINK.search(raw):
            findings.append(Finding('error', 'PROPOSAL-MARKDOWN-LINK', line.no,
                                    'use a plain URL in the Upwork field', raw))
        # The body of a technical proposal uses system subjects. A chosen offer
        # profile may use first-person commercial commitments; quotes are masked.
        if profile.get('voice', 'technical') == 'technical' and re.search(r'\bI\b', author):
            findings.append(Finding('error', 'PROPOSAL-FIRST-PERSON', line.no,
                                    'name the system action or the required step instead of I', raw))
        if re.search(r'(?i)\bjourneys?\b', author):
            findings.append(Finding('error', 'PROPOSAL-JOURNEY', line.no,
                                    'name the precise session/event history', raw))
        # An explicit internal compiler index is not a user-visible UI label.
        if re.search(r'(?i)\b(?:Tag|Rule)\s+\d+\b', author):
            findings.append(Finding('warning', 'PROPOSAL-INTERNAL-INDEX', line.no,
                                    'identify the object as the client sees it in the interface', raw))
        for match in URL.finditer(raw):
            url = match.group(0).rstrip('.,;!')
            if url in seen_urls:
                findings.append(Finding('error', 'PROPOSAL-DUP-URL', line.no,
                                        f'URL already used at line {seen_urls[url]}; cite its § point', url))
            else:
                seen_urls[url] = line.no


def lint_text(text: str, *, kind: str | None = None, lang: str | None = None,
              path: Path | None = None, lexicon=None, bans=None,
              profile: Mapping | None = None) -> list[Finding]:
    if kind not in (None, 'proposal'):
        raise ValueError('proposal.lint_text accepts only kind=proposal')
    profile = dict(profile or {})
    if profile.get('numbering', 'nested') not in ('flat', 'nested'):
        raise ValueError('proposal numbering must be flat or nested')
    if profile.get('voice', 'technical') not in ('technical', 'offer'):
        raise ValueError('proposal voice must be technical or offer')
    lines = scan(text)
    findings: list[Finding] = []
    blocks = parse_blocks(lines, findings)
    if not blocks:
        findings.append(Finding('error', 'PROPOSAL-EMPTY', 1,
                                'the proposal needs at least one plain numbered point'))
    _check_sequence(blocks, findings, profile)
    _check_references(lines, blocks, findings, profile)
    _format_checks(lines, findings, profile)
    check_prose(lines, 'proposal', lang or detect_language(text), findings,
                lexicon if lexicon is not None else load_lexicon(),
                bans if bans is not None else find_bans(Path(path) if path else None))
    check_code(lines, findings)
    return findings


def to_source(text: str) -> str:
    """Convert addressable point numbers and references, leaving literals intact."""
    lines = scan(text)
    by_line = {block.line: block for block in parse_blocks(lines)}
    out = []
    for line in lines:
        raw = line.raw
        if line.no in by_line:
            block = by_line[line.no]
            raw = f'{block.prefix}@{block.name}{block.gap}{block.body}'
        if line.kind == 'prose':
            def replace(segment):
                def ref(match):
                    if external_section_ref(segment, match):
                        return match.group()
                    start, end = match.group('start', 'end')
                    return f'§§@{start}-@{end}' if end else f'§@{start}'
                return REF.sub(ref, segment)
            raw = transform_prose(raw, replace)
        out.append(raw)
    return _reassemble(text, lines, out)


def render(source: str, previous: str | None = None):
    """Number a keyed proposal by block order; return (text, report, findings)."""
    lines = scan(source)
    findings: list[Finding] = []
    external_changes = []
    blocks = parse_blocks(lines, findings, keyed=True)
    if not blocks:
        findings.append(Finding('error', 'KEY-EMPTY', 1, 'the keyed proposal has no @points'))
    by_name, by_line, groups, mapping = {}, {}, {}, {}
    closed_paths, active_path = set(), []
    for block in blocks:
        parts = block.name.split('.')
        path = ['.'.join(parts[:index]) for index in range(1, len(parts) + 1)]
        shared = 0
        while shared < min(len(path), len(active_path)) and path[shared] == active_path[shared]:
            shared += 1
        closed_paths.update(active_path[shared:])
        if any(name in closed_paths for name in path):
            findings.append(Finding('error', 'KEY-NONCONTIGUOUS', block.line,
                                    'move a parent together with all its child points', block.name))
        active_path = path
        parent_name = _parent_name(block.name, by_name)
        parent_number = ()
        if parent_name:
            parent = by_name.get(parent_name)
            if parent is not None:
                parent_number = parent.number
                if parts[-2] == '0' and parent_name != '.'.join(parts[:-1]):
                    parent_number = (*parent_number, 0)
        siblings = groups.setdefault(parent_number, 0)
        ordinal = 0 if len(parts) > 1 and parts[-1] == '0' else siblings + 1
        if ordinal:
            groups[parent_number] = ordinal
        block.number = (*parent_number, ordinal)
        by_name[block.name] = block
        by_line[block.line] = block
        mapping[block.name] = block.key
    out = []
    for line in lines:
        raw = line.raw
        if line.kind == 'prose' and any(_number_refs(raw)):
            findings.append(Finding('error', 'KEY-NUMERIC-REF', line.no,
                                    'use §@key in the keyed view; a number may bind to a different point after reordering', raw))
        if line.no in by_line:
            block = by_line[line.no]
            raw = f'{block.prefix}{block.key}.{block.gap}{block.body}'
        if line.kind == 'prose':
            def replace(segment):
                def ref(match):
                    start, end = match.group('start', 'end')
                    for endpoint in (start, end):
                        if endpoint and endpoint not in mapping:
                            findings.append(Finding('error', 'KEY-DANGLING', line.no,
                                                    f'§@{endpoint} does not exist', line.raw))
                    if start not in mapping or (end and end not in mapping):
                        return match.group(0)
                    return f'§§{mapping[start]}-{mapping[end]}' if end else f'§{mapping[start]}'
                return normalize_external_refs(KEY_REF.sub(ref, segment), changes=external_changes, line=line.no)
            raw = transform_prose(raw, replace)
        out.append(raw)
    rendered = _reassemble(source, lines, out)
    old = [block.key for block in parse_blocks(previous)] if previous is not None else []
    numbered = re.compile(r'^\d+(?:\.\d+)*$')
    report = {'renumbered': [[key, value] for key, value in mapping.items() if numbered.fullmatch(key) and key != value],
              'added': [key for key in mapping if not numbered.fullmatch(key)],
              'removed': [key for key in old if key not in mapping]}
    if external_changes:
        report['external_references_normalized'] = external_changes
    final_lines = scan(rendered)
    _check_references(final_lines, parse_blocks(final_lines), findings, {})
    return rendered, report, findings


def lint_fields(fields: Mapping[str, str], limits: Mapping[str, int],
                *, count_mode: str = 'utf16') -> list[Finding]:
    """Validate each field using browser UTF-16 length (or confirmed Unicode mode)."""
    if count_mode not in ('utf16', 'unicode'):
        raise ValueError('character count mode must be utf16 or unicode')
    findings = []
    for name, limit in limits.items():
        if name not in fields:
            findings.append(Finding('error', 'PROPOSAL-FIELD-MISSING', 1,
                                    f'missing Upwork field {name}'))
            continue
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError(f'positive integer character limit required for {name}')
        count = (len(fields[name].encode('utf-16-le')) // 2
                 if count_mode == 'utf16' else len(fields[name]))
        if count > limit:
            findings.append(Finding('error', 'PROPOSAL-FIELD-LIMIT', 1,
                                    f'{name}: {count} characters exceeds its {limit} character limit'))
    for name in fields.keys() - limits.keys():
        findings.append(Finding('error', 'PROPOSAL-FIELD-LIMIT-MISSING', 1,
                                f'no confirmed character limit for Upwork field {name}'))
    return findings
