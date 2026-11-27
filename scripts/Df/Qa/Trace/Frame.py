# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import inspect
from Df.Core.O import O
from Df.Core.lib.array.select import dfa
from Df.Core.lib.cache.dfc import dfc
from Df.Core.lib.empty import df_nts
from Df.Core.lib.lang.try_ import df_try
from Df.Core.lib.reflection.text.cc import df_cc_method
from Df.Core.lib.reflection.text.check import _load_class
from Df.Core.lib.text.starts_ends import df_ends_with
from Df.Qa.lib.validation.assert_ import df_assert
from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_lt
from Df.Qa.lib.validation.error import df_error
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Backtrace frame wrapper providing file, line, method name, and parameter reflection.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L5-L169
class Frame(O):
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L147
	# @used-by :meth:`Frame.__resolveMethodR()`
	# @used-by :meth:`Frame.method()`
	def __class_(self) -> str:
		return df_nts(self['class'])
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L154
	# @used-by :meth:`Frame.__isClosure()`
	# @used-by :meth:`Frame.__resolveMethodR()`
	# @used-by :meth:`Frame.method()`
	def __function_(self) -> str:
		return df_nts(self['function'])
	# Resolve the zero-based inspect.Parameter after validating bounds.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L85-L97
	# @used-by :meth:`Frame.methodParameter()`
	def __getParam(self, idx: int) -> inspect.Parameter:
		m = df_assert(self.methodR())
		params = self.__params(m)
		if idx >= len(params):
			df_error(f'Attempted to access parameter index {idx} of method «{self.method()}», which accepts only %d parameters.', len(params))
		df_assert_lt(len(params), idx)
		r = dfa(params, idx)
		df_assert(isinstance(r, inspect.Parameter))
		return r
	# 2016-07-31
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L160
	# @used-by :meth:`Frame.__resolveMethodR()`
	def __isClosure(self) -> bool:
		fn = self.__function_()
		return df_ends_with(fn, '{closure}') or '<lambda>' == fn
	# Resolve the explicit parameter list (excluding leading self/cls) from a Signature.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L85-L97
	# @used-by :meth:`Frame.__getParam()`
	def __params(self, sig: inspect.Signature) -> list[inspect.Parameter]:
		params = list(sig.parameters.values())
		return params[1:] if params and params[0].name in ('self', 'cls') else params
	# Resolve inspect.Signature for this frame's class method if non-closure.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L75-L79
	# @used-by :meth:`Frame.methodR()`
	def __resolveMethodR(self) -> inspect.Signature | None:
		c, f = self.__class_(), self.__function_()
		return df_try(lambda: self.__resolveSig(c, f), None) if c and f and (not self.__isClosure()) else None
	# Resolve inspect.Signature for `(c, f)` when both exist on a resolvable class.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L75-L79
	# @used-by :meth:`Frame.__resolveMethodR()`
	def __resolveSig(self, c: str, f: str) -> inspect.Signature | None:
		cls = _load_class(c)
		attr = getattr(cls, f, None) if None is not cls else None
		return inspect.signature(attr) if callable(attr) else None
	# 2015-04-03 The file path can be absent in synthetic or dynamic call frames.
	# 2023-01-28 https://github.com/mage2pro/core/issues/187
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L30
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	def file(self) -> str:
		return str(dfc(self, lambda: df_nts(self['file'])))
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L168
	# @used-by :meth:`Df.Qa.Method.Method.__caller()`
	# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_method_and_param_result()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	@staticmethod
	def i(a: dict[str, Any]) -> Frame:
		return Frame(a)
	# 2015-04-03 The line number can be absent in synthetic or dynamic call frames.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L46
	# @used-by :func:`Df.Harness.lib.text_sections._node_content_block()`
	# @used-by :func:`Df.Harness.lib.text_sections._proposal_preface_blocks()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_assign_tree_numbers()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_close_spans()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_scope_blocks()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_section_at()`
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_orphans()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_part1_and_part2()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__pop_component()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__record_prose_refs()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_group_counts()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_section_link()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_sections()`
	# @used-by :meth:`Df.Harness.Text.KeyedProseRewriter.KeyedProseRewriter.__convert()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.__check_sequence()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__assign_numbers()`
	# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
	# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__format()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
	# @used-by :meth:`test_df_article.ReferenceArticleTests.test_reference_article_has_no_errors_and_only_known_warnings()`
	def line(self) -> int:
		return int(self['line'] or 0)
	# 2015-04-03 Return `Class::method` for methods or the bare function name for plain functions.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L57
	# @used-by :meth:`Df.Qa.Method.Method.raiseErrorParam()`
	# @used-by :meth:`Df.Qa.Method.Method.raiseErrorResult()`
	# @used-by :meth:`Df.Qa.Method.Method.raiseErrorVariable()`
	# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__format()`
	# @used-by :meth:`Frame.__getParam()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	def method(self) -> str:
		return df_cc_method(self.__class_(), self.__function_())
	# Return the zero-based inspect.Parameter for this frame's method.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L85-L97
	# @used-by :meth:`Df.Qa.Method.Method.raiseErrorParam()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_method_and_param_result()`
	def methodParameter(self, ordering: int) -> inspect.Parameter:
		return dfc(self, self.__getParam, [ordering])
	# 2020-02-20 Return inspect.Signature for this frame's class method, or None if non-reflectable.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Frame.php#L75-L79
	# @used-by :meth:`Df.Qa.Method.Method.raiseErrorParam()`
	# @used-by :meth:`Frame.__getParam()`
	def methodR(self) -> inspect.Signature | None:
		return dfc(self, self.__resolveMethodR)