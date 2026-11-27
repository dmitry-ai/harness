# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Article.Section import Section
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import dfh_author_text
from Df.Harness.lib.text_sections import ANCHOR_LINK, ARTICLE_SECTION_LABEL, dfh_section_at
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GraphAuditor:
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, lines: list[Line], sections: list[Section], findings: list[Finding]) -> None:
		self.__lines = lines
		self.__sections = sections
		self.__findings = findings
		self.__by_key = {s.key: s for s in sections}
	# @used-by :meth:`GraphAuditor.audit()`
	def __build_graph(self) -> tuple[dict[str, set[str]], dict[str, bool], dict[str, bool]]:
		refs = {s.key: set() for s in self.__sections}
		external = {s.key: False for s in self.__sections}
		primary = {s.key: False for s in self.__sections}
		for line in self.__lines:
			section = dfh_section_at(self.__sections, line.no)
			if None is section or line.kind in ('heading', 'anchor'):
				continue
			if line.kind in ('code', 'quote'):
				primary[section.key] = True
			if 'prose' == line.kind:
				self.__record_prose_refs(line, section, refs, external, primary)
		return (refs, external, primary)
	# @used-by :meth:`GraphAuditor.__check_part2()`
	def __check_conditional_line(self, section: Section, line: Line) -> None:
		visible = dfh_author_text(line.raw).strip()
		if re.match('^(?:If|\\u0415\\u0441\\u043b\\u0438|\\u0412 \\u0441\\u043b\\u0443\\u0447\\u0430\\u0435 \\u0435\\u0441\\u043b\\u0438)\\b', visible, re.I):
			targets = [m.group(2).removeprefix('§') for m in ANCHOR_LINK.finditer(visible.split('→', 1)[0])]
			has_part2 = any((t.startswith('II.') or (t in self.__by_key and 'II' == self.__by_key[t].part) for t in targets))
			has_part1 = any((t.startswith('I.') or (t in self.__by_key and 'I' == self.__by_key[t].part) for t in targets))
			if not has_part2:
				if not has_part1:
					self.__findings.append(Finding('warning', 'GRAPH-CONDITIONAL-STEP', line.no, f'conditional recommendation §{section.key} has no Part II diagnostic premise; branch from an explicit measurement step', line.raw[:100]))
				else:
					self.__findings.append(Finding('error', 'GRAPH-CONDITIONAL-STEP', line.no, f'conditional recommendation §{section.key} conditions on an established Part I fact; it must branch from a Part II diagnostic step (like §II.12.2 from §II.12.1 in 2725.md)', line.raw[:100]))
	# @used-by :meth:`GraphAuditor.audit()`
	def __check_cycles(self, refs: dict[str, set[str]], primary: dict[str, bool]) -> None:
		grounded = {s.key for s in self.__sections if any((primary[a.key] for a in s.lineage()))}
		changed = True
		while changed:
			additions = {key for key, targets in refs.items() if targets and targets <= grounded}
			additions.update((s.key for s in self.__sections if s.children and all((c.key in grounded for c in s.children))))
			changed = not additions <= grounded
			grounded.update(additions)
		state = {'counter': 0, 'stack': [], 'on_stack': set(), 'indexes': {}, 'low': {}}
		for key in refs:
			if key not in state['indexes']:
				self.__visit_scc(key, refs, grounded, state)
	# @used-by :meth:`GraphAuditor.audit()`
	def __check_orphans(self, refs: dict[str, set[str]]) -> None:
		used = self.__collect_used(refs)
		for section in self.__sections:
			own_body = [line for line in self.__lines if section.line < line.no <= section.end and line.kind in ('prose', 'quote', 'code')]
			if 'I' == section.part and section.key not in used and (own_body or not section.children):
				self.__findings.append(Finding('note', 'GRAPH-ORPHAN', section.line, f'§{section.key} is not a premise of any recommendation (directly or transitively): keep it only if it serves the goal of the text'))
	# @used-by :meth:`GraphAuditor.audit()`
	def __check_part1_and_part2(self, refs: dict[str, set[str]], external: dict[str, bool]) -> None:
		grounded = self.__compute_part2_grounded(refs, external)
		for section in self.__sections:
			if 'I' == section.part and (not section.children):
				body = [l for l in self.__lines if section.line < l.no <= section.end and l.kind not in ('blank', 'anchor')]
				has_proof = any((l.kind in ('code', 'fence', 'quote') for l in body)) or external[section.key] or refs[section.key] or (section.parent and any((l.kind in ('code', 'fence') for l in self.__lines if section.parent.line < l.no < section.line)))
				if not has_proof:
					self.__findings.append(Finding('note', 'PROOF-MISSING', section.line, f'§{section.key} states a fact without a command, quote, link or premise'))
			elif 'II' == section.part:
				self.__check_part2(section, grounded)
	# @used-by :meth:`GraphAuditor.__check_part1_and_part2()`
	def __check_part2(self, section: Section, grounded: dict[str, bool]) -> None:
		if not section.children and (not grounded.get(section.key)):
			self.__findings.append(Finding('warning', 'GRAPH-BASELESS', section.line, f'recommendation §{section.key} has no premise in part I and no documentation link'))
		for line in (l for l in self.__lines if section.line < l.no <= section.end and 'prose' == l.kind):
			self.__check_conditional_line(section, line)
	# @used-by :meth:`GraphAuditor.__check_orphans()`
	def __collect_used(self, refs: dict[str, set[str]]) -> set[str]:
		used, expanded = (set(), set())
		queue = [(s.key, False) for s in self.__sections if 'II' == s.part]
		while queue:
			key, expand = queue.pop()
			node = self.__by_key[key]
			if expand and key not in expanded:
				expanded.add(key)
				queue.extend(((child.key, True) for child in node.children))
			for member in node.lineage():
				if member.key not in used:
					used.add(member.key)
					queue.extend(((target, True) for target in refs[member.key]))
		return used
	# @used-by :meth:`GraphAuditor.__check_part1_and_part2()`
	def __compute_part2_grounded(self, refs: dict[str, set[str]], external: dict[str, bool]) -> dict[str, bool]:
		grounded, changed = ({}, True)
		while changed:
			changed = False
			for section in self.__sections:
				if 'II' == section.part and (not grounded.get(section.key)) and any((external[s.key] or any((t.startswith('I.') or grounded.get(t) for t in refs[s.key])) for s in section.lineage())):
					grounded[section.key] = changed = True
		return grounded
	# @used-by :meth:`GraphAuditor.__visit_scc()`
	def __pop_component(self, key: str, refs: dict[str, set[str]], grounded: set[str], state: dict) -> None:
		component: list[str] = []
		while True:
			member = state['stack'].pop()
			state['on_stack'].remove(member)
			component.append(member)
			if member == key:
				break
		if (1 < len(component) or key in refs[key]) and (not any((m in grounded for m in component))):
			first = min((self.__by_key[m] for m in component), key=lambda node: node.line)
			self.__findings.append(Finding('error', 'GRAPH-CYCLE', first.line, 'circular premises without primary evidence: ' + ', '.join(('§' + m for m in sorted(component)))))
	# @used-by :meth:`GraphAuditor.__build_graph()`
	def __record_prose_refs(self, line: Line, section: Section, refs: dict[str, set[str]], external: dict[str, bool], primary: dict[str, bool]) -> None:
		visible = dfh_author_text(line.raw)
		for match in ANCHOR_LINK.finditer(visible):
			target = match.group(2).removeprefix('§')
			if target in self.__by_key:
				refs[section.key].add(target)
			parsed = ARTICLE_SECTION_LABEL.match(match.group(1).replace('**', '').strip())
			if parsed and parsed.group(4) and (target in self.__by_key):
				end_part = parsed.group(3) or parsed.group(1) or section.part
				endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
				if endpoint in self.__by_key:
					refs[section.key].update((s.key for s in self.__sections if self.__by_key[target].line <= s.line <= self.__by_key[endpoint].line))
		if re.search('\\]\\(<?https?://|https?://', line.raw):
			external[section.key] = primary[section.key] = True
	# @used-by :meth:`GraphAuditor.__check_cycles()`
	def __visit_scc(self, key: str, refs: dict[str, set[str]], grounded: set[str], state: dict) -> None:
		indexes, low = (state['indexes'], state['low'])
		indexes[key] = low[key] = state['counter']
		state['counter'] += 1
		state['stack'].append(key)
		state['on_stack'].add(key)
		for target in sorted(refs[key]):
			if target not in indexes:
				self.__visit_scc(target, refs, grounded, state)
				low[key] = min(low[key], low[target])
			elif target in state['on_stack']:
				low[key] = min(low[key], indexes[target])
		if low[key] == indexes[key]:
			self.__pop_component(key, refs, grounded, state)
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def audit(self) -> None:
		if {'I', 'II'} <= {s.part for s in self.__sections}:
			refs, external, primary = self.__build_graph()
			self.__check_orphans(refs)
			self.__check_part1_and_part2(refs, external)
			self.__check_cycles(refs, primary)
