# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.hook_markdown_ops import dfh_check_markdown_content, dfh_is_request_journal_file, dfh_resolve_markdown_content
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class MarkdownSlopGate:
	# @used-by :func:`check_markdown_slop._evaluate_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def __init__(self, payload: dict) -> None:
		self.__payload = payload
	# @used-by :func:`check_markdown_slop._evaluate_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def run(self) -> dict:
		tool_call = self.__payload.get('toolCall', {})
		name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
		path = args.get('Path', '')
		norm_p = path.replace('\\', '/').lower()
		decision = {'decision': 'allow'}
		if name in ('write_file', 'edit_file') and path and path.lower().endswith('.md') and (not dfh_is_request_journal_file(norm_p)):
			content = dfh_resolve_markdown_content(name, args, path)
			violation = dfh_check_markdown_content(content, path)
			if violation:
				decision = {'decision': 'deny', 'reason': f'REJECTED (DOC-4 / VERIFY-1 Anti-Slop Hook): {violation}'}
		return decision