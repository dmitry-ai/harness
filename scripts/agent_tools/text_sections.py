# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Generalize keyed section numbering (@key), section-reference validation, and profile dispatch across article.py, proposal.py, text_workflow.py, text_claims.py, and text_cli.py":
# https://github.com/dmitry-ai/harness/issues/70
from __future__ import annotations
import re
from urllib.parse import unquote
from .text_core import Finding, HEADING, Line, external_section_ref, normalize_external_refs, scan, transform_prose
ANCHOR_LINK = re.compile('\\[([^\\]\\n]*)\\]\\(#([^)\\s]+)\\)')
ARTICLE_NUMBER_KEY = re.compile('^(?:[IVXLC]+\\.)?\\d+(?:\\.\\d+)*$')
KEYED_REF = re.compile('(?<![\\w§])(?P<marks>§§?)@(?P<start>[\\w.\\-]+?)(?:-@(?P<end>[\\w.\\-]+?))?(?=[^\\w.\\-]|\\.(?:\\s|$)|$)')
PART = re.compile('^([IVXLC]+)\\.\\s+\\S')
PROPOSAL_NUMBER_KEY = re.compile('^\\d+(?:\\.\\d+)*$')
TEXT_KINDS = ('article', 'proposal', 'letter')
class AddressedSection:
	def descendants(self):
		for child in self.children:
			yield child
			yield from child.descendants()
	@property
	def dotted(self) -> str:
		return '.'.join(map(str, self.number)) if self.number else self.name
	@property
	def key(self) -> str:
		return f'{self.part}.{self.dotted}' if self.part and self.number else self.dotted
	def lineage(self):
		node = self
		while node:
			yield node
			node = node.parent
	def span_dict(self) -> dict:
		return {'start': self.line, 'end': self.end, 'subtree_end': max([self.end, *(c.end for c in self.descendants())])}
def assign_tree_numbers(roots, findings):
	numbers, mapping = ({}, {})
	def walk(nodes, prefix):
		for index, node in enumerate(nodes, 1):
			node.number = (*prefix, index)
			if node.name in mapping:
				findings.append(Finding('error', 'KEY-DUP', node.line, f'duplicate key @{node.name}'))
			mapping[node.name] = node.key
			numbers[node.line] = node
			walk(node.children, node.number)
	for nodes in roots.values():
		walk(nodes, ())
	return (numbers, mapping)
def build_render_report(mapping, numbered_re, external_changes, old_keys=None):
	r = {'renumbered': [[k, v] for k, v in mapping.items() if k != v and numbered_re.fullmatch(k)], 'added': [k for k in mapping if not numbered_re.fullmatch(k)]}
	if None is not old_keys:
		r['removed'] = [k for k in old_keys if k not in mapping]
	if external_changes:
		r['external_references_normalized'] = external_changes
	return r
def close_spans(nodes, lines):
	last = lines[-1].no if lines else 0
	for current, nxt in zip(nodes, [*nodes[1:], None]):
		current.end = nxt.line - 1 if None is not nxt else last
def content_blocks(text, kind):
	if kind not in TEXT_KINDS:
		raise ValueError('Choose article, proposal or letter')
	if 'letter' == kind:
		r = [{'section': str(i), 'line': text.count('\n', 0, m.start()) + 1, 'text': m.group(), 'prose': m.group()} for i, m in enumerate(re.finditer('(?ms)\\S.*?(?=\\n\\s*\\n|\\Z)', text), 1)]
	else:
		lines = scan(text)
		parsed = parse_addressed(lines, kind)
		r = []
		if 'proposal' == kind:
			first = parsed[0].line if parsed else len(lines) + 1
			preface = [l for l in lines if l.no < first and 'blank' != l.kind]
			if preface:
				r.append({'section': 'preface', 'line': preface[0].no, 'text': '\n'.join((l.raw for l in preface)), 'prose': '\n'.join((l.raw for l in preface if 'prose' == l.kind))})
		skip = ('blank',) if 'proposal' == kind else ('heading', 'anchor', 'blank')
		for node in parsed:
			low = node.line if 'proposal' == kind else node.line + 1
			own = [l for l in lines if low <= l.no <= node.end and l.kind not in skip]
			if own:
				prose = '\n'.join((node.body if 'proposal' == kind and l.no == node.line else l.raw for l in own if 'prose' == l.kind))
				r.append({'section': node.key, 'line': node.line, 'text': '\n'.join((l.raw for l in own)), 'prose': prose})
	return r
def keyed_engine(kind):
	if kind not in ('article', 'proposal'):
		raise ValueError('Keyed numbering is available for article or proposal; a letter preserves its own form')
	from . import article, proposal
	return proposal if 'proposal' == kind else article
def lint_document(text, kind=None, path=None, profile=None, *, lang=None, lexicon=None, bans=None):
	from . import article, proposal
	resolved = kind or article.detect_kind(path, text)
	if 'proposal' == resolved:
		r = proposal.lint_text(text, lang=lang, path=path, lexicon=lexicon, bans=bans, profile=profile)
	else:
		extra = {'link_style': profile['link_style']} if (profile or {}).get('link_style') else {}
		r = article.lint_text(text, kind=resolved, lang=lang, path=path, lexicon=lexicon, bans=bans, **extra)
	return r
def mechanical_projection(text, kind, mode):
	lines = scan(text)
	identities = {str(s.key): str(i) for i, s in enumerate(parse_addressed(lines, kind))}
	def prose(value, current):
		protected = '`+[^`]*`+|«[^»]*»|“[^”]*”|(?<!\\w)"[^"\\n]+"'
		if 'renumber' == mode:
			protected += '|!?\\[[^\\]\\n]*\\]\\(<?https?://[^)]+\\)|<https?://[^>]+>|https?://[^\\s<>"\\x27]+'
		parts = re.split('(' + protected + ')', value)
		for i in range(0, len(parts), 2):
			item = parts[i]
			if 'links' == mode:
				from .links import _bare_urls
				def link(match):
					label, url = match.groups()
					visible = unquote(re.sub('[*`]', '', label))
					address = unquote(re.sub('^https?://', '', url.rstrip('>')))
					return 'URL' if visible.rstrip('/') in (address.rstrip('/'), url.rstrip('>')) else label + '(URL)'
				item = re.sub('\\[([^\\]]+)\\]\\(<?(https?://[^)]+)\\)', link, item)
				item = re.sub('https?://\\S+', lambda m: 'URL' + m.group()[len(next(_bare_urls(m.group()))):], item)
			else:
				item = normalize_external_refs(item)
				item = ANCHOR_LINK.sub(lambda m: 'REF:' + identities.get(m[2].lstrip('§'), 'MISSING:' + m[2]), item)
				def ref(match):
					if external_section_ref(item, match):
						r = match.group()
					else:
						target = current + '.' + match.group(1) if 'article' == kind and (not re.match('^[IVXLC]+\\.', match.group(1))) else match.group(1)
						r = 'REF:' + identities.get(target, 'MISSING:' + target)
					return r
				item = re.sub('§+([IVXLC]+\\.\\d+(?:\\.\\d+)*|\\d+(?:\\.\\d+)*)', ref, item)
				if 'proposal' == kind:
					item = re.sub('^\\s*\\d+(?:\\.\\d+)*\\.\\s*', '', item)
			parts[i] = item
		return ''.join(parts)
	out = []
	for line, raw in zip(lines, text.splitlines(True)):
		ending = raw[len(line.raw):]
		if 'renumber' == mode and 'anchor' == line.kind:
			continue
		if 'renumber' == mode and 'heading' == line.kind:
			out.append(re.sub('^(#{2,6}\\s+)\\d+(?:\\.\\d+)*\\.?\\s*', '\\1', line.raw) + ending)
			continue
		out.append((prose(line.raw, part_at(lines, line.no)) if 'prose' == line.kind else line.raw) + ending)
	return ''.join(out)
def parse_addressed(lines, kind):
	if 'article' == kind:
		from .article import parse_sections
		r = parse_sections(lines)
	elif 'proposal' != kind:
		r = []
	else:
		from .proposal import parse_blocks
		r = parse_blocks(lines)
	return r
def part_at(lines, line_no):
	r = ''
	for line in lines:
		if line.no > line_no:
			break
		if 'heading' == line.kind:
			hashes, text = HEADING.match(line.raw).groups()
			match = PART.match(text) if 1 == len(hashes) else None
			r = match.group(1) if match else r
	return r
def reassemble_lines(template: str, lines: list[Line], values: list[str]) -> str:
	chunks = template.splitlines(keepends=True)
	return ''.join((value + chunk[len(line.raw):] for line, value, chunk in zip(lines, values, chunks)))
def rewrite_keyed_prose(raw, line_no, mapping, findings, external_changes, *, format_ref, anchors=None, dangling_hint=''):
	def anchor_ref(match):
		key = match.group(1)
		if key in mapping:
			r = f'(#{anchors[key]})'
		else:
			findings.append(Finding('error', 'KEY-DANGLING', line_no, f'#@{key} does not exist', raw[:80]))
			r = match.group(0)
		return r
	def replace_ref(match):
		marks, start, end = match.group('marks', 'start', 'end')
		suffix = ''
		if end and end.endswith('.') and (end not in mapping) and (end[:-1] in mapping):
			end, suffix = (end[:-1], '.')
		for endpoint, hint in ((start, dangling_hint), (end, '')):
			if endpoint and endpoint not in mapping:
				findings.append(Finding('error', 'KEY-DANGLING', line_no, f'§@{endpoint} does not exist{hint}', raw[:80]))
				if None is not anchors:
					break
		if start not in mapping or (end and end not in mapping):
			r = match.group(0)
		else:
			r = format_ref(marks, start, end) + suffix
		return r
	def convert(value):
		step = KEYED_REF.sub(replace_ref, value)
		if None is not anchors:
			step = re.sub('\\(#@([\\w.\\-]+)\\)', anchor_ref, step)
		r = normalize_external_refs(step, changes=external_changes, line=line_no)
		if None is not anchors and re.search('§§?@|\\(#@', r) and (not any((line_no == f.line and 'KEY-DANGLING' == f.rule for f in findings))):
			findings.append(Finding('error', 'KEY-SYNTAX', line_no, 'unparseable or unresolved keyed reference', r[:80]))
		return r
	return transform_prose(raw, convert)
def scope_blocks(text, kind):
	if 'letter' == kind:
		r = content_blocks(text, kind)
	else:
		lines = scan(text)
		starts = {node.line: node.key for node in parse_addressed(lines, kind)}
		output, key = ({}, 'preface')
		for line, raw in zip(lines, text.splitlines(True)):
			if line.no in starts:
				key = starts[line.no]
			elif 'article' == kind and re.match('^#\\s+[IVXLC]+\\.', line.raw):
				key = '$part:' + line.raw
			output[key] = output.get(key, '') + raw
		r = [{'section': k, 'text': v} for k, v in output.items()]
	return r
def section_at(sections, line_no):
	r = None
	for section in sections:
		if section.line > line_no:
			break
		r = section
	return r
def validate_ref_range(start, end, known, findings, line_no, excerpt, *, order_key, order_rule='REF-RANGE', order_msg='range endpoints are in reverse document order', allow_same=False, check_dense=False, start_checked=False, end_prefix='§'):
	if not start_checked and start and (start not in known):
		findings.append(Finding('error', 'REF-DANGLING', line_no, f'§{start} does not exist', excerpt))
	if end and end not in known:
		findings.append(Finding('error', 'REF-DANGLING', line_no, f'{end_prefix}{end} does not exist', excerpt))
	elif end and start in known:
		left, right = (order_key(start), order_key(end))
		if left > right if allow_same else left >= right:
			findings.append(Finding('error', order_rule, line_no, order_msg, excerpt))
		elif check_dense and left[:-1] == right[:-1]:
			for ordinal in range(left[-1], right[-1] + 1):
				key = '.'.join(map(str, (*left[:-1], ordinal)))
				if key not in known:
					findings.append(Finding('error', 'REF-DANGLING', line_no, f'§{key} inside the range does not exist', excerpt))
