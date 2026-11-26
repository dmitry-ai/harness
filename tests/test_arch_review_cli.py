# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing, redirect_stdout
from pathlib import Path
from typing import override
from unittest.mock import patch
import argparse
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_PARENT_ID = '11111111-1111-4111-8111-111111111111'
_REVIEWER_ID = '22222222-2222-4222-8222-222222222222'
# 2026-11-26 "Add arch-auditor subagent role and content-addressed review CLI": https://github.com/dmitry-ai/harness/issues/361
# @used-by :func:`_seed_ag_arch_backend()`
# @used-by :func:`_seed_codex_arch_home()`
# @used-by :meth:`ArchReviewCliTests.test_review_project_id_and_fields_support_bare_code_workspace_for_arch_only()`
def _init_text_workspace(proj: Path) -> None:
	from agent_tools.path_registry import project_paths
	from agent_tools.platforms.request_binding import text_project_id
	pp = project_paths(proj, exact_root=True)
	pp.text_project_json.parent.mkdir(parents=True, exist_ok=True)
	pp.text_project_json.write_text(json.dumps({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(pp.root), 'id': text_project_id(pp.root)}), encoding='utf-8')
# 2026-11-26 "Add arch-auditor subagent role and content-addressed review CLI": https://github.com/dmitry-ai/harness/issues/361
# @used-by :meth:`ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
def _run_arch_cli(argv: list[str]) -> tuple[int, str]:
	from agent_tools.cli_registry import add_registered_parsers, dispatch_registered
	parser = argparse.ArgumentParser()
	add_registered_parsers(parser.add_subparsers(dest='command', required=True))
	ns = parser.parse_args(argv)
	buf = io.StringIO()
	with redirect_stdout(buf):
		_, code = dispatch_registered(ns, lambda res: sys.stdout.write(json.dumps(res)), lambda res: 0 if res.get('valid', True) else 2)
	return (0 if None is code else int(code), buf.getvalue())
# @used-by :meth:`ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`ArchReviewCliTests.test_antigravity_native_review_proof_supports_arch_auditor_role()`
# @used-by :meth:`ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
# @used-by :meth:`ArchReviewCliTests.test_cli_registry_and_send_message_gate_expose_arch_commands_and_block_verdict_duplication()`
# @used-by :meth:`ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
# @used-by :meth:`ArchReviewCliTests.test_validator_rejects_pattern_washing_and_rubber_stamp_approvals()`
def _sample_verdict(pkg_rel: str, pkg_sha: str, *, result: str='approved', outcome: str='grounded', participants_ok: bool=True, findings: list | None=None) -> dict:
	return {
		'schema_version': 1,
		'review_mode': 'falsifier',
		'package': pkg_rel,
		'package_sha256': pkg_sha,
		'result': result,
		'summary': 'Verified Strategy pattern participants and collaboration against module symbols.',
		'pattern_checks': [{'pattern': 'Strategy', 'category': 'Behavioral', 'participants_verified': participants_ok, 'overengineering_risk': 'low', 'outcome': outcome, 'evidence': 'Checked module symbols.'}],
		'findings': [] if None is findings else findings,
	}
# 2026-11-27 "Pass ARCH role through Antigravity native_review_proof binding": https://github.com/dmitry-ai/harness/issues/393
# @used-by :meth:`ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`ArchReviewCliTests.test_antigravity_native_review_proof_supports_arch_auditor_role()`
# @used-by :meth:`ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
def _seed_ag_arch_backend(root: Path, project: Path, pkg_rel: str, verdict_json: str, *, init_text: bool=True) -> Path:
	if init_text:
		_init_text_workspace(project)
	backend = root / 'ag-backend'
	brain = backend / 'brain'
	convs = backend / 'conversations'
	for d in (brain / _PARENT_ID / '.system_generated/logs', brain / _REVIEWER_ID / '.system_generated/logs', convs):
		d.mkdir(parents=True, exist_ok=True)
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, parent_conversation_id TEXT, agent_name TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER)')
		ws_json = json.dumps([project.as_uri()])
		conn.execute('INSERT INTO conversation_summaries VALUES (?, ?, ?, ?, ?, ?)', (_PARENT_ID, None, 'main', ws_json, 'IDLE', 0))
		conn.execute('INSERT INTO conversation_summaries VALUES (?, ?, ?, ?, ?, ?)', (_REVIEWER_ID, _PARENT_ID, 'arch-auditor', ws_json, 'IDLE', 0))
		conn.commit()
	for cid, steps in ((_PARENT_ID, [(0, 14, 3)]), (_REVIEWER_ID, [(0, 14, 3), (1, 15, 3)])):
		with closing(sqlite3.connect(convs / f'{cid}.db')) as conn:
			conn.execute('CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB, metadata BLOB)')
			for idx, stype, status in steps:
				conn.execute('INSERT INTO steps VALUES (?, ?, ?, 0, NULL, NULL)', (idx, stype, status))
			conn.commit()
	prompt = f'Audit architecture package {pkg_rel} in {project.as_posix()} as independent read-only falsifier.'
	parent_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Design new module'}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'arch-auditor', 'Prompt': prompt, 'Model': 'inherit'}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': _REVIEWER_ID}]
	child_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': prompt}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': verdict_json}]
	(brain / _PARENT_ID / '.system_generated/logs/transcript_full.jsonl').write_text('\n'.join((json.dumps(r) for r in parent_rows)) + '\n', encoding='utf-8')
	(brain / _REVIEWER_ID / '.system_generated/logs/transcript_full.jsonl').write_text('\n'.join((json.dumps(r) for r in child_rows)) + '\n', encoding='utf-8')
	return backend
# 2026-11-26 "Add arch-auditor subagent role and content-addressed review CLI": https://github.com/dmitry-ai/harness/issues/361
# 2026-11-27 "Pass ARCH role through Codex native_review_proof binding": https://github.com/dmitry-ai/harness/issues/394
# @used-by :meth:`ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
def _seed_codex_arch_home(root: Path, project: Path, pkg_rel: str, receipt: dict, verdict_json: str, *, init_text: bool=True) -> Path:
	if init_text:
		_init_text_workspace(project)
	cx_home = root / 'codex-home'
	sess = cx_home / 'sessions/2026/11/26'
	sess.mkdir(parents=True, exist_ok=True)
	p_path, c_path = (sess / f'{_PARENT_ID}.jsonl', sess / f'{_REVIEWER_ID}.jsonl')
	prompt = f'Audit architecture package {pkg_rel} in {project.as_posix()} as independent read-only falsifier.'
	parent_rows = [
		{'type': 'session_meta', 'payload': {'id': _PARENT_ID, 'cwd': str(project), 'source': 'vscode'}},
		{'type': 'turn_context', 'payload': {'model': 'gpt-5-codex', 'effort': 'high', 'cwd': str(project)}},
		{'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Audit architecture'}]}},
		{'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent', 'call_id': 'spawn-arch', 'arguments': json.dumps({'task_name': 'arch-auditor', 'message': prompt})}},
	]
	child_rows = [
		{'type': 'session_meta', 'payload': {'id': _REVIEWER_ID, 'cwd': str(project), 'source': {'subagent': {'thread_spawn': {'parent_thread_id': _PARENT_ID, 'agent_path': '/root/arch-auditor'}}}}},
		{'type': 'turn_context', 'payload': {'model': 'gpt-5-codex', 'effort': 'high'}},
		{'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'arch-inp', 'name': 'exec', 'input': f'python harness.py arch-review-input "{project}" --package "{pkg_rel}"'}},
		{'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'arch-inp', 'output': [{'type': 'input_text', 'text': json.dumps(receipt)}]}},
		{'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': verdict_json}},
	]
	p_path.write_text('\n'.join((json.dumps(r) for r in parent_rows)) + '\n', encoding='utf-8')
	c_path.write_text('\n'.join((json.dumps(r) for r in child_rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(cx_home / 'state_1.sqlite')) as conn:
		conn.execute('CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
		conn.execute('INSERT INTO threads VALUES (?, ?, ?)', (_PARENT_ID, str(p_path), None))
		conn.execute('INSERT INTO threads VALUES (?, ?, ?)', (_REVIEWER_ID, str(c_path), '/root/arch-auditor'))
		conn.commit()
	return cx_home
# 2026-11-26 "Add arch-auditor subagent role and content-addressed review CLI": https://github.com/dmitry-ai/harness/issues/361
class ArchReviewCliTests(unittest.TestCase):
	# @used-by :meth:`unittest.TestCase.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`unittest.TestCase.setUp()`
	@override
	def setUp(self) -> None:
		p = patch('agent_tools.runtime.default_runtime_file', return_value=WT_ROOT / 'runtime.json')
		p.start()
		self.addCleanup(p.stop)
	# 2026-11-27 "Pass ARCH role through Antigravity native_review_proof binding": https://github.com/dmitry-ai/harness/issues/393
	# @used-by :mod:`unittest`
	def test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker(self) -> None:
		from agent_tools.platforms import antigravity as ag
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, scratch = (base / 'bare-ag', base / 'bare-ag/\ua616/data/scratch')
			scratch.mkdir(parents=True)
			resp_f, rep_f, ev_f = (scratch / 'cand.md', scratch / 'ok.json', scratch / 'ev.json')
			resp_f.write_text('Proposed Strategy routing with clear separation.\n', encoding='utf-8')
			code_p, out_p = _run_arch_cli(['arch-prepare', str(proj), '--parent', _PARENT_ID, '--kind', 'response', '--response-file', str(resp_f), '--consume-input'])
			self.assertEqual(0, code_p)
			prep = json.loads(out_p)
			verdict_bytes = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			rep_f.write_bytes(verdict_bytes)
			backend = _seed_ag_arch_backend(base, proj, prep['package'], verdict_bytes.decode('utf-8'), init_text=False)
			self.assertFalse((proj / '\ua616/data/text-project.json').exists())
			self.assertFalse((proj / '\ua616/project.json').exists())
			proof = ag.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=backend, role='ARCH')
			self.assertEqual('code_workspace', proof['project_kind'])
			self.assertIsNone(proof['job_id'])
			self.assertEqual('ARCH', proof['executor_metadata']['role'])
			ev_f.write_text(json.dumps(proof), encoding='utf-8')
			with patch.object(ag, 'platform_instances', return_value={}), patch.object(ag, '_default_platform_paths', return_value={'backend_dir': str(backend)}):
				verified = ag.verify_native_proof(proj, proof, package=Path(prep['package']).name)
				self.assertEqual('code_workspace', verified['project_kind'])
				code_ok, out_ok = _run_arch_cli(['arch-record-review', str(proj), '--report', str(rep_f), '--parent', _PARENT_ID, '--reviewer', _REVIEWER_ID, '--native-evidence', str(ev_f), '--consume-input'])
			self.assertEqual(0, code_ok, out_ok)
			self.assertEqual('approved', json.loads(out_ok)['result'])
			with self.assertRaises(ValueError):
				ag.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=backend, role='AA')
	# @used-by :mod:`unittest`
	def test_antigravity_native_review_proof_supports_arch_auditor_role(self) -> None:
		from agent_tools.platforms import antigravity as ag
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'proj'
			(proj / '\ua616/data/arch-reviews/packages').mkdir(parents=True)
			pkg_rel = '\ua616/data/arch-reviews/packages/demo.json'
			(proj / pkg_rel).write_text('{"ok": true}', encoding='utf-8')
			verdict_str = json.dumps(_sample_verdict(pkg_rel, 'a' * 64))
			backend = _seed_ag_arch_backend(base, proj, pkg_rel, verdict_str)
			proof = ag.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=backend, role='ARCH')
			self.assertEqual('arch-auditor', proof['agent_name'])
			self.assertEqual('ARCH', proof['executor_metadata']['role'])
			with self.assertRaises(ValueError):
				ag.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=backend, role='AA')
	# @used-by :mod:`unittest`
	def test_arch_check_cli_executes_cleanly(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'arch-check', td, '--format', 'json'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			out = json.loads(proc.stdout)
			self.assertTrue(out['valid'])
	# 2026-11-27 "Forward reviewer role in build_native_review_proof": https://github.com/dmitry-ai/harness/issues/392
	# @used-by :mod:`unittest`
	def test_build_native_review_proof_forwards_arch_role_on_bare_workspace(self) -> None:
		from agent_tools.platforms.trace_common import build_native_review_proof
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'bare-proj'
			proj.mkdir()
			proof = build_native_review_proof(proj, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'arch-auditor', base / 'child.jsonl', base / 'parent.jsonl', b'{}\n', 1, '{"result": "approved"}', ['Audit architecture package as independent read-only falsifier.'], [], write=False, role='ARCH')
			self.assertEqual('code_workspace', proof['project_kind'])
			self.assertIsNone(proof['job_id'])
			self.assertTrue(proof['project_id'].startswith('text-'))
			with self.assertRaises(ValueError):
				build_native_review_proof(proj, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'self', base / 'child.jsonl', base / 'parent.jsonl', b'{}\n', 1, '{"result": "approved"}', ['Audit package.'], [], write=False, role='AA')
	# @used-by :mod:`unittest`
	def test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip(self) -> None:
		from agent_tools import metrics
		from agent_tools.platforms import antigravity as ag
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, scratch = (base / 'proj', base / 'proj/\ua616/data/scratch')
			scratch.mkdir(parents=True)
			resp_f, nc_f, ok_f, ev_f = (scratch / 'cand.md', scratch / 'nc.json', scratch / 'ok.json', scratch / 'ev.json')
			resp_f.write_text('Proposed Strategy routing with clear separation.\n', encoding='utf-8')
			code, out = _run_arch_cli(['arch-prepare', str(proj), '--parent', _PARENT_ID, '--kind', 'response', '--response-file', str(resp_f), '--consume-input'])
			self.assertEqual((0, False), (code, resp_f.exists()))
			prep = json.loads(out)
			code_in, out_in = _run_arch_cli(['arch-review-input', str(proj), '--package', prep['package'], '--parent', _PARENT_ID, '--reviewer', _REVIEWER_ID])
			self.assertEqual((0, 1), (code_in, json.loads(out_in)['arch_review_input']))
			finding = {'id': 'F-1', 'violation_class': 'missing_pattern', 'severity': 'significant', 'target': 'response', 'description': 'Strategy participants are not specified.', 'status': 'open'}
			nc_bytes = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'], result='needs_changes', outcome='missing_pattern', participants_ok=False, findings=[finding])).encode('utf-8')
			nc_f.write_bytes(nc_bytes)
			with patch.object(metrics, 'native_review_proof', return_value={'final_response_sha256': hashlib.sha256(nc_bytes).hexdigest(), 'proof': 'nc-proof.json'}):
				code_nc, _ = _run_arch_cli(['arch-record-review', str(proj), '--report', str(nc_f), '--parent', _PARENT_ID, '--reviewer', _REVIEWER_ID, '--consume-input'])
			code_fail, txt_fail = _run_arch_cli(['arch-check', str(proj), '--format', 'text'])
			self.assertEqual((0, 2), (code_nc, code_fail))
			self.assertIn('FAIL', txt_fail)
			ok_bytes = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			ok_f.write_bytes(ok_bytes)
			backend = _seed_ag_arch_backend(base, proj, prep['package'], ok_bytes.decode('utf-8'))
			ev_f.write_text(json.dumps(ag.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=backend, role='ARCH')), encoding='utf-8')
			with patch.object(ag, 'platform_instances', return_value={}), patch.object(ag, '_default_platform_paths', return_value={'backend_dir': str(backend)}):
				code_ok, _ = _run_arch_cli(['arch-record-review', str(proj), '--report', str(ok_f), '--parent', _PARENT_ID, '--reviewer', _REVIEWER_ID, '--native-evidence', str(ev_f), '--consume-input'])
			code_pass, txt_pass = _run_arch_cli(['arch-check', str(proj), '--format', 'text'])
			self.assertEqual((0, 0), (code_ok, code_pass))
			self.assertIn('PASS', txt_pass)
			meta = metrics.native_executor_metadata(proj, _REVIEWER_ID, role='ARCH', parent_id=_PARENT_ID, platform='antigravity', backend=backend)
			self.assertEqual('ARCH', meta['role'])
	# @used-by :mod:`unittest`
	def test_cli_registry_and_send_message_gate_expose_arch_commands_and_block_verdict_duplication(self) -> None:
		from agent_tools.cli_registry import registered_commands
		from agent_tools.gates.send_message_gate import check as check_send_msg
		cmds = set(registered_commands())
		for cmd in ('arch-prepare', 'arch-review-input', 'arch-record-review', 'arch-check'):
			self.assertIn(cmd, cmds, f'Missing CLI command {cmd}')
		dup_verdict = json.dumps(_sample_verdict('\ua616/data/arch-reviews/packages/p.json', '0' * 64))
		err = check_send_msg('send_message', {'Message': dup_verdict}, {})
		self.assertIsNotNone(err)
		self.assertIn('REVIEW-4-SEND-MESSAGE-GATE', err or '')
	# 2026-11-27 "Pass ARCH role through Codex native_review_proof binding": https://github.com/dmitry-ai/harness/issues/394
	# @used-by :mod:`unittest`
	def test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker(self) -> None:
		from agent_tools.arch.review_store import prepare_arch_package, read_arch_review_input
		from agent_tools.platforms import codex
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'bare-cx'
			proj.mkdir()
			prep = prepare_arch_package(proj, _PARENT_ID, kind='response', response_text='Proposed Strategy routing with clear separation.\n')
			receipt = read_arch_review_input(proj, prep['package'], parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			verdict_str = json.dumps(_sample_verdict(prep['package'], prep['package_sha256']))
			cx_home = _seed_codex_arch_home(base, proj, prep['package'], receipt, verdict_str, init_text=False)
			self.assertFalse((proj / '\ua616/data/text-project.json').is_file())
			self.assertFalse((proj / '\ua616/project.json').is_file())
			proof = codex.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=cx_home, role='ARCH')
			self.assertEqual('code_workspace', proof['project_kind'])
			self.assertIsNone(proof['job_id'])
			self.assertEqual('ARCH', proof['executor_metadata']['role'])
			with patch.object(codex, 'extract_platform_homes', return_value={'C1': str(cx_home)}):
				verified = codex.verify_native_proof(proj, proof, package=Path(prep['package']).name)
			self.assertEqual('code_workspace', verified['project_kind'])
			self.assertEqual('ARCH', verified['executor_metadata']['role'])
			with self.assertRaises(ValueError):
				codex.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=cx_home, role='AA')
	# @used-by :mod:`unittest`
	def test_codex_native_review_proof_and_verify_support_arch_role(self) -> None:
		from agent_tools import metrics
		from agent_tools.arch.review_store import prepare_arch_package, read_arch_review_input
		from agent_tools.platforms import codex
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'proj'
			proj.mkdir()
			prep = prepare_arch_package(proj, _PARENT_ID, kind='response', response_text='Proposed Strategy routing with clear separation.\n')
			receipt = read_arch_review_input(proj, prep['package'], parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			verdict_str = json.dumps(_sample_verdict(prep['package'], prep['package_sha256']))
			cx_home = _seed_codex_arch_home(base, proj, prep['package'], receipt, verdict_str)
			proof = codex.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=cx_home, role='ARCH')
			self.assertEqual('ARCH', proof['executor_metadata']['role'])
			m_proof = metrics.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=cx_home, platform='codex', write=False, role='ARCH')
			self.assertEqual('ARCH', m_proof['executor_metadata']['role'])
			with patch.object(codex, 'extract_platform_homes', return_value={'C1': str(cx_home)}):
				verified = codex.verify_native_proof(proj, proof, package=Path(prep['package']).name)
			self.assertEqual('ARCH', verified['executor_metadata']['role'])
			with self.assertRaises(ValueError):
				codex.native_review_proof(proj, _PARENT_ID, _REVIEWER_ID, backend=cx_home, role='AA')
	# @used-by :mod:`unittest`
	def test_native_profiles_generates_arch_auditor_for_antigravity_and_codex(self) -> None:
		from agent_tools import links, native_profiles, runtime
		import check_markdown_slop
		cfg = runtime.settings(WT_ROOT / 'runtime.json')
		self.assertEqual('arch-auditor', cfg['platforms']['antigravity']['roles']['ARCH']['agent'])
		self.assertEqual('arch-auditor', cfg['platforms']['codex']['roles']['ARCH']['agent'])
		proto = WT_ROOT / 'agents/arch-protocol.md'
		self.assertTrue(proto.is_file(), 'Missing agents/arch-protocol.md')
		self.assertEqual([], links.validate_file(proto, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(proto.read_text(encoding='utf-8')))
		outputs = native_profiles.shared_native_outputs(WT_ROOT)
		ag_agent = WT_ROOT / 'agents/arch-auditor.md'
		cx_agent = WT_ROOT / 'platforms/codex/agents/arch-auditor.toml'
		self.assertIn(ag_agent, outputs)
		self.assertIn(cx_agent, outputs)
		self.assertIn('name: arch-auditor', outputs[ag_agent])
		self.assertIn('arch-review-input', outputs[ag_agent])
		self.assertIn('name = "arch-auditor"', outputs[cx_agent])
		self.assertEqual(outputs[ag_agent], ag_agent.read_text(encoding='utf-8'))
		self.assertEqual(outputs[cx_agent], cx_agent.read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_prepare_input_record_and_check_roundtrip_with_module_cache(self) -> None:
		from agent_tools.arch.review_store import inspect_arch_status, prepare_arch_package, read_arch_review_input, record_arch_review
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			mod_p = proj / 'src/engine.py'
			mod_p.parent.mkdir(parents=True)
			mod_p.write_text('class StrategyEngine:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			spec_txt = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap engine rules.\n- **Participants:** `StrategyEngine`\n- **Collaboration:** Engine delegates to strategy.\n- **Consequences:** Decoupled extension.\n'
			prep = prepare_arch_package(proj, _PARENT_ID, kind='code_diff', spec_text=spec_txt, repo=proj, files=['src/engine.py'])
			self.assertTrue(prep['valid'])
			self.assertFalse(prep['cached_approval'])
			inp = read_arch_review_input(proj, prep['package'], parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertEqual(1, inp['arch_review_input'])
			self.assertTrue(inp['verified'])
			self.assertEqual(prep['package_sha256'], inp['package_sha256'])
			verdict = _sample_verdict(prep['package'], prep['package_sha256'])
			verdict_bytes = json.dumps(verdict).encode('utf-8')
			fake_proof = {'surface': 'antigravity-ui', 'parent_id': _PARENT_ID, 'reviewer_id': _REVIEWER_ID, 'agent_name': 'arch-auditor', 'final_response': verdict_bytes.decode('utf-8'), 'final_response_sha256': hashlib.sha256(verdict_bytes).hexdigest(), 'native_log_sha256': 'b' * 64}
			with patch('agent_tools.arch.review_store._authenticate_arch_report', return_value=fake_proof):
				rec = record_arch_review(proj, verdict_bytes, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertTrue(rec['valid'])
			self.assertEqual('approved', rec['result'])
			self.assertIn('src/engine.py', rec['cached_modules'])
			prep2 = prepare_arch_package(proj, _PARENT_ID, kind='code_diff', spec_text=spec_txt, repo=proj, files=['src/engine.py'])
			self.assertTrue(prep2['cached_approval'])
			status = inspect_arch_status(proj, repo=proj)
			self.assertTrue(status['valid'])
			self.assertEqual(1, status['approved_module_count'])
	# 2026-11-27 "Support ARCH role fallback in review_project_id and native_project_fields": https://github.com/dmitry-ai/harness/issues/391
	# @used-by :mod:`unittest`
	def test_review_project_id_and_fields_support_bare_code_workspace_for_arch_only(self) -> None:
		from agent_tools.platforms.request_binding import completion_project_id, native_project_fields, review_project_id
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			bare = base / 'bare-code'
			bare.mkdir()
			expected = completion_project_id(bare)
			self.assertTrue(expected.startswith('text-'))
			self.assertEqual(expected, review_project_id(bare, role='ARCH'))
			self.assertEqual({'project_id': expected, 'project_kind': 'code_workspace', 'job_id': None}, native_project_fields(bare, role='ARCH'))
			with self.assertRaises(ValueError):
				review_project_id(bare, role='AA')
			with self.assertRaises(ValueError):
				native_project_fields(bare, role='AA')
			text_ws = base / 'text-ws'
			text_ws.mkdir()
			_init_text_workspace(text_ws)
			self.assertEqual({'project_id': completion_project_id(text_ws), 'project_kind': 'client_text_workspace', 'job_id': None}, native_project_fields(text_ws, role='ARCH'))
			up_ws = base / 'upwork-ws'
			(up_ws / '\ua616').mkdir(parents=True)
			(up_ws / '\ua616/project.json').write_text(json.dumps({'job_id': '~0123456789'}), encoding='utf-8')
			self.assertEqual({'project_id': '~0123456789', 'project_kind': 'upwork_job', 'job_id': '~0123456789'}, native_project_fields(up_ws, role='ARCH'))
	# @used-by :mod:`unittest`
	def test_validator_rejects_pattern_washing_and_rubber_stamp_approvals(self) -> None:
		from agent_tools.arch.review_validator import ArchitectureAuditValidator
		validator = ArchitectureAuditValidator()
		pkg = {'subject_kind': 'code_diff', 'subject_sha256': 'c' * 64}
		pkg_rel, pkg_sha = ('\ua616/data/arch-reviews/packages/p.json', 'd' * 64)
		self.assertEqual([], validator.validate(_sample_verdict(pkg_rel, pkg_sha), pkg, package_rel=pkg_rel, package_sha256=pkg_sha))
		bad_pw = _sample_verdict(pkg_rel, pkg_sha, result='approved', outcome='pattern_washing', participants_ok=False)
		self.assertTrue(bool(validator.validate(bad_pw, pkg, package_rel=pkg_rel, package_sha256=pkg_sha)))
		bad_nc = _sample_verdict(pkg_rel, pkg_sha, result='needs_changes', findings=[])
		self.assertTrue(bool(validator.validate(bad_nc, pkg, package_rel=pkg_rel, package_sha256=pkg_sha)))
		good_nc = _sample_verdict(pkg_rel, pkg_sha, result='needs_changes', outcome='pattern_washing', participants_ok=False, findings=[{'id': 'F-1', 'violation_class': 'pattern_washing', 'severity': 'significant', 'target': 'src/engine.py', 'description': 'Declared Strategy participant missing.', 'status': 'open'}])
		self.assertEqual([], validator.validate(good_nc, pkg, package_rel=pkg_rel, package_sha256=pkg_sha))
if '__main__' == __name__:
	unittest.main()