# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Surface ask_question clarifications in journal headers and require deferral disclosure":
# https://github.com/dmitry-ai/harness/issues/376
from __future__ import annotations
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, links, metadata, scope_deferral
from agent_tools.gates import run_answer_gates
import check_markdown_slop
STEP_100 = {
	'step_index': 100,
	'type': 'PLANNER_RESPONSE',
	'status': 'DONE',
	'created_at': '2026-11-26T12:42:49Z',
	'model': 'gemini-4-neon-xhigh',
	'tool_calls': [{
		'name': 'ask_question',
		'args': {'questions': [{'question': 'Choose execution scope?', 'options': ['Phase 1', 'All']}]},
	}],
}
STEP_102 = {
	'step_index': 102,
	'type': 'GENERIC',
	'status': 'DONE',
	'created_at': '2026-11-26T13:23:39Z',
	'content': 'Created At: 2026-11-26T15:42:49+03:00\nCompleted At: 2026-11-26T16:23:39+03:00\nA4: Phase 1 first.',
}
# @used-by :meth:`JournalClarificationsAndDisclosureTests.test_build_journal_metadata_includes_clarifications_and_preserves_user_input_hash()`
def _setup_ag_turn_with_clarifications(base: Path) -> tuple[Path, Path, str, str]:
	proj = base / 'demo-proj'
	proj.mkdir()
	backend = base / 'ag'
	(backend / 'conversations').mkdir(parents=True)
	cid = str(uuid.uuid4())
	log_path = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	log_path.parent.mkdir(parents=True)
	req_text = 'Execute sections 1 to 11.'
	rows = [{'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-26T12:33:03Z', 'content': req_text}, STEP_100, STEP_102]
	log_path.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_user_input_step_index INTEGER,title TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.resolve().as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, '1'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as conn:
		conn.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
		conn.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (_wire(19, _wire(2, req_text.encode('utf-8'))),))
		conn.execute('INSERT INTO steps VALUES(100,15,3,0,?)', (b'',))
		conn.commit()
	return (proj, backend, cid, req_text)
# @used-by :func:`_setup_ag_turn_with_clarifications()`
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
# "Surface ask_question clarifications in journal headers and require deferral disclosure":
# https://github.com/dmitry-ai/harness/issues/376
class JournalClarificationsAndDisclosureTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_build_journal_metadata_includes_clarifications_and_preserves_user_input_hash(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		with tempfile.TemporaryDirectory() as tmp:
			proj, backend, cid, req_text = _setup_ag_turn_with_clarifications(Path(tmp).resolve())
			clean_body = 'Phase 1 completed.'
			prepared = completion.prepare(proj, clean_body, cid, platform='antigravity', backend=backend, watch=False)
			self.assertTrue(prepared['ready'])
			self.assertEqual(hashlib.sha256(clean_body.encode('utf-8')).hexdigest(), prepared['body_sha256'])
			req_saved = (proj / '\ua66e/\u227b/1\u201320/1.md').read_text(encoding='utf-8')
			self.assertEqual(req_text, req_saved)
			res_raw = Path(prepared['response_file']).read_text(encoding='utf-8')
			parsed, extracted = metadata.extract_leading_metadata_header(res_raw)
			self.assertIsNotNone(parsed)
			self.assertEqual(clean_body, extracted)
			clars = parsed.get('Clarifications')
			self.assertIsInstance(clars, list)
			self.assertEqual(1, len(clars))
			self.assertEqual(100, clars[0]['Ask Step'])
			self.assertEqual(102, clars[0]['Answer Step'])
			self.assertEqual(['Choose execution scope?'], clars[0]['Questions'])
			self.assertEqual([{'ID': 'A4', 'Text': 'Phase 1 first.'}], clars[0]['Answers'])
			state_p = Path(prepared['turn_state']) if prepared.get('turn_state') else (proj / f"\ua616/data/turns/{prepared['turn_key']}.json")
			raw_state = {'clarifications': [{'ask_step': 5, 'answer_step': 6, 'asked_at': '2026-11-26T10:00:00Z', 'answered_at': 'not-a-ts', 'raw_output': 'Stop now.'}]}
			state_p.write_text(json.dumps(raw_state), encoding='utf-8')
			fb = metadata.build_journal_metadata(proj, {'platform': 'antigravity', 'conversation_id': cid}, {'turn_id': f'ag-{cid}-0'}, journal_dir=proj / '\ua66e', steps=[1], turn_key=prepared['turn_key'], turn_state_path=state_p, response_at=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc), tz=tz_plus3)
			self.assertEqual('Stop now.', fb['Clarifications'][0]['Raw Output'])
			self.assertEqual('2026-11-26 13:00:00 UTC+3', fb['Clarifications'][0]['Asked At'])
			self.assertEqual('not-a-ts', fb['Clarifications'][0]['Answered At'])
			empty_meta = metadata.build_journal_metadata(proj, {'platform': 'codex', 'conversation_id': cid}, {'turn_id': 't1'}, journal_dir=proj / '\ua66e', steps=[1], turn_key='none', turn_state_path=proj / 'missing.json', response_at=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc), tz=tz_plus3)
			self.assertNotIn('Clarifications', empty_meta)
	# @used-by :mod:`unittest`
	def test_deferral_disclosure_gate_rejects_silent_response_and_accepts_disclosed_rationale(self) -> None:
		lc = {'verified': True, 'deferred_children': [{'parent': 'https://github.com/dmitry-ai/harness/issues/319', 'children': ['https://github.com/dmitry-ai/harness/issues/337']}]}
		consent_turn = {'clarifications': [{'ask_step': 10, 'answer_step': 12, 'answers': [{'id': 'A1', 'text': '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438 \u0445\u043e\u0434 \u043f\u043e\u0441\u043b\u0435 \u0424\u0430\u0437\u044b 1.'}]}]}
		silent = '\u0424\u0430\u0437\u0430 1 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430; #337 \u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u043c \u0434\u043b\u044f \u0424\u0430\u0437\u044b 2, \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0432 continuation.md.'
		res_silent = scope_deferral.evaluate_scope_deferral(consent_turn, {}, lc, silent)
		self.assertFalse(res_silent['verified'], res_silent)
		self.assertTrue(any(('disclosure' in v for v in res_silent['violations'])), res_silent['violations'])
		reason_only = scope_deferral.evaluate_scope_deferral(consent_turn, {}, lc, '\u0424\u0430\u0437\u0430 2 \u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0435\u043d\u0430 \u0438\u0437-\u0437\u0430 \u0431\u043e\u043b\u044c\u0448\u043e\u0433\u043e \u043e\u0431\u044a\u0451\u043c\u0430.')
		self.assertFalse(reason_only['verified'], reason_only)
		disclosed = '\u0424\u0430\u0437\u0430 2 \u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0435\u043d\u0430 \u043f\u043e \u0441\u043e\u0433\u043b\u0430\u0441\u0438\u044e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f (\u043e\u0442\u0432\u0435\u0442 A1 \u0432 ask_question).'
		ctx = {'role': 'primary', 'blocked_report': False, 'turn': consent_turn, 'value': {}, 'response': disclosed, 'doc4_errs': [], 'link_errs': [], 'prob_errs': [], 'source_errs': [], 'lang_errs': [], 'exec5_chk': {'verified': True, 'violations': []}, 'http_chk': {'verified': True, 'violations': []}, 'comp_chk': {'verified': True}, 'evicted_cited': [], 'del_chk': {'verified': True}, 'issue_first_chk': {'verified': True, 'violations': []}, 'lifecycle_chk': lc, 'tdd_chk': {'verified': True, 'violations': []}, 'wf_errs': []}
		issues_ok, checks_ok = run_answer_gates(ctx)
		self.assertTrue(checks_ok['scope_deferral'], issues_ok)
		self.assertEqual([], issues_ok)
		blk_silent = scope_deferral.evaluate_scope_deferral({}, {}, lc, silent, blocked_report=True)
		self.assertFalse(blk_silent['verified'], blk_silent)
		blk_ok = scope_deferral.evaluate_scope_deferral({}, {}, lc, '\u0424\u0430\u0437\u0430 2 \u043e\u0442\u043b\u043e\u0436\u0435\u043d\u0430 \u0438\u0437-\u0437\u0430 \u0432\u043d\u0435\u0448\u043d\u0435\u0433\u043e \u0431\u043b\u043e\u043a\u0435\u0440\u0430 API (--blocked-report).', blocked_report=True)
		self.assertTrue(blk_ok['verified'], blk_ok)
	# @used-by :mod:`unittest`
	def test_turn_completion_doc_covers_clarifications_header_and_deferral_disclosure(self) -> None:
		doc = WT_ROOT / 'references/turn-completion.md'
		text = doc.read_text(encoding='utf-8')
		self.assertIn('Clarifications', text)
		self.assertIn('scope_deferral_check', text)
		self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(text))
if '__main__' == __name__:
	unittest.main()