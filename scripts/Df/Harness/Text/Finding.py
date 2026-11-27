# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from dataclasses import dataclass
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
@dataclass
class Finding:
	severity: str
	rule: str
	line: int
	message: str
	excerpt: str = ''
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_perf_profile_tests()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_perf_timesheet()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_problem_metadata()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_rules_audit()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_run_tests()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_schema_help()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_test_watchdog()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_xref()`
	# @used-by :func:`Df.Harness.lib.trace_review.dfh_current_turn_requests()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__format_arch_check()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__handle_source_or_render()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.findings_output()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__check_gate_response()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__collect_target_and_lint_issues()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__emit_validation_result()`
	# @used-by :meth:`test_df_article.ReferenceArticleTests.test_reference_article_has_no_errors_and_only_known_warnings()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.assertFlags()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def format(self, path='') -> str:
		where = f'{path}:{self.line}' if path else f'{self.line}'
		tail = f' | {self.excerpt}' if self.excerpt else ''
		return f'{where}: [{self.severity}] {self.rule}: {self.message}{tail}'
