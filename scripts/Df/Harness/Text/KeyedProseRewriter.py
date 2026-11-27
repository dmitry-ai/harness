# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.lib.text_core import dfh_normalize_external_refs, dfh_transform_prose
from Df.Harness.lib.text_sections import KEYED_REF
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class KeyedProseRewriter:
	# @used-by :func:`agent_tools.text_sections.rewrite_keyed_prose()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def __init__(self, raw: str, line_no: int, mapping: dict, findings: list[Finding], external_changes: list, *, format_ref, anchors=None, dangling_hint: str='') -> None:
		self.__raw = raw
		self.__line_no = line_no
		self.__mapping = mapping
		self.__findings = findings
		self.__external_changes = external_changes
		self.__format_ref = format_ref
		self.__anchors = anchors
		self.__dangling_hint = dangling_hint
	# @used-by :meth:`KeyedProseRewriter.__convert()`
	def __anchor_ref(self, match) -> str:
		key = match.group(1)
		if key in self.__mapping:
			r = f'(#{self.__anchors[key]})'
		else:
			self.__findings.append(Finding('error', 'KEY-DANGLING', self.__line_no, f'#@{key} does not exist', self.__raw[:80]))
			r = match.group(0)
		return r
	# @used-by :meth:`KeyedProseRewriter.rewrite()`
	def __convert(self, value: str) -> str:
		step = KEYED_REF.sub(self.__replace_ref, value)
		if None is not self.__anchors:
			step = re.sub('\\(#@([\\w.\\-]+)\\)', self.__anchor_ref, step)
		r = dfh_normalize_external_refs(step, changes=self.__external_changes, line=self.__line_no)
		if None is not self.__anchors and re.search('§§?@|\\(#@', r) and (not any((self.__line_no == f.line and 'KEY-DANGLING' == f.rule for f in self.__findings))):
			self.__findings.append(Finding('error', 'KEY-SYNTAX', self.__line_no, 'unparseable or unresolved keyed reference', r[:80]))
		return r
	# @used-by :meth:`KeyedProseRewriter.__convert()`
	def __replace_ref(self, match) -> str:
		marks, start, end = match.group('marks', 'start', 'end')
		suffix = ''
		if end and end.endswith('.') and (end not in self.__mapping) and (end[:-1] in self.__mapping):
			end, suffix = (end[:-1], '.')
		for endpoint, hint in ((start, self.__dangling_hint), (end, '')):
			if endpoint and endpoint not in self.__mapping:
				self.__findings.append(Finding('error', 'KEY-DANGLING', self.__line_no, f'§@{endpoint} does not exist{hint}', self.__raw[:80]))
				if None is not self.__anchors:
					break
		if start not in self.__mapping or (end and end not in self.__mapping):
			r = match.group(0)
		else:
			r = self.__format_ref(marks, start, end) + suffix
		return r
	# @used-by :func:`agent_tools.text_sections.rewrite_keyed_prose()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def rewrite(self) -> str:
		return dfh_transform_prose(self.__raw, self.__convert)
