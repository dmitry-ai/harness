# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add behavioral regression matrix for scope deferral and ask_question gating":
# https://github.com/dmitry-ai/harness/issues/377
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
HOOK_SCRIPT = SCRIPTS / 'check_rules_and_server_gate.py'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, issue_lifecycle, repo_tags
from agent_tools.gates import run_answer_gates
SLUG = 'dmitry-ai/antigravity-addons'
Q1_Q3_ARCH = [
	{'question': 'How to structure Python namespaces?', 'options': ['(Recommended) PascalCase modules', 'snake_case modules']},
	{'question': 'Private method convention?', 'options': ['(Recommended) Double underscore __method', 'Single underscore _method']},
	{'question': 'Where to place scripts/Df/?', 'options': ['(Recommended) Under scripts/Df/', 'At repo root Df/']},
]
Q4_STEP_100 = {
	'question': '\u041a\u0430\u043a\u043e\u0439 \u043f\u043e\u0440\u044f\u0434\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043f\u0440\u0435\u0434\u043f\u043e\u0447\u0442\u0438\u0442\u0435\u043b\u0435\u043d?',
	'options': [
		'(Recommended) \u0412\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u043f\u043e\u044d\u0442\u0430\u043f\u043d\u043e \u0447\u0435\u0440\u0435\u0437 parent + child issues: \u043d\u0430\u0447\u0430\u0442\u044c \u0441 \u043f\u043e\u0440\u0442\u0430 \u00a7\u00a72\u20137, \u0444\u0438\u043a\u0441\u0438\u0440\u0443\u044f \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0432 continuation.md \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043a \u00a7\u00a78\u201311',
		'\u0412\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u043d\u0435\u043f\u0440\u0435\u0440\u044b\u0432\u043d\u043e \u043e\u0442 \u00a72 \u0434\u043e \u00a711',
	],
}
STEP_100_102_CLAR = [{'ask_step': 100, 'answer_step': 102, 'questions': [Q4_STEP_100['question']], 'answers': [{'id': 'A4', 'text': Q4_STEP_100['options'][0]}]}]
# @used-by :meth:`IncompleteScopeRegressionMatrixTests.test_turn_begin_budget_check_isolates_fresh_code_turn_from_5h_history()`
def _build_ag_turn(base: Path, name: str, *, has_project_json: bool, hist_status: str, hist_steps: int) -> tuple[Path, Path, str]:
	proj = base / name
	(proj / '\ua66e/\u227a').mkdir(parents=True)
	(proj / '\ua66e/\u227b').mkdir(parents=True)
	turns_dir = proj / '\ua616/data/turns'
	turns_dir.mkdir(parents=True)
	if has_project_json:
		(proj / '\ua616/project.json').write_text(json.dumps({'job_id': '~123'}), encoding='utf-8')
	(turns_dir / 'hist.json').write_text(json.dumps({'native_turn_id': 'ag-hist-0', 'status': hist_status, 'delegation_check': {'tool_step_count': hist_steps}}), encoding='utf-8')
	backend = base / f'ag_{name}'
	(backend / 'conversations').mkdir(parents=True)
	cid = str(uuid.uuid4())
	tx = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	tx.parent.mkdir(parents=True)
	req = 'Implement requested changes.'
	rows = [{'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-26T12:33:03Z', 'content': req}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-26T12:34:00Z', 'model': 'gemini-4-neon-xhigh', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(proj)}}]}]
	tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_user_input_step_index INTEGER,title TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.resolve().as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, '1'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as conn:
		conn.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
		conn.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (_wire(19, _wire(2, req.encode('utf-8'))),))
		conn.commit()
	return (proj, backend, cid)
# @used-by :meth:`IncompleteScopeRegressionMatrixTests.test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent()`
def _build_step_281_fixture(base: Path) -> tuple[Path, Path, dict]:
	bare = base / 'remote.git'
	subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	project = base / 'proj'
	(project / '_/\ua616').mkdir(parents=True)
	code_repo = project / 'code'
	code_repo.mkdir()
	subprocess.run(['git', 'init'], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	cfg = code_repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/{SLUG}.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n[url "{bare.as_posix()}"]\n\tinsteadOf = https://github.com/{SLUG}.git\n', encoding='utf-8')
	urls = {n: f'https://github.com/{SLUG}/issues/{n}' for n in (319, 321, 337, 338, 339, 340)}
	f_c1 = code_repo / 'p1.py'
	f_c1.write_text(f'# {urls[321]}\nx = 1\n', encoding='utf-8')
	for args in (['add', 'p1.py'], ['commit', '-m', urls[321]]):
		subprocess.run(['git', *args], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	repo_tags.ensure_commit_tag(code_repo, push=False)
	for args in (['branch', '-M', 'main'], ['push', '-u', 'origin', 'main', '--tags']):
		subprocess.run(['git', *args], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	safe_slug = SLUG.replace('/', '__')
	ev_dir = project / f'_/\ua616/KB/Evidence/GitHub/{safe_slug}'
	ev_dir.mkdir(parents=True)
	specs = ((319, None, 'open', 'Parent'), (321, 319, 'closed', 'Phase 1'), (337, 319, 'open', 'Phase 2A'), (338, 319, 'open', 'Phase 2B'), (339, None, 'open', 'Unrelated Bug A'), (340, None, 'open', 'Unrelated Bug B'))
	for num, parent, st, title in specs:
		doc = {'url': urls[num], 'number': num, 'state': st, 'title': title, 'body': f'Parent: #{parent}\n' if parent else '# Scope\n'}
		if None is not parent:
			doc['parent_number'] = parent
		(ev_dir / f'issue-{num}.json').write_text(json.dumps(doc), encoding='utf-8')
	actions = [{'action': 'create', 'repo': SLUG, 'number': 319, 'url': urls[319], 'state': 'open'}, {'action': 'create', 'repo': SLUG, 'number': 321, 'url': urls[321], 'state': 'open', 'parent_number': 319}, {'action': 'close', 'repo': SLUG, 'number': 321, 'url': urls[321], 'state': 'closed', 'parent_number': 319}, {'action': 'create', 'repo': SLUG, 'number': 337, 'url': urls[337], 'state': 'open', 'parent_number': 319}, {'action': 'create', 'repo': SLUG, 'number': 338, 'url': urls[338], 'state': 'open', 'parent_number': 319}, {'action': 'create', 'repo': SLUG, 'number': 339, 'url': urls[339], 'state': 'open'}, {'action': 'create', 'repo': SLUG, 'number': 340, 'url': urls[340], 'state': 'open'}]
	return (project, ev_dir, {'touched_files': [str(f_c1)], 'issue_actions': actions})
# @used-by :meth:`IncompleteScopeRegressionMatrixTests.test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent()`
def _gate_ctx(turn: dict, lifecycle_chk: dict, response: str, *, blocked_report: bool=False) -> dict:
	return {'role': 'primary', 'blocked_report': blocked_report, 'turn': turn, 'value': {}, 'response': response, 'doc4_errs': [], 'link_errs': [], 'prob_errs': [], 'source_errs': [], 'lang_errs': [], 'exec5_chk': {'verified': True, 'violations': []}, 'http_chk': {'verified': True, 'violations': []}, 'comp_chk': {'verified': True}, 'evicted_cited': [], 'del_chk': {'verified': True}, 'issue_first_chk': {'verified': True, 'violations': []}, 'lifecycle_chk': lifecycle_chk, 'tdd_chk': {'verified': True, 'violations': []}, 'wf_errs': []}
# @used-by :meth:`IncompleteScopeRegressionMatrixTests.test_live_pre_tool_subprocess_intercepts_ask_question_via_hooks_matcher()`
def _run_hook_ask(questions: list[dict]) -> dict:
	payload = json.dumps({'toolCall': {'name': 'ask_question', 'args': {'questions': questions}}}, ensure_ascii=False)
	proc = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input=payload, text=True, capture_output=True, encoding='utf-8', timeout=30)
	return json.loads(proc.stdout)
# @used-by :func:`_build_ag_turn()`
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
# 2026-11-26
# "Add behavioral regression matrix for scope deferral and ask_question gating":
# https://github.com/dmitry-ai/harness/issues/377
class IncompleteScopeRegressionMatrixTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_live_pre_tool_subprocess_intercepts_ask_question_via_hooks_matcher(self) -> None:
		hooks = json.loads((WT_ROOT / 'platforms/antigravity/hooks.json').read_text(encoding='utf-8'))
		matcher = hooks['rules-and-server-gate']['PreToolUse'][0]['matcher']
		self.assertIsNotNone(re.fullmatch(matcher, 'ask_question'))
		res_arch = _run_hook_ask(Q1_Q3_ARCH)
		self.assertEqual('allow', res_arch['decision'], res_arch)
		res_q4 = _run_hook_ask([*Q1_Q3_ARCH, Q4_STEP_100])
		self.assertEqual('deny', res_q4['decision'], res_q4)
		self.assertIn('SCOPE-2-ASK-QUESTION-GATE', res_q4.get('reason', ''))
		res_669 = _run_hook_ask([{'question': 'Confirm when Harness fixes are applied:', 'options': ['Continue finalization', 'Cancel']}])
		self.assertEqual('deny', res_669['decision'], res_669)
		self.assertIn('--blocked-report', res_669.get('reason', ''))
	# @used-by :mod:`unittest`
	def test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			project, ev_dir, base_turn = _build_step_281_fixture(Path(tmp))
			turn_281 = {**base_turn, 'clarifications': STEP_100_102_CLAR}
			lc_281 = issue_lifecycle.code_and_issue_lifecycle_status(project, turn_281, turn_state={})
			self.assertFalse(lc_281['verified'], lc_281)
			v_joined = ' '.join(lc_281['violations'])
			self.assertIn('issues/337', v_joined)
			self.assertIn('issues/338', v_joined)
			self.assertNotIn('issues/339', v_joined)
			self.assertNotIn('issues/340', v_joined)
			issues_281, checks_281 = run_answer_gates(_gate_ctx(turn_281, lc_281, 'Phase 1 done; #337 left open for Phase 2.'))
			self.assertFalse(checks_281['code_lifecycle'])
			self.assertFalse(checks_281['scope_deferral'], issues_281)
			consent_turn = {**base_turn, 'clarifications': [{'ask_step': 10, 'answer_step': 12, 'answers': [{'id': 'A1', 'text': 'Stop the turn after Phase 1 and return control before Phase 2.'}]}]}
			lc_ok = issue_lifecycle.code_and_issue_lifecycle_status(project, consent_turn, turn_state={})
			self.assertTrue(lc_ok['verified'], lc_ok['violations'])
			_, checks_silent = run_answer_gates(_gate_ctx(consent_turn, lc_ok, 'Phase 1 done; #337 left open for Phase 2.'))
			self.assertFalse(checks_silent['scope_deferral'])
			issues_ok, checks_ok = run_answer_gates(_gate_ctx(consent_turn, lc_ok, 'Phase 2 deferred per explicit user confirmation A1 in ask_question.'))
			self.assertTrue(checks_ok['scope_deferral'], issues_ok)
			self.assertEqual([], issues_ok)
			issues_blk, checks_blk = run_answer_gates(_gate_ctx(turn_281, lc_281, 'Phase 2 deferred due to external API blocker (--blocked-report).', blocked_report=True))
			self.assertEqual([], issues_blk)
			self.assertFalse(checks_blk['code_lifecycle'])
			self.assertTrue(checks_blk['scope_deferral'], issues_blk)
			(ev_dir / 'issue-319.json').write_text(json.dumps({'url': f'https://github.com/{SLUG}/issues/319', 'number': 319, 'state': 'closed', 'title': 'Parent', 'body': '# Scope\n'}), encoding='utf-8')
			clean_turn = {'touched_files': base_turn['touched_files'], 'issue_actions': [a for a in base_turn['issue_actions'] if a['number'] not in (337, 338)]}
			lc_clean = issue_lifecycle.code_and_issue_lifecycle_status(project, clean_turn, turn_state={})
			self.assertTrue(lc_clean['verified'], lc_clean['violations'])
	# @used-by :mod:`unittest`
	def test_turn_begin_budget_check_isolates_fresh_code_turn_from_5h_history(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			code_proj, code_ag, code_cid = _build_ag_turn(base, 'code-repo', has_project_json=False, hist_status='delivered', hist_steps=8133)
			beg_code = completion.begin(code_proj, code_cid, platform='antigravity', backend=code_ag)
			self.assertFalse(beg_code['budget_check']['client_artifacts_scoped'])
			self.assertFalse(beg_code['budget_check']['graceful_checkpoint_required'], beg_code['budget_check'])
			self.assertLess(beg_code['budget_check']['window_5h_tool_steps'], 10)
			client_proj, client_ag, client_cid = _build_ag_turn(base, 'client-job', has_project_json=True, hist_status='open', hist_steps=450)
			beg_client = completion.begin(client_proj, client_cid, platform='antigravity', backend=client_ag)
			self.assertTrue(beg_client['budget_check']['client_artifacts_scoped'])
			self.assertTrue(beg_client['budget_check']['graceful_checkpoint_required'], beg_client['budget_check'])
if '__main__' == __name__:
	unittest.main()