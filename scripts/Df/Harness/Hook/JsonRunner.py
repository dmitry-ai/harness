# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class JsonRunner:
	# @used-by :func:`agent_tools.hook_runtime.run_json_hook()`
	# @used-by :func:`check_markdown_slop.main()`
	# @used-by :func:`check_rules_and_server_gate.main()`
	# @used-by :func:`check_stop_gate.main()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
	def __init__(self, handler, *, stdin=None, stdout=None) -> None:
		self.__handler = handler
		self.__stdin = stdin
		self.__stdout = stdout
	# @used-by :func:`agent_tools.hook_runtime.run_json_hook()`
	# @used-by :func:`check_markdown_slop.main()`
	# @used-by :func:`check_rules_and_server_gate.main()`
	# @used-by :func:`check_stop_gate.main()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
	def run(self) -> dict:
		in_stream = self.__stdin if None is not self.__stdin else sys.stdin
		out_stream = self.__stdout if None is not self.__stdout else sys.stdout
		decision: dict = {'decision': 'allow'}
		try:
			raw = in_stream.read()
			if raw and raw.strip():
				decision = self.__handler(json.loads(raw))
		except Exception:
			decision = {'decision': 'allow'}
		out_stream.write(json.dumps(decision, ensure_ascii=False))
		return decision