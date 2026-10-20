"""df.tips article and proposal tooling (skill /df-article).

lint      — deterministic checks for the 2725 format and for LLM slop (data: skills/df-article/references/lexicon.json);
source    — numbered Markdown → keyed editing view (`## @I.12.1`, `§@I.4.1`), lossless for the format;
render    — keyed view → numbered Markdown with anchors and recomputed § references, plus a factual change report;
replay    — reruns fenced bash commands and compares their output with the quoted output;
response  — checks a chat/journal answer: duplicate of an earlier answer, procedural filler, removal claims
            contradicted by the target file.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, asdict
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .runtime import PRIMARY

LEXICON = PRIMARY / 'skills/df-article/references/lexicon.json'
BANS = Path('ꘖ/data/article-bans.json')

FENCE = re.compile(r'^\s*(```|~~~)')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
ANCHOR = re.compile(r"""^\s*<a\s+name=['"]([^'"]+)['"]\s*>\s*</a>\s*$""")
PART = re.compile(r'^([IVXLC]+)\.\s+\S')
NUMBERED = re.compile(r'^(\d+(?:\.\d+)*)\.?(?:\s+(.*))?$')
KEYED = re.compile(r'^@([\w.\-]+)(?:\s+(.*))?$')
LIST_MARK = re.compile(r'^\s*(?:[-*+]|\d+(?:\.\d+)*[.)])\s+')
ANCHOR_LINK = re.compile(r'\[([^\]\n]*)\]\(#([^)\s]+)\)')
SECTION_LABEL = re.compile(r'^§{1,2}\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*)(?:\s*[-–]\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*))?$')
SOURCE_REF = re.compile(r'(§§?)@([\w.\-]+?)(?:-@([\w.\-]+))?(?=[^\w.\-]|\.(?:\s|$)|$)')
ARROW_CONNECTIVE = re.compile(
    r'^\s*(?:because|since|as|although|though|while|so|thus|therefore|hence|which|this means|consequently|'
    r'as a result|потому что|так как|поскольку|хотя|следовательно|поэтому|что означает)\b', re.I)
BOLD_LEADIN = re.compile(r'^\*\*(?!\{?\[§)(?!§)([^*\n]{2,90})\*\*\s*[:—–]')
REMOVAL = re.compile(r'(?i)\b(?:удал[её]н\w*|удалил\w*|убран\w*|убрал\w*|устран[её]н\w*|устранил\w*|вычищен\w*|вычистил\w*|'
                     r'вырезан\w*|исключ[её]н\w*|исключил\w*|removed|deleted|eliminated|stripped|dropped)\b')
REPLACED = re.compile(r'(?i)\b(?:заменен\w*|заменён\w*|заменил\w*|replaced)\b')
KEPT = re.compile(r'(?i)\b(?:оставлен\w*|оставил\w*|кроме|за исключением|except|kept|retained)\b')
ABBREVIATIONS = {'e.g', 'i.e', 'vs', 'etc', 'inc', 'ltd', 'co', 'no', 'mr', 'mrs', 'dr', 'st', 'fig', 'approx', 'т.е', 'т.д', 'т.п', 'др', 'см', 'г', 'гг'}
THRESHOLDS = {'sentence_words': 60, 'code_spans': 8, 'parentheses': 3, 'bold_spans': 3, 'heading_words': 8, 'grep_literal': 100}


@dataclass
class Finding:
    severity: str
    rule: str
    line: int
    message: str
    excerpt: str = ''

    def format(self, path='') -> str:
        where = f'{path}:{self.line}' if path else f'{self.line}'
        tail = f' | {self.excerpt}' if self.excerpt else ''
        return f'{where}: [{self.severity}] {self.rule}: {self.message}{tail}'


@dataclass
class Line:
    no: int
    raw: str
    kind: str  # blank, fence, code, heading, anchor, quote, hr, prose


@dataclass
class Section:
    part: str
    number: tuple
    title: str | None
    line: int
    level: int
    parent: 'Section | None' = None
    children: list = field(default_factory=list)
    end: int = 0
    anchor: str | None = None
    name: str = ''  # key in the keyed view

    @property
    def dotted(self) -> str:
        return '.'.join(map(str, self.number))

    @property
    def key(self) -> str:
        return f'{self.part}.{self.dotted}' if self.part else self.dotted

    def lineage(self):
        node = self
        while node:
            yield node
            node = node.parent

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


# ---------------------------------------------------------------- scanning

def scan(text: str) -> list[Line]:
    lines, fenced = [], False
    for no, raw in enumerate(text.splitlines(), 1):
        if FENCE.match(raw):
            lines.append(Line(no, raw, 'fence'))
            fenced = not fenced
        elif fenced:
            lines.append(Line(no, raw, 'code'))
        elif not raw.strip():
            lines.append(Line(no, raw, 'blank'))
        elif ANCHOR.match(raw):
            lines.append(Line(no, raw, 'anchor'))
        elif HEADING.match(raw):
            lines.append(Line(no, raw, 'heading'))
        elif raw.lstrip().startswith('>'):
            lines.append(Line(no, raw, 'quote'))
        elif re.match(r'^\s*(?:-{3,}|\*{3,}|_{3,})\s*$', raw):
            lines.append(Line(no, raw, 'hr'))
        else:
            lines.append(Line(no, raw, 'prose'))
    return lines


def clean(raw: str) -> str:
    """Prose without code, URLs, verbatim quotes and markup: what the lexicon must judge."""
    s = LIST_MARK.sub('', raw)
    s = re.sub(r'`[^`]*`', ' CODE ', s)
    s = re.sub(r'\[§[^\]]*\]\([^)]*\)', ' REF ', s)
    s = re.sub(r'§§?@[\w.\-]+(?:-@[\w.\-]+)?', ' REF ', s)
    s = re.sub(r'!?\[([^\]]*)\]\((?:<[^>]*>|[^)\s]*)\)',
               lambda m: ' URL ' if not re.search(r'\s', m.group(1).replace('**', '')) else m.group(1), s)
    s = re.sub(r'<https?://[^>]+>|https?://\S+', ' URL ', s)
    s = re.sub(r'«[^»]*»|“[^”]*”', ' QUOTE ', s)
    s = s.replace('**', '').replace('__', '')
    s = re.sub(r'(?<![\w*])\*(?!\s)([^*\n]+?)\*(?!\w)', r'\1', s)
    s = re.sub(r'<[^>\n]+>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def sentences(cleaned: str) -> list[str]:
    parts, start = [], 0
    for match in re.finditer(r'[.!?](?=\s+[A-ZА-ЯЁ«"(\[])', cleaned):
        word = re.findall(r'[\w.]+$', cleaned[start:match.start()])
        token = (word[-1] if word else '').lower().rstrip('.')
        if token in ABBREVIATIONS or (len(token) == 1 and token.isalpha()):
            continue
        parts.append(cleaned[start:match.end()].strip())
        start = match.end()
    tail = cleaned[start:].strip()
    return parts + ([tail] if tail else [])


def detect_language(text: str) -> str:
    letters = re.findall(r'[A-Za-zА-Яа-яЁё]', clean(text))
    cyrillic = sum(1 for ch in letters if re.match(r'[А-Яа-яЁё]', ch))
    return 'ru' if letters and cyrillic / len(letters) > 0.3 else 'en'


def detect_kind(path: Path | None, text: str) -> str:
    if path is not None and path.parent.name == 'res':
        return 'response'
    if ANCHOR.search(text) or re.search(r'(?m)^#\s+[IVXLC]+\.\s', text) or re.search(r'(?m)^#{2,6}\s+(?:\d|@)', text):
        return 'article'
    return 'proposal'


# ---------------------------------------------------------------- structure

def parse_sections(lines: list[Line], findings: list[Finding] | None = None):
    """Numbered headings (`## 12`, `### 12.1. Title`) grouped by parts (`# I. Analysis`)."""
    findings = findings if findings is not None else []
    part, sections, by_key, roots = '', [], {}, {}
    for index, line in enumerate(lines):
        if line.kind != 'heading':
            continue
        hashes, text = HEADING.match(line.raw).groups()
        if len(hashes) == 1:
            match = PART.match(text)
            part = match.group(1) if match else part
            continue
        match = NUMBERED.match(text)
        if not match:
            continue
        number = tuple(int(x) for x in match.group(1).split('.'))
        section = Section(part, number, match.group(2), line.no, len(hashes))
        if len(hashes) != len(number) + 1:
            findings.append(Finding('warning', 'STRUCT-LEVEL', line.no,
                                    f'heading level {len(hashes)} does not match number depth {len(number)} (expected {"#" * (len(number) + 1)})', line.raw))
        section.parent = by_key.get((part, number[:-1])) if len(number) > 1 else None
        if len(number) > 1 and section.parent is None:
            findings.append(Finding('error', 'STRUCT-PARENT', line.no, f'no parent section {".".join(map(str, number[:-1]))}', line.raw))
        siblings = section.parent.children if section.parent else roots.setdefault(part, [])
        if number[-1] != len(siblings) + 1:
            findings.append(Finding('error', 'STRUCT-SEQ', line.no, f'number {section.dotted} breaks the sequence (expected …{len(siblings) + 1})', line.raw))
        if (part, number) in by_key:
            findings.append(Finding('error', 'STRUCT-DUP', line.no, f'duplicate section {section.key}', line.raw))
        by_key[(part, number)] = section
        siblings.append(section)
        following = next((x for x in lines[index + 1:] if x.kind != 'blank'), None)
        if following is not None and following.kind == 'anchor':
            section.anchor = ANCHOR.match(following.raw).group(1)
        sections.append(section)
    _close(sections, lines)
    return sections


def parse_keyed(lines: list[Line], findings: list[Finding]):
    """Keyed headings (`## @key Title`): the tree comes from heading levels, numbers are assigned on render."""
    part, sections, roots = '', [], {}
    for line in lines:
        if line.kind != 'heading':
            continue
        hashes, text = HEADING.match(line.raw).groups()
        if len(hashes) == 1:
            match = PART.match(text)
            part = match.group(1) if match else part
            continue
        match = KEYED.match(text)
        if not match:
            if NUMBERED.match(text):
                findings.append(Finding('error', 'KEY-NUMBERED', line.no, 'numbered heading inside a keyed view: use `@key`', line.raw))
            continue
        section = Section(part, (), match.group(2), line.no, len(hashes))
        section.name = match.group(1)
        for previous in reversed(sections):
            if previous.part != part:
                break
            if previous.level < section.level:
                section.parent = previous
                break
        expected = section.parent.level + 1 if section.parent else 2
        if section.level != expected:
            findings.append(Finding('error', 'STRUCT-LEVEL', line.no, f'heading level {section.level}, expected {expected}', line.raw))
        (section.parent.children if section.parent else roots.setdefault(part, [])).append(section)
        sections.append(section)
    _close(sections, lines)
    return sections, roots


def _close(sections, lines):
    last = lines[-1].no if lines else 0
    for current, nxt in zip(sections, sections[1:] + [None]):
        current.end = (nxt.line - 1) if nxt else last


def section_at(sections, line_no):
    found = None
    for section in sections:
        if section.line <= line_no:
            found = section
        else:
            break
    return found


def part_at(lines, line_no):
    part = ''
    for line in lines:
        if line.no > line_no:
            break
        if line.kind == 'heading':
            hashes, text = HEADING.match(line.raw).groups()
            match = PART.match(text) if len(hashes) == 1 else None
            part = match.group(1) if match else part
    return part


def bold_spans(raw: str):
    marks = [m.start() for m in re.finditer(r'\*\*', raw)]
    return [(marks[i], marks[i + 1]) for i in range(0, len(marks) - 1, 2)]


def check_structure(lines, sections, findings):
    anchors = {}
    for line in lines:
        if line.kind == 'anchor':
            name = ANCHOR.match(line.raw).group(1)
            if name in anchors:
                findings.append(Finding('error', 'ANCHOR-DUP', line.no, f'duplicate anchor {name}', line.raw))
            anchors[name] = line.no
    for section in sections:
        if section.anchor is None:
            findings.append(Finding('error', 'ANCHOR-MISSING', section.line, f"expected <a name='{section.key}'></a> right after the heading"))
        elif section.anchor != section.key:
            findings.append(Finding('error', 'ANCHOR-MISMATCH', section.line, f'anchor {section.anchor} does not match section {section.key}'))
        title = section.title
        if title:
            plain = clean(title)
            plain = re.sub(r'\(\s*\d+[^)]*\)', '', plain).strip()
            words = re.findall(r"[A-Za-zА-Яа-яЁё][\w'’-]*", plain)
            if ',' in plain and re.search(r'\band\b|&|\bи\b', plain):
                findings.append(Finding('error', 'HEADING-ENUM', section.line, 'heading enumerates several topics: one section — one claim; split it', title))
            if len(words) > THRESHOLDS['heading_words']:
                findings.append(Finding('warning', 'HEADING-LONG', section.line, f'{len(words)} words in a heading; 2725 uses a bare number or a short group label', title))
            capital = [w for w in words[1:] if len(w) > 3 and w[0].isupper() and not w.isupper()]
            long_words = [w for w in words[1:] if len(w) > 3]
            if len(capital) >= 2 and len(capital) * 2 > len(long_words):
                findings.append(Finding('warning', 'HEADING-TITLECASE', section.line, 'Title Case heading (WP:AITITLECASE)', title))
    for line in lines:
        if line.kind not in ('prose', 'quote', 'heading'):
            continue
        spans = bold_spans(line.raw)
        for match in ANCHOR_LINK.finditer(line.raw):
            label, target = match.groups()
            if target not in anchors:
                findings.append(Finding('error', 'REF-DANGLING', line.no, f'#{target} does not exist', match.group(0)))
                continue
            parsed = SECTION_LABEL.match(label.replace('**', '').strip())
            if label.strip().startswith('§'):
                if not parsed:
                    findings.append(Finding('error', 'REF-LABEL', line.no, 'unparseable § label', match.group(0)))
                    continue
                current = part_at(lines, line.no)
                label_part = parsed.group(1) or current
                expected = f'{label_part}.{parsed.group(2)}' if label_part else parsed.group(2)
                if expected != target:
                    findings.append(Finding('error', 'REF-LABEL', line.no, f'label points to {expected}, link goes to #{target}', match.group(0)))
                if line.kind != 'heading' and not any(a < match.start() < b for a, b in spans):
                    findings.append(Finding('warning', 'REF-BOLD', line.no, 'section reference is not bold: **[§N](#P.N)**', match.group(0)))


def check_graph(lines, sections, findings):
    parts = {s.part for s in sections}
    if not {'I', 'II'} <= parts:
        return
    by_key = {s.key: s for s in sections}
    refs = {s.key: set() for s in sections}
    external = {s.key: False for s in sections}
    for line in lines:
        section = section_at(sections, line.no)
        if section is None or line.kind in ('heading', 'anchor'):
            continue
        if line.kind in ('prose', 'quote'):
            for match in ANCHOR_LINK.finditer(line.raw):
                if match.group(2) in by_key:
                    refs[section.key].add(match.group(2))
            if re.search(r'\]\(<?https?://|https?://', line.raw):
                external[section.key] = True
    # GRAPH-ORPHAN: analysis paragraphs that no recommendation needs, directly or through premises.
    used, queue = set(), [s.key for s in sections if s.part == 'II']
    while queue:
        key = queue.pop()
        if key in used:
            continue
        node = by_key[key]
        family = list(node.lineage()) + list(node.descendants())
        for member in family:
            if member.key not in used:
                used.add(member.key)
                queue.extend(refs[member.key])
    for section in sections:
        if section.part == 'I' and section.parent is None and section.key not in used:
            findings.append(Finding('note', 'GRAPH-ORPHAN', section.line,
                                    f'§{section.key} is not a premise of any recommendation (directly or transitively): keep it only if it serves the goal of the text'))
    # GRAPH-BASELESS: recommendations without an analysis premise or a documentation link.
    grounded = {}
    changed = True
    while changed:
        changed = False
        for section in sections:
            if section.part != 'II' or grounded.get(section.key):
                continue
            chain = list(section.lineage())
            ok = any(external[s.key] or any(t.startswith('I.') or grounded.get(t) for t in refs[s.key]) for s in chain)
            if ok:
                grounded[section.key] = changed = True
    for section in sections:
        if section.part == 'II' and not section.children and not grounded.get(section.key):
            findings.append(Finding('warning', 'GRAPH-BASELESS', section.line, f'recommendation §{section.key} has no premise in part I and no documentation link'))
    # PROOF-MISSING: analysis leaves with neither proof nor premise.
    for section in sections:
        if section.part != 'I' or section.children:
            continue
        body = [l for l in lines if section.line < l.no <= section.end and l.kind not in ('blank', 'anchor')]
        has_proof = any(l.kind in ('code', 'fence', 'quote') for l in body) or external[section.key] or refs[section.key] \
            or (section.parent and any(l.kind in ('code', 'fence') for l in lines if section.parent.line < l.no < section.line))
        if not has_proof:
            findings.append(Finding('note', 'PROOF-MISSING', section.line, f'§{section.key} states a fact without a command, quote, link or premise'))


def check_code(lines, findings):
    index = 0
    while index < len(lines):
        if lines[index].kind != 'fence':
            index += 1
            continue
        start = index
        index += 1
        body = []
        while index < len(lines) and lines[index].kind == 'code':
            body.append(lines[index])
            index += 1
        index += 1
        commands = sum(1 for l in body if l.raw.strip() and not l.raw.rstrip().endswith('\\') and not l.raw.strip().startswith('#'))
        for line in body:
            for literal in re.findall(r"'([^']*)'|\"([^\"]*)\"", line.raw):
                literal = literal[0] or literal[1]
                if len(literal) > THRESHOLDS['grep_literal']:
                    findings.append(Finding('warning', 'CODE-UNREADABLE', line.no,
                                            f'{len(literal)}-character literal: a reader cannot check it; publish a small script and run it as 2725 §11–§12 do', literal[:60] + '…'))
        cursor = index
        while cursor < len(lines) and lines[cursor].kind == 'blank':
            cursor += 1
        output = []
        while cursor < len(lines) and lines[cursor].kind == 'quote':
            output.append(lines[cursor])
            cursor += 1
        values = [re.sub(r'^\s*>\s?', '', l.raw).rstrip() for l in output]
        for value in set(values):
            if value and values.count(value) > max(commands, 1):
                first = output[values.index(value)]
                findings.append(Finding('warning', 'CODE-DUP-OUTPUT', first.no,
                                        f'line repeated {values.count(value)}× for {commands} command(s): add sort -u / -m1 or show why the repetition matters', value[:80]))
        _ = start


def check_prose(lines, kind, lang, findings, lexicon, bans):
    entries = [e for e in lexicon if kind in e['kinds'] and e['lang'] in ('*', lang)]
    compiled = [(e, [re.compile(p, 0 if e.get('case') else re.I) for p in e['patterns']]) for e in entries]
    ban_patterns = [(b, re.compile(b['pattern'], 0 if b.get('case') else re.I)) for b in bans]
    for line in lines:
        if line.kind not in ('prose', 'heading'):
            continue
        raw = line.raw
        text = clean(HEADING.match(raw).group(2) if line.kind == 'heading' else raw)
        if not text:
            continue
        stripped = LIST_MARK.sub('', raw).strip()
        if line.kind == 'prose' and BOLD_LEADIN.match(stripped):
            findings.append(Finding('error' if kind != 'response' else 'warning', 'BOLD-LEADIN', line.no,
                                    'inline bold label before a colon (WP:AILIST); state the claim itself', stripped[:80]))
        for entry, patterns in compiled:
            targets = sentences(text) if entry['where'] == 'start' else [text]
            for target in targets:
                for pattern in patterns:
                    match = pattern.match(target) if entry['where'] == 'start' else pattern.search(target)
                    if match:
                        findings.append(Finding(entry['severity'], entry['id'], line.no, entry['fix'], _excerpt(target, match)))
                        break
                else:
                    continue
                break
        for ban, pattern in ban_patterns:
            match = pattern.search(raw)
            if match:
                findings.append(Finding(ban.get('severity', 'error'), 'BAN', line.no, ban.get('why', 'project ban'), _excerpt(raw, match)))
        if line.kind != 'prose':
            continue
        for arrow in re.finditer(r'→', text):
            if ARROW_CONNECTIVE.match(text[arrow.end():]):
                findings.append(Finding('error', 'ARROW-CONNECTIVE', line.no,
                                        '`→` already means «follows from the premises»; a connective after it restates or re-argues the premise', _excerpt(text, arrow)))
        if kind == 'response':
            continue
        found = sentences(text)
        lead = kind == 'proposal' and line.no == next((l.no for l in lines if l.kind == 'prose'), 0)
        if len(found) > 1 and not lead:
            findings.append(Finding('error', 'SENT-SPLIT', line.no, f'{len(found)} sentences on one line (DOC-4): one sentence — one line', found[1][:60]))
        for sentence in found:
            words = re.findall(r"[A-Za-zА-Яа-яЁё0-9][\w'’-]*", sentence)
            if len(words) > THRESHOLDS['sentence_words']:
                findings.append(Finding('warning', 'SENT-LONG', line.no, f'{len(words)} words in one sentence', sentence[:60] + '…'))
            if sentence.count('(') > THRESHOLDS['parentheses']:
                findings.append(Finding('warning', 'SENT-PARENS', line.no, f'{sentence.count("(")} parenthetical groups: move details into their own paragraphs or drop them', sentence[:60] + '…'))
        spans = len(re.findall(r'`[^`]+`', raw))
        if spans > THRESHOLDS['code_spans']:
            findings.append(Finding('warning', 'SENT-IDENTIFIERS', line.no, f'{spans} code identifiers on one line: keep only those the claim needs', raw[:60] + '…'))
        bold = [s for s in re.findall(r'\*\*(.+?)\*\*', raw) if '§' not in s]
        if len(bold) > THRESHOLDS['bold_spans']:
            findings.append(Finding('warning', 'BOLD-DENSITY', line.no, f'{len(bold)} bold fragments on one line (WP:AIBOLD)', raw[:60] + '…'))
        if kind in ('article', 'proposal') and re.search(r'\]\((?!<?https?://|#|mailto:)', raw):
            findings.append(Finding('error', 'LINK-LOCAL', line.no, 'link to a local file: the client cannot open it', raw[:80]))


def _excerpt(text, match, width=40):
    start, end = max(match.start() - width, 0), min(match.end() + width, len(text))
    return ('…' if start else '') + text[start:end] + ('…' if end < len(text) else '')


def check_proposal(lines, findings):
    """Upwork plain text: the lead paragraph is §1, then `2.`, `2.1.` …; references are bare `§N`."""
    numbers = {'1'}
    for line in lines:
        if line.kind == 'prose':
            match = re.match(r'^\s*(\d+(?:\.\d+)*)\.?\s', line.raw)
            if match:
                numbers.add(match.group(1))
    top = max(int(n.split('.')[0]) for n in numbers)
    for line in lines:
        if line.kind in ('prose', 'quote'):
            for ref in re.findall(r'§§?\s*(\d+(?:\.\d+)*)', line.raw):
                if ref not in numbers and int(ref.split('.')[0]) <= top + 3:
                    findings.append(Finding('error', 'REF-DANGLING', line.no, f'§{ref} does not exist in this text', line.raw[:80]))
            if re.search(r'\[[^\]]+\]\(https?://', line.raw):
                findings.append(Finding('warning', 'PROPOSAL-MARKDOWN-LINK', line.no, 'Upwork shows proposal text as plain text: put the bare URL', line.raw[:80]))


def load_lexicon(path=None):
    return json.loads(Path(path or LEXICON).read_text(encoding='utf-8'))['entries']


def find_bans(path: Path | None):
    if path is None:
        return []
    for folder in [path.resolve().parent, *path.resolve().parents]:
        candidate = folder / BANS
        if candidate.is_file():
            data = json.loads(candidate.read_text(encoding='utf-8'))
            return data.get('bans', data) if isinstance(data, dict) else data
    return []


def lint_text(text: str, *, kind: str | None = None, lang: str | None = None, path: Path | None = None,
              lexicon=None, bans=None) -> list[Finding]:
    kind = kind or detect_kind(path, text)
    lang = lang or detect_language(text)
    lexicon = load_lexicon() if lexicon is None else lexicon
    bans = find_bans(path) if bans is None else bans
    lines = scan(text)
    findings: list[Finding] = []
    if kind == 'article':
        sections = parse_sections(lines, findings)
        check_structure(lines, sections, findings)
        check_graph(lines, sections, findings)
        check_code(lines, findings)
    elif kind == 'proposal':
        check_proposal(lines, findings)
        check_code(lines, findings)
    check_prose(lines, kind, lang, findings, lexicon, bans)
    return sorted(findings, key=lambda f: (f.line, f.severity != 'error', f.rule))


# ---------------------------------------------------------------- responses

def normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def check_response(path: Path, text: str | None = None, against=(), lexicon=None, journal: Path | None = None) -> list[Finding]:
    """`journal` is the journal folder (with `res/`); without it a file inside `res/` is compared with its siblings."""
    text = path.read_bytes().decode('utf-8') if text is None else text
    findings = lint_text(text, kind='response', path=path, lexicon=lexicon, bans=[])
    folder = Path(journal) / 'res' if journal else (path.parent if path.parent.name == 'res' else None)
    if folder is not None and folder.is_dir():
        mine = normalized(text)
        for other in sorted(folder.glob('*.md')):
            if other.resolve() == path.resolve():
                continue
            if path.stem.isdigit() and other.stem.isdigit() and int(other.stem) > int(path.stem):
                continue  # only earlier answers can be repeated
            theirs = normalized(other.read_bytes().decode('utf-8', errors='replace'))
            if not theirs or not mine or min(len(mine), len(theirs)) < 0.8 * max(len(mine), len(theirs)):
                continue
            if theirs == mine:
                ratio = 1.0
            else:
                matcher = difflib.SequenceMatcher(None, mine.split(' '), theirs.split(' '))
                ratio = matcher.ratio() if matcher.quick_ratio() >= 0.9 else 0.0
            if ratio >= 0.9:
                findings.append(Finding('error', 'RESP-DUP', 1, f'{ratio:.0%} identical to {other.name}: a repeated answer means the new request was not executed'))
    for target in against:
        target = Path(target)
        body = target.read_bytes().decode('utf-8')
        target_lines = body.splitlines()
        for no, raw in enumerate(text.splitlines(), 1):
            for sentence in re.split(r'(?<=[.!?])\s+', raw):
                removal, replaced = REMOVAL.search(sentence), REPLACED.search(sentence)
                if not removal and not replaced:
                    continue
                stop = len(sentence)
                if replaced and not removal:
                    stop = replaced.start()
                kept = KEPT.search(sentence)
                if kept:
                    stop = min(stop, kept.start())
                for token in re.findall(r'`([^`]+)`', sentence[:stop]):
                    token = token.replace('...', '').replace('…', '').strip()
                    if len(token) < 3 or token.startswith('§'):
                        continue
                    needle = re.compile(r'(?<![\w-])' + re.escape(token) + r'(?!\w)', re.I)
                    hits = [i for i, l in enumerate(target_lines, 1) if needle.search(l)]
                    if hits:
                        findings.append(Finding('warning', 'RESP-CLAIM', no,
                                                f'claimed removed/replaced, but `{token}` remains in {target.name} at lines {", ".join(map(str, hits[:8]))}{" …" if len(hits) > 8 else ""}',
                                                sentence[:100]))
    return sorted(findings, key=lambda f: (f.line, f.rule))


# ---------------------------------------------------------------- source ⇄ render

def to_source(text: str) -> str:
    """Numbered Markdown → keyed view; keys are the current anchors, so the conversion is lossless."""
    lines = scan(text)
    findings = []
    sections = parse_sections(lines, findings)
    by_line = {s.line: s for s in sections}
    anchor_lines = {next((x.no for x in lines if x.no > s.line and x.kind != 'blank'), None) for s in sections if s.anchor}
    out = []
    for line in lines:
        if line.no in by_line:
            section = by_line[line.no]
            title = f' {section.title}' if section.title else ''
            out.append('#' * (len(section.number) + 1) + f' @{section.key}{title}')
        elif line.no in anchor_lines and line.kind == 'anchor':
            continue
        elif line.kind in ('prose', 'quote', 'heading'):
            current = part_at(lines, line.no)

            def replace(match):
                label, target = match.groups()
                parsed = SECTION_LABEL.match(label.replace('**', '').strip())
                if not parsed or not label.strip().startswith('§'):
                    return f'[{label}](#@{target})'
                marks = '§§' if label.strip().startswith('§§') else '§'
                if parsed.group(4):
                    end_part = parsed.group(3) or parsed.group(1) or current
                    return f'{marks}@{target}-@{end_part}.{parsed.group(4)}' if end_part else f'{marks}@{target}-@{parsed.group(4)}'
                return f'{marks}@{target}'
            out.append(ANCHOR_LINK.sub(replace, line.raw))
        else:
            out.append(line.raw)
    return '\n'.join(out) + ('\n' if text.endswith('\n') else '')


def render(source: str, previous: str | None = None):
    """Keyed view → numbered Markdown. Returns (markdown, report, findings)."""
    lines = scan(source)
    findings: list[Finding] = []
    sections, roots = parse_keyed(lines, findings)
    numbers, mapping = {}, {}

    def assign(nodes, prefix):
        for index, node in enumerate(nodes, 1):
            node.number = (*prefix, index)
            if node.name in mapping:
                findings.append(Finding('error', 'KEY-DUP', node.line, f'duplicate key @{node.name}'))
            mapping[node.name] = node.key
            numbers[node.line] = node
            assign(node.children, node.number)

    for nodes in roots.values():
        assign(nodes, ())
    out = []
    for line in lines:
        if line.no in numbers:
            node = numbers[line.no]
            title = (' ' if node.title.startswith('(') else '. ') + node.title if node.title else ''
            out.append('#' * (len(node.number) + 1) + f' {node.dotted}{title}')
            out.append(f"<a name='{node.key}'></a>")
            continue
        if line.kind == 'anchor':
            continue  # anchors are regenerated from the keys
        if line.kind not in ('prose', 'quote', 'heading'):
            out.append(line.raw)
            continue
        current = part_at(lines, line.no)

        def label(anchor):
            part, _, number = anchor.partition('.') if re.match(r'^[IVXLC]+\.', anchor) else ('', '', anchor)
            return number if part == current else anchor

        def replace(match):
            marks, start, end = match.groups()
            if start not in mapping:
                findings.append(Finding('error', 'KEY-DANGLING', line.no, f'§@{start} does not exist (deleted premise: delete or re-ground the dependent claim)', line.raw[:80]))
                return match.group(0)
            if end:
                if end not in mapping:
                    findings.append(Finding('error', 'KEY-DANGLING', line.no, f'§@{end} does not exist', line.raw[:80]))
                    return match.group(0)
                return f'[{marks}{label(mapping[start])}-{label(mapping[end])}](#{mapping[start]})'
            return f'[{marks}{label(mapping[start])}](#{mapping[start]})'

        value = SOURCE_REF.sub(replace, line.raw)

        def anchor_ref(match):
            key = match.group(1)
            if key not in mapping:
                findings.append(Finding('error', 'KEY-DANGLING', line.no, f'#@{key} does not exist', line.raw[:80]))
                return match.group(0)
            return f'(#{mapping[key]})'
        out.append(re.sub(r'\(#@([\w.\-]+)\)', anchor_ref, value))
    markdown = '\n'.join(out) + ('\n' if source.endswith('\n') else '')
    report = {'renumbered': [[k, v] for k, v in mapping.items() if k != v and re.match(r'^(?:[IVXLC]+\.)?\d', k)],
              'added': [k for k in mapping if not re.match(r'^(?:[IVXLC]+\.)?\d+(?:\.\d+)*$', k)]}
    if previous is not None:
        old = [s.key for s in parse_sections(scan(previous))]
        report['removed'] = [key for key in old if key not in mapping]
    return markdown, report, findings


# ---------------------------------------------------------------- replay

def default_shell():
    git = shutil.which('git')
    if git:
        for candidate in (Path(git).resolve().parents[1] / 'bin/bash.exe', Path(git).resolve().parents[1] / 'usr/bin/bash.exe'):
            if candidate.is_file():
                return str(candidate)
    return shutil.which('bash') or 'bash'


def _plain(value: str) -> str:
    value = re.sub(r'^\s*>\s?', '', value).rstrip()
    value = value.strip('`')
    return '' if value == '<empty response>' else value


def replay(text: str, *, shell=None, timeout=60, only=None):
    lines = scan(text)
    results, index = [], 0
    shell = shell or default_shell()
    while index < len(lines):
        if lines[index].kind != 'fence' or not re.match(r'^\s*```\s*(bash|sh|shell)\s*$', lines[index].raw):
            index += 1
            continue
        first = lines[index].no
        index += 1
        body = []
        while index < len(lines) and lines[index].kind == 'code':
            body.append(lines[index].raw)
            index += 1
        index += 1
        cursor = index
        while cursor < len(lines) and lines[cursor].kind == 'blank':
            cursor += 1
        expected = []
        while cursor < len(lines) and lines[cursor].kind == 'quote':
            expected.append(_plain(lines[cursor].raw))
            cursor += 1
        if only and not any(first <= wanted <= cursor for wanted in only):
            continue
        if not expected:
            results.append({'line': first, 'status': 'no-quoted-output'})
            continue
        try:
            done = subprocess.run([shell, '-c', '\n'.join(body)], capture_output=True, timeout=timeout,
                                  encoding='utf-8', errors='replace')
            actual = [x.rstrip() for x in done.stdout.splitlines()]
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append({'line': first, 'status': 'error', 'error': str(exc)})
            continue
        want = [x for x in expected if x]
        status = 'match' if want == [x for x in actual if x] else 'mismatch'
        results.append({'line': first, 'status': status, 'expected': want, 'actual': actual[:50], 'stderr': done.stderr[-500:]})
    return results


# ---------------------------------------------------------------- CLI

def _print_findings(findings, path, as_json):
    if as_json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=1))
    else:
        for finding in findings:
            print(finding.format(str(path)))
        count = {level: sum(f.severity == level for f in findings) for level in ('error', 'warning', 'note')}
        print(f"{path}: {count['error']} error(s), {count['warning']} warning(s), {count['note']} note(s)")
    return 1 if any(f.severity == 'error' for f in findings) else 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(prog='df_article.py', description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    lint = sub.add_parser('lint', help='format and slop checks; exit 1 on errors')
    lint.add_argument('targets', nargs='+', type=Path)
    lint.add_argument('--kind', choices=['article', 'proposal', 'response'])
    lint.add_argument('--lang', choices=['en', 'ru'])
    lint.add_argument('--bans', type=Path, help='explicit project bans JSON (default: nearest ꘖ/data/article-bans.json)')
    lint.add_argument('--errors-only', action='store_true')
    lint.add_argument('--json', action='store_true')
    source = sub.add_parser('source', help='numbered Markdown → keyed editing view')
    source.add_argument('target', type=Path)
    source.add_argument('-o', '--output', type=Path)
    rend = sub.add_parser('render', help='keyed view → numbered Markdown')
    rend.add_argument('source', type=Path)
    rend.add_argument('-o', '--output', type=Path, required=True)
    rend.add_argument('--previous', type=Path, help='previous numbered version, for the removed-sections report')
    rend.add_argument('--force', action='store_true', help='write even with dangling keys')
    rep = sub.add_parser('replay', help='rerun ```bash blocks and compare with quoted output')
    rep.add_argument('target', type=Path)
    rep.add_argument('--shell')
    rep.add_argument('--timeout', type=float, default=60)
    rep.add_argument('--line', type=int, action='append', help='only the block that starts at this line')
    resp = sub.add_parser('response', help='check a journal/chat answer')
    resp.add_argument('target', type=Path)
    resp.add_argument('--against', type=Path, action='append', default=[], help='file whose edits the answer reports')
    resp.add_argument('--journal', type=Path, help='journal folder with res/ (when the answer is still a candidate outside it)')
    resp.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'lint':
            status = 0
            for target in args.targets:
                text = target.read_bytes().decode('utf-8')
                bans = json.loads(args.bans.read_text(encoding='utf-8')) if args.bans else None
                if isinstance(bans, dict):
                    bans = bans.get('bans', [])
                findings = lint_text(text, kind=args.kind, lang=args.lang, path=target, bans=bans)
                if args.errors_only:
                    findings = [f for f in findings if f.severity == 'error']
                status |= _print_findings(findings, target, args.json)
            return status
        if args.command == 'source':
            value = to_source(args.target.read_bytes().decode('utf-8'))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(value.encode('utf-8'))
                print(f'{args.output}: keyed view written')
            else:
                sys.stdout.write(value)
            return 0
        if args.command == 'render':
            previous = args.previous.read_bytes().decode('utf-8') if args.previous else None
            markdown, report, findings = render(args.source.read_bytes().decode('utf-8'), previous)
            for finding in findings:
                print(finding.format(str(args.source)))
            if any(f.severity == 'error' for f in findings) and not args.force:
                print('not written: fix the errors above')
                return 1
            args.output.write_bytes(markdown.encode('utf-8'))
            print(json.dumps(report, ensure_ascii=False, indent=1))
            return 0
        if args.command == 'replay':
            results = replay(args.target.read_bytes().decode('utf-8'), shell=args.shell, timeout=args.timeout, only=args.line)
            print(json.dumps(results, ensure_ascii=False, indent=1))
            return 1 if any(r['status'] in ('mismatch', 'error') for r in results) else 0
        if args.command == 'response':
            findings = check_response(args.target, against=args.against, journal=args.journal)
            return _print_findings(findings, args.target, args.json)
    except (OSError, ValueError, json.JSONDecodeError, re.error) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    return 0
