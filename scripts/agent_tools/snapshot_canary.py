# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
# 2026-11-25
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
CANARY_COMMITTED_FILES = 20
CANARY_MAX_SECONDS = 2.0
CANARY_MAX_SUBPROCESSES = 5
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_CANARY_PROBE = (
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
def run_pre_tool_use_canary(staging: Path, *, max_seconds: float=CANARY_MAX_SECONDS, max_subprocesses: int=CANARY_MAX_SUBPROCESSES, committed_files: int=CANARY_COMMITTED_FILES) -> tuple[bool, str]:
	proc = subprocess.run(
		[sys.executable, '-I', '-c', _CANARY_PROBE, str(Path(staging).resolve()), str(max_seconds), str(max_subprocesses), str(committed_files)],
		stdin=subprocess.DEVNULL,
		capture_output=True,
		text=True,
		encoding='utf-8',
		errors='replace',
		timeout=45,
		check=False,
		creationflags=_NO_WINDOW,
	)
	detail = (proc.stderr or proc.stdout or '').strip()
	return (0 == proc.returncode, detail)
__all__ = ['CANARY_COMMITTED_FILES', 'CANARY_MAX_SECONDS', 'CANARY_MAX_SUBPROCESSES', 'run_pre_tool_use_canary']
