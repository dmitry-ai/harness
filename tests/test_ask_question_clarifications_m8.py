# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, links
from agent_tools.platforms import antigravity
import check_markdown_slop
CID = '22222222-3333-4444-8555-666666666666'
STEP_669 = {
	'step_index': 669,
	'type': 'PLANNER_RESPONSE',
	'status': 'DONE',
	'created_at': '2026-11-24T03:49:04Z',
	'tool_calls': [{
		'name': 'ask_question',
		'args': {
			'questions': [{
				'is_multi_select': False,
				'options': ['Continue finalization', 'Cancel'],
				'question': 'Confirm when Harness fixes are applied:',
			}],
		},
	}],
}
STEP_670 = {
	'step_index': 670,
	'type': 'GENERIC',
	'status': 'DONE',
	'created_at': '2026-11-24T03:49:20Z',
	'content': 'Created At: 2026-11-24T06:49:20+03:00\nCompleted At: 2026-11-25T16:19:40+03:00\nCreated At: 2026-11-24T06:49:20+03:00\nCompleted At: 2026-11-25T16:19:40+03:00\nA1: \u041f\u0440\u043e\u0431\u043b\u0435\u043c\u0430 \u0443\u0441\u0442\u0440\u0430\u043d\u0435\u043d\u0430 \u0432 \u043e\u0442\u0432\u0435\u0442\u0435 250.\n\u0417\u0430\u0432\u0435\u0440\u0448\u0438 \u0441\u0432\u043e\u044e \u0437\u0430\u0434\u0430\u0447\u0443.',
}
# @used-by :meth:`AskQuestionClarificationsM8Tests.test_antigravity_scanner_and_turn_state_preserve_clarifications_without_breaking_user_turns()`
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
# 2026-11-25
# "Extract ask_question clarification metadata and prohibit Stop Gate bypass via ask_question":
# https://github.com/dmitry-ai/harness/issues/234
class AskQuestionClarificationsM8Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_scanner_and_turn_state_preserve_clarifications_without_breaking_user_turns(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / '\ua66e/\u227a').mkdir(parents=True)
			(proj / '\ua66e/\u227b').mkdir(parents=True)
			backend = base / 'ag_backend'
			(backend / 'conversations').mkdir(parents=True)
			tx = backend / 'brain' / CID / '.system_generated/logs/transcript_full.jsonl'
			tx.parent.mkdir(parents=True)
			req_text = 'Complete the pending analysis.'
			rows = [{'step_index': 434, 'type': 'USER_INPUT', 'content': req_text, 'created_at': '2026-11-24T03:00:00Z'}, STEP_669, STEP_670]
			tx.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n', encoding='utf-8')
			with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
				conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
				conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (CID, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 434, 'primary'))
				conn.commit()
			with closing(sqlite3.connect(backend / 'conversations' / f'{CID}.db')) as conn:
				conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
				conn.execute('INSERT INTO steps VALUES(434, 14, 3, 0, ?)', (_wire(19, _wire(2, req_text.encode('utf-8'))),))
				conn.commit()
			native = antigravity.native_answers(proj, CID, backend=backend)
			self.assertEqual(1, len(native['turns']))
			self.assertEqual(434, native['turns'][0]['start_step'])
			clar = native['turns'][0].get('clarifications') or []
			self.assertEqual(1, len(clar))
			self.assertEqual(669, clar[0]['ask_step'])
			self.assertEqual(670, clar[0]['answer_step'])
			self.assertIn('\u0417\u0430\u0432\u0435\u0440\u0448\u0438 \u0441\u0432\u043e\u044e \u0437\u0430\u0434\u0430\u0447\u0443.', clar[0]['answers'][0]['text'])
			beg = completion.begin(proj, CID, platform='antigravity', backend=backend)
			state_file = proj / beg['state']
			state_data = json.loads(state_file.read_text(encoding='utf-8'))
			self.assertEqual(clar, state_data.get('clarifications'))
	# @used-by :mod:`unittest`
	def test_extract_ask_question_clarifications_from_steps_669_670(self) -> None:
		from agent_tools.platforms.clarifications import extract_ask_question_clarifications
		items = extract_ask_question_clarifications([STEP_669, STEP_670])
		self.assertEqual(1, len(items))
		item = items[0]
		self.assertEqual(669, item['ask_step'])
		self.assertEqual(670, item['answer_step'])
		self.assertEqual('2026-11-25T16:19:40+03:00', item['answered_at'])
		self.assertEqual(['Confirm when Harness fixes are applied:'], item['questions'])
		self.assertEqual([{'id': 'A1', 'text': '\u041f\u0440\u043e\u0431\u043b\u0435\u043c\u0430 \u0443\u0441\u0442\u0440\u0430\u043d\u0435\u043d\u0430 \u0432 \u043e\u0442\u0432\u0435\u0442\u0435 250.\n\u0417\u0430\u0432\u0435\u0440\u0448\u0438 \u0441\u0432\u043e\u044e \u0437\u0430\u0434\u0430\u0447\u0443.'}], item['answers'])
	# @used-by :mod:`unittest`
	def test_skill_and_turn_completion_docs_prohibit_ask_question_stop_gate_bypass(self) -> None:
		for rel in ('skills/upwork-init/SKILL.md', 'references/turn-completion.md'):
			doc = WT_ROOT / rel
			text = doc.read_text(encoding='utf-8')
			self.assertIn('ask_question', text, rel)
			self.assertIn('--blocked-report', text, rel)
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), rel)
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(text), rel)
		self.assertIn('clarifications', (WT_ROOT / 'references/turn-completion.md').read_text(encoding='utf-8'))
if '__main__' == __name__:
	unittest.main()
