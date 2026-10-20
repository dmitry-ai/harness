"""Shared client-text mechanics. Article and proposal own their respective formats."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .runtime import PRIMARY, settings

LEXICON = PRIMARY / 'references/client-text/lexicon.json'


BANS = Path('ꘖ/data/text-bans.json')
ANCHOR = re.compile(r"""^\s*<a\s+name=['"]([^'"]+)['"]\s*>\s*</a>\s*$""")


FENCE = re.compile(r'^\s*(```|~~~)')


HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*$')


LIST_MARK = re.compile(r'^\s*(?:[-*+]|\d+(?:\.\d+)*[.)])\s+')


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


def scan(text: str) -> list[Line]:
    """Classify Markdown without treating a shorter/different fence as its close."""
    lines, fenced = [], None
    for no, raw in enumerate(text.splitlines(), 1):
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', raw)
        closing = (re.fullmatch(r' {0,3}' + re.escape(fenced[0]) +
                                '{' + str(fenced[1]) + r',}\s*', raw)
                   if fenced else None)
        if closing:
            lines.append(Line(no, raw, 'fence'))
            fenced = None
        elif fenced:
            lines.append(Line(no, raw, 'code'))
        elif opening and not (opening.group(1).startswith('`') and '`' in opening.group(2)):
            lines.append(Line(no, raw, 'fence'))
            fenced = (opening.group(1)[0], len(opening.group(1)))
        elif not raw.strip():
            lines.append(Line(no, raw, 'blank'))
        elif re.fullmatch(r'\s*<!--.*-->\s*', raw):
            lines.append(Line(no, raw, 'comment'))
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


INLINE_LITERAL = re.compile(r'(`+)(?!`)(.*?)\1(?!`)|«[^»]*»|“[^”]*”|(?<!\w)"[^"\n]+"')
PROTECTED_SPAN = re.compile(INLINE_LITERAL.pattern +
                            r'|!?\[[^\]\n]*\]\((?:<?https?://[^\s>)]*>?)\)'
                            r'|<https?://[^>\n]+>|https?://[^\s<>"\']+'
                            r'|(?<!\w)"[^"\n]+"')


def prose_spans(raw: str):
    """Offsets outside inline code and verbatim quotations; never edit literals."""
    start = 0
    for match in PROTECTED_SPAN.finditer(raw):
        if match.start() > start:
            yield start, match.start()
        start = match.end()
    if start < len(raw):
        yield start, len(raw)


def transform_prose(raw: str, transform):
    pieces, cursor = [], 0
    for start, end in prose_spans(raw):
        pieces.extend((raw[cursor:start], transform(raw[start:end])))
        cursor = end
    pieces.append(raw[cursor:])
    return ''.join(pieces)


def reference_document(text, match):
    """Return the explicit document namespace; an unqualified § reference is local."""
    prefix = re.search(r'\b(?:(?:RFC|ISO(?:/IEC)?|IEC|IEEE|EN)\s+\d+(?::\d+)?|'
                       r'\d+\s+(?:CCR|CFR|U\.?S\.?C\.?))\s*$', text[:match.start()], re.I)
    return ' '.join(prefix.group().split()) if prefix else None


def external_section_ref(text, match):
    return reference_document(text, match) is not None


def normalize_external_refs(raw, *, changes=None, line=None):
    """Format external references without changing their numbers or protected literals."""
    def segment(value):
        def replace(match):
            document = reference_document(value, match)
            if document is None:
                return match.group()
            if changes is not None:
                number = re.match(r'\d+(?:\.\d+)*', value[match.end():]).group()
                changes.append({'line': line, 'document': document,
                                'before': match.group() + number, 'after': match.group(1) + number})
            return match.group(1)
        return re.sub(r'(§{1,2})[ \t]+(?=\d)', replace, value)
    return transform_prose(raw, segment)


def author_text(raw: str):
    """Mask literals, retaining offsets for diagnostics and reference parsing."""
    out = [' '] * len(raw)
    for start, end in prose_spans(raw):
        out[start:end] = raw[start:end]
    return ''.join(out)


def check_markdown_lists(lines, findings):
    """Author-owned Markdown lists use native numbering; quotations are literal."""
    for line in lines:
        if line.kind != 'prose':
            continue
        match = re.match(r'^\s*(\d+)[.)]\s+', line.raw)
        if match and match.group(1) != '1':
            findings.append(Finding('error', 'LIST-AUTONUM', line.no,
                                    'use the native Markdown 1. marker for ordinary list items', line.raw[:80]))


def clean(raw: str) -> str:
    """Prose without code, URLs, verbatim quotes and markup: what the lexicon must judge."""
    s = LIST_MARK.sub('', raw)
    s = INLINE_LITERAL.sub(lambda m: ' CODE ' if m.group(1) else ' QUOTE ', s)
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


def bold_spans(raw: str):
    marks = [m.start() for m in re.finditer(r'\*\*', raw)]
    return [(marks[i], marks[i + 1]) for i in range(0, len(marks) - 1, 2)]


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
            if re.search(r'/assets/(?:index|app|main)[.-][A-Za-z0-9_-]{6,}\.(?:js|css)\b', line.raw):
                findings.append(Finding('warning', 'CODE-VOLATILE', line.no,
                                        'hashed build URL can change: resolve the current asset, or pin and identify the historical build the claim concerns', line.raw[:100]))
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
        for reference in re.finditer(r'§{1,2}[ \t]+(?=\d)', author_text(raw)):
            if external_section_ref(author_text(raw), reference):
                findings.append(Finding('error', 'REF-EXTERNAL-SPACE', line.no,
                                        'write the external paragraph immediately after §; keep its document and number', raw[:100]))
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


def load_lexicon(path=None):
    return json.loads(Path(path or LEXICON).read_text(encoding='utf-8'))['entries']


def find_bans(path: Path | None):
    if path is None:
        return []
    for folder in [path.resolve().parent, *path.resolve().parents]:
        result = []
        for relative in (BANS, Path('ꘖ/data/article-bans.json')):
            candidate = folder / relative
            if candidate.is_file():
                data = json.loads(candidate.read_text(encoding='utf-8'))
                result.extend(data.get('bans', []) if isinstance(data, dict) else data)
        if result:
            return result
    return []


def normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def check_response(path: Path, text: str | None = None, against=(), lexicon=None, journal: Path | None = None) -> list[Finding]:
    """`journal` is the journal folder (with `res/`); without it a file inside `res/` is compared with its siblings."""
    text = path.read_bytes().decode('utf-8') if text is None else text
    findings = []
    check_prose(scan(text), 'response', detect_language(text), findings,
                load_lexicon() if lexicon is None else lexicon, [])
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
                findings.append(Finding('warning', 'RESP-DUP', 1,
                                        f'{ratio:.0%} similar to {other.name}: compare the current request and operation receipts; similarity alone does not establish whether it was executed'))
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


def default_shell():
    """An explicit environment setting wins; prefer Cygwin on Windows."""
    configured = os.environ.get('DF_TEXT_BASH') or os.environ.get('CYGWIN_BASH') or settings().get('client_text', {}).get('bash')
    if configured:
        return configured
    if os.name == 'nt':
        for candidate in ('C:/tools/cygwin/bin/bash.exe', 'C:/cygwin64/bin/bash.exe', 'C:/cygwin/bin/bash.exe'):
            if Path(candidate).is_file():
                return candidate
    found = shutil.which('bash')
    if found:
        return found
    git = shutil.which('git')
    if git:
        for candidate in (Path(git).resolve().parents[1] / 'bin/bash.exe', Path(git).resolve().parents[1] / 'usr/bin/bash.exe'):
            if candidate.is_file():
                return str(candidate)
    return 'bash'


def _plain(value: str) -> str:
    """Remove the reader-facing wrapper, preserving the separate raw stdout."""
    value = re.sub(r'^\s*>\s?', '', value).rstrip()
    value = re.sub(r'^\s*(?:\d+[.)]|[-*+])\s+', '', value)
    value = re.sub(r'\[([^\]]+)\]\((?:<[^>]+>|[^)]*)\)', r'\1', value)
    value = re.sub(r'(`+)(.*?)\1', r'\2', value)
    return '' if value == '<empty response>' else value


def command_blocks(text: str):
    """Fenced commands with their quoted presentation, never executing anything."""
    lines = scan(text)
    blocks, index = [], 0
    while index < len(lines):
        if lines[index].kind != 'fence' or not re.match(r'^\s*(?:`{3,}|~{3,})\s*(bash|sh|shell)\s*$', lines[index].raw):
            index += 1
            continue
        first = lines[index].no
        index += 1
        body = []
        while index < len(lines) and lines[index].kind == 'code':
            body.append(lines[index].raw)
            index += 1
        closed = index < len(lines) and lines[index].kind == 'fence'
        if closed:
            index += 1
        cursor = index
        expected, presentation = [], []
        # Output can be divided into addressed child sections, as in the
        # reference article's lists. A heading alone is never output.
        output_end = lines[index - 1].no if index else first
        while cursor < len(lines) and lines[cursor].kind in ('blank', 'quote', 'heading', 'anchor'):
            if lines[cursor].kind == 'quote':
                presentation.append(lines[cursor].raw)
                expected.append(_plain(lines[cursor].raw))
                output_end = lines[cursor].no
            cursor += 1
        command = '\n'.join(body)
        blocks.append({'line': first, 'end': output_end, 'command': command,
                       'command_sha256': hashlib.sha256(command.encode('utf-8')).hexdigest(),
                       'expected': expected, 'presentation': '\n'.join(presentation), 'closed': closed})
    return blocks


def changed_command_lines(text: str, previous: str | None = None):
    """Lines needing a receipt; moving an unchanged block does not re-run it."""
    from collections import Counter
    old = Counter((b['command_sha256'], tuple(b['expected'])) for b in command_blocks(previous or ''))
    changed = []
    for block in command_blocks(text):
        identity = (block['command_sha256'], tuple(block['expected']))
        if old[identity]:
            old[identity] -= 1
        else:
            changed.append(block['line'])
    return changed


def _output_lines(value):
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def replay(text: str, *, shell=None, timeout=60, only=None, expected_exit=None, contracts=None):
    """Execute selected blocks with strict Bash/pipefail and retain raw receipts.

    Expected nonzero exits must be explicit (``expected_exit={line: 1}`` or
    ``contracts={line: {'exit': 1}}``). Missing comparisons and uncovered
    selectors are failures, not successful verification.
    """
    results, covered = [], set()
    shell = shell or default_shell()
    selected = set(only) if only is not None else None
    contracts = contracts or {}
    for block in command_blocks(text):
        first = block['line']
        wanted = {line for line in selected or () if first <= line <= block['end']}
        if selected is not None and not wanted:
            continue
        covered.update(wanted)
        contract = contracts.get(first, contracts.get(str(first), {}))
        wanted_exit = contract.get('exit', 0)
        if expected_exit is not None:
            wanted_exit = (expected_exit.get(first, expected_exit.get(str(first), wanted_exit))
                           if isinstance(expected_exit, dict) else expected_exit)
        if not isinstance(wanted_exit, int) or isinstance(wanted_exit, bool):
            raise ValueError(f'expected exit for line {first} must be an integer')
        record = {'line': first, 'end': block['end'], 'command_sha256': block['command_sha256'],
                  'shell': str(shell), 'expected_exit': wanted_exit,
                  'presentation': block['presentation']}
        if not block['closed']:
            results.append({**record, 'status': 'error', 'error': 'unclosed command fence'})
            continue
        expected = (_output_lines(contract['stdout']) if 'stdout' in contract else
                    _output_lines('\n'.join(block['expected'])))
        if not block['presentation'] and 'stdout' not in contract:
            results.append({**record, 'status': 'no-quoted-output'})
            continue
        try:
            environment = os.environ.copy()
            if Path(shell).is_absolute():
                environment['PATH'] = str(Path(shell).parent) + os.pathsep + environment.get('PATH', '')
            done = subprocess.run([shell, '-e', '-o', 'pipefail', '-c', block['command']], capture_output=True, timeout=timeout,
                                  encoding='utf-8', errors='replace', env=environment)
            actual = _output_lines(done.stdout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append({**record, 'status': 'error', 'error': str(exc)})
            continue
        status = ('exit-mismatch' if done.returncode != wanted_exit else
                  'match' if expected == actual else 'mismatch')
        if status == 'match' and 'stderr' in contract and contract['stderr'] != done.stderr:
            status = 'mismatch'
        results.append({**record, 'status': status, 'expected': expected, 'actual': actual,
                        'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
    for line in sorted((selected or set()) - covered):
        results.append({'line': line, 'status': 'uncovered', 'error': 'selected line is not in a Bash block or its quoted output'})
    return results
