# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import hashlib
import json
import os
import sqlite3
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
HARNESS_PY = SCRIPTS / 'harness.py'
PRE_HOOK_PY = SCRIPTS / 'check_pre_invocation.py'
STOP_HOOK_PY = SCRIPTS / 'check_stop_gate.py'
JOB_ID = '~022124567641359999991'
JOB_NUM = '022124567641359999991'
PARENT_CID = '33333333-4444-4555-8666-777777777771'
CHILD_CID = '33333333-4444-4555-8666-777777777772'
BLOCKED_CID = '33333333-4444-4555-8666-777777777773'
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
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
def _run_cli(env: dict[str, str], *args: str, cwd: Path, expect_ok: bool=True) -> dict:
	proc = subprocess.run([sys.executable, str(HARNESS_PY), *args], cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
	if expect_ok and 0 != proc.returncode:
		raise AssertionError(f'CLI failed ({proc.returncode}): {args}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
	return json.loads(proc.stdout)
def _run_hook(script: Path, payload: dict, env: dict[str, str], *, cwd: Path) -> dict:
	proc = subprocess.run([sys.executable, str(script)], input=json.dumps(payload, ensure_ascii=False), cwd=str(cwd), env=env, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
	if 0 != proc.returncode:
		raise AssertionError(f'Hook failed ({proc.returncode}): {script.name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
	return json.loads(proc.stdout)
def _write_transcript(backend: Path, cid: str, rows: list[dict]) -> Path:
	tx = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	tx.parent.mkdir(parents=True, exist_ok=True)
	tx.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n', encoding='utf-8')
	return tx
def _upsert_summary(backend: Path, cid: str, parent: str, ws_uris: list[str], status: str, last_user: int, agent_name: str) -> None:
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE IF NOT EXISTS conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		conn.execute('DELETE FROM conversation_summaries WHERE conversation_id=?', (cid,))
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, parent, json.dumps(ws_uris), status, 0 if 'CASCADE_RUN_STATUS_IDLE' == status else 1, 0, last_user, agent_name))
		conn.commit()
def _write_steps_db(backend: Path, cid: str, step_rows: list[tuple[int, int, int, bytes | None]]) -> None:
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as conn:
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		conn.execute('DELETE FROM steps')
		for idx, stype, status, blob in step_rows:
			conn.execute('INSERT INTO steps VALUES(?,?,?,0,?)', (idx, stype, status, blob))
		conn.commit()
def _source_capture(base: Path) -> Path:
	from test_onboarding import source
	src = dict(source())
	src['job_id'] = JOB_ID
	src['url'] = f'https://upwork.com/jobs/{JOB_ID}'
	src_file = base / 'source.json'
	src_file.write_text(json.dumps(src, ensure_ascii=False), encoding='utf-8')
	return src_file
def _significant_analysis(proj: Path) -> dict:
	from agent_tools.analysis import SECTIONS
	pj = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
	snap = proj / pj['snapshot']
	ref = snap.relative_to(proj / '\ua616/KB').as_posix()
	title = json.loads(snap.read_text(encoding='utf-8'))['title']
	claim = {'id': 'F-TITLE', 'essence': title, 'assessment_basis': 'Exact title in registered intake.', 'knowledge_type': 'client_report', 'verification_status': 'limited', 'scope': {'description': 'Saved job title only.', 'sample': [ref], 'limitations': []}, 'properties': ['content', 'causality'], 'missing_checks': ['Inspect private storefront admin logs.'], 'derived_from': [], 'materiality': 'significant', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'No business impact inferred.', 'evidence_claim_ids': []}, 'probability_percent': 100, 'addresses': [], 'evidence': [{'id': 'E-TITLE', 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': hashlib.sha256(snap.read_bytes()).hexdigest(), 'quote': title, 'locator': {'type': 'json_pointer', 'value': '/title'}}], 'for': [{'argument': 'Registered intake contains the title.', 'evidence_id': 'E-TITLE'}], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': [ref], 'limitations': 'Attributed client report only.'}}
	return {'schema_version': 3, 'facts': [], 'identity': [claim], **{s: [] for s in SECTIONS if 'identity' != s}, 'notes': {s: 'No conclusion established.' for s in SECTIONS}, 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-TITLE'}]}
def _write_falsifier_auditor(backend: Path, proj: Path, pkg: dict, cand_path: Path, parent_rows: list[dict]) -> Path:
	from agent_tools.review import REVIEW_SCHEMA, SCOPES
	pkg_name = Path(pkg['package']).name
	prompt = f'<USER_REQUEST>\nAudit {pkg_name} using review-input and inspect full candidate.\n</USER_REQUEST>'
	parent_rows.append({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}}]})
	_write_transcript(backend, PARENT_CID, parent_rows)
	rep = {'schema_version': REVIEW_SCHEMA, 'review_mode': 'falsifier', 'package': pkg['package'], 'package_sha256': pkg['package_sha256'], 'scope': list(SCOPES), 'result': 'approved', 'summary': 'No Tier 0 contradiction found.', 'disproved_claims': [], 'findings': []}
	rep_json = json.dumps(rep, ensure_ascii=False)
	cand_lines = len(cand_path.read_text(encoding='utf-8').splitlines())
	child_rows = [
		{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt},
		{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(cand_path)}}]},
		{'step_index': 2, 'type': 'GENERIC', 'content': f'Showing lines 1-{cand_lines} of {cand_lines}\nTotal Lines: {cand_lines}'},
		{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'content': rep_json, 'tool_calls': []},
	]
	_write_transcript(backend, CHILD_CID, child_rows)
	_upsert_summary(backend, CHILD_CID, PARENT_CID, [proj.as_uri()], 'CASCADE_RUN_STATUS_IDLE', 0, 'self')
	_write_steps_db(backend, CHILD_CID, [(3, 15, 3, None)])
	rep_file = proj / '\ua616/data/scratch/falsifier-report.json'
	rep_file.write_text(rep_json, encoding='utf-8')
	return rep_file
def _complete_pre_review_stages(env: dict[str, str], proj: Path) -> None:
	_run_cli(env, 'resume', str(proj), '--reason', 'verify_saved_capture', cwd=proj)
	(proj / '\ua616/KB/Evidence/init-check.json').write_text('{}', encoding='utf-8')
	(proj / '\ua616/KB/Evidence/research-report.json').write_text('{}', encoding='utf-8')
	_run_cli(env, 'stage', str(proj), 'identity_init', '--input', '\ua616/project.json', '--output', '\ua616/KB/Evidence/init-check.json', cwd=proj)
	_run_cli(env, 'stage', str(proj), 'research', '--input', '\ua616/project.json', '--output', '\ua616/KB/Evidence/research-report.json', cwd=proj)
	cand = proj / '\ua616/data/scratch/analysis-cand.json'
	cand.parent.mkdir(parents=True, exist_ok=True)
	cand.write_text(json.dumps(_significant_analysis(proj), ensure_ascii=False), encoding='utf-8')
	_run_cli(env, 'save-analysis', str(proj), '--candidate', str(cand), '--consume-input', cwd=proj)
	_run_cli(env, 'render-analysis', str(proj / '\ua616/KB/Analysis.json'), '--output', str(proj / '\ua616/KB/Analysis.md'), cwd=proj)
	_run_cli(env, 'stage', str(proj), 'analysis', '--input', '\ua616/project.json', '--output', '\ua616/KB/Analysis.json', '--output', '\ua616/KB/Analysis.md', cwd=proj)
def _doc5_blocked_report(src_link: str) -> str:
	return (
		'# 0. Metadata\n\n'
		'```json\n'
		'{\n'
		'\t"Time": "2026-11-25 18:00:00 UTC+3",\n'
		'\t"Issue": "https://github.com/dmitry-ai/harness/issues/229",\n'
		'\t"Project": {"Name": "Harness", "Path": "C:/work/research/provision/code/AI/harness"}\n'
		'}\n'
		'```\n\n'
		'# 1. Problem\n\n'
		'Verbatim diagnostic error:  \n'
		'```text\n'
		'HTTP 503 Service Unavailable from upstream admin endpoint\n'
		'```\n\n'
		'# 2. Root Cause\n\n'
		'## H-1: Upstream service outage\n'
		f'- Essence: The remote endpoint returned 503 ([continuation.md](<{src_link}>)).  \n'
		'- Arguments for: Direct 503 diagnostic above.  \n'
		'- Arguments against: Local network check not yet repeated.  \n'
		'- Plausibility: 70% based on direct HTTP 503 status.  \n\n'
		'## H-2: Local proxy misconfiguration\n'
		f'- Essence: A local proxy intercepted the request ([continuation.md](<{src_link}>)).  \n'
		'- Arguments for: Proxy environment variables exist on host.  \n'
		'- Arguments against: Other hosts respond with 200.  \n'
		'- Plausibility: 25% based on host proxy configuration.  \n\n'
		'# 3. Source Project\n\n'
		'Harness owns the retry and blocked-report lifecycle.  \n\n'
		'# 4. Solutions\n\n'
		'## M-1: Retry with bounded backoff\n'
		'- Essence: Retry the request once the upstream recovers.  \n'
		'- Arguments for: Preserves exact automation flow.  \n'
		'- Arguments against: Cannot succeed while outage persists.  \n'
		'- Score: 85% for reliability.  \n\n'
		'## M-2: Pause with blocked-report handoff\n'
		'- Essence: Record continuation state and exit cleanly.  \n'
		'- Arguments for: Avoids stalled turns and preserves audit trail.  \n'
		'- Arguments against: Requires follow-up turn.  \n'
		'- Score: 90% for safe recovery.  \n'
	) + _doc5_companion_blocks(src_link)
# 2026-11-25
# "Require separate companion /df-analysis tracks for every complex problem analysis":
# https://github.com/dmitry-ai/harness/issues/249
def _doc5_companion_block(header: str, tag: str, desc: str, src_link: str) -> str:
	return (
		f'\n---\n\n# {header}\n\n# 0. Metadata ({tag})\n\n'
		'```json\n{"Time": "2026-11-25 18:01:00 UTC+3", "Issue": null, "Project": {"Name": "Harness", "Path": "C:/work/research/provision/code/AI/harness"}}\n```\n\n'
		f'# 1. Problem ({tag})\n\n{desc}  \n\n# 2. Root Cause ({tag})\n\n'
		f'## H-{tag}-1: Direct gap\n- Essence: Confirmed in [continuation.md](<{src_link}>).  \n- Arguments for: Observed directly.  \n- Arguments against: Minor noise.  \n- Plausibility: 85%.  \n\n'
		f'## H-{tag}-2: Secondary factor\n- Essence: External timing in [continuation.md](<{src_link}>).  \n- Arguments for: Possible factor.  \n- Arguments against: Not primary.  \n- Plausibility: 20%.  \n\n'
		f'# 3. Source Project ({tag})\n\nHarness owns this verification layer.  \n\n# 4. Solutions ({tag})\n\n'
		f'## M-{tag}-1: Systemic check\n- Essence: Add automated check.  \n- Arguments for: Prevents recurrence.  \n- Arguments against: Small cost.  \n- Score: 90%.  \n\n'
		f'## M-{tag}-2: Manual check\n- Essence: Verify manually.  \n- Arguments for: Fast setup.  \n- Arguments against: Unreliable.  \n- Score: 20%.  \n'
	)
# 2026-11-25
# "Require separate companion /df-analysis tracks for every complex problem analysis":
# https://github.com/dmitry-ai/harness/issues/249
def _doc5_companion_blocks(src_link: str) -> str:
	return (
		_doc5_companion_block('Analysis 2: Culprit attribution', '2', 'Who introduced the upstream blocker: external endpoint returned `HTTP 503`.', src_link)
		+ _doc5_companion_block('Analysis 3: Test and verification escape', '3', 'Why tests did not catch the `HTTP 503` retry gap during pre-flight.', src_link)
		+ _doc5_companion_block('Analysis 4: Journal and reporting integrity', '4', 'Verified Journal `ꙮ` (`FILE-3`) recording via `answer-prepare --blocked-report`.', src_link)
	)
def _stop_payload(cwd: Path, cid: str, tx: Path) -> dict:
	return {'hookEventName': 'Stop', 'cwd': str(cwd), 'workspacePaths': [str(cwd)], 'conversationId': cid, 'transcriptPath': str(tx), 'terminationReason': 'NO_TOOL_CALL', 'error': '', 'fullyIdle': True, 'continuationActive': False, 'executionNum': 0}
def _run_turn1_init_and_review(case: unittest.TestCase, base: Path, launcher: Path, backend: Path, env: dict[str, str]) -> tuple[Path, Path, Path, Path, str, str, list[dict]]:
	req1 = f'/upwork-init https://upwork.com/jobs/{JOB_ID}'
	parent_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1, 'created_at': '2026-11-25T10:00:00Z'}]
	tx = _write_transcript(backend, PARENT_CID, parent_rows)
	_upsert_summary(backend, PARENT_CID, '', [launcher.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 0, 'primary')
	_write_steps_db(backend, PARENT_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8'))))])
	pre1 = _run_hook(PRE_HOOK_PY, {'conversationId': PARENT_CID, 'cwd': str(launcher), 'transcriptPath': str(tx)}, env, cwd=launcher)
	case.assertIn(launcher.as_posix(), json.dumps(pre1))
	init_out = _run_cli(env, 'init', f'https://upwork.com/jobs/{JOB_ID}', '--from-json', str(_source_capture(base)), '--domain', 'magento-e2e', '--date', '2026-11-25', '--daily-root', str(base / 'proposals/daily'), '--no-register', '--launcher-root', str(launcher), '--conversation', PARENT_CID, cwd=launcher)
	daily = Path(init_out['project_dir']).resolve()
	case.assertEqual(1, len(init_out.get('launcher_handoff') or []))
	beg1 = _run_cli(env, 'turn-begin', str(daily), '--conversation', PARENT_CID, '--platform', 'antigravity', cwd=daily)
	_run_cli(env, 'adopt-requests', str(daily), '--conversation', PARENT_CID, '--platform', 'antigravity', cwd=daily)
	_complete_pre_review_stages(env, daily)
	ev_bin = daily / '\ua616/KB/Evidence/HTTP/e2e/response.bin'
	ev_bin.parent.mkdir(parents=True, exist_ok=True)
	ev_bin.write_bytes(b'ok')
	reply1 = f'\u0417\u0430\u0434\u0430\u0447\u0430 \u043a\u043b\u0438\u0435\u043d\u0442\u0430 Client task \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0430 \u043f\u043e [response.bin](<file:///{ev_bin.resolve().as_posix()}>).  \n'
	cand_md = daily / f"\ua616/data/scratch/answer-{beg1['turn_key']}.md"
	cand_md.write_text(reply1, encoding='utf-8')
	spec_f = daily / '\ua616/data/scratch/review-spec.json'
	spec_f.write_text(json.dumps({'risk': 'significant', 'basis': 'Significant analysis requiring falsifier audit.', 'request_scope': 'Answer initial request.', 'claim_ids': ['F-TITLE'], 'claims': [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'new'}], 'task_flags': ['material_analysis', 'new_causal_analysis']}), encoding='utf-8')
	pkg = _run_cli(env, 'prepare-review', str(daily), '--parent', PARENT_CID, '--spec', str(spec_f), '--response-file', str(cand_md), '--consume-input', '--platform', 'antigravity', cwd=daily)
	case.assertEqual('falsifier', pkg.get('review_mode'), pkg)
	cand_md.write_text(reply1, encoding='utf-8')
	rep_f = _write_falsifier_auditor(backend, daily, pkg, cand_md, parent_rows)
	_write_steps_db(backend, PARENT_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (2, 15, 3, None)])
	proof = _run_cli(env, 'native-review-proof', str(daily), '--parent', PARENT_CID, '--reviewer', CHILD_CID, '--platform', 'antigravity', cwd=daily)
	rec = _run_cli(env, 'record-review', str(daily), '--parent', PARENT_CID, '--reviewer', CHILD_CID, '--report', str(rep_f), '--native-evidence', proof['proof'], '--consume-input', '--platform', 'antigravity', cwd=daily)
	kb_args = [tok for p in sorted((daily / '\ua616/KB').glob('*')) if p.is_file() and 'Progress.md' != p.name for tok in ('--input', p.relative_to(daily).as_posix())]
	review_out = (rec['reviews'][-1]['report'] if isinstance(rec.get('reviews'), list) and rec['reviews'] else proof['proof'])
	_run_cli(env, 'stage', str(daily), 'review', '--input', '\ua616/KB/Analysis.json', '--output', review_out, cwd=daily)
	_run_cli(env, 'stage', str(daily), 'kb_review', *kb_args, '--output', '\ua616/KB/Analysis.md', '--note', 'KB consistent', cwd=daily)
	return (daily, tx, cand_md, ev_bin, req1, reply1, parent_rows)
def _run_turn2_continuation(case: unittest.TestCase, launcher: Path, daily: Path, backend: Path, env: dict[str, str], tx: Path, ev_bin: Path, req1: str, parent_rows: list[dict]) -> None:
	launcher_before = sorted((p.name for p in (launcher / '\ua616/data/turns').glob('*.json')))
	req2 = 'Follow up on the finalized project.'
	parent_rows.append({'step_index': 20, 'type': 'USER_INPUT', 'content': req2, 'created_at': '2026-11-25T10:20:00Z'})
	_write_transcript(backend, PARENT_CID, parent_rows)
	_upsert_summary(backend, PARENT_CID, '', [launcher.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 20, 'primary')
	_write_steps_db(backend, PARENT_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (2, 15, 3, None), (10, 15, 3, None), (20, 14, 3, _wire(19, _wire(2, req2.encode('utf-8'))))])
	pre2 = _run_hook(PRE_HOOK_PY, {'conversationId': PARENT_CID, 'cwd': str(launcher), 'transcriptPath': str(tx)}, env, cwd=launcher)
	case.assertIn(daily.as_posix(), json.dumps(pre2))
	case.assertEqual(launcher_before, sorted((p.name for p in (launcher / '\ua616/data/turns').glob('*.json'))))
	reply2 = f'Follow-up answer referencing [response.bin](<file:///{ev_bin.resolve().as_posix()}>).  \n'
	ans2 = daily / '\ua616/data/scratch/answer-turn2.md'
	ans2.write_text(reply2, encoding='utf-8')
	prep2 = _run_cli(env, 'answer-prepare', str(daily), '--conversation', PARENT_CID, '--response-file', str(ans2), '--consume-input', '--platform', 'antigravity', cwd=daily)
	case.assertTrue(prep2['ready'], prep2)
	parent_rows.append({'step_index': 25, 'type': 'PLANNER_RESPONSE', 'content': reply2, 'tool_calls': []})
	_write_transcript(backend, PARENT_CID, parent_rows)
	case.assertEqual('allow', _run_hook(STOP_HOOK_PY, _stop_payload(launcher, PARENT_CID, tx), env, cwd=launcher)['decision'])
# 2026-11-25
# "Add full offline CLI and hook end-to-end lifecycle test for /upwork-init":
# https://github.com/dmitry-ai/harness/issues/235
class UpworkInitFullE2ETests(unittest.TestCase):
	def test_e2e_blocked_report_doc5_and_shadowing_stop_gate_cli(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			home, launcher = (base / 'home', base / 'proposals/init')
			backend = home / '.gemini/antigravity'
			env = _iso_env(home)
			(launcher / '\ua66e/\u227a').mkdir(parents=True)
			(launcher / '\ua66e/\u227b').mkdir(parents=True)
			req1, req2 = (f'/upwork-init https://upwork.com/jobs/{JOB_ID}', 'Finish blocked report now.')
			tx = _write_transcript(backend, BLOCKED_CID, [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1, 'created_at': '2026-11-25T10:00:00Z'}, {'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 summary.', 'tool_calls': []}, {'step_index': 434, 'type': 'USER_INPUT', 'content': req2, 'created_at': '2026-11-25T11:00:00Z'}])
			_upsert_summary(backend, BLOCKED_CID, '', [launcher.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 434, 'primary')
			_write_steps_db(backend, BLOCKED_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (5, 15, 3, None), (434, 14, 3, _wire(19, _wire(2, req2.encode('utf-8'))))])
			init_out = _run_cli(env, 'init', f'https://upwork.com/jobs/{JOB_ID}', '--from-json', str(_source_capture(base)), '--domain', 'blocked-e2e', '--date', '2026-11-25', '--daily-root', str(base / 'proposals/daily'), '--no-register', '--launcher-root', str(launcher), '--conversation', BLOCKED_CID, cwd=launcher)
			daily = Path(init_out['project_dir']).resolve()
			_run_cli(env, 'adopt-requests', str(daily), '--conversation', BLOCKED_CID, '--platform', 'antigravity', cwd=daily)
			(launcher / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').parent.mkdir(parents=True, exist_ok=True)
			(launcher / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps({'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': BLOCKED_CID, 'native_turn_id': f'ag-{BLOCKED_CID}-0', 'native_start_step': 0, 'status': 'handed_off', 'handed_off_to': {'project_root': str(daily), 'job_id': JOB_NUM}}), encoding='utf-8')
			cont_p = daily / '\ua616/data/continuation.md'
			cont_p.write_text('Active blocker: external admin API unavailable; next step is retry after access.\n', encoding='utf-8')
			doc5 = _doc5_blocked_report(f'file:///{cont_p.resolve().as_posix()}')
			ans_file = daily / '\ua616/data/scratch/blocked-answer.md'
			ans_file.parent.mkdir(parents=True, exist_ok=True)
			ans_file.write_text(doc5, encoding='utf-8')
			chk = _run_cli(env, 'answer-check', str(daily), '--conversation', BLOCKED_CID, '--response-file', str(ans_file), '--blocked-report', '--platform', 'antigravity', cwd=daily)
			self.assertTrue(chk['valid'], chk)
			prep = _run_cli(env, 'answer-prepare', str(daily), '--conversation', BLOCKED_CID, '--response-file', str(ans_file), '--consume-input', '--blocked-report', '--platform', 'antigravity', cwd=daily)
			self.assertTrue(prep['ready'], prep)
			stale_open = {'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': BLOCKED_CID, 'native_turn_id': f'ag-{BLOCKED_CID}-0', 'native_start_step': 0, 'status': 'open', 'requests': [{'id': f'{BLOCKED_CID}-0', 'native_step': 0}, {'id': f'{BLOCKED_CID}-434', 'native_step': 434}], 'readiness_check': {'verified': False, 'gate_id': 'issue_first', 'detail': 'stale'}}
			(daily / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps(stale_open), encoding='utf-8')
			_write_transcript(backend, BLOCKED_CID, [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1}, {'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 summary.', 'tool_calls': []}, {'step_index': 434, 'type': 'USER_INPUT', 'content': req2}, {'step_index': 450, 'type': 'PLANNER_RESPONSE', 'content': doc5, 'tool_calls': []}])
			stop_out = _run_hook(STOP_HOOK_PY, _stop_payload(launcher, BLOCKED_CID, tx), env, cwd=launcher)
			self.assertEqual('allow', stop_out['decision'], stop_out)
	def test_full_upwork_init_cli_and_hooks_lifecycle_two_turns(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			home, launcher = (base / 'home', base / 'proposals/init')
			backend = home / '.gemini/antigravity'
			env = _iso_env(home)
			(launcher / '\ua66e/\u227a').mkdir(parents=True)
			(launcher / '\ua66e/\u227b').mkdir(parents=True)
			daily, tx, cand_md, ev_bin, req1, reply1, parent_rows = _run_turn1_init_and_review(self, base, launcher, backend, env)
			chk1 = _run_cli(env, 'answer-check', str(daily), '--conversation', PARENT_CID, '--response-file', str(cand_md), '--platform', 'antigravity', cwd=daily)
			self.assertTrue(chk1['valid'], chk1)
			prep1 = _run_cli(env, 'answer-prepare', str(daily), '--conversation', PARENT_CID, '--response-file', str(cand_md), '--consume-input', '--platform', 'antigravity', cwd=daily)
			self.assertTrue(prep1['ready'], prep1)
			kb_args = [tok for p in sorted((daily / '\ua616/KB').glob('*')) if p.is_file() and 'Progress.md' != p.name for tok in ('--input', p.relative_to(daily).as_posix())]
			fin = _run_cli(env, 'stage', str(daily), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md', cwd=daily)
			self.assertEqual('complete', fin['stages']['finalize'])
			parent_rows.append({'step_index': 10, 'type': 'PLANNER_RESPONSE', 'content': reply1, 'tool_calls': [], 'created_at': '2026-11-25T10:10:00Z'})
			_write_transcript(backend, PARENT_CID, parent_rows)
			self.assertEqual('allow', _run_hook(STOP_HOOK_PY, _stop_payload(launcher, PARENT_CID, tx), env, cwd=launcher)['decision'])
			_run_turn2_continuation(self, launcher, daily, backend, env, tx, ev_bin, req1, parent_rows)
if '__main__' == __name__:
	unittest.main()
