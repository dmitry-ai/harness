# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import override
from unittest.mock import patch
import json
import os
import sqlite3
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for _p in (SCRIPTS, TESTS):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
from agent_tools import cleanup, runtime
from agent_tools.platforms import antigravity
from test_agent_tools import TemporaryCase
# 2026-11-26
# "Compute upwork-cleanup age from lifecycle activity and scan disabled history stores":
# https://github.com/dmitry-ai/harness/issues/307
class CleanupLifecycleTests(TemporaryCase):
	# @used-by :meth:`CleanupLifecycleTests.test_delayed_finalize_and_recent_rename_extend_effective_activity_window()`
	# @used-by :meth:`CleanupLifecycleTests.test_disabled_codex_and_antigravity_history_dbs_preserve_projects_without_mutating()`
	# @used-by :meth:`CleanupLifecycleTests.test_post_init_deliverables_and_multi_turn_work_preserve_while_single_init_is_cleaned()`
	# @used-by :meth:`CleanupLifecycleTests.test_renamed_from_paths_preserve_projects_with_old_path_conversations()`
	def _make_project(self, number: int, name: str, *, created_hours: float, extra_state: dict | None=None) -> tuple[Path, dict]:
		proj = self.daily / f'2026/11/20/{number} - {name}'
		(proj / '\ua616').mkdir(parents=True, exist_ok=True)
		state = {'job_id': f'~02990000000{number}', 'initialized': True, 'request_date': '2026-11-20', 'created_at': (self.now - timedelta(hours=created_hours)).isoformat()}
		if None is not extra_state:
			state.update(extra_state)
		(proj / '\ua616/project.json').write_text(json.dumps(state), encoding='utf-8')
		(proj / 'readme.md').write_text(f'# {name}\n', encoding='utf-8')
		with patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=self.config, **kw)), patch.object(antigravity, 'platform_settings', return_value=self.config['platforms']['antigravity']), patch.object(runtime, 'settings', return_value=self.config):
			reg = antigravity.register(proj, name, '2026-11-20')
		return (proj, reg)
	# @used-by :meth:`CleanupLifecycleTests.test_delayed_finalize_and_recent_rename_extend_effective_activity_window()`
	# @used-by :meth:`CleanupLifecycleTests.test_disabled_codex_and_antigravity_history_dbs_preserve_projects_without_mutating()`
	# @used-by :meth:`CleanupLifecycleTests.test_post_init_deliverables_and_multi_turn_work_preserve_while_single_init_is_cleaned()`
	# @used-by :meth:`CleanupLifecycleTests.test_renamed_from_paths_preserve_projects_with_old_path_conversations()`
	def _run_cleanup(self, *, apply: bool=True) -> dict:
		# @used-by :meth:`CleanupLifecycleTests._run_cleanup()`
		def _boom(_req):
			raise AssertionError('Disabled Codex must not invoke shared_control')
		return cleanup.cleanup_projects(apply=apply, daily_root=self.daily, now=self.now, config=self.config, control=_boom)
	# @used-by :meth:`CleanupLifecycleTests.setUp()`
	# @used-by :meth:`CleanupLifecycleTests.test_disabled_codex_and_antigravity_history_dbs_preserve_projects_without_mutating()`
	# @used-by :meth:`CleanupLifecycleTests.test_renamed_from_paths_preserve_projects_with_old_path_conversations()`
	def _sql(self, path: Path, stmt: str, params: tuple=()) -> None:
		path.parent.mkdir(parents=True, exist_ok=True)
		with closing(sqlite3.connect(path)) as conn:
			conn.execute(stmt, params)
			conn.commit()
	# @used-by :meth:`CleanupLifecycleTests.test_delayed_finalize_and_recent_rename_extend_effective_activity_window()`
	# @used-by :meth:`CleanupLifecycleTests.test_post_init_deliverables_and_multi_turn_work_preserve_while_single_init_is_cleaned()`
	def _write_journal_pair(self, proj: Path, step: int, req_text: str, res_text: str, *, hours_ago: float) -> None:
		req_f = proj / f'\ua66e/\u227b/1\u201320/{step}.md'
		res_f = proj / f'\ua66e/\u227a/1\u201320/{step}.md'
		req_f.parent.mkdir(parents=True, exist_ok=True)
		res_f.parent.mkdir(parents=True, exist_ok=True)
		req_f.write_text(req_text, encoding='utf-8')
		res_f.write_text(res_text, encoding='utf-8')
		ts = (self.now - timedelta(hours=hours_ago)).timestamp()
		os.utime(req_f, (ts, ts))
		os.utime(res_f, (ts, ts))
	# @used-by :mod:`unittest`
	# @see :meth:`test_agent_tools.TemporaryCase.setUp()`
	@override
	def setUp(self) -> None:
		super().setUp()
		self.now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
		self.workspace = self.root / 'workspace'
		self.daily = self.workspace / 'proposals/daily'
		self.daily.mkdir(parents=True)
		self.folders = self.root / 'ag/folders.json'
		self.folders.parent.mkdir(parents=True, exist_ok=True)
		self.folders.write_text('{"folders":[],"projectFolderMap":{},"collapsedFolders":[]}', encoding='utf-8')
		self.ag_homes = {name: self.root / f'ag/{name}' for name in ('A0', 'A6', 'A7')}
		self.cx_homes = {name: self.root / f'cx/{name}' for name in ('C1', 'C2')}
		for iid, home in self.ag_homes.items():
			(home / '.gemini/config/projects').mkdir(parents=True)
			(home / '.gemini/antigravity').mkdir(parents=True)
			if 'A7' != iid:
				self._sql(home / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		for home in self.cx_homes.values():
			home.mkdir(parents=True)
		self.config = deepcopy(runtime.settings())
		self.config['workspace_root'] = str(self.workspace)
		self.config['daily_root'] = 'proposals/daily'
		self.config['platforms']['antigravity']['folders_json'] = str(self.folders)
		self.config['platforms']['antigravity']['instances'] = {
			'A0': {'enabled': True, 'primary': True, 'label': 'A0', 'home': str(self.ag_homes['A0'])},
			'A6': {'enabled': True, 'primary': False, 'label': 'A6', 'home': str(self.ag_homes['A6'])},
			'A7': {'enabled': False, 'primary': False, 'label': 'A7', 'home': str(self.ag_homes['A7'])},
		}
		self.config['platforms']['codex']['instances'] = {
			'C1': {'enabled': False, 'label': 'C1', 'home': str(self.cx_homes['C1'])},
			'C2': {'enabled': False, 'label': 'C2', 'home': str(self.cx_homes['C2'])},
		}
	# @used-by :mod:`unittest`
	def test_delayed_finalize_and_recent_rename_extend_effective_activity_window(self) -> None:
		p_fin, r_fin = self._make_project(1, 'delayed-finalize.com', created_hours=82)
		fin_at = (self.now - timedelta(hours=15)).isoformat()
		(p_fin / '\ua616/data').mkdir(parents=True, exist_ok=True)
		(p_fin / '\ua616/data/workflow.json').write_text(json.dumps({'stages': {'finalize': {'status': 'complete', 'time': fin_at}}}), encoding='utf-8')
		ren_at = (self.now - timedelta(hours=2)).isoformat()
		p_ren, r_ren = self._make_project(2, 'recent-rename.com', created_hours=96, extra_state={'renamed_from': [{'from': str(self.daily / '2026/11/20/2 - old-name'), 'to': str(self.daily / '2026/11/20/2 - recent-rename.com'), 'at': ren_at}]})
		p_ho, r_ho = self._make_project(3, 'recent-handoff.com', created_hours=96)
		ho_turn = self.workspace / 'proposals/init/\ua616/data/turns/handoff01.json'
		ho_turn.parent.mkdir(parents=True, exist_ok=True)
		ho_at = (self.now - timedelta(hours=10)).isoformat()
		ho_turn.write_text(json.dumps({'key': 'handoff01', 'status': 'handed_off', 'updated_at': ho_at, 'handed_off_to': {'project_root': str(p_ho), 'job_id': '~029900000003'}}), encoding='utf-8')
		p_jrn, r_jrn = self._make_project(4, 'recent-journal.com', created_hours=96)
		self._write_journal_pair(p_jrn, 1, '/upwork-init https://upwork.com/jobs/~029900000004', 'Done.', hours_ago=5)
		p_old, r_old = self._make_project(5, 'truly-old.com', created_hours=96)
		res = self._run_cleanup(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(item['root']).resolve(): item for item in res['projects']}
		self.assertEqual('recent', by_root[p_fin.resolve()]['status'])
		self.assertEqual('workflow.finalize', by_root[p_fin.resolve()]['age_basis'])
		self.assertEqual(fin_at, by_root[p_fin.resolve()]['effective_activity_at'])
		self.assertEqual('recent', by_root[p_ren.resolve()]['status'])
		self.assertEqual('project.renamed_from', by_root[p_ren.resolve()]['age_basis'])
		self.assertEqual('recent', by_root[p_ho.resolve()]['status'])
		self.assertEqual('handed_off_conversation', by_root[p_ho.resolve()]['age_basis'])
		self.assertEqual('recent', by_root[p_jrn.resolve()]['status'])
		self.assertEqual('journal.latest_pair', by_root[p_jrn.resolve()]['age_basis'])
		self.assertEqual('removed', by_root[p_old.resolve()]['status'])
		for reg in (r_fin, r_ren, r_ho, r_jrn):
			self.assertTrue(Path(reg['instances']['A0']['project_file']).exists())
			self.assertTrue(Path(reg['instances']['A6']['project_file']).exists())
		self.assertFalse(Path(r_old['instances']['A0']['project_file']).exists())
	# @used-by :mod:`unittest`
	def test_disabled_codex_and_antigravity_history_dbs_preserve_projects_without_mutating(self) -> None:
		p_cx, r_cx = self._make_project(1, 'codex-history.com', created_hours=120)
		p_a7, r_a7 = self._make_project(2, 'a7-history.com', created_hours=120)
		p_empty, r_empty = self._make_project(3, 'no-history.com', created_hours=120)
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'INSERT INTO threads VALUES (?,?,?,?)', ('t-c1-1', 'cx-id-1', str(p_cx), 0))
		self._sql(self.ag_homes['A7'] / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		self._sql(self.ag_homes['A7'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?,?)', ('other-id', json.dumps([p_a7.resolve().as_uri()])))
		res = self._run_cleanup(apply=True)
		self.assertTrue(res['complete'], res)
		self.assertEqual({'antigravity': ['A0', 'A6'], 'codex': []}, res['active_instances'])
		by_root = {Path(item['root']).resolve(): item for item in res['projects']}
		self.assertEqual('preserved', by_root[p_cx.resolve()]['status'])
		self.assertEqual(1, by_root[p_cx.resolve()]['conversations']['codex:C1'])
		self.assertEqual('preserved', by_root[p_a7.resolve()]['status'])
		self.assertEqual(1, by_root[p_a7.resolve()]['conversations']['antigravity:A7'])
		self.assertEqual('removed', by_root[p_empty.resolve()]['status'])
		self.assertTrue(Path(r_cx['instances']['A0']['project_file']).exists())
		self.assertTrue(Path(r_a7['instances']['A0']['project_file']).exists())
		self.assertFalse(Path(r_empty['instances']['A0']['project_file']).exists())
		(self.cx_homes['C2'] / 'state_5.sqlite').write_text('not-a-valid-sqlite-db', encoding='utf-8')
		p_corrupt, r_corrupt = self._make_project(4, 'corrupt-check.com', created_hours=120)
		res_bad = self._run_cleanup(apply=True)
		self.assertFalse(res_bad['complete'])
		by_bad = {Path(item['root']).resolve(): item for item in res_bad['projects']}
		self.assertEqual('blocked', by_bad[p_corrupt.resolve()]['status'])
		self.assertTrue(Path(r_corrupt['instances']['A0']['project_file']).exists())
	# @used-by :mod:`unittest`
	def test_post_init_deliverables_and_multi_turn_work_preserve_while_single_init_is_cleaned(self) -> None:
		p_v1, r_v1 = self._make_project(1, 'v1-letter.com', created_hours=120)
		(p_v1 / 'result/EN').mkdir(parents=True)
		(p_v1 / 'result/EN/draft.md').write_text('Proposal draft.', encoding='utf-8')
		p_v2, r_v2 = self._make_project(2, 'v2-letter.com', created_hours=120)
		v2_let = p_v2 / '\u2c0f/\u227b/\u2655/\U0001f582/Letters/EN.md'
		v2_let.parent.mkdir(parents=True)
		v2_let.write_text('V2 proposal draft.', encoding='utf-8')
		p_multi, r_multi = self._make_project(3, 'multi-turn.com', created_hours=120)
		self._write_journal_pair(p_multi, 1, '/upwork-init https://upwork.com/jobs/~029900000003', 'Initial analysis.', hours_ago=120)
		self._write_journal_pair(p_multi, 2, 'Write a follow-up question.', 'Follow-up reply.', hours_ago=100)
		p_single, r_single = self._make_project(4, 'single-init-only.com', created_hours=120)
		self._write_journal_pair(p_single, 1, '/upwork-init https://upwork.com/jobs/~029900000004', 'Initial analysis.', hours_ago=120)
		res = self._run_cleanup(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(item['root']).resolve(): item for item in res['projects']}
		self.assertEqual('preserved', by_root[p_v1.resolve()]['status'])
		self.assertEqual('preserved', by_root[p_v2.resolve()]['status'])
		self.assertEqual('preserved', by_root[p_multi.resolve()]['status'])
		self.assertEqual('removed', by_root[p_single.resolve()]['status'])
		for reg in (r_v1, r_v2, r_multi):
			self.assertTrue(Path(reg['instances']['A0']['project_file']).exists())
		self.assertFalse(Path(r_single['instances']['A0']['project_file']).exists())
	# @used-by :mod:`unittest`
	def test_renamed_from_paths_preserve_projects_with_old_path_conversations(self) -> None:
		old_ag = self.daily / '2026/11/20/1 - old-ag-topic'
		old_cx = self.daily / '2026/11/20/2 - old-cx-topic'
		old_ts = (self.now - timedelta(hours=100)).isoformat()
		p_ag, r_ag = self._make_project(1, 'renamed-ag.com', created_hours=120, extra_state={'renamed_from': [{'from': str(old_ag), 'to': str(self.daily / '2026/11/20/1 - renamed-ag.com'), 'at': old_ts}]})
		p_cx, r_cx = self._make_project(2, 'renamed-cx.com', created_hours=120, extra_state={'renamed_from': [{'from': str(old_cx), 'to': str(self.daily / '2026/11/20/2 - renamed-cx.com'), 'at': old_ts}]})
		self._sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?,?)', ('unrelated-id', json.dumps([old_ag.resolve().as_uri()])))
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'INSERT INTO threads VALUES (?,?,?,?)', ('t-old-cx', 'cx-old', str(old_cx / 'sub'), 0))
		res = self._run_cleanup(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(item['root']).resolve(): item for item in res['projects']}
		self.assertEqual('preserved', by_root[p_ag.resolve()]['status'])
		self.assertEqual(1, by_root[p_ag.resolve()]['conversations']['antigravity:A0'])
		self.assertEqual('preserved', by_root[p_cx.resolve()]['status'])
		self.assertEqual(1, by_root[p_cx.resolve()]['conversations']['codex:C1'])
		self.assertTrue(Path(r_ag['instances']['A0']['project_file']).exists())
		self.assertTrue(Path(r_cx['instances']['A0']['project_file']).exists())
if '__main__' == __name__:
	unittest.main()
