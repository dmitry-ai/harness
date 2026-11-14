# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Generalize keyed section numbering (@key), section-reference validation, and profile dispatch across article.py, proposal.py, text_workflow.py, text_claims.py, and text_cli.py":
# https://github.com/dmitry-ai/harness/issues/70
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Mapping
from .text_core import Finding, Line, author_text, check_code, check_prose, detect_language, external_section_ref, find_bans, load_lexicon, scan, transform_prose
from .text_sections import AddressedSection, KEYED_REF as KEY_REF, PROPOSAL_NUMBER_KEY, build_render_report, close_spans, reassemble_lines as _reassemble, rewrite_keyed_prose, validate_ref_range
PREFIX = '(?P<prefix>(?:[^\\w\\s@#]+\\s+)?)'
NUMBERED = re.compile(PREFIX + '(?P<number>\\d+(?:\\.\\d+)*)\\.(?P<gap>[ \\t]+)(?P<body>.*)$')
KEYED = re.compile(PREFIX + '@(?P<name>[\\w]+(?:[.\\-][\\w]+)*)(?P<gap>[ \\t]+)(?P<body>.*)$')
REF = re.compile('(?<![\\w§])(?P<marks>§§?)(?P<space>[ \\t]*)(?P<start>\\d+(?:\\.\\d+)*)(?:[ \\t]*(?P<dash>[-–—])[ \\t]*§?(?P<end>\\d+(?:\\.\\d+)*))?(?!\\w|\\.\\d)')
MARKDOWN_LINK = re.compile('!?\\[[^\\]\\n]*\\]\\(<?(?:https?://|#)[^\\n]*?\\)')
URL = re.compile('https?://[^\\s<>`]+')
@dataclass
class ProposalBlock(AddressedSection):
	name: str
	number: tuple[int, ...]
	line: int
	end: int
	prefix: str = ''
	body: str = ''
	parent: 'ProposalBlock | None' = None
	gap: str = ' '
	part: str = ''
	children: list = field(default_factory=list)
def _lines(value: str | list[Line]) -> list[Line]:
	return scan(value) if isinstance(value, str) else value
def _parent_name(name: str, known: Mapping[str, ProposalBlock]) -> str | None:
	segments = name.split('.')
	if 1 == len(segments):
		r = None
	else:
		parent = '.'.join(segments[:-1])
		r = '.'.join(segments[:-2]) if parent not in known and '0' == segments[-2] and ('.'.join(segments[:-2]) in known) else parent
	return r
def parse_blocks(value: str | list[Line], findings: list[Finding] | None=None, *, keyed: bool=False) -> list[ProposalBlock]:
	lines = _lines(value)
	findings = findings if None is not findings else []
	r, known = ([], {})
	pattern = KEYED if keyed else NUMBERED
	for line in lines:
		if 'prose' != line.kind:
			continue
		match = pattern.fullmatch(line.raw)
		if None is match:
			if keyed and NUMBERED.fullmatch(line.raw):
				findings.append(Finding('error', 'KEY-NUMBERED', line.no, 'use @key in the keyed view', line.raw))
			continue
		name = match.group('name' if keyed else 'number')
		number = () if keyed else tuple((int(n) for n in name.split('.')))
		block = ProposalBlock(name, number, line.no, len(lines), match.group('prefix'), match.group('body'), gap=match.group('gap'))
		if name in known:
			findings.append(Finding('error', 'KEY-DUP' if keyed else 'PROPOSAL-DUP', line.no, f"duplicate {('@' if keyed else '§')}{name}", line.raw))
		parent = _parent_name(name, known)
		if None is not parent:
			block.parent = known.get(parent)
			if None is block.parent:
				findings.append(Finding('error', 'KEY-PARENT' if keyed else 'PROPOSAL-PARENT', line.no, f'no preceding parent {parent}', line.raw))
		known[name] = block
		r.append(block)
	close_spans(r, lines)
	return r
parse_sections = parse_blocks
parse = parse_blocks
def _number_refs(raw: str):
	author = author_text(raw)
	return (match for match in REF.finditer(author) if not external_section_ref(author, match))
def _check_sequence(blocks, findings, profile):
	groups = {}
	for block in blocks:
		number = block.number
		if not number:
			continue
		if re.search('(?<!\\s)' + re.escape(block.key) + '\\.\\s+', author_text(block.body)):
			findings.append(Finding('error', 'PROPOSAL-CONCAT', block.line, f'a second {block.key}. point is joined onto the same line; remove the duplicate or separate it', block.body))
		if 'flat' == profile.get('numbering') and 1 < len(number):
			findings.append(Finding('error', 'PROPOSAL-FLAT', block.line, 'nested point in the selected flat profile', block.key))
		prefix, ordinal = (number[:-1], number[-1])
		siblings = groups.setdefault(prefix, [])
		if 0 == ordinal and prefix:
			siblings.append(ordinal)
			continue
		expected = (int(profile.get('start', 1)) if not prefix else 1) + sum((1 for n in siblings if 0 < n))
		if ordinal != expected:
			findings.append(Finding('error', 'PROPOSAL-SEQ', block.line, f'§{block.key} breaks the sequence (expected {expected} at this level)'))
		siblings.append(ordinal)
def _check_references(lines, blocks, findings, profile):
	known = {block.key for block in blocks} | {str(n) for n in profile.get('reference_targets', [])}
	for line in lines:
		if line.kind not in ('prose', 'heading'):
			continue
		for match in _number_refs(line.raw):
			marks, start, dash, end = match.group('marks', 'start', 'dash', 'end')
			if match.group('space'):
				findings.append(Finding('error', 'PROPOSAL-REF-SPACE', line.no, 'write the point number immediately after §', match.group(0)))
			if end and ('§§' != marks or '-' != dash) or (not end and '§§' == marks):
				findings.append(Finding('error', 'PROPOSAL-RANGE', line.no, 'use §N for one point and §§N-M for a range', match.group(0)))
			validate_ref_range(start, end, known, findings, line.no, match.group(0), order_key=lambda k: tuple(map(int, k.split('.'))), order_rule='PROPOSAL-RANGE-ORDER', order_msg='range endpoints must be in document order', check_dense=True)
		if KEY_REF.search(author_text(line.raw)):
			findings.append(Finding('error', 'KEY-UNRENDERED', line.no, 'render keyed references before using the proposal', line.raw))
def _format_checks(lines, findings, profile):
	seen_urls = {}
	for line in lines:
		if line.kind in ('code', 'quote', 'comment'):
			continue
		raw = line.raw
		author = author_text(raw)
		if 'heading' == line.kind:
			findings.append(Finding('error', 'PROPOSAL-HEADING', line.no, 'use plain numbered points in the Upwork proposal', raw))
		elif 'anchor' == line.kind:
			findings.append(Finding('error', 'PROPOSAL-ANCHOR', line.no, 'HTML anchors belong to article format; use §N in the proposal', raw))
		if 'fence' == line.kind and raw[:1].isspace():
			findings.append(Finding('error', 'PROPOSAL-CODE-INDENT', line.no, 'place the code fence at the left margin', raw))
		if 'prose' != line.kind:
			continue
		if MARKDOWN_LINK.search(raw):
			findings.append(Finding('error', 'PROPOSAL-MARKDOWN-LINK', line.no, 'use a plain URL in the Upwork field', raw))
		if 'technical' == profile.get('voice', 'technical') and re.search('\\bI\\b', author):
			findings.append(Finding('error', 'PROPOSAL-FIRST-PERSON', line.no, 'name the system action or the required step instead of I', raw))
		if re.search('(?i)\\bjourneys?\\b', author):
			findings.append(Finding('error', 'PROPOSAL-JOURNEY', line.no, 'name the precise session/event history', raw))
		if re.search('(?i)\\b(?:Tag|Rule)\\s+\\d+\\b', author):
			findings.append(Finding('warning', 'PROPOSAL-INTERNAL-INDEX', line.no, 'identify the object as the client sees it in the interface', raw))
		for match in URL.finditer(raw):
			url = match.group(0).rstrip('.,;!')
			if url not in seen_urls:
				seen_urls[url] = line.no
			else:
				findings.append(Finding('error', 'PROPOSAL-DUP-URL', line.no, f'URL already used at line {seen_urls[url]}; cite its § point', url))
def lint_text(text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, profile: Mapping | None=None) -> list[Finding]:
	if kind not in (None, 'proposal'):
		raise ValueError('proposal.lint_text accepts only kind=proposal')
	profile = dict(profile or {})
	if profile.get('numbering', 'nested') not in ('flat', 'nested'):
		raise ValueError('proposal numbering must be flat or nested')
	if profile.get('voice', 'technical') not in ('technical', 'offer'):
		raise ValueError('proposal voice must be technical or offer')
	lines = scan(text)
	r: list[Finding] = []
	blocks = parse_blocks(lines, r)
	if not blocks:
		r.append(Finding('error', 'PROPOSAL-EMPTY', 1, 'the proposal needs at least one plain numbered point'))
	_check_sequence(blocks, r, profile)
	_check_references(lines, blocks, r, profile)
	_format_checks(lines, r, profile)
	check_prose(lines, 'proposal', lang or detect_language(text), r, lexicon if None is not lexicon else load_lexicon(), bans if None is not bans else find_bans(Path(path) if path else None))
	check_code(lines, r)
	return r
def to_source(text: str) -> str:
	lines = scan(text)
	by_line = {block.line: block for block in parse_blocks(lines)}
	out = []
	for line in lines:
		raw = line.raw
		if line.no in by_line:
			block = by_line[line.no]
			raw = f'{block.prefix}@{block.name}{block.gap}{block.body}'
		if 'prose' == line.kind:
			def replace(segment):
				def ref(match):
					if external_section_ref(segment, match):
						r = match.group()
					else:
						start, end = match.group('start', 'end')
						r = f'§§@{start}-@{end}' if end else f'§@{start}'
					return r
				return REF.sub(ref, segment)
			raw = transform_prose(raw, replace)
		out.append(raw)
	return _reassemble(text, lines, out)
def render(source: str, previous: str | None=None):
	lines = scan(source)
	findings: list[Finding] = []
	external_changes = []
	blocks = parse_blocks(lines, findings, keyed=True)
	if not blocks:
		findings.append(Finding('error', 'KEY-EMPTY', 1, 'the keyed proposal has no @points'))
	by_name, by_line, groups, mapping = ({}, {}, {}, {})
	closed_paths, active_path = (set(), [])
	for block in blocks:
		parts = block.name.split('.')
		path = ['.'.join(parts[:index]) for index in range(1, len(parts) + 1)]
		shared = 0
		while shared < min(len(path), len(active_path)) and path[shared] == active_path[shared]:
			shared += 1
		closed_paths.update(active_path[shared:])
		if any((name in closed_paths for name in path)):
			findings.append(Finding('error', 'KEY-NONCONTIGUOUS', block.line, 'move a parent together with all its child points', block.name))
		active_path = path
		parent_name = _parent_name(block.name, by_name)
		parent_number = ()
		if parent_name and parent_name in by_name:
			parent_number = by_name[parent_name].number
			if '0' == parts[-2] and parent_name != '.'.join(parts[:-1]):
				parent_number = (*parent_number, 0)
		siblings = groups.setdefault(parent_number, 0)
		ordinal = 0 if 1 < len(parts) and '0' == parts[-1] else siblings + 1
		if ordinal:
			groups[parent_number] = ordinal
		block.number = (*parent_number, ordinal)
		by_name[block.name] = by_line[block.line] = block
		mapping[block.name] = block.key
	out = []
	for line in lines:
		raw = line.raw
		if 'prose' == line.kind and any(_number_refs(raw)):
			findings.append(Finding('error', 'KEY-NUMERIC-REF', line.no, 'use §@key in the keyed view; a number may bind to a different point after reordering', raw))
		if line.no in by_line:
			block = by_line[line.no]
			raw = f'{block.prefix}{block.key}.{block.gap}{block.body}'
		if 'prose' == line.kind:
			raw = rewrite_keyed_prose(raw, line.no, mapping, findings, external_changes, format_ref=lambda _m, s, e: f'§§{mapping[s]}-{mapping[e]}' if e else f'§{mapping[s]}')
		out.append(raw)
	rendered = _reassemble(source, lines, out)
	report = build_render_report(mapping, PROPOSAL_NUMBER_KEY, external_changes, [block.key for block in parse_blocks(previous)] if None is not previous else [])
	final_lines = scan(rendered)
	_check_references(final_lines, parse_blocks(final_lines), findings, {})
	return (rendered, report, findings)
def lint_fields(fields: Mapping[str, str], limits: Mapping[str, int], *, count_mode: str='utf16') -> list[Finding]:
	if count_mode not in ('utf16', 'unicode'):
		raise ValueError('character count mode must be utf16 or unicode')
	r = []
	for name, limit in limits.items():
		if name not in fields:
			r.append(Finding('error', 'PROPOSAL-FIELD-MISSING', 1, f'missing Upwork field {name}'))
			continue
		if not isinstance(limit, int) or isinstance(limit, bool) or 1 > limit:
			raise ValueError(f'positive integer character limit required for {name}')
		count = len(fields[name].encode('utf-16-le')) // 2 if 'utf16' == count_mode else len(fields[name])
		if count > limit:
			r.append(Finding('error', 'PROPOSAL-FIELD-LIMIT', 1, f'{name}: {count} characters exceeds its {limit} character limit'))
	for name in fields.keys() - limits.keys():
		r.append(Finding('error', 'PROPOSAL-FIELD-LIMIT-MISSING', 1, f'no confirmed character limit for Upwork field {name}'))
	return r
