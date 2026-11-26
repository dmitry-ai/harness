# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.platforms import antigravity
from agent_tools.platforms.trace_common import persist_review_proof, verify_review_proof_core
PARENT_ID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
REVIEWER_ID = '8ec25783-99cc-40fa-99ff-a557eb04dde3'
def _base_exec_meta(configs: list[str], extra_sources: list[dict] | None=None) -> dict:
	sources = [
		{'native_file': 'r.db', 'table': 'gen_metadata', 'row': 0, 'protobuf_path': [1, 19], 'sha256': 'aa' * 32},
		{'native_file': 'r.db', 'table': 'executor_metadata', 'row': 0, 'protobuf_path': [10, 1, 28], 'sha256': 'bb' * 32},
	] + list(extra_sources or [])
	return {
		'schema_version': 1,
		'surface': 'antigravity-ui',
		'role': 'AA',
		'conversation_id': REVIEWER_ID,
		'parent_id': PARENT_ID,
		'requested': {'model': 'gemini-4-neon', 'generation_model': 'gemini-4-neon', 'executor_model': 'gemini-4-neon', 'effort': 'xhigh', 'selection': 'inherit'},
		'observed': {'model': 'gemini-4-neon', 'generation_model': 'gemini-4-neon', 'executor_model': 'gemini-4-neon', 'effort': 'xhigh', 'configuration': 'gemini-4-neon-xhigh', 'model_ids': [1535]},
		'observation_history': {
			'generations': [{'index': 0, 'value': 'gemini-4-neon'}],
			'configurations': [{'index': idx, 'value': val} for idx, val in enumerate(configs)],
			'model_ids': [{'step': 1, 'value': 1535}],
		},
		'metadata_sources': sources,
		'verification': {'status': 'verified', 'model': 'verified', 'effort': 'verified', 'detail': 'ok'},
	}
def _make_proof(log_path: Path, final_text: str, exec_meta: dict) -> dict:
	return {
		'surface': 'antigravity-ui',
		'parent_id': PARENT_ID,
		'reviewer_id': REVIEWER_ID,
		'agent_name': 'self',
		'status': 'completed',
		'project_kind': 'upwork',
		'job_id': '022124567641351805598',
		'native_log': str(log_path),
		'native_log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest(),
		'final_step': 10,
		'final_response_sha256': hashlib.sha256(final_text.encode('utf-8')).hexdigest(),
		'final_response': final_text,
		'executor_metadata': exec_meta,
	}
# 2026-11-24
# "Verify reused reviewer package assignments and tolerate volatile executor metadata":
# https://github.com/dmitry-ai/harness/issues/222
class ReusedReviewerAndMetadataDriftM5Tests(unittest.TestCase):
	def test_verify_native_proof_accepts_reused_reviewer_send_message_and_rejects_self_mention(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			log = root / 'transcript_full.jsonl'
			rows = [
				{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-22T23:06:28Z sender={PARENT_ID} content=Audit old-pkg-inputs.json\n</SYSTEM_MESSAGE>'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': '{"result":"approved"}'},
				{'step_index': 6, 'type': 'SYSTEM_MESSAGE', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-24T03:20:00Z sender={PARENT_ID} content=Audit new-pkg-inputs.json\n</SYSTEM_MESSAGE>'},
				{'step_index': 8, 'type': 'SYSTEM_MESSAGE', 'content': '<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-24T03:21:00Z sender=00000000-0000-0000-0000-000000000000 content=Audit foreign-pkg-inputs.json\n</SYSTEM_MESSAGE>'},
				{'step_index': 10, 'type': 'PLANNER_RESPONSE', 'content': '{"package":"forged-pkg-inputs.json","result":"approved"}'},
			]
			log.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			final_text = rows[-1]['content']
			meta = _base_exec_meta(['gemini-4-neon-xhigh'])
			saved = persist_review_proof(root, REVIEWER_ID, hashlib.sha256(log.read_bytes()).hexdigest(), final_text, _make_proof(log, final_text, meta), write=True)
			live = {**saved}
			with patch.object(antigravity, '_proof_paths', return_value={'backend_dir': str(root), 'instance': 'A0'}), patch.object(antigravity, 'native_review_proof', return_value=live):
				verified = antigravity.verify_native_proof(root, saved, package='new-pkg-inputs.json')
				self.assertEqual(REVIEWER_ID, verified['reviewer_id'])
				with self.assertRaises(ValueError):
					antigravity.verify_native_proof(root, saved, package='forged-pkg-inputs.json')
				with self.assertRaises(ValueError):
					antigravity.verify_native_proof(root, saved, package='foreign-pkg-inputs.json')
	def test_tolerates_monotonic_same_model_metadata_append_and_rejects_model_change(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			log = root / 'transcript_full.jsonl'
			log.write_text('{"step_index":0,"type":"USER_INPUT","content":"Audit pkg-inputs.json"}\n', encoding='utf-8')
			final_text = '{"result":"approved"}'
			digest = hashlib.sha256(log.read_bytes()).hexdigest()
			saved_meta = _base_exec_meta(['gemini-4-neon-xhigh', 'gemini-4-neon-xhigh'])
			live_meta = _base_exec_meta(
				['gemini-4-neon-xhigh', 'gemini-4-neon-xhigh', 'gemini-4-neon-xhigh'],
				extra_sources=[{'native_file': 'r.db', 'table': 'executor_metadata', 'row': 2, 'protobuf_path': [10, 1, 28], 'sha256': 'cc' * 32}],
			)
			saved = persist_review_proof(root, REVIEWER_ID, digest, final_text, _make_proof(log, final_text, saved_meta), write=True)
			live_proof = _make_proof(log, final_text, live_meta)
			repersisted = persist_review_proof(root, REVIEWER_ID, digest, final_text, dict(live_proof), write=True)
			self.assertEqual(saved['proof'], repersisted['proof'])
			live_with_authored = {**live_proof, 'authored_response': saved['authored_response']}
			checked = verify_review_proof_core(root, saved, live_with_authored, ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'), allow_legacy_generation_model=True)
			self.assertEqual(REVIEWER_ID, checked['reviewer_id'])
			drift_meta = _base_exec_meta(
				['gemini-4-neon-xhigh', 'gemini-4-neon-xhigh', 'gemini-3-flash-low'],
				extra_sources=[{'native_file': 'r.db', 'table': 'executor_metadata', 'row': 2, 'protobuf_path': [10, 1, 28], 'sha256': 'dd' * 32}],
			)
			drift_proof = _make_proof(log, final_text, drift_meta)
			with self.assertRaises(ValueError):
				persist_review_proof(root, REVIEWER_ID, digest, final_text, dict(drift_proof), write=True)
			with self.assertRaises(ValueError):
				verify_review_proof_core(root, saved, {**drift_proof, 'authored_response': saved['authored_response']}, ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'), allow_legacy_generation_model=True)
if '__main__' == __name__:
	unittest.main()
