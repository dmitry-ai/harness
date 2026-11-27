# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class AddressedSection:
	# @used-by :meth:`AddressedSection.span_dict()`
	def descendants(self):
		for child in self.children:
			yield child
			yield from child.descendants()
	# @used-by :meth:`AddressedSection.key()`
	# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.__register_section()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__render_lines()`
	@property
	def dotted(self) -> str:
		return '.'.join(map(str, self.number)) if self.number else self.name
	# @used-by :func:`Df.Harness.lib.text_sections._node_content_block()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_assign_tree_numbers()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_scope_blocks()`
	# @used-by :func:`agent_tools.article.render_map()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__build_graph()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_conditional_line()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_cycles()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_orphans()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_part1_and_part2()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_part2()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__collect_used()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__compute_part2_grounded()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__init__()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__record_prose_refs()`
	# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.__register_section()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__build_header()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__export_line()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_sections()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.audit()`
	# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.project()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.__check_block_order()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.__check_sequence()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.check_references()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__assign_numbers()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	@property
	def key(self) -> str:
		return f'{self.part}.{self.dotted}' if self.part and self.number else self.dotted
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_cycles()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__collect_used()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__compute_part2_grounded()`
	def lineage(self):
		node = self
		while node:
			yield node
			node = node.parent
	# @used-by :func:`agent_tools.article.render_map()`
	def span_dict(self) -> dict:
		return {'start': self.line, 'end': self.end, 'subtree_end': max([self.end, *(c.end for c in self.descendants())])}
