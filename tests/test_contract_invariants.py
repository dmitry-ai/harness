# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce call-site policy registry and hook parity contract invariants":
# https://github.com/dmitry-ai/harness/issues/236
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
from agent_tools import completion, upwork_project as up, workflow as flow
from agent_tools.analysis import SECTIONS, publish_owned, render_analysis
from agent_tools.knowledge import sync_website_card
import check_pre_invocation
import check_stop_gate
CID = '44444444-5555-4666-8777-888888888881'
JOB_1 = '022124567641358888881'
JOB_2 = '022124567641358888882'
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
def _build_ag(base: Path, ws_root: Path, rows: list[dict], steps: list[tuple[int, int, int, bytes | None]], last_user: int) -> tuple[Path, Path, Path]:
	home = base / 'home'
	backend = home / '.gemini/antigravity'
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	tx = backend / 'brain' / CID / '.system_generated/logs/transcript_full.jsonl'
	tx.parent.mkdir(parents=True, exist_ok=True)
	tx.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (CID, '', json.dumps([ws_root.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, last_user, 'primary'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{CID}.db')) as conn:
		conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		for idx, stype, status, blob in steps:
			conn.execute('INSERT INTO steps VALUES(?,?,?,0,?)', (idx, stype, status, blob))
		conn.commit()
	return (home, backend, tx)
def _init_tracked_project(base: Path) -> Path:
	from test_onboarding import source
	src = dict(source())
	src['job_id'] = f'~{JOB_1}'
	proj = Path(up.initialize_upwork_project(src['job_id'], domain_or_topic='Parity', extracted_data=src, date_str='2026-11-25', daily_root=base / 'daily', register_antigravity=False)['project_dir'])
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
def _authorize_routine(proj: Path, home: Path, reply: str) -> None:
	spec = {'risk': 'routine', 'basis': 'Routine restatement of saved title.', 'request_scope': 'Answer active request.', 'claim_ids': ['F-TITLE'], 'claims': [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task'}], 'task_flags': []}
	pkg = flow.prepare_review(proj, CID, spec, reply)
	rep = {'schema_version': 2, 'review_kind': 'self_review', 'package': pkg['package'], 'package_sha256': pkg['package_sha256'], 'scope': [*SECTIONS, 'kb_consistency', 'response'], 'result': 'approved', 'claim_reviews': [{'claim_id': 'F-TITLE', 'observed': 'Exact title inspected.', 'inferred': 'Attributed title only.', 'method': 'Read saved intake JSON.', 'alternatives': 'No hidden cause inferred.', 'limits': 'Client attribution only.', 'falsification': 'Different title contradicts.', 'raw_vs_criteria': 'Matches excerpt.', 'test_alignment': {'target_claim': pkg['claims'][0]['essence'], 'tested_claim': 'Intake contains title.', 'relationship': 'direct', 'rationale': 'Literal title check.', 'counterexample': 'Live site could change later.'}, 'outcome': 'supported'}], 'findings': []}
	rpath = proj / '\ua616/KB/Evidence/Reviews/self.json'
	rpath.parent.mkdir(parents=True, exist_ok=True)
	rpath.write_text(json.dumps(rep), encoding='utf-8')
	with patch.object(Path, 'home', return_value=home):
		flow.record_review(proj, '\ua616/KB/Evidence/Reviews/self.json', parent_id=CID, reviewer_id=CID)
def _run_parity_defect_case(case: unittest.TestCase, mode: str) -> None:
	with tempfile.TemporaryDirectory() as tmp:
		base = Path(tmp).resolve()
		proj = _init_tracked_project(base) if mode in ('misaligned_pending', 'blocked_report_missing_continuation') else (base / 'plain')
		(proj / '\ua66e/\u227a').mkdir(parents=True, exist_ok=True)
		(proj / '\ua66e/\u227b').mkdir(parents=True, exist_ok=True)
		ev = proj / '\ua616/KB/Evidence/source.md'
		ev.parent.mkdir(parents=True, exist_ok=True)
		ev.write_text('Primary source text.\n', encoding='utf-8')
		req = 'Check parity scenario.'
		rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req, 'created_at': '2026-11-25T10:00:00Z'}]
		if 'evicted_citations' == mode:
			rows.extend([{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(ev)}}]}, {'step_index': 2, 'type': 'CHECKPOINT', 'content': 'compacted'}, {'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(base / 'home/.gemini/antigravity/brain' / CID / '.system_generated/logs/transcript_full.jsonl')}}]}])
		home, backend, _tx = _build_ag(base, proj, rows, [(0, 14, 3, _wire(19, _wire(2, req.encode('utf-8'))))], 0)
		blocked = 'blocked_report_missing_continuation' == mode
		if 'misaligned_pending' == mode:
			reply = 'Client task verified.  \n'
			flow.resume(proj, 'quota', 'Prior unanswered request.')
			flow.adopt_requests(proj, CID, backend=backend, platform='antigravity')
			_authorize_routine(proj, home, reply)
		elif 'doc4_markdown_table' == mode:
			reply = '| A | B |\n| --- | --- |\n| 1 | 2 |\n'
		elif 'link5_percent_encoded' == mode:
			reply = 'Broken link: [doc](file:///C:/work/my%20file.md).  \n'
		elif 'evicted_citations' == mode:
			reply = f'Cited evicted file: [source.md](<file:///{ev.resolve().as_posix()}>).  \n'
		else:
			reply = 'Blocked on external issue without continuation file.  \n'
		chk = completion.check_answer(proj, reply, CID, platform='antigravity', backend=backend, blocked_report=blocked)
		case.assertFalse(chk['valid'], f'{mode}: {chk}')
		with case.assertRaises(ValueError, msg=mode):
			completion.prepare(proj, reply, CID, platform='antigravity', backend=backend, blocked_report=blocked)
		case.assertEqual([], list((proj / '\ua66e').rglob('*.md')), mode)
def _stop_payload(cwd: Path, tx: Path) -> dict:
	return {'hookEventName': 'Stop', 'cwd': str(cwd), 'workspacePaths': [str(cwd)], 'conversationId': CID, 'transcriptPath': str(tx), 'terminationReason': 'NO_TOOL_CALL', 'error': '', 'fullyIdle': True, 'continuationActive': False, 'executionNum': 0}
def _setup_routing_dirs(base: Path) -> tuple[Path, Path]:
	launcher, daily = (base / 'proposals/init', base / 'proposals/daily/2026/11/25/1 - parity')
	for r in (launcher, daily):
		(r / '\ua66e/\u227a').mkdir(parents=True)
		(r / '\ua66e/\u227b').mkdir(parents=True)
		(r / '\ua616/data/turns').mkdir(parents=True)
	(daily / '\ua616/project.json').write_text(json.dumps({'job_id': f'~{JOB_1}', 'snapshot': '\ua616/KB/Evidence/in.json'}), encoding='utf-8')
	return (launcher, daily)
def _run_routing_parity_case(case: unittest.TestCase, scenario: str) -> None:
	with tempfile.TemporaryDirectory() as tmp:
		base = Path(tmp).resolve()
		launcher, daily = _setup_routing_dirs(base)
		req1 = f'/upwork-init https://upwork.com/jobs/~{JOB_1}'
		req2 = f'/upwork-init https://upwork.com/jobs/~{JOB_2}' if 'turn2_new_upwork_init_job' == scenario else 'Continue handed-off analysis.'
		reply_txt = 'Verified final reply.'
		if scenario in ('turn1_launcher', 'turn1_handed_off'):
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1}, {'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': reply_txt, 'tool_calls': []}]
			steps, last_u = ([(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (5, 15, 3, None)], 0)
		else:
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1}, {'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 done.', 'tool_calls': []}, {'step_index': 434, 'type': 'USER_INPUT', 'content': req2}, {'step_index': 450, 'type': 'PLANNER_RESPONSE', 'content': reply_txt, 'tool_calls': []}]
			steps, last_u = ([(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (5, 15, 3, None), (434, 14, 3, _wire(19, _wire(2, req2.encode('utf-8')))), (450, 15, 3, None)], 434)
		_home, backend, tx = _build_ag(base, launcher, rows, steps, last_u)
		if 'turn1_launcher' != scenario:
			(launcher / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps({'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'handed_off', 'handed_off_to': {'project_root': str(daily), 'job_id': JOB_1}}), encoding='utf-8')
		res_f = daily / '\ua66e/\u227a/1\u201320/1.md'
		res_f.parent.mkdir(parents=True, exist_ok=True)
		res_f.write_text(reply_txt, encoding='utf-8')
		sha = hashlib.sha256(reply_txt.encode('utf-8')).hexdigest()
		if 'coexisting_stale_open_and_prepared' == scenario:
			(daily / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps({'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'requests': [{'id': f'{CID}-0', 'native_step': 0}, {'id': f'{CID}-434', 'native_step': 434}], 'readiness_check': {'verified': False, 'detail': 'stale'}}), encoding='utf-8')
			(daily / '\ua616/data/turns/6f7be571e32c539377281da738e4fb213fb504c8.json').write_text(json.dumps({'key': '6f7be571e32c539377281da738e4fb213fb504c8', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-434', 'native_start_step': 434, 'status': 'prepared', 'requests': [{'id': f'{CID}-434', 'native_step': 434}], 'readiness_check': {'verified': True}, 'prepared': {'response_file': str(res_f), 'response_sha256': sha, 'body_sha256': sha}}), encoding='utf-8')
		expect_daily = scenario in ('turn1_handed_off', 'turn2_handed_off_followup', 'coexisting_stale_open_and_prepared')
		routed_pre = check_pre_invocation._routed_pre_invocation_root(launcher, CID, last_u, backend / 'brain', backend / 'conversations', tx)
		stop_st = check_stop_gate._find_turn_state(launcher / '\ua616/data/turns', CID, last_u, rows=rows)
		stop_routes_daily = isinstance(stop_st, dict) and 'handed_off' == stop_st.get('status') and Path(stop_st['handed_off_to']['project_root']).resolve() == daily
		case.assertEqual(expect_daily, routed_pre == daily, scenario)
		case.assertEqual(expect_daily, stop_routes_daily, scenario)
		if 'coexisting_stale_open_and_prepared' == scenario:
			picked = check_stop_gate._find_turn_state(daily / '\ua616/data/turns', CID, 434, rows=rows)
			case.assertEqual('6f7be571e32c539377281da738e4fb213fb504c8', picked['key'])
			case.assertEqual('allow', check_stop_gate.evaluate_stop_payload(_stop_payload(launcher, tx), backend_override=backend)['decision'])
class ContractInvariantsM2Tests(unittest.TestCase):
	def test_answer_check_and_prepare_parity_matrix_zero_journal_writes_on_failure(self) -> None:
		for mode in ('misaligned_pending', 'blocked_report_missing_continuation', 'doc4_markdown_table', 'link5_percent_encoded', 'evicted_citations'):
			with self.subTest(mode=mode):
				_run_parity_defect_case(self, mode)
	def test_pre_invocation_and_stop_gate_routing_parity_matrix(self) -> None:
		for scenario in ('turn1_launcher', 'turn1_handed_off', 'turn2_handed_off_followup', 'turn2_new_upwork_init_job', 'coexisting_stale_open_and_prepared'):
			with self.subTest(scenario=scenario):
				_run_routing_parity_case(self, scenario)
	def test_readable_link_call_site_ast_policy_registry_and_negative_detection(self) -> None:
		from agent_tools.contract_invariants import audit_readable_link_call_sites
		self.assertEqual([], audit_readable_link_call_sites(SCRIPTS))
		with tempfile.TemporaryDirectory() as tmp:
			fake_scripts = Path(tmp).resolve() / 'scripts'
			(fake_scripts / 'agent_tools').mkdir(parents=True)
			(fake_scripts / 'agent_tools/rogue.py').write_text('def check_chat(x):\n\treturn readable_link_issues(x)\ndef raw_flag(x):\n\treturn readable_link_issues(x, allow_unencoded_file_uri=True)\n', encoding='utf-8')
			errs = audit_readable_link_call_sites(fake_scripts, require_expected_chat_sites=False)
			self.assertGreaterEqual(len(errs), 2, errs)
			self.assertTrue(any('rogue.py' in e for e in errs), errs)
if '__main__' == __name__:
	unittest.main()
