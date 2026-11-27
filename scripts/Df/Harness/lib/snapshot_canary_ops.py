# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
CANARY_COMMITTED_FILES = 20
CANARY_MAX_SECONDS = 2.0
CANARY_MAX_SUBPROCESSES = 5
DEFAULT_FALLBACK_SPIKE_THRESHOLD = 5
LARGE_CANARY_MAX_MEDIAN_SECONDS = 1.5
LARGE_CANARY_RUNS = 3
LARGE_TRANSCRIPT_BYTES = 2_500_000
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
CANARY_PROBE = (
	'import importlib.util, json, pathlib, subprocess, sys, tempfile, time\n'
	'staging = pathlib.Path(sys.argv[1]).resolve()\n'
	'max_secs = float(sys.argv[2])\n'
	'max_subs = int(sys.argv[3])\n'
	'n_files = int(sys.argv[4])\n'
	"sdir = staging / 'scripts'\n"
	"ep = sdir / 'check_rules_and_server_gate.py'\n"
	'if not ep.is_file():\n'
	'\traise SystemExit(0)\n'
	'sys.path.insert(0, str(sdir))\n'
	"spec = importlib.util.spec_from_file_location('_canary_rg', ep)\n"
	'mod = importlib.util.module_from_spec(spec)\n'
	'spec.loader.exec_module(mod)\n'
	"eval_fn = getattr(mod, '_evaluate_payload', None)\n"
	'if not callable(eval_fn):\n'
	'\traise SystemExit(0)\n'
	"nw = getattr(subprocess, 'CREATE_NO_WINDOW', 0)\n"
	'def _g(repo, *a):\n'
	"\tsubprocess.run(['git', '--no-optional-locks', '-C', str(repo), *a], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30, creationflags=nw)\n"
	'with tempfile.TemporaryDirectory() as td:\n'
	'\tbase = pathlib.Path(td).resolve()\n'
	"\trepo = base / 'canary_repo'\n"
	'\trepo.mkdir(parents=True)\n'
	"\t_g(repo, 'init', '-b', 'main')\n"
	"\tcfg = repo / '.git/config'\n"
	"\tcfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\\n\\temail = c@example.com\\n\\tname = Canary\\n', encoding='utf-8')\n"
	"\ttest_f = repo / 'tests/test_canary.py'\n"
	'\ttest_f.parent.mkdir(parents=True, exist_ok=True)\n'
	"\ttest_f.write_text('import unittest\\nclass T(unittest.TestCase):\\n\\tdef test_ok(self):\\n\\t\\tself.assertEqual(1, 1)\\n', encoding='utf-8')\n"
	"\trows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Canary multi-commit turn'}]\n"
	'\tstep = 1\n'
	'\tbatch = max(1, (n_files + 2) // 3)\n'
	'\tfor c_idx in range(3):\n'
	'\t\tstart_i = c_idx * batch\n'
	'\t\tend_i = min(n_files, start_i + batch)\n'
	'\t\tif start_i >= end_i:\n'
	'\t\t\tbreak\n'
	"\t\trows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]})\n"
	"\t\trows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'})\n"
	"\t\trows.append({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest \"{test_f}\"')}}]})\n"
	"\t\trows.append({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\\nFAIL\\n'})\n"
	'\t\tstep += 4\n'
	'\t\tfor i in range(start_i, end_i):\n'
	"\t\t\tfp = repo / f'src/m_{i:02d}.py'\n"
	'\t\t\tfp.parent.mkdir(parents=True, exist_ok=True)\n'
	"\t\t\tfp.write_text(f'VAL = {i}\\n', encoding='utf-8')\n"
	"\t\t\trows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(fp))}}]})\n"
	"\t\t\trows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Created file.'})\n"
	'\t\t\tstep += 2\n'
	"\t\t_g(repo, 'add', '.')\n"
	"\t\t_g(repo, 'commit', '--no-verify', '-m', f'c{c_idx}')\n"
	"\t\trows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'git -C \"{repo}\" commit -m c{c_idx}')}}]})\n"
	"\t\trows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Command exited with code 0.\\n[main 1111111] ok\\n'})\n"
	'\t\tstep += 2\n'
	"\trows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]})\n"
	"\trows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'})\n"
	"\trows.append({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest \"{test_f}\"')}}]})\n"
	"\trows.append({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\\nFAIL\\n'})\n"
	"\ttx = base / 'transcript_full.jsonl'\n"
	"\ttx.write_text(''.join((json.dumps(r) + '\\n' for r in rows)), encoding='utf-8')\n"
	'\torig_run = subprocess.run\n'
	'\tcalls = [0]\n'
	'\tdef _spy(*a, **kw):\n'
	'\t\tcalls[0] += 1\n'
	'\t\treturn orig_run(*a, **kw)\n'
	'\tsubprocess.run = _spy\n'
	'\tpayloads = (\n'
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / '\\ua616/data/scratch/answer-canary.md'), 'Content': 'Answer.\\n'}}},\n"
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'python scripts/harness.py answer-prepare . --response-file x.md'}}},\n"
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'tests/test_next.py'), 'Content': 'import unittest\\nclass T(unittest.TestCase):\\n\\tdef test_n(self):\\n\\t\\tself.assertEqual(1, 1)\\n'}}},\n"
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'src/m_next.py'), 'Content': 'X = 1\\n'}}},\n"
	'\t)\n'
	'\tt0 = time.perf_counter()\n'
	'\ttry:\n'
	'\t\tfor pay in payloads:\n'
	'\t\t\teval_fn(pay)\n'
	'\t\t\tif calls[0] > max_subs:\n'
	"\t\t\t\traise SystemExit(f'PreToolUse canary exceeded subprocess budget: {calls[0]} > {max_subs}')\n"
	'\t\t\tif (time.perf_counter() - t0) > max_secs:\n'
	"\t\t\t\traise SystemExit(f'PreToolUse canary exceeded latency budget: {time.perf_counter() - t0:.3f}s > {max_secs:.2f}s')\n"
	'\tfinally:\n'
	'\t\tsubprocess.run = orig_run\n'
	'\telapsed = time.perf_counter() - t0\n'
	"\tprint(json.dumps({'elapsed': round(elapsed, 4), 'subprocesses': calls[0]}))\n"
)
LARGE_CANARY_PROBE = (
	'import importlib.util, json, pathlib, statistics, subprocess, sys, tempfile, time\n'
	'staging = pathlib.Path(sys.argv[1]).resolve()\n'
	'max_med = float(sys.argv[2])\n'
	'runs = max(1, int(sys.argv[3]))\n'
	'target_b = int(sys.argv[4])\n'
	"sdir = staging / 'scripts'\n"
	"ep = sdir / 'check_rules_and_server_gate.py'\n"
	'if not ep.is_file():\n'
	'\traise SystemExit(0)\n'
	'sys.path.insert(0, str(sdir))\n'
	"spec = importlib.util.spec_from_file_location('_large_canary_rg', ep)\n"
	'mod = importlib.util.module_from_spec(spec)\n'
	'spec.loader.exec_module(mod)\n'
	"eval_fn = getattr(mod, '_evaluate_payload', None)\n"
	'if not callable(eval_fn):\n'
	'\traise SystemExit(0)\n'
	"nw = getattr(subprocess, 'CREATE_NO_WINDOW', 0)\n"
	'def _g(repo, *a):\n'
	"\tsubprocess.run(['git', '--no-optional-locks', '-C', str(repo), *a], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30, creationflags=nw)\n"
	'with tempfile.TemporaryDirectory() as td:\n'
	'\tbase = pathlib.Path(td).resolve()\n'
	"\trepo = base / 'canary_repo'\n"
	'\trepo.mkdir(parents=True)\n'
	"\t_g(repo, 'init', '-b', 'main')\n"
	"\tcfg = repo / '.git/config'\n"
	'\tcfg.write_text(cfg.read_text(encoding=\'utf-8\') + \'[user]\\n\\temail = c@example.com\\n\\tname = Canary\\n[remote "origin"]\\n\\turl = https://github.com/example/canary.git\\n\', encoding=\'utf-8\')\n'
	"\tev = repo / '\\ua616/KB/Evidence/GitHub/example__canary/issue-1.json'\n"
	'\tev.parent.mkdir(parents=True, exist_ok=True)\n'
	"\tev.write_text(json.dumps({'number': 1, 'repo': 'example/canary', 'state': 'open', 'title': 'Canary', 'url': 'https://github.com/example/canary/issues/1'}), encoding='utf-8')\n"
	"\ttest_f = repo / 'tests/test_canary.py'\n"
	'\ttest_f.parent.mkdir(parents=True, exist_ok=True)\n'
	"\ttest_f.write_text('import unittest\\nclass T(unittest.TestCase):\\n\\tdef test_ok(self):\\n\\t\\tself.assertEqual(1, 1)\\n', encoding='utf-8')\n"
	"\tprod_f = repo / 'src/m_00.py'\n"
	'\tprod_f.parent.mkdir(parents=True, exist_ok=True)\n'
	"\tprod_f.write_text('VAL = 0\\n', encoding='utf-8')\n"
	"\t_g(repo, 'add', 'tests/test_canary.py', 'src/m_00.py')\n"
	"\t_g(repo, 'commit', '--no-verify', '-m', 'init')\n"
	'\tlines = [\n'
	"\t\tjson.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Large transcript canary for https://github.com/example/canary/issues/1'}) + '\\n',\n"
	"\t\tjson.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps('python scripts/df_github_issue.py fetch --repo example/canary --issue 1')}}]}) + '\\n',\n"
	"\t\tjson.dumps({'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\\n' + json.dumps({'ok': True, 'action': 'fetch', 'repo': 'example/canary', 'number': 1, 'state': 'open', 'html_url': 'https://github.com/example/canary/issues/1'}) + '\\n'}) + '\\n',\n"
	'\t]\n'
	"\tblob = ('tool output line ' + ('x' * 110) + '\\n') * 128\n"
	"\ttotal = sum((len(x.encode('utf-8')) for x in lines))\n"
	'\tstep = 3\n'
	'\twhile total < target_b:\n'
	"\t\tp_ln = json.dumps({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': json.dumps(str(prod_f))}}]}) + '\\n'\n"
	"\t\tg_ln = json.dumps({'step_index': step + 1, 'type': 'GENERIC', 'content': blob}) + '\\n'\n"
	'\t\tlines.extend((p_ln, g_ln))\n'
	"\t\ttotal += len(p_ln.encode('utf-8')) + len(g_ln.encode('utf-8'))\n"
	'\t\tstep += 2\n'
	'\tlines.extend((\n'
	"\t\tjson.dumps({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]}) + '\\n',\n"
	"\t\tjson.dumps({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'}) + '\\n',\n"
	"\t\tjson.dumps({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest \"{test_f}\"')}}]}) + '\\n',\n"
	"\t\tjson.dumps({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\\nFAIL\\n'}) + '\\n',\n"
	'\t))\n'
	"\ttx = base / 'transcript_full.jsonl'\n"
	"\ttx.write_text(''.join(lines), encoding='utf-8')\n"
	'\ttx_bytes = tx.stat().st_size\n'
	'\tpayloads = (\n'
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / '\\ua616/data/scratch/answer-canary.md'), 'Content': 'Answer.  \\n'}}},\n"
	"\t\t{'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'src/m_next.py'), 'Content': '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\\n# @used-by :mod:`m_next`\\ndef value() -> int:\\n\\treturn 1\\n'}}},\n"
	'\t)\n'
	'\teval_fn(payloads[0])\n'
	'\tsamples = []\n'
	'\tfor _ in range(runs):\n'
	'\t\tt0 = time.perf_counter()\n'
	'\t\tfor pay in payloads:\n'
	'\t\t\teval_fn(pay)\n'
	'\t\tsamples.append(time.perf_counter() - t0)\n'
	'\tmedian_s = statistics.median(samples)\n'
	'\tif median_s > max_med:\n'
	"\t\traise SystemExit(f'Large-transcript PreToolUse canary exceeded latency budget: median {median_s:.3f}s > {max_med:.2f}s across {runs} runs ({tx_bytes} bytes)')\n"
	"\tprint(json.dumps({'median_seconds': round(median_s, 4), 'runs': runs, 'transcript_bytes': tx_bytes}))\n"
)
# @used-by :func:`dfh_inspect_fallback_timeout_spike()`
def _parse_iso_ts(raw: str | None) -> datetime | None:
	r: datetime | None = None
	s = str(raw or '').strip()
	if s:
		try:
			dt = datetime.fromisoformat(f'{s[:-1]}+00:00' if s.endswith('Z') else s)
			r = dt.replace(tzinfo=timezone.utc) if None is dt.tzinfo else dt
		except ValueError:
			r = None
	return r
# @used-by :func:`dfh_finalize_snapshot_promotion()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_inspect_fallback_timeout_spike_filters_timestamps_and_check_before_promote()`
# @used-by :mod:`agent_tools.snapshot_latency_canary`
def dfh_check_fallback_before_promote(store: Path, prior: dict, *, fail_on_fallback_spike: bool=False, spike_threshold: int=DEFAULT_FALLBACK_SPIKE_THRESHOLD) -> tuple[dict, str | None]:
	since_raw = prior.get('updated_at') if isinstance(prior, dict) else None
	since_iso = str(since_raw).strip() or None if None is not since_raw else None
	audit = dfh_inspect_fallback_timeout_spike(store, since_iso=since_iso, threshold=spike_threshold)
	err = f"Fallback TimeoutError spike detected ({audit['new_timeout_count']} >= {audit['threshold']} since {since_iso or 'start'})" if fail_on_fallback_spike and audit['spike_detected'] else None
	return (audit, err)
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
# @used-by :mod:`agent_tools.snapshot_latency_canary`
def dfh_finalize_snapshot_promotion(store: Path, prior: dict, sha: str, ok: bool, detail: str, activate_fn, *, fail_on_fallback_spike: bool=False) -> dict:
	fb_audit, fb_err = dfh_check_fallback_before_promote(store, prior, fail_on_fallback_spike=fail_on_fallback_spike)
	if not ok:
		r = {'commit_sha': sha, 'error': detail or 'Snapshot validation failed', 'fallback_audit': fb_audit, 'promoted': False, 'valid': False}
	elif None is not fb_err:
		r = {'commit_sha': sha, 'error': fb_err, 'fallback_audit': fb_audit, 'promoted': False, 'valid': False}
	else:
		r = {**activate_fn(), 'fallback_audit': fb_audit}
	return r
# @used-by :func:`dfh_check_fallback_before_promote()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_inspect_fallback_timeout_spike_filters_timestamps_and_check_before_promote()`
# @used-by :mod:`agent_tools.snapshot_latency_canary`
def dfh_inspect_fallback_timeout_spike(store: Path, *, since_iso: str | None=None, threshold: int=DEFAULT_FALLBACK_SPIKE_THRESHOLD) -> dict:
	log_file = Path(store) / 'fallback.log'
	since_dt = _parse_iso_ts(since_iso)
	count = 0
	if log_file.is_file():
		for line in log_file.read_text(encoding='utf-8', errors='replace').splitlines():
			if 'TimeoutError' in line:
				line_dt = _parse_iso_ts(line.split(None, 1)[0]) if line.strip() else None
				if None is since_dt or (None is not line_dt and line_dt > since_dt):
					count += 1
	return {'new_timeout_count': count, 'since': since_iso, 'spike_detected': count >= threshold, 'threshold': threshold}
# @used-by :func:`agent_tools.snapshot_canary._large_canary_via_facade()`
# @used-by :meth:`Df.Harness.Runtime.CanaryProbe.CanaryProbe.run()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_live_worktree_passes_large_transcript_latency_canary()`
# @used-by :mod:`agent_tools.snapshot_latency_canary`
def dfh_run_large_transcript_latency_canary(staging: Path, *, max_median_seconds: float=LARGE_CANARY_MAX_MEDIAN_SECONDS, runs: int=LARGE_CANARY_RUNS, target_bytes: int=LARGE_TRANSCRIPT_BYTES) -> tuple[bool, str]:
	timeout_s = max(45.0, float(max_median_seconds) * max(1, int(runs)) * 6.0)
	try:
		proc = subprocess.run([sys.executable, '-I', '-c', LARGE_CANARY_PROBE, str(Path(staging).resolve()), str(max_median_seconds), str(runs), str(target_bytes)], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout_s, check=False, creationflags=NO_WINDOW)
		detail = (proc.stderr or proc.stdout or '').strip()
		r = (0 == proc.returncode, detail)
	except subprocess.TimeoutExpired:
		r = (False, f'Large-transcript PreToolUse canary exceeded latency timeout ({timeout_s:g}s)')
	return r
