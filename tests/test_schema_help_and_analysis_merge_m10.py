# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add schema-help CLI, validator hints, save-analysis --merge, and af-worker file handoff":
# https://github.com/dmitry-ai/harness/issues/217
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.claims import contract_issues
from agent_tools.cli_registry import execute_registered, registered_commands
from agent_tools.diagnostics import ValidationError
from agent_tools.experiments import requirement_issues
from agent_tools.review import ReviewReportValidator
def _intake_claim(cid: str, eid: str, quote: str, ptr: str, ref: str, sha: str) -> dict:
	return {
		'id': cid,
		'essence': quote,
		'assessment_basis': 'Verbatim intake quote.',
		'knowledge_type': 'client_report',
		'verification_status': 'verified',
		'scope': {'description': 'Saved intake file.', 'sample': [ref], 'limitations': ['Intake text only.']},
		'properties': ['content'],
		'missing_checks': [],
		'derived_from': [],
		'materiality': 'routine',
		'novelty': 'new',
		'category': 'descriptive',
		'impact': {'severity': 'unknown', 'basis': 'Not measured.', 'evidence_claim_ids': []},
		'probability_percent': 100,
		'addresses': [],
		'evidence': [{'id': eid, 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': sha, 'quote': quote, 'locator': {'type': 'json_pointer', 'value': ptr}}],
		'for': [{'argument': 'Exact intake statement.', 'evidence_id': eid}],
		'against': [],
		'counterevidence': {'status': 'not_found', 'reviewed_sources': [ref], 'limitations': 'Intake only.'},
	}
class SchemaHelpAndAnalysisMergeM10Tests(unittest.TestCase):
	def test_save_analysis_merge_supports_partial_draft_final_commit_and_patch(self) -> None:
		from agent_tools.analysis_merge import save_merged_analysis
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			raw = json.dumps({'job_id': '~01testm10', 'title': 'Store Feed Fix', 'concern': 'Feed lags prices'}).encode('utf-8')
			sha = hashlib.sha256(raw).hexdigest()
			intake = root / f'\ua616/KB/Evidence/{sha}.json'
			intake.parent.mkdir(parents=True, exist_ok=True)
			intake.write_bytes(raw)
			(root / '\ua616/project.json').write_text(json.dumps({'initialized': True, 'job_id': '~01testm10', 'snapshot': f'\ua616/KB/Evidence/{sha}.json'}), encoding='utf-8')
			ref = f'Evidence/{sha}.json'
			c_id = _intake_claim('F-TITLE', 'E-TITLE', 'Store Feed Fix', '/title', ref, sha)
			c_con = _intake_claim('F-CONCERN', 'E-CONCERN', 'Feed lags prices', '/concern', ref, sha)
			with self.assertRaises(ValidationError):
				save_merged_analysis(root, {'identity': [{**c_id, 'scope': {}}]}, partial=True)
			draft_res = save_merged_analysis(root, {'identity': [c_id], 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-TITLE'}]}, partial=True)
			self.assertTrue(draft_res['partial'])
			self.assertTrue((root / '\ua616/data/analysis-draft.json').is_file())
			self.assertFalse((root / '\ua616/KB/Analysis.json').is_file())
			notes = {'misconceptions': 'None established.', 'causes': 'Pending access.', 'methods': 'Pending access.'}
			final_res = save_merged_analysis(root, {'concerns': [c_con], 'notes': notes, 'red_flags': []}, partial=False)
			self.assertTrue(final_res['merged'])
			self.assertTrue(final_res['draft_cleared'])
			self.assertFalse((root / '\ua616/data/analysis-draft.json').is_file())
			saved = json.loads((root / '\ua616/KB/Analysis.json').read_text(encoding='utf-8'))
			self.assertEqual(['F-TITLE'], [x['id'] for x in saved['identity']])
			self.assertEqual(['F-CONCERN'], [x['id'] for x in saved['concerns']])
			patch_res = save_merged_analysis(root, {'notes': {'causes': 'Updated pending note.'}}, expected_sha256=final_res['sha256'], partial=False)
			self.assertNotEqual(final_res['sha256'], patch_res['sha256'])
			patched = json.loads((root / '\ua616/KB/Analysis.json').read_text(encoding='utf-8'))
			self.assertEqual('Updated pending note.', patched['notes']['causes'])
			self.assertEqual(['F-TITLE'], [x['id'] for x in patched['identity']])
	def test_schema_help_command_returns_contract_for_all_topics(self) -> None:
		from agent_tools.schema_help import format_schema_help_text
		from argparse import Namespace
		self.assertIn('schema-help', registered_commands())
		for topic, expected_ver in (('analysis', 3), ('experiment', 1), ('review', 2)):
			handled, res, code = execute_registered(Namespace(command='schema-help', topic=topic, format='json'))
			self.assertTrue(handled)
			self.assertEqual(0, code)
			self.assertEqual(expected_ver, res['schema_version'])
			self.assertTrue(res['required_fields'])
			self.assertTrue(res['enums'])
			self.assertTrue(res['minimal_example'])
			txt = format_schema_help_text(res)
			self.assertIn(topic, txt.lower())
	def test_validators_emit_actionable_hints(self) -> None:
		bad_analysis = {'schema_version': 3, 'facts': [], 'identity': [{'id': 'H-1', 'essence': 'X', 'assessment_basis': 'B', 'knowledge_type': 'hypothesis', 'verification_status': 'limited', 'scope': {}, 'properties': ['content'], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'derived_from': [], 'evidence': [], 'missing_checks': [], 'impact': {'severity': 'unknown', 'basis': 'B', 'evidence_claim_ids': []}, 'for': [{'argument': 'A'}], 'against': [], 'counterevidence': {'status': 'unavailable', 'reviewed_sources': ['x'], 'limitations': 'L'}, 'probability_percent': 50}], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {}}
		issues = contract_issues(bad_analysis)
		hints = [item.get('hint', '') for item in issues if item.get('hint')]
		self.assertTrue(any(('schema-help analysis' in h for h in hints)))
		self.assertIn('[hint:', str(ValidationError(issues)))
		exp_issues = requirement_issues([{'id': 'R-1'}])
		self.assertTrue(any(('schema-help experiment' in m for m in exp_issues)))
		pkg = {'risk': 'routine', 'claims': [{'claim_id': 'F-1', 'essence': 'Exact text', 'response_excerpt': 'Exact text'}]}
		rev_issues = ReviewReportValidator(pkg).validate({'schema_version': 1, 'result': 'maybe'})
		self.assertTrue(any(('schema-help review' in m for m in rev_issues)))
if '__main__' == __name__:
	unittest.main()
