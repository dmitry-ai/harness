# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from Df.Core.lib.text.source import df_text_rewrite_pairs
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# Return True when a project-relative path should be skipped during Harness tree cloning.
# @used-by :func:`agent_tools.shadow_replay_clone._is_skipped_rel()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_is_skipped_rel(rel: Path) -> bool:
	parts = rel.parts
	if any((p.endswith('.lock') for p in parts)):
		r = True
	elif 3 <= len(parts) and '\ua616' == parts[0] and 'data' == parts[1] and parts[2] in ('scratch', '.journal'):
		r = True
	else:
		r = False
	return r
# Rewrite path strings inside a JSON file in place using case-insensitive replacement pairs.
# @used-by :func:`agent_tools.shadow_replay_clone._rewrite_json_file()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_rewrite_json_file(path: Path, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> bool:
	r = False
	if path.is_file():
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		updated = dfh_rewrite_value(data, pairs, preserve_keys=preserve_keys)
		path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		r = True
	return r
# Recursively rewrite string keys and values inside JSON-like structures with replacement pairs.
# @used-by :func:`agent_tools.project_rename_state._rewrite_value()`
# @used-by :func:`agent_tools.shadow_replay_clone._rewrite_value()`
# @used-by :func:`dfh_rewrite_json_file()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_rewrite_value(value: Any, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> Any:
	if isinstance(value, str):
		r: Any = df_text_rewrite_pairs(value, pairs)
	elif isinstance(value, list):
		r = [dfh_rewrite_value(v, pairs, preserve_keys=preserve_keys) for v in value]
	elif isinstance(value, dict):
		r = {(df_text_rewrite_pairs(k, pairs) if isinstance(k, str) else k): (v if k in preserve_keys else dfh_rewrite_value(v, pairs, preserve_keys=preserve_keys)) for k, v in value.items()}
	else:
		r = value
	return r