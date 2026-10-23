"""df.tips article tooling (skill /df-article).

lint      — deterministic checks for the 2725 format and shared client-text lexicon;
source    — numbered Markdown → keyed editing view (`## @I.12.1`, `§@I.4.1`), lossless for the format;
render    — keyed view → numbered Markdown with anchors and recomputed § references, plus a factual change report;
replay    — reruns fenced bash commands and compares their output with the quoted output;
response  — checks a chat/journal answer: duplicate of an earlier answer, procedural filler, removal claims
            contradicted by the target file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re

from .text_core import (ABBREVIATIONS, ANCHOR, ARROW_CONNECTIVE, BANS, BOLD_LEADIN, FENCE, Finding, HEADING, KEPT, LEXICON, LIST_MARK, Line, REMOVAL, REPLACED, THRESHOLDS, _excerpt, _plain, bold_spans, check_code, check_prose, check_response, clean, default_shell, detect_language, find_bans, load_lexicon, normalized, replay, scan, sentences)
from .text_core import author_text, transform_prose, command_blocks, changed_command_lines, check_markdown_lists, INLINE_LITERAL, external_section_ref, normalize_external_refs


PART = re.compile(r'^([IVXLC]+)\.\s+\S')
NUMBERED = re.compile(r'^(\d+(?:\.\d+)*)\.?(?:\s+(.*))?$')
KEYED = re.compile(r'^@([\w.\-]+)(?:\s+(.*))?$')
ANCHOR_LINK = re.compile(r'\[([^\]\n]*)\]\(#([^)\s]+)\)')
SECTION_LABEL = re.compile(r'^§{1,2}\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*)(?:\s*[-–]\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*))?$')
SOURCE_REF = re.compile(r'(§§?)@([\w.\-]+?)(?:-@([\w.\-]+))?(?=[^\w.\-]|\.(?:\s|$)|$)')
BARE_REF = re.compile(r'(?<![\w@])(§{1,2})\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*)(?:\s*[-–]\s*(?:([IVXLC]+)\.)?(\d+(?:\.\d+)*))?(?!\w)')
SOURCE_META = re.compile(r'^\s*<!-- df-article: (\{.*\}) -->\s*$')


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


def detect_kind(path: Path | None, text: str) -> str:
    if path is not None and path.parent.name == 'res':
        return 'response'
    return 'article'


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


def check_structure(lines, sections, findings):
    part_headings = [(line, PART.match(HEADING.match(line.raw).group(2)))
                     for line in lines if line.kind == 'heading' and HEADING.match(line.raw).group(1) == '#']
    parts = [match.group(1) for _, match in part_headings if match]
    if parts != ['I', 'II']:
        findings.append(Finding('error', 'STRUCT-PARTS', 1,
                                'article requires exactly two ordered parts: # I. Analysis and # II. Recommendations'))
    if not sections:
        findings.append(Finding('error', 'STRUCT-EMPTY', 1, 'article has no addressed numbered sections'))
    for line in lines:
        if line.kind not in ('prose', 'quote', 'fence', 'code'):
            continue
        section = section_at(sections, line.no)
        if section is None or section.part != part_at(lines, line.no):
            findings.append(Finding('error', 'STRUCT-UNADDRESSED', line.no,
                                    'article content must belong to a numbered section', line.raw[:80]))
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
        elif section.anchor not in (section.key, '§' + section.key):
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
    by_key = {section.key: section for section in sections}
    for line in lines:
        if line.kind not in ('prose', 'heading'):
            continue
        spans = bold_spans(line.raw)
        visible = author_text(line.raw)
        linked_spans = []
        for match in ANCHOR_LINK.finditer(visible):
            linked_spans.append(match.span())
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
                if expected != target.removeprefix('§'):
                    findings.append(Finding('error', 'REF-LABEL', line.no, f'label points to {expected}, link goes to #{target}', match.group(0)))
                if parsed.group(4):
                    end_part = parsed.group(3) or label_part
                    endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
                    if endpoint not in by_key:
                        findings.append(Finding('error', 'REF-DANGLING', line.no,
                                                f'range endpoint §{endpoint} does not exist', match.group(0)))
                    elif expected in by_key and by_key[expected].line > by_key[endpoint].line:
                        findings.append(Finding('error', 'REF-RANGE', line.no,
                                                'range endpoints are in reverse document order', match.group(0)))
                if line.kind != 'heading' and not any(a < match.start() < b for a, b in spans):
                    findings.append(Finding('warning', 'REF-BOLD', line.no, 'section reference is not bold: **[§N](#P.N)**', match.group(0)))
        for match in BARE_REF.finditer(visible):
            if not external_section_ref(visible, match) and not any(start <= match.start() < end for start, end in linked_spans):
                findings.append(Finding('error', 'REF-BARE', line.no,
                                        'article section reference needs a working anchor link', match.group(0)))
        if re.search(r'§§?@|\]\(#@', visible):
            findings.append(Finding('error', 'KEY-UNRENDERED', line.no,
                                    'unrendered keyed reference remains in the numbered article', line.raw[:80]))
    check_group_counts(lines, sections, findings)


def check_group_counts(lines, sections, findings):
    """Check explicit counts only where the displayed objects are countable."""
    for section in sections:
        match = re.search(r'\((\d+)(?:\s+[^()]*)?\)\s*$', section.title or '')
        if not match:
            continue
        expected = int(match.group(1))
        own = [line for line in lines if section.line < line.no <= section.end]
        items = [line for line in own if line.kind in ('prose', 'quote') and
                 LIST_MARK.match(re.sub(r'^\s*>\s?', '', line.raw))]
        actual = len(items) if items else None
        if actual is None and section.children:
            child_counts = [re.search(r'\((\d+)(?:\s+[^()]*)?\)\s*$', child.title or '') for child in section.children]
            if all(child_counts):
                actual = sum(int(child.group(1)) for child in child_counts)
        if actual is not None and actual != expected:
            findings.append(Finding('error', 'GROUP-COUNT', section.line,
                                    f'heading declares {expected} objects, displayed group contains {actual}', section.title or ''))


def check_graph(lines, sections, findings):
    parts = {s.part for s in sections}
    if not {'I', 'II'} <= parts:
        return
    by_key = {s.key: s for s in sections}
    refs = {s.key: set() for s in sections}
    external = {s.key: False for s in sections}
    primary = {s.key: False for s in sections}
    for line in lines:
        section = section_at(sections, line.no)
        if section is None or line.kind in ('heading', 'anchor'):
            continue
        if line.kind in ('code', 'quote'):
            primary[section.key] = True
        if line.kind == 'prose':
            visible = author_text(line.raw)
            for match in ANCHOR_LINK.finditer(visible):
                target = match.group(2).removeprefix('§')
                if target in by_key:
                    refs[section.key].add(target)
                parsed = SECTION_LABEL.match(match.group(1).replace('**', '').strip())
                if parsed and parsed.group(4) and target in by_key:
                    end_part = parsed.group(3) or parsed.group(1) or section.part
                    endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
                    if endpoint in by_key:
                        refs[section.key].update(s.key for s in sections if by_key[target].line <= s.line <= by_key[endpoint].line)
            if re.search(r'\]\(<?https?://|https?://', line.raw):
                external[section.key] = True
                primary[section.key] = True
    # GRAPH-ORPHAN: analysis paragraphs that no recommendation needs, directly or through premises.
    used, expanded = set(), set()
    queue = [(s.key, False) for s in sections if s.part == 'II']
    while queue:
        key, expand = queue.pop()
        node = by_key[key]
        # A referenced group includes its objects. Walking upward from a
        # referenced leaf includes its context, never its unrelated siblings.
        if expand and key not in expanded:
            expanded.add(key)
            queue.extend((child.key, True) for child in node.children)
        for member in node.lineage():
            if member.key not in used:
                used.add(member.key)
                queue.extend((target, True) for target in refs[member.key])
    for section in sections:
        own_body = [line for line in lines if section.line < line.no <= section.end and line.kind in ('prose', 'quote', 'code')]
        if section.part == 'I' and section.key not in used and (own_body or not section.children):
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
    # GRAPH-CONDITIONAL-STEP: a conditional recommendation must branch from an earlier Part II diagnostic step.
    for section in sections:
        if section.part != 'II':
            continue
        body_prose = [l for l in lines if section.line < l.no <= section.end and l.kind == 'prose']
        for line in body_prose:
            visible = author_text(line.raw).strip()
            if re.match(r'^(?:If|Если|В случае если)\b', visible, re.I):
                prefix = visible.split('→', 1)[0]
                has_part2_branch = False
                has_part1_cond = False
                for match in ANCHOR_LINK.finditer(prefix):
                    target = match.group(2).removeprefix('§')
                    if target.startswith('II.') or (target in by_key and by_key[target].part == 'II'):
                        has_part2_branch = True
                    elif target.startswith('I.') or (target in by_key and by_key[target].part == 'I'):
                        has_part1_cond = True
                if has_part1_cond and not has_part2_branch:
                    findings.append(Finding('error', 'GRAPH-CONDITIONAL-STEP', line.no,
                                            f'conditional recommendation §{section.key} conditions on an established Part I fact; it must branch from a Part II diagnostic step (like §II.12.2 from §II.12.1 in 2725.md)',
                                            line.raw[:100]))
                elif not has_part2_branch:
                    findings.append(Finding('warning', 'GRAPH-CONDITIONAL-STEP', line.no,
                                            f'conditional recommendation §{section.key} has no Part II diagnostic premise; branch from an explicit measurement step',
                                            line.raw[:100]))
    # PROOF-MISSING: analysis leaves with neither proof nor premise.
    for section in sections:
        if section.part != 'I' or section.children:
            continue
        body = [l for l in lines if section.line < l.no <= section.end and l.kind not in ('blank', 'anchor')]
        has_proof = any(l.kind in ('code', 'fence', 'quote') for l in body) or external[section.key] or refs[section.key] \
            or (section.parent and any(l.kind in ('code', 'fence') for l in lines if section.parent.line < l.no < section.line))
        if not has_proof:
            findings.append(Finding('note', 'PROOF-MISSING', section.line, f'§{section.key} states a fact without a command, quote, link or premise'))
    # A citation cycle cannot manufacture evidence. Diagnose strongly connected
    # components only when no member reaches a primary observation/source.
    grounded = {s.key for s in sections if any(primary[a.key] for a in s.lineage())}
    changed = True
    while changed:
        additions = {key for key, targets in refs.items() if targets and targets <= grounded}
        additions.update(s.key for s in sections if s.children and all(child.key in grounded for child in s.children))
        changed = not additions <= grounded
        grounded.update(additions)
    counter, stack, on_stack, indexes, low = 0, [], set(), {}, {}

    def visit(key):
        nonlocal counter
        indexes[key] = low[key] = counter
        counter += 1
        stack.append(key)
        on_stack.add(key)
        for target in sorted(refs[key]):
            if target not in indexes:
                visit(target)
                low[key] = min(low[key], low[target])
            elif target in on_stack:
                low[key] = min(low[key], indexes[target])
        if low[key] != indexes[key]:
            return
        component = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == key:
                break
        if (len(component) > 1 or key in refs[key]) and not any(member in grounded for member in component):
            first = min((by_key[member] for member in component), key=lambda node: node.line)
            findings.append(Finding('error', 'GRAPH-CYCLE', first.line,
                                    'circular premises without primary evidence: ' + ', '.join('§' + member for member in sorted(component))))

    for key in refs:
        if key not in indexes:
            visit(key)


def check_proposal(lines, findings):
    """Compatibility entry point; the proposal profile owns its grammar."""
    from . import proposal
    findings.extend(proposal.lint_text('\n'.join(line.raw for line in lines), lexicon=[], bans=[]))


def check_link_style(lines, findings, link_style):
    if link_style != 'formatted':
        return
    from .markdown_links import parser, inline_links, display_address
    engine, environment = parser(), {}
    engine.parse('\n'.join(line.raw for line in lines), environment)
    definitions = {index for item in environment.get('references', {}).values()
                   for index in range(*item.get('map', (0, 0)))}
    for line in lines:
        if line.kind not in ('prose', 'heading') or line.no - 1 in definitions:
            continue
        # Keep literal quotes/code outside the author's formatting contract.
        authored = INLINE_LITERAL.sub('', line.raw)
        tokens = engine.parseInline(authored, environment)[0].children or []
        for href, label in inline_links(tokens):
            if href.startswith(('https://', 'http://')):
                try:
                    actual = display_address(label if '://' in label else 'https://' + label)
                    expected = display_address(href)
                except ValueError:
                    actual, expected = None, href
                if actual != expected:
                    findings.append(Finding('error', 'LINK-LABEL', line.no,
                        'formatted label must preserve the destination domain, path, query and fragment', label))
        protected = [match.span() for match in INLINE_LITERAL.finditer(line.raw)]
        protected.extend(match.span() for match in re.finditer(r'(?<!\w)"[^"\n]+"', line.raw))
        protected.extend(match.span() for match in re.finditer(r'!?\[[^\]\n]*\]\((?:<?https?://[^\s>)]*>?)\)|<https?://[^>\n]+>', line.raw))
        for match in re.finditer(r'https?://[^\s<>]+', line.raw):
            if not any(start <= match.start() < end for start, end in protected):
                findings.append(Finding('error', 'LINK-BARE', line.no,
                                        'the selected article profile requires formatted external links', match.group(0)))


def lint_text(text: str, *, kind: str | None = None, lang: str | None = None, path: Path | None = None,
              lexicon=None, bans=None, link_style=None) -> list[Finding]:
    kind = kind or detect_kind(path, text)
    if kind == 'proposal':
        from . import proposal
        return proposal.lint_text(text, lang=lang, path=path, lexicon=lexicon, bans=bans)
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
        check_markdown_lists(lines, findings)
        check_link_style(lines, findings, link_style)
    check_prose(lines, kind, lang, findings, lexicon, bans)
    return sorted(findings, key=lambda f: (f.line, f.severity != 'error', f.rule))


# ---------------------------------------------------------------- responses


# ---------------------------------------------------------------- source ⇄ render

def to_source(text: str) -> str:
    """Numbered Markdown → keyed view, preserving anchor style and literals."""
    lines = scan(text)
    findings = []
    sections = parse_sections(lines, findings)
    by_line = {s.line: s for s in sections}
    aliases = {s.anchor or s.key: s.key for s in sections}
    standalone = {ANCHOR.match(line.raw).group(1) for line in lines if line.kind == 'anchor'} - set(aliases)
    anchor_lines = {next((x.no for x in lines if x.no > s.line and x.kind != 'blank'), None) for s in sections if s.anchor}
    prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in sections}
    default = '§' if prefixes and all(prefixes.values()) else ''
    overrides = {key: prefix for key, prefix in prefixes.items() if prefix != default}
    metadata = {'anchor_prefix': default}
    if overrides:
        metadata['anchor_prefixes'] = overrides
    out = ['<!-- df-article: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')) + ' -->']
    for line in lines:
        if line.no in by_line:
            section = by_line[line.no]
            title = f' {section.title}' if section.title else ''
            out.append('#' * (len(section.number) + 1) + f' @{section.key}{title}')
        elif line.no in anchor_lines and line.kind == 'anchor':
            continue
        elif line.kind in ('prose', 'heading'):
            current = part_at(lines, line.no)

            def replace(match):
                label, target = match.groups()
                key = aliases.get(target, target.removeprefix('§'))
                parsed = SECTION_LABEL.match(label.replace('**', '').strip())
                if not parsed or not label.strip().startswith('§'):
                    return match.group(0) if target in standalone else f'[{label}](#@{key})'
                marks = '§§' if label.strip().startswith('§§') else '§'
                if parsed.group(4):
                    end_part = parsed.group(3) or parsed.group(1) or current
                    endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
                    return f'{marks}@{key}-@{endpoint}'
                return f'{marks}@{key}'

            def bare(match):
                if external_section_ref(match.string, match):
                    return match.group(0)
                marks, start_part, start_number, end_part, end_number = match.groups()
                start_part = start_part or current
                start = f'{start_part}.{start_number}' if start_part else start_number
                if end_number:
                    end_part = end_part or start_part
                    endpoint = f'{end_part}.{end_number}' if end_part else end_number
                    return f'{marks}@{start}-@{endpoint}'
                return f'{marks}@{start}'

            def convert(value):
                return BARE_REF.sub(bare, ANCHOR_LINK.sub(replace, value))
            out.append(transform_prose(line.raw, convert))
        else:
            out.append(line.raw)
    return '\n'.join(out) + ('\n' if text.endswith('\n') else '')


def render(source: str, previous: str | None = None):
    """Keyed view → numbered Markdown. Returns (markdown, report, findings)."""
    lines = scan(source)
    findings: list[Finding] = []
    external_changes = []
    metadata = {}
    for line in lines:
        match = SOURCE_META.match(line.raw) if line.kind == 'comment' else None
        if match:
            try:
                value = json.loads(match.group(1))
                if not isinstance(value, dict) or value.get('anchor_prefix', '') not in ('', '§') or any(prefix not in ('', '§') for prefix in value.get('anchor_prefixes', {}).values()):
                    raise ValueError('anchor prefix must be empty or §')
                metadata.update(value)
            except (ValueError, TypeError, AttributeError) as exc:
                findings.append(Finding('error', 'KEY-METADATA', line.no, str(exc)))
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
    if not sections:
        findings.append(Finding('error', 'KEY-EMPTY', 1, 'keyed source has no addressed sections'))
    old_sections = parse_sections(scan(previous)) if previous is not None else []
    old_prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in old_sections}
    default_prefix = metadata.get('anchor_prefix', '§' if old_prefixes and all(old_prefixes.values()) else '')
    prefixes = metadata.get('anchor_prefixes', {})
    anchors = {key: prefixes.get(key, old_prefixes.get(key, default_prefix)) + number for key, number in mapping.items()}
    out = []
    for line in lines:
        if line.kind == 'comment' and SOURCE_META.match(line.raw):
            continue
        if line.no in numbers:
            node = numbers[line.no]
            title = (' ' if node.title.startswith('(') else '. ') + node.title if node.title else ''
            out.append('#' * (len(node.number) + 1) + f' {node.dotted}{title}')
            out.append(f"<a name='{anchors[node.name]}'></a>")
            continue
        if line.kind not in ('prose', 'heading'):
            out.append(line.raw)
            continue
        current = part_at(lines, line.no)

        def label(anchor):
            part, _, number = anchor.partition('.') if re.match(r'^[IVXLC]+\.', anchor) else ('', '', anchor)
            return number if part == current else anchor

        def replace(match):
            marks, start, end = match.groups()
            suffix = ''
            if end and end.endswith('.') and end not in mapping and end[:-1] in mapping:
                end, suffix = end[:-1], '.'
            if start not in mapping:
                findings.append(Finding('error', 'KEY-DANGLING', line.no, f'§@{start} does not exist (deleted premise: delete or re-ground the dependent claim)', line.raw[:80]))
                return match.group(0)
            if end:
                if end not in mapping:
                    findings.append(Finding('error', 'KEY-DANGLING', line.no, f'§@{end} does not exist', line.raw[:80]))
                    return match.group(0)
                return f'[{marks}{label(mapping[start])}-{label(mapping[end])}](#{anchors[start]})' + suffix
            return f'[{marks}{label(mapping[start])}](#{anchors[start]})'

        def anchor_ref(match):
            key = match.group(1)
            if key not in mapping:
                findings.append(Finding('error', 'KEY-DANGLING', line.no, f'#@{key} does not exist', line.raw[:80]))
                return match.group(0)
            return f'(#{anchors[key]})'

        def convert(value):
            result = re.sub(r'\(#@([\w.\-]+)\)', anchor_ref, SOURCE_REF.sub(replace, value))
            result = normalize_external_refs(result, changes=external_changes, line=line.no)
            if re.search(r'§§?@|\(#@', result) and not any(f.line == line.no and f.rule == 'KEY-DANGLING' for f in findings):
                findings.append(Finding('error', 'KEY-SYNTAX', line.no, 'unparseable or unresolved keyed reference', result[:80]))
            return result
        out.append(transform_prose(line.raw, convert))
    markdown = '\n'.join(out) + ('\n' if source.endswith('\n') else '')
    report = {'renumbered': [[k, v] for k, v in mapping.items() if k != v and re.match(r'^(?:[IVXLC]+\.)?\d', k)],
              'added': [k for k in mapping if not re.match(r'^(?:[IVXLC]+\.)?\d+(?:\.\d+)*$', k)]}
    if external_changes:
        report['external_references_normalized'] = external_changes
    if previous is not None:
        old = [s.key for s in old_sections]
        report['removed'] = [key for key in old if key not in mapping]
    reference_findings = []
    check_structure(scan(markdown), parse_sections(scan(markdown)), reference_findings)
    findings.extend(f for f in reference_findings if f.rule in ('REF-DANGLING', 'REF-LABEL', 'REF-RANGE', 'REF-BARE', 'KEY-UNRENDERED', 'ANCHOR-DUP'))
    return markdown, report, findings


def render_map(source: str, markdown: str | None = None):
    """Stable source keys and exact body/subtree spans for the workflow sidecar."""
    source_sections, _ = parse_keyed(scan(source), [])
    if markdown is None:
        markdown, _, _ = render(source)
    rendered = parse_sections(scan(markdown))
    def span(node):
        return {'start': node.line, 'end': node.end,
                'subtree_end': max([node.end] + [child.end for child in node.descendants()])}
    return [{'key': original.name, 'number': current.key, 'part': current.part, 'anchor': current.anchor,
             'source': span(original), 'rendered': span(current)}
            for original, current in zip(source_sections, rendered)]


# ---------------------------------------------------------------- replay


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    from .text_cli import main as common_main
    return common_main(argv, default_kind='article')
