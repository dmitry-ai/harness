# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any
from Df.Harness.lib.trace_effects import dfh_summarize_token_records
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TokenSummarizer:
	# @used-by :func:`agent_tools.platforms.codex.summarize()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def __init__(self, paths, bindings=None) -> None:
		self.__paths = paths
		self.__bindings = bindings
	# @used-by :meth:`TokenSummarizer.run()`
	def __scan_file(self, path, tools: Counter, events: list, seen: set) -> None:
		cid = None
		for index, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
			item = json.loads(line)
			payload = item.get('payload', {})
			if 'session_meta' == item.get('type') and None is cid:
				cid = payload['id']
			if 'response_item' == item.get('type') and payload.get('type') in ('custom_tool_call', 'function_call'):
				tools[payload.get('name', 'unknown')] += 1
			if 'token_usage_record' == item.get('type'):
				owner = payload.get('thread_id') or cid
				key = (owner, payload.get('turn_id'), payload.get('response_id', index))
				if key in seen:
					events.append(('duplicate',))
				else:
					seen.add(key)
					events.append(('generation', owner, index, payload.get('usage') or {}))
	# @used-by :func:`agent_tools.platforms.codex.summarize()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def run(self) -> dict[str, Any]:
		tools, events, seen = (Counter(), [], set())
		for path in self.__paths:
			self.__scan_file(path, tools, events, seen)
		return dfh_summarize_token_records(events, self.__bindings, prefix={'surface': 'codex-ui'}, field_map={'input_tokens': 'input_tokens', 'cache_read_tokens': 'cached_input_tokens', 'output_tokens': 'output_tokens'}, tools=tools, extra={'interpretation': 'Observed native token_usage_record counters; not quota percentage, currency or proof of quality'})
