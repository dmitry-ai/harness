# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
from agent_tools import completion, journal, upwork_project as up, workflow as flow
from agent_tools.analysis import publish_owned, render_analysis
CID = '11111111-2222-4333-8444-555555555555'
# @used-by :func:`_build_split_backend()`
def _wire(field: int, payload: bytes) -> bytes:
	out = bytearray()
	for val in ((field << 3) | 2, len(payload)):
		while True:
			b = val & 127
			val >>= 7
			out.append(b | 128 if val else b)
			if not val:
				break
	return bytes(out) + payload
# @used-by :meth:`AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
def _build_split_backend(base: Path, proj: Path, req1: str, req2: str, *, turn1_reply: str='Turn 1 done.') -> tuple[Path, Path]:
	home = base / 'home'
	backend = home / '.gemini/antigravity'
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	tx = backend / 'brain' / CID / '.system_generated/logs/transcript_full.jsonl'
	tx.parent.mkdir(parents=True, exist_ok=True)
	rows = [
		{'step_index': 0, 'type': 'USER_INPUT', 'content': req1, 'created_at': '2026-11-24T01:00:00Z'},
		{'step_index': 10, 'type': 'PLANNER_RESPONSE', 'content': turn1_reply, 'tool_calls': [], 'created_at': '2026-11-24T01:05:00Z'},
		{'step_index': 434, 'type': 'USER_INPUT', 'content': req2, 'created_at': '2026-11-24T02:00:00Z'},
	]
	tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (CID, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 434, 'primary'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{CID}.db')) as conn:
		conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, req1.encode('utf-8'))),))
		conn.execute('INSERT INTO steps VALUES(10, 15, 3, 0, NULL)')
		conn.execute('INSERT INTO steps VALUES(434, 14, 3, 0, ?)', (_wire(19, _wire(2, req2.encode('utf-8'))),))
		conn.commit()
	return (home, backend)
# @used-by :meth:`AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
def _init_review_ready_project(base: Path) -> Path:
	from test_onboarding import source
	from agent_tools.knowledge import sync_website_card
	from agent_tools.analysis import SECTIONS
	src = source()
	proj = Path(up.initialize_upwork_project(src['job_id'], domain_or_topic='Topic', extracted_data=src, date_str='2026-11-24', daily_root=base / 'daily', register_antigravity=False)['project_dir'])
	pj = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
	snap = proj / pj['snapshot']
	ref = snap.relative_to(proj / '\ua616/KB').as_posix()
	title = json.loads(snap.read_text(encoding='utf-8'))['title']
	claim = {'id': 'F-TITLE', 'essence': title, 'assessment_basis': 'Exact title in registered intake.', 'knowledge_type': 'client_report', 'verification_status': 'verified', 'scope': {'description': 'Saved job title only.', 'sample': [ref], 'limitations': []}, 'properties': ['content'], 'missing_checks': [], 'derived_from': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'No business impact inferred.', 'evidence_claim_ids': []}, 'probability_percent': 100, 'addresses': [], 'evidence': [{'id': 'E-TITLE', 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': hashlib.sha256(snap.read_bytes()).hexdigest(), 'quote': title, 'locator': {'type': 'json_pointer', 'value': '/title'}}], 'for': [{'argument': 'Registered intake contains the title.', 'evidence_id': 'E-TITLE'}], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': [ref], 'limitations': 'Attributed client report only.'}}
	val = {'schema_version': 3, 'facts': [], 'identity': [claim], **{s: [] for s in SECTIONS if 'identity' != s}, 'notes': {s: 'No conclusion established.' for s in SECTIONS}, 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-TITLE'}]}
	(proj / '\ua616/KB/Analysis.json').write_text(json.dumps(val, ensure_ascii=False), encoding='utf-8')
	sync_website_card(proj, val)
	publish_owned(proj / '\ua616/KB/Analysis.md', render_analysis(val))
	return proj
# @used-by :meth:`AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
def _authorize_routine_reply(proj: Path, home: Path, reply: str) -> None:
	from agent_tools.analysis import SECTIONS
	spec = {'risk': 'routine', 'basis': 'Routine restatement of exact title.', 'request_scope': 'Answer current request.', 'claim_ids': ['F-TITLE'], 'claims': [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task'}], 'task_flags': []}
	pkg = flow.prepare_review(proj, CID, spec, reply)
	rep = {'schema_version': 2, 'review_kind': 'self_review', 'package': pkg['package'], 'package_sha256': pkg['package_sha256'], 'scope': [*SECTIONS, 'kb_consistency', 'response'], 'result': 'approved', 'claim_reviews': [{'claim_id': 'F-TITLE', 'observed': 'Exact registered title inspected.', 'inferred': 'Only attributed title.', 'method': 'Read saved intake JSON.', 'alternatives': 'No hidden cause inferred.', 'limits': 'Client attribution only.', 'falsification': 'Different title would contradict.', 'raw_vs_criteria': 'Title matches excerpt.', 'test_alignment': {'target_claim': pkg['claims'][0]['essence'], 'tested_claim': 'Intake contains title.', 'relationship': 'direct', 'rationale': 'Literal title check.', 'counterexample': 'Live site could change later.'}, 'outcome': 'supported'}], 'findings': []}
	rpath = proj / '\ua616/KB/Evidence/Reviews/self.json'
	rpath.parent.mkdir(parents=True, exist_ok=True)
	rpath.write_text(json.dumps(rep), encoding='utf-8')
	with patch.object(Path, 'home', return_value=home):
		flow.record_review(proj, '\ua616/KB/Evidence/Reviews/self.json', parent_id=CID, reviewer_id=CID)
# 2026-11-25
# "Ensure atomic answer-prepare workflow alignment and safe open-turn reconciliation":
# https://github.com/dmitry-ai/harness/issues/232
class AtomicPrepareAndNarrowedReconcileM7Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			reply = 'Client task verified in saved intake.  \n'
			proj = _init_review_ready_project(base)
			flow.resume(proj, 'quota', 'Prior unanswered continuation request.')
			home, backend = _build_split_backend(base, proj, 'Analyze initial job.', 'Finish now.', turn1_reply='')
			flow.adopt_requests(proj, CID, backend=backend, platform='antigravity')
			_authorize_routine_reply(proj, home, reply)
			chk = completion.check_answer(proj, reply, CID, platform='antigravity', backend=backend)
			self.assertFalse(chk['valid'], chk)
			self.assertTrue(any('Align unanswered tracked requests' in str(e.get('message', e) if isinstance(e, dict) else e) for e in chk['issues']), chk['issues'])
			with self.assertRaisesRegex(ValueError, 'Align unanswered tracked requests'):
				completion.prepare(proj, reply, CID, platform='antigravity', backend=backend)
			self.assertEqual([], list((proj / '\ua66e').rglob('*.md')))
	# @used-by :mod:`unittest`
	def test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / '\ua66e/\u227a').mkdir(parents=True)
			(proj / '\ua66e/\u227b').mkdir(parents=True)
			_home, backend = _build_split_backend(base, proj, 'Turn 1 request.', 'Turn 2 request.')
			native = completion._native(proj, CID, platform='antigravity', backend=backend)
			t1, t2 = (native['turns'][0], native['turns'][1])
			merged_reqs = [t1['requests'][0], t2['requests'][0]]
			t1_key = completion._key(native, t1)
			t1_path = completion._folder(proj) / f'{t1_key}.json'
			jdir = completion._directory(proj)
			journal.reserve_turn_steps(jdir, t1_key, CID, [r['id'] for r in merged_reqs])
			old_state = completion._new(proj, native, {**t1, 'requests': merged_reqs})
			old_state['reserved_journal_steps'] = [1, 2]
			completion._persist(t1_path, old_state)
			res = completion.TurnJournalReconciler(proj, CID, platform='antigravity', backend=backend).run()
			self.assertTrue(res['valid'], res)
			self.assertEqual('delivered', res['turns'][0]['status'])
			self.assertEqual([1], res['turns'][0]['journal_steps'])
			beg = completion.begin(proj, CID, platform='antigravity', backend=backend)
			self.assertEqual([2], beg['reserved_journal_steps'])
	# @used-by :mod:`unittest`
	def test_narrowed_prepared_or_missing_tail_turn_remains_rejected(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / '\ua66e/\u227a').mkdir(parents=True)
			(proj / '\ua66e/\u227b').mkdir(parents=True)
			_home, backend = _build_split_backend(base, proj, 'Turn 1 request.', 'Turn 2 request.')
			native = completion._native(proj, CID, platform='antigravity', backend=backend)
			t1, t2 = (native['turns'][0], native['turns'][1])
			merged_reqs = [t1['requests'][0], t2['requests'][0]]
			t1_key = completion._key(native, t1)
			t1_path = completion._folder(proj) / f'{t1_key}.json'
			prep_state = completion._new(proj, native, {**t1, 'requests': merged_reqs})
			prep_state['status'] = 'prepared'
			prep_state['prepared'] = {'journal_steps': [1, 2], 'response_sha256': 'a' * 64}
			completion._persist(t1_path, prep_state)
			with self.assertRaisesRegex(ValueError, 'Native requests changed before the saved boundary'):
				completion._state(proj, native, t1, recovered=True)
			open_state = completion._new(proj, native, {**t1, 'requests': merged_reqs})
			completion._persist(t1_path, open_state)
			native_without_t2 = {**native, 'turns': [t1]}
			with self.assertRaisesRegex(ValueError, 'Native requests changed before the saved boundary'):
				completion._state(proj, native_without_t2, t1, recovered=True)
if '__main__' == __name__:
	unittest.main()
