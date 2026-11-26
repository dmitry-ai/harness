# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden follow-up launcher handoff and journal reservation integrity":
# https://github.com/dmitry-ai/harness/issues/269
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
from test_project_domain_drift import _complete_review_and_prepare, _prepare_pre_finalize_with_target
from test_project_rename import _run_harness
from test_upwork_init_e2e import _upsert_summary
CID = '55555555-6666-4777-8888-999999999991'
JOB_1 = '~022124567641351805598'
JOB_2 = '~099999999999999999999'
# @used-by :meth:`JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
# @used-by :meth:`JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
def _init_domain(base: Path, *, job_id: str=JOB_1, domain: str='blueskypeptide.com') -> tuple[Path, Path]:
	from agent_tools import upwork_project as up
	from test_onboarding import source
	daily = base / 'daily'
	data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
	res = up.initialize_upwork_project(job_id, domain_or_topic=domain, date_str='2026-11-23', daily_root=daily, extracted_data=data, register_native=False)
	return (Path(res['project_dir']).resolve(), daily)
# @used-by :meth:`JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
# @used-by :meth:`JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
def _write_step_pair(jdir: Path, step: int, req: str='Request text\n', res: str='Response text\n') -> None:
	from agent_tools.journal import journal_bucket_name
	bucket = journal_bucket_name(step)
	for side, body in (('\u227b', req), ('\u227a', res)):
		p = jdir / side / bucket / f'{step}.md'
		p.parent.mkdir(parents=True, exist_ok=True)
		p.write_text(body, encoding='utf-8')
# @used-by :meth:`JournalIntegrityM4Tests.test_handoff_launcher_turn_cascades_followup_without_job_url_and_clears_reservation()`
# @used-by :meth:`JournalIntegrityM4Tests.test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title()`
# @used-by :meth:`JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
def _write_turn_json(root: Path, key: str, payload: dict) -> Path:
	p = root / '\ua616/data/turns' / f'{key}.json'
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(json.dumps(payload), encoding='utf-8')
	return p
# @used-by :meth:`JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
def _run_validate_step(*args: str) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(SCRIPTS / 'validate_step.py'), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
class JournalIntegrityM4Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_handoff_launcher_turn_cascades_followup_without_job_url_and_clears_reservation(self) -> None:
		from agent_tools import completion, journal
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher = base / 'proposals/init'
			daily = base / 'proposals/daily/2026/11/23/1 - blueskypeptide.com'
			for root in (launcher, daily):
				(root / '\ua66e/\u227b').mkdir(parents=True)
				(root / '\ua66e/\u227a').mkdir(parents=True)
				(root / '\ua616/data/turns').mkdir(parents=True)
			l_jdir = launcher / '\ua66e'
			_write_turn_json(launcher, 'turn1key', {'key': 'turn1key', 'conversation_id': CID, 'native_start_step': 0, 'status': 'handed_off', 'journal': str(l_jdir), 'handed_off_to': {'project_root': str(daily), 'job_id': JOB_1}, 'requests': [{'id': f'{CID}-0', 'text': f'/upwork-init https://upwork.com/jobs/{JOB_1}'}]})
			st2 = journal.reserve_turn_steps(l_jdir, 'turn2key', CID, [f'{CID}-434'])
			st3 = journal.reserve_turn_steps(l_jdir, 'turn3key', CID, [f'{CID}-900'])
			self.assertEqual([1], st2)
			self.assertEqual([2], st3)
			t2_f = _write_turn_json(launcher, 'turn2key', {'key': 'turn2key', 'conversation_id': CID, 'native_start_step': 434, 'status': 'open', 'journal': str(l_jdir), 'reserved_journal_steps': [1], 'requests': [{'id': f'{CID}-434', 'text': 'Finish the analysis now.'}]})
			t3_f = _write_turn_json(launcher, 'turn3key', {'key': 'turn3key', 'conversation_id': CID, 'native_start_step': 900, 'status': 'open', 'journal': str(l_jdir), 'reserved_journal_steps': [2], 'requests': [{'id': f'{CID}-900', 'text': f'/upwork-init https://upwork.com/jobs/{JOB_2}'}]})
			handed = completion.handoff_launcher_turn(launcher, daily, JOB_1, conversation_id=CID)
			self.assertEqual(['turn2key'], [h['turn_key'] for h in handed])
			t2_after = json.loads(t2_f.read_text(encoding='utf-8'))
			self.assertEqual('handed_off', t2_after['status'])
			self.assertNotIn('reserved_journal_steps', t2_after)
			self.assertEqual('open', json.loads(t3_f.read_text(encoding='utf-8'))['status'])
			res_after = journal.iter_turn_reservations(l_jdir)
			self.assertNotIn('turn2key', res_after)
			self.assertEqual([2], res_after['turn3key']['steps'])
	# @used-by :mod:`unittest`
	def test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title(self) -> None:
		from agent_tools import completion, journal
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			jdir = proj / '\ua66e'
			(jdir / '\u227b').mkdir(parents=True)
			(jdir / '\u227a').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			r1 = journal.reserve_turn_steps(jdir, 'turn1key', CID, [f'{CID}-0', f'{CID}-434'])
			r2 = journal.reserve_turn_steps(jdir, 'turn2key', CID, [f'{CID}-434'])
			self.assertEqual([1, 2], r1)
			self.assertEqual([3], r2)
			_write_turn_json(proj, 'turn1key', {'key': 'turn1key', 'conversation_id': CID, 'native_start_step': 0, 'status': 'open', 'journal': str(jdir), 'reserved_journal_steps': [1, 2], 'native_reconciliation': {'valid': False, 'error': 'Native requests changed before the saved boundary; preserved'}})
			_write_turn_json(proj, 'turn2key', {'key': 'turn2key', 'conversation_id': CID, 'native_start_step': 434, 'status': 'open', 'journal': str(jdir), 'reserved_journal_steps': [3]})
			steps_before = completion.conversation_journal_steps(proj, jdir, CID)
			self.assertEqual([3], steps_before)
			committed = journal.record_answer(jdir, ['Follow-up prompt'], 'Follow-up reply.  \n', 'native-turn2key', [f'{CID}-434'], reserved_turn_key='turn2key')
			self.assertEqual([3], committed)
			res_mid = journal.iter_turn_reservations(jdir)
			self.assertNotIn('turn2key', res_mid)
			self.assertIn('turn1key', res_mid)
			self.assertEqual([f'{CID}-0'], res_mid['turn1key']['request_ids'])
			self.assertEqual([1], res_mid['turn1key']['steps'])
			_write_turn_json(proj, 'turn2key', {'key': 'turn2key', 'conversation_id': CID, 'native_start_step': 434, 'status': 'prepared', 'journal': str(jdir), 'prepared': {'journal_steps': [3]}})
			self.assertEqual([3], completion.conversation_journal_steps(proj, jdir, CID))
			journal.record_answer(jdir, ['Initial prompt'], 'Initial reply.  \n', 'native-turn1key', [f'{CID}-0'], reserved_turn_key='turn1key')
			self.assertEqual({}, journal.iter_turn_reservations(jdir))
	# @used-by :mod:`unittest`
	def test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans(self) -> None:
		from agent_tools import journal, workflow
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _ = _init_domain(base, job_id=JOB_1, domain='blueskypeptide.com')
			jdir = proj / '\ua66e'
			_write_step_pair(jdir, 3, 'Follow-up\n', 'Answer\n')
			journal.reserve_turn_steps(jdir, 'stalekey', CID, [f'{CID}-0', f'{CID}-434'])
			res_file = journal.state_dir(jdir) / journal.TURN_RESERVATIONS_FILE
			res_file.write_text(json.dumps({'version': 1, 'journal': str(jdir), 'reservations': {'stalekey': {'conversation_id': CID, 'request_ids': [f'{CID}-0', f'{CID}-434'], 'steps': [1, 2]}}}), encoding='utf-8')
			strict_fail = _run_validate_step('--dir', str(jdir), '--all', '--strict-sequence')
			self.assertNotEqual(0, strict_fail.returncode)
			self.assertIn('1, 2', strict_fail.stdout + strict_fail.stderr)
			chk = workflow.check_project(proj)
			codes = {i['code'] for i in chk['issues']}
			self.assertIn('journal.step_gap', codes, chk)
			self.assertIn('journal.orphaned_reservation', codes, chk)
			(journal.state_dir(jdir) / 'sequence-recovery.json').write_text(json.dumps({'acknowledged_gaps': [1, 2], 'reason': 'Historical steps recovered outside journal.'}), encoding='utf-8')
			res_file.unlink()
			active_steps = journal.reserve_turn_steps(jdir, 'activekey', CID, [f'{CID}-999'])
			self.assertEqual([4], active_steps)
			_write_turn_json(proj, 'activekey', {'key': 'activekey', 'conversation_id': CID, 'native_start_step': 999, 'status': 'open', 'journal': str(jdir), 'reserved_journal_steps': [4]})
			strict_ok = _run_validate_step('--dir', str(jdir), '--all', '--strict-sequence')
			self.assertEqual(0, strict_ok.returncode, strict_ok.stdout + strict_ok.stderr)
			chk_ok = workflow.check_project(proj)
			self.assertEqual([], [i for i in chk_ok['issues'] if str(i.get('code') or '').startswith('journal.')])
	# @used-by :mod:`unittest`
	def test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error(self) -> None:
		from agent_tools import journal
		from test_project_domain_drift import CID as DRIFT_CID
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _ = _init_domain(base, job_id=JOB_1, domain='blueskypeptide.com')
			backend, rows = _prepare_pre_finalize_with_target(base, proj)
			_upsert_summary(backend, DRIFT_CID, '', [proj.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 0, 'primary')
			self.assertEqual(0, _run_harness(base, 'stage', str(proj), 'analysis', '--input', '\ua616/project.json', '--output', '\ua616/KB/Analysis.json', '--output', '\ua616/KB/Analysis.md').returncode)
			cand_md, review_out = _complete_review_and_prepare(base, proj, backend, rows)
			kb_args = [tok for p in sorted((proj / '\ua616/KB').glob('*')) if p.is_file() and 'Progress.md' != p.name for tok in ('--input', p.relative_to(proj).as_posix())]
			self.assertEqual(0, _run_harness(base, 'stage', str(proj), 'review', '--input', '\ua616/KB/Analysis.json', '--output', review_out).returncode)
			self.assertEqual(0, _run_harness(base, 'stage', str(proj), 'kb_review', *kb_args, '--output', '\ua616/KB/Analysis.md', '--note', 'KB consistent').returncode)
			prep = _run_harness(base, 'answer-prepare', str(proj), '--conversation', DRIFT_CID, '--response-file', str(cand_md), '--consume-input', '--platform', 'antigravity')
			self.assertEqual(0, prep.returncode, prep.stdout + prep.stderr)
			jdir = proj / '\ua66e'
			res_file = journal.state_dir(jdir) / journal.TURN_RESERVATIONS_FILE
			res_file.write_text(json.dumps({'version': 1, 'journal': str(jdir), 'reservations': {'orphan01': {'conversation_id': DRIFT_CID, 'request_ids': [f'{DRIFT_CID}-0'], 'steps': [1, 2]}}}), encoding='utf-8')
			bad_res = _run_harness(base, 'stage', str(proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertNotEqual(0, bad_res.returncode)
			res_file.unlink()
			turn_files = [p for p in (proj / '\ua616/data/turns').glob('*.json') if '-' not in p.stem]
			orig_turn = turn_files[0].read_text(encoding='utf-8')
			t_data = json.loads(orig_turn)
			t_data['native_reconciliation'] = {'valid': False, 'error': 'Native requests changed before the saved boundary; preserved'}
			turn_files[0].write_text(json.dumps(t_data), encoding='utf-8')
			bad_rec = _run_harness(base, 'stage', str(proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertNotEqual(0, bad_rec.returncode)
			turn_files[0].write_text(orig_turn, encoding='utf-8')
			_write_step_pair(jdir, 3, 'Gap step 3\n', 'Gap reply 3\n')
			bad_gap = _run_harness(base, 'stage', str(proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertNotEqual(0, bad_gap.returncode)
			for side in ('\u227b', '\u227a'):
				(jdir / side / '1\u201320/3.md').unlink()
			fin_ok = _run_harness(base, 'stage', str(proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertEqual(0, fin_ok.returncode, fin_ok.stdout + fin_ok.stderr)
if '__main__' == __name__:
	unittest.main()
