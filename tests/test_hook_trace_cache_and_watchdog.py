# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add incremental transcript event cache and single-process hook watchdog":
# https://github.com/dmitry-ai/harness/issues/356
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import builtins
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import hook_runtime, issue_first_gate, tdd_gate
from agent_tools.gates import run_pre_tool_gates
# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
def _init_github_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	subprocess.run(['git', '--no-optional-locks', 'init', str(repo)], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'remote', 'add', 'origin', 'https://github.com/acme/demo.git'], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_single_process_watchdog_and_hung_timeout_lkg_fallback()`
def _is_pid_alive(pid: int) -> bool:
	r = False
	if 0 < pid:
		if 'nt' == os.name:
			import ctypes
			h = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)
			if h:
				code = ctypes.windll.kernel32.WaitForSingleObject(h, 0)
				ctypes.windll.kernel32.CloseHandle(h)
				r = 0 != code
		else:
			try:
				os.kill(pid, 0)
				r = True
			except OSError:
				r = False
	return r
# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_incremental_disk_cache_appends_and_invalidation()`
# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_untracked_dir_skips_disk_index_and_stays_in_process_only()`
def _write_jsonl(path: Path, rows: list[dict]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(''.join((json.dumps(row, ensure_ascii=False) + '\n' for row in rows)), encoding='utf-8')
# @used-by :mod:`unittest`
class HookTraceCacheAndWatchdogTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_in_process_cache_shares_single_disk_read_across_pre_tool_gates(self) -> None:
		from agent_tools import trace_event_cache
		trace_event_cache.clear_in_process_trace_cache()
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'proj'
			(proj / '\ua616/data/turns').mkdir(parents=True)
			repo = proj / 'code'
			_init_github_repo(repo)
			(repo / 'tests').mkdir()
			(repo / 'tests/test_x.py').write_text('def test_x(): assert True\n', encoding='utf-8')
			cid = str(uuid.uuid4())
			tpath = base / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix app'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --title "Bug" --body-file b.md'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 7, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/7', 'verified': True}) + '\n'},
			]
			_write_jsonl(tpath, rows)
			target_key = os.path.normcase(str(tpath.resolve()))
			opens = {'count': 0}
			real_open = builtins.open
			# @used-by :meth:`HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
			def _counting_open(file, *args, **kwargs):
				try:
					if os.path.normcase(str(Path(file).resolve())) == target_key:
						opens['count'] += 1
				except (OSError, TypeError, ValueError):
					pass
				return real_open(file, *args, **kwargs)
			with patch('builtins.open', side_effect=_counting_open):
				dec = run_pre_tool_gates('write_file', {'Path': str(repo / 'tests/test_new.py'), 'Content': '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# "Bug": https://github.com/acme/demo/issues/7\n# @used-by :mod:`unittest`\ndef test_ok() -> None:\n\tassert True\n'}, {'cwd': str(proj), 'transcriptPath': str(tpath)})
				issue_first_gate.extract_antigravity_issue_first_events(tpath, cwd=proj)
				tdd_gate.extract_antigravity_tdd_events(tpath, cwd=proj)
			self.assertEqual('allow', dec['decision'], dec)
			self.assertEqual(1, opens['count'])
	# @used-by :mod:`unittest`
	def test_incremental_disk_cache_appends_and_invalidation(self) -> None:
		from agent_tools import trace_event_cache
		trace_event_cache.clear_in_process_trace_cache()
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'proj'
			turns_dir = proj / '\ua616/data/turns'
			turns_dir.mkdir(parents=True)
			cid = str(uuid.uuid4())
			tpath = base / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			row0 = {'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix issue #10'}
			row1 = {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(proj / 'tests/test_a.py')}}]}
			_write_jsonl(tpath, [row0, row1])
			rows1, st1 = trace_event_cache.load_transcript_rows_cached(tpath, cwd=proj, return_stats=True)
			self.assertTrue((turns_dir / f'{cid}-trace-index.json').is_file())
			self.assertFalse(st1['cache_hit'])
			self.assertEqual([row0, row1], rows1)
			self.assertEqual([], hook_runtime.iter_turn_state_files(turns_dir))
			row2 = {'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'}
			with tpath.open('a', encoding='utf-8') as fh:
				fh.write(json.dumps(row2, ensure_ascii=False) + '\n')
			trace_event_cache.clear_in_process_trace_cache()
			rows2, st2 = trace_event_cache.load_transcript_rows_cached(tpath, cwd=proj, return_stats=True)
			self.assertTrue(st2['cache_hit'])
			self.assertGreater(st2['parsed_bytes'], 0)
			self.assertLess(st2['parsed_bytes'], st2['total_bytes'])
			self.assertEqual([row0, row1, row2], rows2)
			row_rw = {'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix issue #99'}
			_write_jsonl(tpath, [row_rw, row1, row2])
			trace_event_cache.clear_in_process_trace_cache()
			rows_rw, st_rw = trace_event_cache.load_transcript_rows_cached(tpath, cwd=proj, return_stats=True)
			self.assertFalse(st_rw['cache_hit'])
			self.assertEqual([row_rw, row1, row2], rows_rw)
			row_trunc = {'step_index': 0, 'type': 'USER_INPUT', 'content': 'Reset'}
			_write_jsonl(tpath, [row_trunc])
			trace_event_cache.clear_in_process_trace_cache()
			rows3, st3 = trace_event_cache.load_transcript_rows_cached(tpath, cwd=proj, return_stats=True)
			self.assertFalse(st3['cache_hit'])
			self.assertEqual([row_trunc], rows3)
	# @used-by :mod:`unittest`
	def test_single_process_watchdog_and_hung_timeout_lkg_fallback(self) -> None:
		from test_hook_runner_watchdog import _seed_two_releases
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			_, store, runner, sha1, sha2 = _seed_two_releases(base)
			info_file = base / 'fast_pid.json'
			fast_src = f'import json, os, pathlib, sys\nsys.stdin.read()\npathlib.Path({str(info_file)!r}).write_text(json.dumps({{"pid": os.getpid(), "ppid": os.getppid()}}), encoding="utf-8")\nsys.stdout.write(json.dumps({{"decision": "allow"}}))\n'
			(store / 'releases' / sha2 / 'scripts/check_markdown_slop.py').write_text(fast_src, encoding='utf-8')
			proc = subprocess.Popen([sys.executable, str(runner), 'check_markdown_slop.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
			out, err = proc.communicate(input='{}', timeout=10)
			self.assertEqual(0, proc.returncode, err)
			self.assertEqual('allow', json.loads(out)['decision'])
			info = json.loads(info_file.read_text(encoding='utf-8'))
			self.assertEqual(proc.pid, info['pid'])
			self.assertEqual(os.getpid(), info['ppid'])
			hung_file = base / 'hung.pid'
			(store / 'releases' / sha2 / 'scripts/check_markdown_slop.py').write_text(f'import os, pathlib, time\npathlib.Path({str(hung_file)!r}).write_text(str(os.getpid()), encoding="utf-8")\ntime.sleep(30.0)\n', encoding='utf-8')
			env = {**os.environ, 'HARNESS_HOOK_WATCHDOG_SECONDS': '0.5'}
			hproc = subprocess.run([sys.executable, str(runner), 'check_markdown_slop.py'], input='{}', text=True, encoding='utf-8', capture_output=True, env=env, timeout=10, check=False)
			self.assertEqual(0, hproc.returncode, hproc.stderr)
			self.assertEqual('LKG-PREVIOUS-OK', json.loads(hproc.stdout)['reason'])
			hung_pid = int(hung_file.read_text(encoding='utf-8').strip())
			time.sleep(0.1)
			self.assertFalse(_is_pid_alive(hung_pid))
			fb_text = (store / 'fallback.log').read_text(encoding='utf-8')
			self.assertIn('TimeoutError', fb_text)
			self.assertIn(sha1, fb_text)
	# @used-by :mod:`unittest`
	def test_untracked_dir_skips_disk_index_and_stays_in_process_only(self) -> None:
		from agent_tools import trace_event_cache
		trace_event_cache.clear_in_process_trace_cache()
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			untracked = base / 'plain_workspace'
			untracked.mkdir()
			tpath = base / 'transcript.jsonl'
			full_sib = base / 'transcript_full.jsonl'
			row0 = {'step_index': 0, 'type': 'USER_INPUT', 'content': 'Hello'}
			_write_jsonl(tpath, [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Compact'}])
			_write_jsonl(full_sib, [row0])
			rows, stats = trace_event_cache.load_transcript_rows_cached(tpath, cwd=untracked, return_stats=True)
			self.assertIsNone(stats['index_path'])
			self.assertEqual([row0], rows)
			self.assertEqual([], list(untracked.rglob('*')))
if '__main__' == __name__:
	unittest.main()
