# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, evidence, evidence_loader, knowledge, path_registry, research, review, runtime, shell_audit, workflow
from agent_tools.platforms import trace_common
_HTML_DOC = b'<!doctype html><html><head><title>Sample</title></head><body><h1 id="sec-1">Heading One</h1><p>Section body quote and Plain body quote.</p></body></html>'
def _build_html_obs_project(root: Path, url: str) -> tuple[str, dict]:
	(root / '\ua616/KB').mkdir(parents=True, exist_ok=True)
	(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
	obs = research.collect(root, url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', _HTML_DOC))
	research.extract_observation(root, obs['observation'], 'html')
	r = (obs['observation'], research.load_observation(root, obs['observation']))
	return r
def _write_minimal_v3_project(root: Path, url: str) -> str:
	obs_ref, meta = _build_html_obs_project(root, url)
	analysis_obj = {
		'schema_version': 3,
		'facts': [{'id': 'F-1', 'essence': 'Section body quote.', 'assessment_basis': 'Saved HTML.', 'knowledge_type': 'observation', 'verification_status': 'verified', 'scope': {'description': 'Single page.', 'sample': [url], 'limitations': ['Static HTML.']}, 'properties': ['content'], 'derived_from': [], 'evidence': [{'id': 'E-1', 'kind': 'observation', 'source': url, 'observation': obs_ref, 'source_sha256': meta['body_sha256'], 'quote': 'Section body quote', 'locator': {'type': 'text', 'value': 'Section body quote'}}], 'missing_checks': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'Unmeasured.', 'evidence_claim_ids': []}}],
		'identity': [{'id': 'H-ID', 'essence': 'Client site is example.test.', 'assessment_basis': 'Saved HTML.', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'scope': {'description': 'Single page.', 'sample': [url], 'limitations': ['Static HTML.']}, 'properties': ['content'], 'derived_from': [], 'evidence': [{'id': 'E-2', 'kind': 'observation', 'source': url + '#sec-1', 'observation': obs_ref, 'source_sha256': meta['body_sha256'], 'quote': 'Section body quote', 'locator': {'type': 'anchor', 'value': 'sec-1'}}], 'missing_checks': ['Verify DNS ownership.'], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'Unmeasured.', 'evidence_claim_ids': []}, 'probability_percent': 70, 'addresses': [], 'for': [{'argument': 'Matches page.', 'evidence_id': 'E-2'}], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': [url], 'limitations': 'Static HTML.'}}],
		'concerns': [],
		'misconceptions': [],
		'causes': [],
		'methods': [],
		'notes': {'concerns': 'None.', 'misconceptions': 'None.', 'causes': 'None.', 'methods': 'None.'},
		'websites': [{'role': 'target', 'url': url, 'basis_id': 'H-ID'}],
		'red_flags': [],
	}
	(root / '\ua616/KB/Analysis.json').write_text(json.dumps(analysis_obj, ensure_ascii=False, indent=2), encoding='utf-8')
	(root / '.md').write_text('# Project\n', encoding='utf-8')
	knowledge.sync_website_card(root, analysis_obj)
	(root / '\ua616/project.json').write_text(json.dumps({'schema_version': 1, 'job_id': '~0123456789abcdef', 'url': 'https://www.upwork.com/jobs/~0123456789abcdef'}, ensure_ascii=False, indent=2), encoding='utf-8')
	(root / '\ua616/data/workflow.json').write_text(json.dumps({'schema_version': 1, 'project_root': str(root.resolve()), 'job_id': '~0123456789abcdef', 'requests': [{'id': 'r1', 'text': 'Analyze'}], 'questions': {}, 'stages': {'finalize': {'status': 'pending'}}, 'reviews': []}, ensure_ascii=False, indent=2), encoding='utf-8')
	return obs_ref
def _write_fake_ag_backend(tmp: Path, root: Path, cid: str) -> Path:
	backend = tmp / 'backend'
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	logs = backend / 'brain' / cid / '.system_generated/logs'
	logs.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(backend / 'conversation_summaries.db') as conn:
		conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, parent_conversation_id TEXT, agent_name TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, workspace_uris TEXT, project_id TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES (?,?,?,?,?,?,?,?,?)', (cid, '', 'primary', 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, json.dumps([root.as_uri()]), ''))
	with sqlite3.connect(backend / 'conversations' / f'{cid}.db') as conn:
		conn.execute('CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		conn.execute('INSERT INTO steps VALUES (0, 14, 5, 0, ?)', (b'',))
		conn.execute('INSERT INTO steps VALUES (1, 15, 3, 0, ?)', (b'',))
	rows = [
		{'step_index': 0, 'type': 'USER_INPUT', 'content': '<USER_REQUEST>\nCheck status\n</USER_REQUEST>', 'created_at': '2026-11-24T05:00:00Z'},
		{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'echo ok'}}], 'created_at': '2026-11-24T05:00:01Z'},
		{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\nok', 'created_at': '2026-11-24T05:00:02Z'},
	]
	(logs / 'transcript_full.jsonl').write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	return backend
class RuntimeCacheAndEvidenceFastpathM9Tests(unittest.TestCase):
	def test_authorize_deduplicates_evidence_issues_across_check_project(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td) / 'proj'
			_write_minimal_v3_project(root, 'https://example.test/page')
			state = workflow.load(root)
			calls = []
			orig_ev = evidence.evidence_issues
			def _spy(r_arg, val_arg, **kw):
				calls.append(kw.get('skip_structural', False))
				return orig_ev(r_arg, val_arg, **kw)
			with mock.patch.object(evidence, 'evidence_issues', side_effect=_spy), mock.patch.object(workflow, 'evidence_issues', side_effect=_spy):
				with self.assertRaisesRegex(ValueError, 'Need current answer-bound'):
					review.authorize(root, state, response='Candidate text.')
			self.assertEqual(len(calls), 1)
	def test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td) / 'proj'
			url = 'https://example.test/doc'
			obs_ref, meta = _build_html_obs_project(root, url)
			meta_with_obs = {**meta, 'observation': obs_ref}
			parse_calls = []
			orig_extract = evidence_loader.extract_bytes
			def _spy_extract(*args, **kwargs):
				parse_calls.append(1)
				return orig_extract(*args, **kwargs)
			with mock.patch.object(evidence_loader, 'extract_bytes', side_effect=_spy_extract):
				self.assertEqual(evidence_loader.probe_observation_status(root, meta_with_obs, url, fragment='sec-1'), 'http-ok')
				evidence.verify_saved_quote(root, url, 'Plain body quote', observation=obs_ref)
				evidence.verify_saved_quote(root, url, 'Heading One', observation=obs_ref)
				self.assertEqual(len(parse_calls), 0)
				evidence.verify_saved_quote(root, url + '#sec-1', 'Section body quote', observation=obs_ref)
				evidence.verify_saved_quote(root, url + '#sec-1', 'Heading One', observation=obs_ref)
				self.assertEqual(len(parse_calls), 1)
				(root / '\ua616/KB' / obs_ref).with_name('extracted-html.json').unlink()
				path_registry.clear_registry_cache()
				self.assertEqual(evidence_loader.probe_observation_status(root, meta_with_obs, url, fragment='sec-1'), 'http-ok')
				self.assertEqual(len(parse_calls), 2)
	def test_runtime_cache_import_skips_path_registry(self) -> None:
		probe = 'import sys; sys.path.insert(0, sys.argv[1]); import agent_tools.runtime_cache; print("agent_tools.path_registry" in sys.modules)'
		out = subprocess.check_output([sys.executable, '-c', probe, str(SCRIPTS)], stdin=subprocess.DEVNULL, text=True, timeout=15).strip()
		self.assertEqual(out, 'False')
	def test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			rt = Path(td) / 'runtime.json'
			base = {'version': 2, 'workspace_root': '%HARNESS_M9_ENV_DIR%', 'timezone': 'Europe/Istanbul', 'platforms': {'antigravity': {'enabled': True, 'instances': {'A0': {'enabled': True, 'home': td}}}}}
			rt.write_text(json.dumps(base), encoding='utf-8')
			loads_count = []
			orig_loads = json.loads
			def _spy_loads(s, *a, **kw):
				if 'HARNESS_M9_ENV_DIR' in str(s):
					loads_count.append(1)
				return orig_loads(s, *a, **kw)
			with mock.patch.dict(os.environ, {'HARNESS_M9_ENV_DIR': 'C:/work/m9_a'}):
				path_registry.clear_registry_cache()
				with mock.patch.object(json, 'loads', side_effect=_spy_loads):
					first = runtime.settings(rt)
					second = runtime.settings(rt)
				self.assertEqual(len(loads_count), 1)
				self.assertEqual(first['workspace_root'], 'C:/work/m9_a')
				first['timezone'] = 'Mutated/Zone'
				self.assertEqual(runtime.settings(rt)['timezone'], 'Europe/Istanbul')
				self.assertEqual(second['timezone'], 'Europe/Istanbul')
			with mock.patch.dict(os.environ, {'HARNESS_M9_ENV_DIR': 'C:/work/m9_b'}):
				third = runtime.settings(rt)
				self.assertEqual(third['workspace_root'], 'C:/work/m9_b')
				base['timezone'] = 'UTC'
				rt.write_text(json.dumps(base, indent=2), encoding='utf-8')
				self.assertEqual(runtime.settings(rt)['timezone'], 'UTC')
			custom_cfg = {'platforms': {'antigravity': {'browser': {'cdp_port': 19444}}}}
			with mock.patch.object(runtime, 'settings', return_value=custom_cfg):
				self.assertEqual(shell_audit.protected_browser_perimeter()['ports'], [19444])
	def test_tdd_and_issue_first_check_skip_shell_violation_scanning(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			root = tmp / 'proj'
			(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
			cid = '11111111-2222-3333-4444-555555555555'
			backend = _write_fake_ag_backend(tmp, root, cid)
			with mock.patch.object(trace_common, 'collect_shell_violations', wraps=trace_common.collect_shell_violations) as spy:
				tdd_res = completion.tdd_check_turn(root, conversation=cid, platform='antigravity', backend=backend)
				if_res = completion.issue_first_check_turn(root, conversation=cid, platform='antigravity', backend=backend)
				self.assertTrue(tdd_res['valid'])
				self.assertTrue(if_res['valid'])
				self.assertEqual(spy.call_count, 0)
				full_res = completion._native(root, cid, platform='antigravity', backend=backend)
				self.assertTrue(full_res['turns'])
				self.assertGreaterEqual(spy.call_count, 1)
if '__main__' == __name__:
	unittest.main()
