# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import HEADING, dfh_author_text, dfh_external_section_ref, dfh_scan
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ANCHOR_LINK = re.compile('\\[([^\\]\\n]*)\\]\\(#([^)\\s]+)\\)')
ARTICLE_BARE_REF = re.compile('(?<![\\w@])(§{1,2})\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*)(?:\\s*[-–]\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*))?(?!\\w)')
ARTICLE_KEYED = re.compile('^@([\\w.\\-]+)(?:\\s+(.*))?$')
ARTICLE_NUMBERED = re.compile('^(\\d+(?:\\.\\d+)*)\\.?(?:\\s+(.*))?$')
ARTICLE_NUMBER_KEY = re.compile('^(?:[IVXLC]+\\.)?\\d+(?:\\.\\d+)*$')
ARTICLE_SECTION_LABEL = re.compile('^§{1,2}\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*)(?:\\s*[-–]\\s*(?:([IVXLC]+)\\.)?(\\d+(?:\\.\\d+)*))?$')
ARTICLE_SOURCE_META = re.compile('^\\s*<!-- df-article: (\\{.*\\}) -->\\s*$')
KEYED_REF = re.compile('(?<![\\w§])(?P<marks>§§?)@(?P<start>[\\w.\\-]+?)(?:-@(?P<end>[\\w.\\-]+?))?(?=[^\\w.\\-]|\\.(?:\\s|$)|$)')
PART = re.compile('^([IVXLC]+)\\.\\s+\\S')
PROPOSAL_KEYED = re.compile('(?P<prefix>(?:[^\\w\\s@#]+\\s+)?)@(?P<name>[\\w]+(?:[.\\-][\\w]+)*)(?P<gap>[ \\t]+)(?P<body>.*)$')
PROPOSAL_MARKDOWN_LINK = re.compile('!?\\[[^\\]\\n]*\\]\\(<?(?:https?://|#)[^\\n]*?\\)')
PROPOSAL_NUMBERED = re.compile('(?P<prefix>(?:[^\\w\\s@#]+\\s+)?)(?P<number>\\d+(?:\\.\\d+)*)\\.(?P<gap>[ \\t]+)(?P<body>.*)$')
PROPOSAL_NUMBER_KEY = re.compile('^\\d+(?:\\.\\d+)*$')
PROPOSAL_PREFIX = '(?P<prefix>(?:[^\\w\\s@#]+\\s+)?)'
PROPOSAL_REF = re.compile('(?<![\\w§])(?P<marks>§§?)(?P<space>[ \\t]*)(?P<start>\\d+(?:\\.\\d+)*)(?:[ \\t]*(?P<dash>[-–—])[ \\t]*§?(?P<end>\\d+(?:\\.\\d+)*))?(?!\\w|\\.\\d)')
PROPOSAL_URL = re.compile('https?://[^\\s<>`]+')
TEXT_KINDS = ('article', 'proposal', 'letter')
# @used-by :func:`dfh_content_blocks()`
def _addressed_content_blocks(text: str, kind: str) -> list[dict]:
	lines = dfh_scan(text)
	parsed = dfh_parse_addressed(lines, kind)
	is_prop = 'proposal' == kind
	r = _proposal_preface_blocks(lines, parsed) if is_prop else []
	skip = ('blank',) if is_prop else ('heading', 'anchor', 'blank')
	for node in parsed:
		block = _node_content_block(node, lines, is_prop, skip)
		if None is not block:
			r.append(block)
	return r
# @used-by :func:`dfh_validate_ref_range()`
def _check_dense_range(left: tuple, right: tuple, known, findings: list[Finding], line_no: int, excerpt: str) -> None:
	if left[:-1] == right[:-1]:
		for ordinal in range(left[-1], right[-1] + 1):
			key = '.'.join(map(str, (*left[:-1], ordinal)))
			if key not in known:
				findings.append(Finding('error', 'REF-DANGLING', line_no, f'§{key} inside the range does not exist', excerpt))
# @used-by :func:`_addressed_content_blocks()`
def _node_content_block(node, lines: list[Line], is_prop: bool, skip: tuple[str, ...]) -> dict | None:
	low = node.line if is_prop else node.line + 1
	own = [l for l in lines if low <= l.no <= node.end and l.kind not in skip]
	if not own:
		r = None
	else:
		prose = '\n'.join((node.body if is_prop and l.no == node.line else l.raw for l in own if 'prose' == l.kind))
		r = {'section': node.key, 'line': node.line, 'text': '\n'.join((l.raw for l in own)), 'prose': prose}
	return r
# @used-by :func:`_addressed_content_blocks()`
def _proposal_preface_blocks(lines: list[Line], parsed: list) -> list[dict]:
	first = parsed[0].line if parsed else len(lines) + 1
	preface = [l for l in lines if l.no < first and 'blank' != l.kind]
	return [{'section': 'preface', 'line': preface[0].no, 'text': '\n'.join((l.raw for l in preface)), 'prose': '\n'.join((l.raw for l in preface if 'prose' == l.kind))}] if preface else []
# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
def dfh_assign_tree_numbers(roots: dict, findings: list[Finding]) -> tuple[dict, dict]:
	numbers, mapping = ({}, {})
	# @used-by :func:`dfh_assign_tree_numbers()`
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
# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
def dfh_build_render_report(mapping: dict, numbered_re, external_changes: list, old_keys=None) -> dict:
	r = {'renumbered': [[k, v] for k, v in mapping.items() if k != v and numbered_re.fullmatch(k)], 'added': [k for k in mapping if not numbered_re.fullmatch(k)]}
	if None is not old_keys:
		r['removed'] = [k for k in old_keys if k not in mapping]
	if external_changes:
		r['external_references_normalized'] = external_changes
	return r
# @used-by :meth:`Df.Harness.Text.Article.KeyedParser.KeyedParser.parse()`
# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.parse()`
# @used-by :meth:`Df.Harness.Text.Proposal.Parser.Parser.parse()`
def dfh_close_spans(nodes: list, lines: list[Line]) -> None:
	last = lines[-1].no if lines else 0
	for current, nxt in zip(nodes, [*nodes[1:], None]):
		current.end = nxt.line - 1 if None is not nxt else last
# @used-by :func:`dfh_scope_blocks()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__run_validation()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_article_reexports_single_shared_implementation()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_article_grouping_node_does_not_duplicate_its_child_claim()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_map_includes_proposal_continuations_and_literal_evidence()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.manifest()`
def dfh_content_blocks(text: str, kind: str) -> list[dict]:
	if kind not in TEXT_KINDS:
		raise ValueError('Choose article, proposal or letter')
	if 'letter' == kind:
		r = [{'section': str(i), 'line': text.count('\n', 0, m.start()) + 1, 'text': m.group(), 'prose': m.group()} for i, m in enumerate(re.finditer('(?ms)\\S.*?(?=\\n\\s*\\n|\\Z)', text), 1)]
	else:
		r = _addressed_content_blocks(text, kind)
	return r
# @used-by :func:`dfh_lint_document()`
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
def dfh_detect_kind(path, text: str) -> str:
	r = 'article'
	if None is not path:
		from agent_tools.journal import is_bucket_dir_name
		if path.parent.name in ('res', '\u227a') or (is_bucket_dir_name(path.parent.name) and path.parent.parent.name in ('res', '\u227a')):
			r = 'response'
	return r
# @used-by :meth:`Df.Harness.Text.Article.KeyedParser.KeyedParser.parse()`
# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.parse()`
def dfh_iter_article_headings(lines: list[Line]):
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
# @used-by :func:`agent_tools.article.check_proposal()`
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__handle_lint()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__collect_target_and_lint_issues()`
def dfh_lint_document(text: str, kind=None, path=None, profile=None, *, lang=None, lexicon=None, bans=None) -> list[Finding]:
	resolved = kind or dfh_detect_kind(path, text)
	if 'proposal' == resolved:
		from Df.Harness.Text.Proposal.Linter import Linter as ProposalLinter
		r = ProposalLinter(text, lang=lang, path=path, lexicon=lexicon, bans=bans, profile=profile).lint()
	else:
		from Df.Harness.Text.Article.Linter import Linter as ArticleLinter
		extra = {'link_style': profile['link_style']} if (profile or {}).get('link_style') else {}
		r = ArticleLinter(text, kind=resolved, lang=lang, path=path, lexicon=lexicon, bans=bans, **extra).lint()
	return r
# @used-by :func:`_addressed_content_blocks()`
# @used-by :func:`dfh_scope_blocks()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.project()`
def dfh_parse_addressed(lines: list[Line], kind: str) -> list:
	if 'article' == kind:
		from Df.Harness.Text.Article.NumberedParser import NumberedParser
		r = NumberedParser(lines).parse()
	elif 'proposal' != kind:
		r = []
	else:
		from Df.Harness.Text.Proposal.Parser import Parser
		r = Parser(lines).parse()
	return r
# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__render_lines()`
# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__export_line()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_parts_and_addressing()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_section_link()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.project()`
def dfh_part_at(lines: list[Line], line_no: int) -> str:
	r = ''
	for line in lines:
		if line.no > line_no:
			break
		if 'heading' == line.kind:
			hashes, text = HEADING.match(line.raw).groups()
			match = PART.match(text) if 1 == len(hashes) else None
			r = match.group(1) if match else r
	return r
# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__render_lines()`
# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
def dfh_reassemble_lines(template: str, lines: list[Line], values: list[str]) -> str:
	chunks = template.splitlines(keepends=True)
	return ''.join((value + chunk[len(line.raw):] for line, value, chunk in zip(lines, values, chunks)))
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.check_references()`
# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__render_lines()`
def dfh_proposal_number_refs(raw: str):
	author = dfh_author_text(raw)
	return (match for match in PROPOSAL_REF.finditer(author) if not dfh_external_section_ref(author, match))
# @used-by :meth:`Df.Harness.Text.WorkspaceScopeChecker.WorkspaceScopeChecker.check()`
def dfh_scope_blocks(text: str, kind: str) -> list[dict]:
	if 'letter' == kind:
		r = dfh_content_blocks(text, kind)
	else:
		lines = dfh_scan(text)
		starts = {node.line: node.key for node in dfh_parse_addressed(lines, kind)}
		output, key = ({}, 'preface')
		for line, raw in zip(lines, text.splitlines(True)):
			if line.no in starts:
				key = starts[line.no]
			elif 'article' == kind and re.match('^#\\s+[IVXLC]+\\.', line.raw):
				key = '$part:' + line.raw
			output[key] = output.get(key, '') + raw
		r = [{'section': k, 'text': v} for k, v in output.items()]
	return r
# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__build_graph()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_parts_and_addressing()`
def dfh_section_at(sections: list, line_no: int):
	r = None
	for section in sections:
		if section.line > line_no:
			break
		r = section
	return r
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_section_link()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.check_references()`
def dfh_validate_ref_range(start, end, known, findings, line_no, excerpt, *, order_key, order_rule='REF-RANGE', order_msg='range endpoints are in reverse document order', allow_same=False, check_dense=False, start_checked=False, end_prefix='§') -> None:
	if not start_checked and start and (start not in known):
		findings.append(Finding('error', 'REF-DANGLING', line_no, f'§{start} does not exist', excerpt))
	if end and end not in known:
		findings.append(Finding('error', 'REF-DANGLING', line_no, f'{end_prefix}{end} does not exist', excerpt))
	elif end and start in known:
		left, right = (order_key(start), order_key(end))
		if left > right if allow_same else left >= right:
			findings.append(Finding('error', order_rule, line_no, order_msg, excerpt))
		elif check_dense:
			_check_dense_range(left, right, known, findings, line_no, excerpt)
