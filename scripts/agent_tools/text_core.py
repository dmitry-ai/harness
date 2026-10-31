# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
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
ANCHOR = re.compile('^\\s*<a\\s+name=[\'"]([^\'"]+)[\'"]\\s*>\\s*</a>\\s*$')
FENCE = re.compile('^\\s*(```|~~~)')
HEADING = re.compile('^(#{1,6})\\s+(.*?)\\s*$')
LIST_MARK = re.compile('^\\s*(?:[-*+]|\\d+(?:\\.\\d+)*[.)])\\s+')
ARROW_CONNECTIVE = re.compile('^\\s*(?:because|since|as|although|though|while|so|thus|therefore|hence|which|this means|consequently|as a result|\\u043f\\u043e\\u0442\\u043e\\u043c\\u0443 \\u0447\\u0442\\u043e|\\u0442\\u0430\\u043a \\u043a\\u0430\\u043a|\\u043f\\u043e\\u0441\\u043a\\u043e\\u043b\\u044c\\u043a\\u0443|\\u0445\\u043e\\u0442\\u044f|\\u0441\\u043b\\u0435\\u0434\\u043e\\u0432\\u0430\\u0442\\u0435\\u043b\\u044c\\u043d\\u043e|\\u043f\\u043e\\u044d\\u0442\\u043e\\u043c\\u0443|\\u0447\\u0442\\u043e \\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\u0435\\u0442)\\b', re.I)
BOLD_LEADIN = re.compile('^\\*\\*(?!\\{?\\[§)(?!§)([^*\\n]{2,90})\\*\\*\\s*[:—–]')
REMOVAL = re.compile('(?i)\\b(?:\\u0443\\u0434\\u0430\\u043b[\\u0435\\u0451]\\u043d\\w*|\\u0443\\u0434\\u0430\\u043b\\u0438\\u043b\\w*|\\u0443\\u0431\\u0440\\u0430\\u043d\\w*|\\u0443\\u0431\\u0440\\u0430\\u043b\\w*|\\u0443\\u0441\\u0442\\u0440\\u0430\\u043d[\\u0435\\u0451]\\u043d\\w*|\\u0443\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u043b\\w*|\\u0432\\u044b\\u0447\\u0438\\u0449\\u0435\\u043d\\w*|\\u0432\\u044b\\u0447\\u0438\\u0441\\u0442\\u0438\\u043b\\w*|\\u0432\\u044b\\u0440\\u0435\\u0437\\u0430\\u043d\\w*|\\u0438\\u0441\\u043a\\u043b\\u044e\\u0447[\\u0435\\u0451]\\u043d\\w*|\\u0438\\u0441\\u043a\\u043b\\u044e\\u0447\\u0438\\u043b\\w*|removed|deleted|eliminated|stripped|dropped)\\b')
REPLACED = re.compile('(?i)\\b(?:\\u0437\\u0430\\u043c\\u0435\\u043d\\u0435\\u043d\\w*|\\u0437\\u0430\\u043c\\u0435\\u043d\\u0451\\u043d\\w*|\\u0437\\u0430\\u043c\\u0435\\u043d\\u0438\\u043b\\w*|replaced)\\b')
KEPT = re.compile('(?i)\\b(?:\\u043e\\u0441\\u0442\\u0430\\u0432\\u043b\\u0435\\u043d\\w*|\\u043e\\u0441\\u0442\\u0430\\u0432\\u0438\\u043b\\w*|\\u043a\\u0440\\u043e\\u043c\\u0435|\\u0437\\u0430 \\u0438\\u0441\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u0435\\u043c|except|kept|retained)\\b')
ABBREVIATIONS = {'e.g', 'i.e', 'vs', 'etc', 'inc', 'ltd', 'co', 'no', 'mr', 'mrs', 'dr', 'st', 'fig', 'approx', '\u0442.\u0435', '\u0442.\u0434', '\u0442.\u043f', '\u0434\u0440', '\u0441\u043c', '\u0433', '\u0433\u0433'}
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
		r = f'{where}: [{self.severity}] {self.rule}: {self.message}{tail}'
		return r
@dataclass
class Line:
	no: int
	raw: str
	kind: str
def scan(text: str) -> list[Line]:
	lines, fenced = ([], None)
	for no, raw in enumerate(text.splitlines(), 1):
		opening = re.match('^ {0,3}(`{3,}|~{3,})(.*)$', raw)
		closing = re.fullmatch(' {0,3}' + re.escape(fenced[0]) + '{' + str(fenced[1]) + ',}\\s*', raw) if fenced else None
		if closing:
			lines.append(Line(no, raw, 'fence'))
			fenced = None
		elif fenced:
			lines.append(Line(no, raw, 'code'))
		elif opening and (not (opening.group(1).startswith('`') and '`' in opening.group(2))):
			lines.append(Line(no, raw, 'fence'))
			fenced = (opening.group(1)[0], len(opening.group(1)))
		elif not raw.strip():
			lines.append(Line(no, raw, 'blank'))
		elif re.fullmatch('\\s*<!--.*-->\\s*', raw):
			lines.append(Line(no, raw, 'comment'))
		elif ANCHOR.match(raw):
			lines.append(Line(no, raw, 'anchor'))
		elif HEADING.match(raw):
			lines.append(Line(no, raw, 'heading'))
		elif raw.lstrip().startswith('>'):
			lines.append(Line(no, raw, 'quote'))
		elif re.match('^\\s*(?:-{3,}|\\*{3,}|_{3,})\\s*$', raw):
			lines.append(Line(no, raw, 'hr'))
		else:
			lines.append(Line(no, raw, 'prose'))
	r = lines
	return r
INLINE_LITERAL = re.compile('(`+)(?!`)(.*?)\\1(?!`)|«[^»]*»|“[^”]*”|(?<!\\w)"[^"\\n]+"')
PROTECTED_SPAN = re.compile(INLINE_LITERAL.pattern + '|!?\\[[^\\]\\n]*\\]\\((?:<?https?://[^\\s>)]*>?)\\)|<https?://[^>\\n]+>|https?://[^\\s<>"\\\']+|(?<!\\w)"[^"\\n]+"')
def prose_spans(raw: str):
	start = 0
	for match in PROTECTED_SPAN.finditer(raw):
		if match.start() > start:
			yield (start, match.start())
		start = match.end()
	if start < len(raw):
		yield (start, len(raw))
def transform_prose(raw: str, transform):
	pieces, cursor = ([], 0)
	for start, end in prose_spans(raw):
		pieces.extend((raw[cursor:start], transform(raw[start:end])))
		cursor = end
	pieces.append(raw[cursor:])
	r = ''.join(pieces)
	return r
def reference_document(text, match):
	prefix = re.search('\\b(?:(?:RFC|ISO(?:/IEC)?|IEC|IEEE|EN)\\s+\\d+(?::\\d+)?|\\d+\\s+(?:CCR|CFR|U\\.?S\\.?C\\.?))\\s*$', text[:match.start()], re.I)
	r = ' '.join(prefix.group().split()) if prefix else None
	return r
def external_section_ref(text, match):
	return None is not reference_document(text, match)
def normalize_external_refs(raw, *, changes=None, line=None):
	def segment(value):
		def replace(match):
			document = reference_document(value, match)
			if None is document:
				r = match.group()
			else:
				if None is not changes:
					number = re.match('\\d+(?:\\.\\d+)*', value[match.end():]).group()
					changes.append({'line': line, 'document': document, 'before': match.group() + number, 'after': match.group(1) + number})
				r = match.group(1)
			return r
		return re.sub('(§{1,2})[ \\t]+(?=\\d)', replace, value)
	return transform_prose(raw, segment)
def author_text(raw: str):
	out = [' '] * len(raw)
	for start, end in prose_spans(raw):
		out[start:end] = raw[start:end]
	r = ''.join(out)
	return r
def check_markdown_lists(lines, findings):
	for line in lines:
		if 'prose' != line.kind:
			continue
		match = re.match('^\\s*(\\d+)[.)]\\s+', line.raw)
		if match and '1' != match.group(1):
			findings.append(Finding('error', 'LIST-AUTONUM', line.no, 'use the native Markdown 1. marker for ordinary list items', line.raw[:80]))
def clean(raw: str) -> str:
	s = LIST_MARK.sub('', raw)
	s = INLINE_LITERAL.sub(lambda m: ' CODE ' if m.group(1) else ' QUOTE ', s)
	s = re.sub('\\[§[^\\]]*\\]\\([^)]*\\)', ' REF ', s)
	s = re.sub('§§?@[\\w.\\-]+(?:-@[\\w.\\-]+)?', ' REF ', s)
	s = re.sub('!?\\[([^\\]]*)\\]\\((?:<[^>]*>|[^)\\s]*)\\)', lambda m: ' URL ' if not re.search('\\s', m.group(1).replace('**', '')) else m.group(1), s)
	s = re.sub('<https?://[^>]+>|https?://\\S+', ' URL ', s)
	s = re.sub('«[^»]*»|“[^”]*”', ' QUOTE ', s)
	s = s.replace('**', '').replace('__', '')
	s = re.sub('(?<![\\w*])\\*(?!\\s)([^*\\n]+?)\\*(?!\\w)', '\\1', s)
	s = re.sub('<[^>\\n]+>', ' ', s)
	r = re.sub('\\s+', ' ', s).strip()
	return r
def sentences(cleaned: str) -> list[str]:
	parts, start = ([], 0)
	for match in re.finditer('[.!?](?=\\s+[A-Z\\u0410-\\u042f\\u0401«"(\\[])', cleaned):
		word = re.findall('[\\w.]+$', cleaned[start:match.start()])
		token = (word[-1] if word else '').lower().rstrip('.')
		if token in ABBREVIATIONS or (1 == len(token) and token.isalpha()):
			continue
		parts.append(cleaned[start:match.end()].strip())
		start = match.end()
	tail = cleaned[start:].strip()
	r = parts + ([tail] if tail else [])
	return r
def detect_language(text: str) -> str:
	letters = re.findall('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]', clean(text))
	cyrillic = sum((1 for ch in letters if re.match('[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]', ch)))
	r = 'ru' if letters and cyrillic / len(letters) > 0.3 else 'en'
	return r
def bold_spans(raw: str):
	marks = [m.start() for m in re.finditer('\\*\\*', raw)]
	r = [(marks[i], marks[i + 1]) for i in range(0, len(marks) - 1, 2)]
	return r
def check_code(lines, findings):
	index = 0
	while index < len(lines):
		if 'fence' != lines[index].kind:
			index += 1
			continue
		start = index
		index += 1
		body = []
		while index < len(lines) and 'code' == lines[index].kind:
			body.append(lines[index])
			index += 1
		index += 1
		commands = sum((1 for l in body if l.raw.strip() and (not l.raw.rstrip().endswith('\\')) and (not l.raw.strip().startswith('#'))))
		for line in body:
			if re.search('/assets/(?:index|app|main)[.-][A-Za-z0-9_-]{6,}\\.(?:js|css)\\b', line.raw):
				findings.append(Finding('warning', 'CODE-VOLATILE', line.no, 'hashed build URL can change: resolve the current asset, or pin and identify the historical build the claim concerns', line.raw[:100]))
			for literal in re.findall('\'([^\']*)\'|\\"([^\\"]*)\\"', line.raw):
				literal = literal[0] or literal[1]
				if len(literal) > THRESHOLDS['grep_literal']:
					findings.append(Finding('warning', 'CODE-UNREADABLE', line.no, f'{len(literal)}-character literal: a reader cannot check it; publish a small script and run it as 2725 §11–§12 do', literal[:60] + '…'))
		cursor = index
		while cursor < len(lines) and 'blank' == lines[cursor].kind:
			cursor += 1
		output = []
		while cursor < len(lines) and 'quote' == lines[cursor].kind:
			output.append(lines[cursor])
			cursor += 1
		values = [re.sub('^\\s*>\\s?', '', l.raw).rstrip() for l in output]
		for value in set(values):
			if value and values.count(value) > max(commands, 1):
				first = output[values.index(value)]
				findings.append(Finding('warning', 'CODE-DUP-OUTPUT', first.no, f'line repeated {values.count(value)}× for {commands} command(s): add sort -u / -m1 or show why the repetition matters', value[:80]))
		_ = start
def check_prose(lines, kind, lang, findings, lexicon, bans):
	entries = [e for e in lexicon if kind in e['kinds'] and e['lang'] in ('*', lang)]
	compiled = [(e, [re.compile(p, 0 if e.get('case') else re.I) for p in e['patterns']]) for e in entries]
	ban_patterns = [(b, re.compile(b['pattern'], 0 if b.get('case') else re.I)) for b in bans]
	for line in lines:
		if line.kind not in ('prose', 'heading'):
			continue
		raw = line.raw
		text = clean(HEADING.match(raw).group(2) if 'heading' == line.kind else raw)
		if not text:
			continue
		stripped = LIST_MARK.sub('', raw).strip()
		if 'prose' == line.kind and BOLD_LEADIN.match(stripped):
			findings.append(Finding('error' if 'response' != kind else 'warning', 'BOLD-LEADIN', line.no, 'inline bold label before a colon (WP:AILIST); state the claim itself', stripped[:80]))
		for entry, patterns in compiled:
			targets = sentences(text) if 'start' == entry['where'] else [text]
			for target in targets:
				for pattern in patterns:
					match = pattern.match(target) if 'start' == entry['where'] else pattern.search(target)
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
		if 'prose' != line.kind:
			continue
		for arrow in re.finditer('→', text):
			if ARROW_CONNECTIVE.match(text[arrow.end():]):
				findings.append(Finding('error', 'ARROW-CONNECTIVE', line.no, '`→` already means «follows from the premises»; a connective after it restates or re-argues the premise', _excerpt(text, arrow)))
		if 'response' == kind:
			continue
		for reference in re.finditer('§{1,2}[ \\t]+(?=\\d)', author_text(raw)):
			if external_section_ref(author_text(raw), reference):
				findings.append(Finding('error', 'REF-EXTERNAL-SPACE', line.no, 'write the external paragraph immediately after §; keep its document and number', raw[:100]))
		found = sentences(text)
		lead = 'proposal' == kind and line.no == next((l.no for l in lines if 'prose' == l.kind), 0)
		if len(found) > 1 and (not lead):
			findings.append(Finding('error', 'SENT-SPLIT', line.no, f'{len(found)} sentences on one line (DOC-4): one sentence — one line', found[1][:60]))
		for sentence in found:
			words = re.findall("[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u04510-9][\\w'’-]*", sentence)
			if len(words) > THRESHOLDS['sentence_words']:
				findings.append(Finding('warning', 'SENT-LONG', line.no, f'{len(words)} words in one sentence', sentence[:60] + '…'))
			if sentence.count('(') > THRESHOLDS['parentheses']:
				findings.append(Finding('warning', 'SENT-PARENS', line.no, f"{sentence.count('(')} parenthetical groups: move details into their own paragraphs or drop them", sentence[:60] + '…'))
		spans = len(re.findall('`[^`]+`', raw))
		if spans > THRESHOLDS['code_spans']:
			findings.append(Finding('warning', 'SENT-IDENTIFIERS', line.no, f'{spans} code identifiers on one line: keep only those the claim needs', raw[:60] + '…'))
		bold = [s for s in re.findall('\\*\\*(.+?)\\*\\*', raw) if '§' not in s]
		if len(bold) > THRESHOLDS['bold_spans']:
			findings.append(Finding('warning', 'BOLD-DENSITY', line.no, f'{len(bold)} bold fragments on one line (WP:AIBOLD)', raw[:60] + '…'))
		if kind in ('article', 'proposal') and re.search('\\]\\((?!<?https?://|#|mailto:)', raw):
			findings.append(Finding('error', 'LINK-LOCAL', line.no, 'link to a local file: the client cannot open it', raw[:80]))
def _excerpt(text, match, width=40):
	start, end = (max(match.start() - width, 0), min(match.end() + width, len(text)))
	r = ('…' if start else '') + text[start:end] + ('…' if end < len(text) else '')
	return r
def load_lexicon(path=None):
	return json.loads(Path(path or LEXICON).read_text(encoding='utf-8'))['entries']
def find_bans(path: Path | None):
	if None is path:
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
	return re.sub('\\s+', ' ', text).strip()
def check_response(path: Path, text: str | None=None, against=(), lexicon=None, journal: Path | None=None) -> list[Finding]:
	text = path.read_bytes().decode('utf-8') if None is text else text
	findings = []
	check_prose(scan(text), 'response', detect_language(text), findings, load_lexicon() if None is lexicon else lexicon, [])
	folder = Path(journal) / 'res' if journal else path.parent if 'res' == path.parent.name else None
	if None is not folder and folder.is_dir():
		mine = normalized(text)
		for other in sorted(folder.glob('*.md')):
			if other.resolve() == path.resolve():
				continue
			if path.stem.isdigit() and other.stem.isdigit() and (int(other.stem) > int(path.stem)):
				continue
			theirs = normalized(other.read_bytes().decode('utf-8', errors='replace'))
			if not theirs or not mine or min(len(mine), len(theirs)) < 0.8 * max(len(mine), len(theirs)):
				continue
			if theirs == mine:
				ratio = 1.0
			else:
				matcher = difflib.SequenceMatcher(None, mine.split(' '), theirs.split(' '))
				ratio = matcher.ratio() if matcher.quick_ratio() >= 0.9 else 0.0
			if ratio >= 0.9:
				findings.append(Finding('warning', 'RESP-DUP', 1, f'{ratio:.0%} similar to {other.name}: compare the current request and operation receipts; similarity alone does not establish whether it was executed'))
	for target in against:
		target = Path(target)
		body = target.read_bytes().decode('utf-8')
		target_lines = body.splitlines()
		for no, raw in enumerate(text.splitlines(), 1):
			for sentence in re.split('(?<=[.!?])\\s+', raw):
				removal, replaced = (REMOVAL.search(sentence), REPLACED.search(sentence))
				if not removal and (not replaced):
					continue
				stop = len(sentence)
				if replaced and (not removal):
					stop = replaced.start()
				kept = KEPT.search(sentence)
				if kept:
					stop = min(stop, kept.start())
				for token in re.findall('`([^`]+)`', sentence[:stop]):
					token = token.replace('...', '').replace('…', '').strip()
					if len(token) < 3 or token.startswith('§'):
						continue
					needle = re.compile('(?<![\\w-])' + re.escape(token) + '(?!\\w)', re.I)
					hits = [i for i, l in enumerate(target_lines, 1) if needle.search(l)]
					if hits:
						findings.append(Finding('warning', 'RESP-CLAIM', no, f"claimed removed/replaced, but `{token}` remains in {target.name} at lines {', '.join(map(str, hits[:8]))}{(' …' if len(hits) > 8 else '')}", sentence[:100]))
	r = sorted(findings, key=lambda f: (f.line, f.rule))
	return r
def default_shell():
	configured = os.environ.get('DF_TEXT_BASH') or os.environ.get('CYGWIN_BASH') or settings().get('client_text', {}).get('bash')
	if configured:
		return configured
	if 'nt' == os.name:
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
	value = re.sub('^\\s*>\\s?', '', value).rstrip()
	value = re.sub('^\\s*(?:\\d+[.)]|[-*+])\\s+', '', value)
	value = re.sub('\\[([^\\]]+)\\]\\((?:<[^>]+>|[^)]*)\\)', '\\1', value)
	value = re.sub('(`+)(.*?)\\1', '\\2', value)
	r = '' if '<empty response>' == value else value
	return r
def command_blocks(text: str):
	lines = scan(text)
	blocks, index = ([], 0)
	while index < len(lines):
		if 'fence' != lines[index].kind or not re.match('^\\s*(?:`{3,}|~{3,})\\s*(bash|sh|shell)\\s*$', lines[index].raw):
			index += 1
			continue
		first = lines[index].no
		index += 1
		body = []
		while index < len(lines) and 'code' == lines[index].kind:
			body.append(lines[index].raw)
			index += 1
		closed = index < len(lines) and 'fence' == lines[index].kind
		if closed:
			index += 1
		cursor = index
		expected, presentation = ([], [])
		output_end = lines[index - 1].no if index else first
		while cursor < len(lines) and lines[cursor].kind in ('blank', 'quote', 'heading', 'anchor'):
			if 'quote' == lines[cursor].kind:
				presentation.append(lines[cursor].raw)
				expected.append(_plain(lines[cursor].raw))
				output_end = lines[cursor].no
			cursor += 1
		command = '\n'.join(body)
		blocks.append({'line': first, 'end': output_end, 'command': command, 'command_sha256': hashlib.sha256(command.encode('utf-8')).hexdigest(), 'expected': expected, 'presentation': '\n'.join(presentation), 'closed': closed})
	r = blocks
	return r
def changed_command_lines(text: str, previous: str | None=None):
	from collections import Counter
	old = Counter(((b['command_sha256'], tuple(b['expected'])) for b in command_blocks(previous or '')))
	changed = []
	for block in command_blocks(text):
		identity = (block['command_sha256'], tuple(block['expected']))
		if old[identity]:
			old[identity] -= 1
		else:
			changed.append(block['line'])
	r = changed
	return r
def _output_lines(value):
	lines = [line.rstrip() for line in value.splitlines()]
	while lines and (not lines[-1]):
		lines.pop()
	r = lines
	return r
def replay(text: str, *, shell=None, timeout=60, only=None, expected_exit=None, contracts=None):
	results, covered = ([], set())
	shell = shell or default_shell()
	selected = set(only) if None is not only else None
	contracts = contracts or {}
	for block in command_blocks(text):
		first = block['line']
		wanted = {line for line in selected or () if first <= line <= block['end']}
		if None is not selected and (not wanted):
			continue
		covered.update(wanted)
		contract = contracts.get(first, contracts.get(str(first), {}))
		wanted_exit = contract.get('exit', 0)
		if None is not expected_exit:
			wanted_exit = expected_exit.get(first, expected_exit.get(str(first), wanted_exit)) if isinstance(expected_exit, dict) else expected_exit
		if not isinstance(wanted_exit, int) or isinstance(wanted_exit, bool):
			raise ValueError(f'expected exit for line {first} must be an integer')
		record = {'line': first, 'end': block['end'], 'command_sha256': block['command_sha256'], 'shell': str(shell), 'expected_exit': wanted_exit, 'presentation': block['presentation']}
		if not block['closed']:
			results.append({**record, 'status': 'error', 'error': 'unclosed command fence'})
			continue
		expected = _output_lines(contract['stdout']) if 'stdout' in contract else _output_lines('\n'.join(block['expected']))
		if not block['presentation'] and 'stdout' not in contract:
			results.append({**record, 'status': 'no-quoted-output'})
			continue
		try:
			environment = os.environ.copy()
			if Path(shell).is_absolute():
				environment['PATH'] = str(Path(shell).parent) + os.pathsep + environment.get('PATH', '')
			done = subprocess.run([shell, '-e', '-o', 'pipefail', '-c', block['command']], capture_output=True, timeout=timeout, encoding='utf-8', errors='replace', env=environment)
			actual = _output_lines(done.stdout)
		except (OSError, subprocess.TimeoutExpired) as exc:
			results.append({**record, 'status': 'error', 'error': str(exc)})
			continue
		status = 'exit-mismatch' if done.returncode != wanted_exit else 'match' if expected == actual else 'mismatch'
		if 'match' == status and 'stderr' in contract and (contract['stderr'] != done.stderr):
			status = 'mismatch'
		results.append({**record, 'status': status, 'expected': expected, 'actual': actual, 'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
	for line in sorted((selected or set()) - covered):
		results.append({'line': line, 'status': 'uncovered', 'error': 'selected line is not in a Bash block or its quoted output'})
	r = results
	return r
