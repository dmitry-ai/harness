# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# Strip `file:///` scheme prefixes before Windows drive paths and trim trailing whitespace.
# @used-by :func:`check_stop_gate._strip_local_file_scheme()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
def dfh_strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
# Resolve the canonical turns state directory for a Harness workspace root.
# @used-by :func:`check_pre_invocation._turns_dir()`
# @used-by :func:`check_stop_gate._turns_dir()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
def dfh_turns_dir(root: Path, *, explicit_only: bool=False) -> Path:
	try:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		if explicit_only:
			r = pp.turns_dir if pp.has_explicit_path('turns_dir') else (pp.data_dir / 'turns')
		else:
			r = pp.turns_dir
	except Exception:
		r = (root / '_/\ua616/data/turns') if (root / '_/\ua616').is_dir() else (root / '\ua616/data/turns')
	return r