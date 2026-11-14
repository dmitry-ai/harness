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
import json
from pathlib import Path
import re
from .text_core import ABBREVIATIONS, ANCHOR, ARROW_CONNECTIVE, BANS, BOLD_LEADIN, FENCE, Finding, HEADING, INLINE_LITERAL, KEPT, LEXICON, LIST_MARK, Line, REMOVAL, REPLACED, THRESHOLDS, _excerpt, _plain, author_text, bold_spans, changed_command_lines, check_code, check_markdown_lists, check_prose, check_response, clean, command_blocks, default_shell, detect_language, external_section_ref, find_bans, load_lexicon, normalize_external_refs, normalized, replay, scan, sentences, transform_prose
from .text_sections import ANCHOR_LINK, ARTICLE_NUMBER_KEY, AddressedSection, KEYED_REF as SOURCE_REF, PART, assign_tree_numbers, build_render_report, close_spans as _close, lint_document, part_at, rewrite_keyed_prose, section_at, validate_ref_range
NUMBERED = re.compile('^(\\d+(?:\\.\\d+)*)\\.?(?:\\s+(.*))?$')
KEYED = re.compile('^@([\\w.\\-]+)(?:\\s+(.*))?$')
SECTION_LABEL = re.compile('^§{1,2}\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*)(?:\\s*[-–]\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*))?$')
BARE_REF = re.compile('(?<![\\w@])(§{1,2})\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*)(?:\\s*[-–]\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*))?(?!\\w)')
SOURCE_META = re.compile('^\\s*<!-- df-article: (\\{.*\\}) -->\\s*$')
@dataclass
class Section(AddressedSection):
	part: str
	number: tuple
	title: str | None
	line: int
	level: int
	parent: 'Section | None' = None
	children: list = field(default_factory=list)
	end: int = 0
	anchor: str | None = None
	name: str = ''
def _iter_headings(lines: list[Line]):
	part = ''
	for index, line in enumerate(lines):
		if 'heading' != line.kind:
			continue
		hashes, text = HEADING.match(line.raw).groups()
		if 1 != len(hashes):
			yield (index, line, len(hashes), text, part)
		else:
			match = PART.match(text)
			part = match.group(1) if match else part
def detect_kind(path: Path | None, text: str) -> str:
	return 'response' if None is not path and 'res' == path.parent.name else 'article'
def parse_sections(lines: list[Line], findings: list[Finding] | None=None):
	findings = findings if None is not findings else []
	r, by_key, roots = ([], {}, {})
	for index, line, level, text, part in _iter_headings(lines):
		match = NUMBERED.match(text)
		if not match:
			continue
		number = tuple((int(x) for x in match.group(1).split('.')))
		section = Section(part, number, match.group(2), line.no, level)
		if level != len(number) + 1:
			findings.append(Finding('warning', 'STRUCT-LEVEL', line.no, f"heading level {level} does not match number depth {len(number)} (expected {'#' * (len(number) + 1)})", line.raw))
		section.parent = by_key.get((part, number[:-1])) if 1 < len(number) else None
		if 1 < len(number) and None is section.parent:
			findings.append(Finding('error', 'STRUCT-PARENT', line.no, f"no parent section {'.'.join(map(str, number[:-1]))}", line.raw))
		siblings = section.parent.children if section.parent else roots.setdefault(part, [])
		if number[-1] != len(siblings) + 1:
			findings.append(Finding('error', 'STRUCT-SEQ', line.no, f'number {section.dotted} breaks the sequence (expected …{len(siblings) + 1})', line.raw))
		if (part, number) in by_key:
			findings.append(Finding('error', 'STRUCT-DUP', line.no, f'duplicate section {section.key}', line.raw))
		by_key[part, number] = section
		siblings.append(section)
		following = next((x for x in lines[index + 1:] if 'blank' != x.kind), None)
		if None is not following and 'anchor' == following.kind:
			section.anchor = ANCHOR.match(following.raw).group(1)
		r.append(section)
	_close(r, lines)
	return r
def parse_keyed(lines: list[Line], findings: list[Finding]):
	sections, roots = ([], {})
	for _, line, level, text, part in _iter_headings(lines):
		match = KEYED.match(text)
		if not match:
			if NUMBERED.match(text):
				findings.append(Finding('error', 'KEY-NUMBERED', line.no, 'numbered heading inside a keyed view: use `@key`', line.raw))
			continue
		section = Section(part, (), match.group(2), line.no, level, name=match.group(1))
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
	return (sections, roots)
def check_structure(lines, sections, findings):
	parts = [m.group(1) for line in lines if 'heading' == line.kind and '#' == HEADING.match(line.raw).group(1) for m in (PART.match(HEADING.match(line.raw).group(2)),) if m]
	if ['I', 'II'] != parts:
		findings.append(Finding('error', 'STRUCT-PARTS', 1, 'article requires exactly two ordered parts: # I. Analysis and # II. Recommendations'))
	if not sections:
		findings.append(Finding('error', 'STRUCT-EMPTY', 1, 'article has no addressed numbered sections'))
	for line in lines:
		if line.kind not in ('prose', 'quote', 'fence', 'code'):
			continue
		section = section_at(sections, line.no)
		if None is section or section.part != part_at(lines, line.no):
			findings.append(Finding('error', 'STRUCT-UNADDRESSED', line.no, 'article content must belong to a numbered section', line.raw[:80]))
	anchors = {}
	for line in lines:
		if 'anchor' == line.kind:
			name = ANCHOR.match(line.raw).group(1)
			if name in anchors:
				findings.append(Finding('error', 'ANCHOR-DUP', line.no, f'duplicate anchor {name}', line.raw))
			anchors[name] = line.no
	for section in sections:
		if None is section.anchor:
			findings.append(Finding('error', 'ANCHOR-MISSING', section.line, f"expected <a name='{section.key}'></a> right after the heading"))
		elif section.anchor not in (section.key, '§' + section.key):
			findings.append(Finding('error', 'ANCHOR-MISMATCH', section.line, f'anchor {section.anchor} does not match section {section.key}'))
		title = section.title
		if title:
			plain = re.sub('\\(\\s*\\d+[^)]*\\)', '', clean(title)).strip()
			words = re.findall("[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451][\\w'’-]*", plain)
			if ',' in plain and re.search('\\band\\b|&|\\b\\u0438\\b', plain):
				findings.append(Finding('error', 'HEADING-ENUM', section.line, 'heading enumerates several topics: one section — one claim; split it', title))
			if len(words) > THRESHOLDS['heading_words']:
				findings.append(Finding('warning', 'HEADING-LONG', section.line, f'{len(words)} words in a heading; 2725 uses a bare number or a short group label', title))
			capital = [w for w in words[1:] if 3 < len(w) and w[0].isupper() and (not w.isupper())]
			long_words = [w for w in words[1:] if 3 < len(w)]
			if 2 <= len(capital) and len(capital) * 2 > len(long_words):
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
				label_part = parsed.group(1) or part_at(lines, line.no)
				expected = f'{label_part}.{parsed.group(2)}' if label_part else parsed.group(2)
				if expected != target.removeprefix('§'):
					findings.append(Finding('error', 'REF-LABEL', line.no, f'label points to {expected}, link goes to #{target}', match.group(0)))
				if parsed.group(4):
					end_part = parsed.group(3) or label_part
					endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
					validate_ref_range(expected, endpoint, by_key, findings, line.no, match.group(0), order_key=lambda k: by_key[k].line, allow_same=True, start_checked=True, end_prefix='range endpoint §')
				if 'heading' != line.kind and (not any((a < match.start() < b for a, b in spans))):
					findings.append(Finding('warning', 'REF-BOLD', line.no, 'section reference is not bold: **[§N](#P.N)**', match.group(0)))
		for match in BARE_REF.finditer(visible):
			if not external_section_ref(visible, match) and (not any((start <= match.start() < end for start, end in linked_spans))):
				findings.append(Finding('error', 'REF-BARE', line.no, 'article section reference needs a working anchor link', match.group(0)))
		if re.search('§§?@|\\]\\(#@', visible):
			findings.append(Finding('error', 'KEY-UNRENDERED', line.no, 'unrendered keyed reference remains in the numbered article', line.raw[:80]))
	check_group_counts(lines, sections, findings)
def check_group_counts(lines, sections, findings):
	for section in sections:
		match = re.search('\\((\\d+)(?:\\s+[^()]*)?\\)\\s*$', section.title or '')
		if not match:
			continue
		expected = int(match.group(1))
		own = [line for line in lines if section.line < line.no <= section.end]
		items = [line for line in own if line.kind in ('prose', 'quote') and LIST_MARK.match(re.sub('^\\s*>\\s?', '', line.raw))]
		actual = len(items) if items else None
		if None is actual and section.children:
			child_counts = [re.search('\\((\\d+)(?:\\s+[^()]*)?\\)\\s*$', child.title or '') for child in section.children]
			if all(child_counts):
				actual = sum((int(child.group(1)) for child in child_counts))
		if None is not actual and actual != expected:
			findings.append(Finding('error', 'GROUP-COUNT', section.line, f'heading declares {expected} objects, displayed group contains {actual}', section.title or ''))
def check_graph(lines, sections, findings):
	if not {'I', 'II'} <= {s.part for s in sections}:
		return
	by_key = {s.key: s for s in sections}
	refs = {s.key: set() for s in sections}
	external = {s.key: False for s in sections}
	primary = {s.key: False for s in sections}
	for line in lines:
		section = section_at(sections, line.no)
		if None is section or line.kind in ('heading', 'anchor'):
			continue
		if line.kind in ('code', 'quote'):
			primary[section.key] = True
		if 'prose' == line.kind:
			visible = author_text(line.raw)
			for match in ANCHOR_LINK.finditer(visible):
				target = match.group(2).removeprefix('§')
				if target in by_key:
					refs[section.key].add(target)
				parsed = SECTION_LABEL.match(match.group(1).replace('**', '').strip())
				if parsed and parsed.group(4) and (target in by_key):
					end_part = parsed.group(3) or parsed.group(1) or section.part
					endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
					if endpoint in by_key:
						refs[section.key].update((s.key for s in sections if by_key[target].line <= s.line <= by_key[endpoint].line))
			if re.search('\\]\\(<?https?://|https?://', line.raw):
				external[section.key] = primary[section.key] = True
	used, expanded = (set(), set())
	queue = [(s.key, False) for s in sections if 'II' == s.part]
	while queue:
		key, expand = queue.pop()
		node = by_key[key]
		if expand and key not in expanded:
			expanded.add(key)
			queue.extend(((child.key, True) for child in node.children))
		for member in node.lineage():
			if member.key not in used:
				used.add(member.key)
				queue.extend(((target, True) for target in refs[member.key]))
	for section in sections:
		own_body = [line for line in lines if section.line < line.no <= section.end and line.kind in ('prose', 'quote', 'code')]
		if 'I' == section.part and section.key not in used and (own_body or not section.children):
			findings.append(Finding('note', 'GRAPH-ORPHAN', section.line, f'§{section.key} is not a premise of any recommendation (directly or transitively): keep it only if it serves the goal of the text'))
	grounded, changed = ({}, True)
	while changed:
		changed = False
		for section in sections:
			if 'II' == section.part and (not grounded.get(section.key)) and any((external[s.key] or any((t.startswith('I.') or grounded.get(t) for t in refs[s.key])) for s in section.lineage())):
				grounded[section.key] = changed = True
	for section in sections:
		if 'I' == section.part and (not section.children):
			body = [l for l in lines if section.line < l.no <= section.end and l.kind not in ('blank', 'anchor')]
			has_proof = any((l.kind in ('code', 'fence', 'quote') for l in body)) or external[section.key] or refs[section.key] or (section.parent and any((l.kind in ('code', 'fence') for l in lines if section.parent.line < l.no < section.line)))
			if not has_proof:
				findings.append(Finding('note', 'PROOF-MISSING', section.line, f'§{section.key} states a fact without a command, quote, link or premise'))
		elif 'II' == section.part:
			if not section.children and (not grounded.get(section.key)):
				findings.append(Finding('warning', 'GRAPH-BASELESS', section.line, f'recommendation §{section.key} has no premise in part I and no documentation link'))
			for line in (l for l in lines if section.line < l.no <= section.end and 'prose' == l.kind):
				visible = author_text(line.raw).strip()
				if re.match('^(?:If|\\u0415\\u0441\\u043b\\u0438|\\u0412 \\u0441\\u043b\\u0443\\u0447\\u0430\\u0435 \\u0435\\u0441\\u043b\\u0438)\\b', visible, re.I):
					targets = [m.group(2).removeprefix('§') for m in ANCHOR_LINK.finditer(visible.split('→', 1)[0])]
					has_part2 = any((t.startswith('II.') or (t in by_key and 'II' == by_key[t].part) for t in targets))
					has_part1 = any((t.startswith('I.') or (t in by_key and 'I' == by_key[t].part) for t in targets))
					if not has_part2:
						if not has_part1:
							findings.append(Finding('warning', 'GRAPH-CONDITIONAL-STEP', line.no, f'conditional recommendation §{section.key} has no Part II diagnostic premise; branch from an explicit measurement step', line.raw[:100]))
						else:
							findings.append(Finding('error', 'GRAPH-CONDITIONAL-STEP', line.no, f'conditional recommendation §{section.key} conditions on an established Part I fact; it must branch from a Part II diagnostic step (like §II.12.2 from §II.12.1 in 2725.md)', line.raw[:100]))
	grounded = {s.key for s in sections if any((primary[a.key] for a in s.lineage()))}
	changed = True
	while changed:
		additions = {key for key, targets in refs.items() if targets and targets <= grounded}
		additions.update((s.key for s in sections if s.children and all((child.key in grounded for child in s.children))))
		changed = not additions <= grounded
		grounded.update(additions)
	counter, stack, on_stack, indexes, low = (0, [], set(), {}, {})
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
		if low[key] == indexes[key]:
			component = []
			while True:
				member = stack.pop()
				on_stack.remove(member)
				component.append(member)
				if member == key:
					break
			if (1 < len(component) or key in refs[key]) and (not any((member in grounded for member in component))):
				first = min((by_key[member] for member in component), key=lambda node: node.line)
				findings.append(Finding('error', 'GRAPH-CYCLE', first.line, 'circular premises without primary evidence: ' + ', '.join(('§' + member for member in sorted(component)))))
	for key in refs:
		if key not in indexes:
			visit(key)
def check_proposal(lines, findings):
	findings.extend(lint_document('\n'.join((line.raw for line in lines)), 'proposal', lexicon=[], bans=[]))
def check_link_style(lines, findings, link_style):
	if 'formatted' != link_style:
		return
	from .markdown_links import parser, inline_links, display_address
	engine, environment = (parser(), {})
	engine.parse('\n'.join((line.raw for line in lines)), environment)
	definitions = {index for item in environment.get('references', {}).values() for index in range(*item.get('map', (0, 0)))}
	for line in lines:
		if line.kind not in ('prose', 'heading') or line.no - 1 in definitions:
			continue
		authored = INLINE_LITERAL.sub('', line.raw)
		tokens = engine.parseInline(authored, environment)[0].children or []
		for href, label in inline_links(tokens):
			if href.startswith(('https://', 'http://')):
				try:
					actual = display_address(label if '://' in label else 'https://' + label)
					expected = display_address(href)
				except ValueError:
					actual, expected = (None, href)
				if actual != expected:
					findings.append(Finding('error', 'LINK-LABEL', line.no, 'formatted label must preserve the destination domain, path, query and fragment', label))
		protected = [match.span() for match in INLINE_LITERAL.finditer(line.raw)]
		protected.extend((match.span() for match in re.finditer('(?<!\\w)"[^"\\n]+"', line.raw)))
		protected.extend((match.span() for match in re.finditer('!?\\[[^\\]\\n]*\\]\\((?:<?https?://[^\\s>)]*>?)\\)|<https?://[^>\\n]+>', line.raw)))
		for match in re.finditer('https?://[^\\s<>]+', line.raw):
			if not any((start <= match.start() < end for start, end in protected)):
				findings.append(Finding('error', 'LINK-BARE', line.no, 'the selected article profile requires formatted external links', match.group(0)))
def lint_text(text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, link_style=None) -> list[Finding]:
	kind = kind or detect_kind(path, text)
	if 'proposal' == kind:
		r = lint_document(text, 'proposal', path=path, lang=lang, lexicon=lexicon, bans=bans)
	else:
		lines = scan(text)
		findings: list[Finding] = []
		if 'article' == kind:
			sections = parse_sections(lines, findings)
			check_structure(lines, sections, findings)
			check_graph(lines, sections, findings)
			check_code(lines, findings)
			check_markdown_lists(lines, findings)
			check_link_style(lines, findings, link_style)
		check_prose(lines, kind, lang or detect_language(text), findings, load_lexicon() if None is lexicon else lexicon, find_bans(path) if None is bans else bans)
		r = sorted(findings, key=lambda f: (f.line, 'error' != f.severity, f.rule))
	return r
def to_source(text: str) -> str:
	lines = scan(text)
	sections = parse_sections(lines, [])
	by_line = {s.line: s for s in sections}
	aliases = {s.anchor or s.key: s.key for s in sections}
	standalone = {ANCHOR.match(line.raw).group(1) for line in lines if 'anchor' == line.kind} - set(aliases)
	anchor_lines = {next((x.no for x in lines if x.no > s.line and 'blank' != x.kind), None) for s in sections if s.anchor}
	prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in sections}
	default = '§' if prefixes and all(prefixes.values()) else ''
	overrides = {key: prefix for key, prefix in prefixes.items() if prefix != default}
	metadata = {'anchor_prefix': default, **({'anchor_prefixes': overrides} if overrides else {})}
	out = ['<!-- df-article: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')) + ' -->']
	for line in lines:
		if line.no in by_line:
			section = by_line[line.no]
			title = f' {section.title}' if section.title else ''
			out.append('#' * (len(section.number) + 1) + f' @{section.key}{title}')
		elif line.no in anchor_lines and 'anchor' == line.kind:
			continue
		elif line.kind not in ('prose', 'heading'):
			out.append(line.raw)
		else:
			current = part_at(lines, line.no)
			def replace(match):
				label, target = match.groups()
				key = aliases.get(target, target.removeprefix('§'))
				parsed = SECTION_LABEL.match(label.replace('**', '').strip())
				if not parsed or not label.strip().startswith('§'):
					r = match.group(0) if target in standalone else f'[{label}](#@{key})'
				else:
					marks = '§§' if label.strip().startswith('§§') else '§'
					if not parsed.group(4):
						r = f'{marks}@{key}'
					else:
						end_part = parsed.group(3) or parsed.group(1) or current
						endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
						r = f'{marks}@{key}-@{endpoint}'
				return r
			def bare(match):
				if external_section_ref(match.string, match):
					r = match.group(0)
				else:
					marks, start_part, start_number, end_part, end_number = match.groups()
					start_part = start_part or current
					start = f'{start_part}.{start_number}' if start_part else start_number
					if not end_number:
						r = f'{marks}@{start}'
					else:
						end_part = end_part or start_part
						endpoint = f'{end_part}.{end_number}' if end_part else end_number
						r = f'{marks}@{start}-@{endpoint}'
				return r
			out.append(transform_prose(line.raw, lambda value: BARE_REF.sub(bare, ANCHOR_LINK.sub(replace, value))))
	return '\n'.join(out) + ('\n' if text.endswith('\n') else '')
def render(source: str, previous: str | None=None):
	lines = scan(source)
	findings: list[Finding] = []
	external_changes = []
	metadata = {}
	for line in lines:
		match = SOURCE_META.match(line.raw) if 'comment' == line.kind else None
		if match:
			try:
				value = json.loads(match.group(1))
				if not isinstance(value, dict) or value.get('anchor_prefix', '') not in ('', '§') or any((prefix not in ('', '§') for prefix in value.get('anchor_prefixes', {}).values())):
					raise ValueError('anchor prefix must be empty or §')
				metadata.update(value)
			except (ValueError, TypeError, AttributeError) as exc:
				findings.append(Finding('error', 'KEY-METADATA', line.no, str(exc)))
	sections, roots = parse_keyed(lines, findings)
	numbers, mapping = assign_tree_numbers(roots, findings)
	if not sections:
		findings.append(Finding('error', 'KEY-EMPTY', 1, 'keyed source has no addressed sections'))
	old_sections = parse_sections(scan(previous)) if None is not previous else []
	old_prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in old_sections}
	default_prefix = metadata.get('anchor_prefix', '§' if old_prefixes and all(old_prefixes.values()) else '')
	prefixes = metadata.get('anchor_prefixes', {})
	anchors = {key: prefixes.get(key, old_prefixes.get(key, default_prefix)) + number for key, number in mapping.items()}
	out = []
	for line in lines:
		if 'comment' == line.kind and SOURCE_META.match(line.raw):
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
			part, _, number = anchor.partition('.') if re.match('^[IVXLC]+\\.', anchor) else ('', '', anchor)
			return number if part == current else anchor
		def format_ref(marks, start, end):
			left = label(mapping[start])
			return f'[{marks}{left}-{label(mapping[end])}](#{anchors[start]})' if end else f'[{marks}{left}](#{anchors[start]})'
		out.append(rewrite_keyed_prose(line.raw, line.no, mapping, findings, external_changes, format_ref=format_ref, anchors=anchors, dangling_hint=' (deleted premise: delete or re-ground the dependent claim)'))
	markdown = '\n'.join(out) + ('\n' if source.endswith('\n') else '')
	report = build_render_report(mapping, ARTICLE_NUMBER_KEY, external_changes, [s.key for s in old_sections] if None is not previous else None)
	rendered_lines = scan(markdown)
	reference_findings = []
	check_structure(rendered_lines, parse_sections(rendered_lines), reference_findings)
	findings.extend((f for f in reference_findings if f.rule in ('REF-DANGLING', 'REF-LABEL', 'REF-RANGE', 'REF-BARE', 'KEY-UNRENDERED', 'ANCHOR-DUP')))
	return (markdown, report, findings)
def render_map(source: str, markdown: str | None=None):
	source_sections, _ = parse_keyed(scan(source), [])
	if None is markdown:
		markdown, _, _ = render(source)
	rendered = parse_sections(scan(markdown))
	return [{'key': original.name, 'number': current.key, 'part': current.part, 'anchor': current.anchor, 'source': original.span_dict(), 'rendered': current.span_dict()} for original, current in zip(source_sections, rendered)]
def main(argv=None) -> int:
	from .text_cli import main as common_main
	return common_main(argv, default_kind='article')
