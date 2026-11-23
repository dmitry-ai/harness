# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
# https://github.com/dmitry-ai/harness/issues/138
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce similar_projects parity gate, hooks, and documented CLI contract across turn completion and issue lifecycle":
# https://github.com/dmitry-ai/harness/issues/123
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
# https://github.com/dmitry-ai/harness/issues/109
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
# https://github.com/dmitry-ai/harness/issues/105
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
def _strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
def _ensure_scripts_on_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
def _tracked_workspace(root: Path, *, projects_dirs=None) -> tuple[bool, Path]:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import is_tracked_workspace
		return is_tracked_workspace(root, projects_dirs=projects_dirs)
	except Exception:
		pass
	tracked = (root / '\ua616/project.json').is_file() or (root / '_/\ua66e').is_dir() or (root / '\ua66e').is_dir()
	return (tracked, root)
def _is_tracked_workspace(root: Path, *, projects_dirs=None) -> bool:
	return _tracked_workspace(root, projects_dirs=projects_dirs)[0]
def _turns_dir(root: Path) -> Path:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import project_paths
		return project_paths(root).turns_dir
	except Exception:
		return (root / '_/\ua616/data/turns') if (root / '_/\ua616').is_dir() else (root / '\ua616/data/turns')
def _is_child_conversation(backend: Path, conversation_id: str, *, conversations_db: Path | None = None) -> bool:
	db_path = Path(conversations_db) if None is not conversations_db else Path(backend) / 'conversation_summaries.db'
	if not db_path.is_file():
		return False
	conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
	try:
		row = conn.execute('SELECT parent_conversation_id FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
		return bool(row and row[0])
	except Exception:
		return False
	finally:
		conn.close()
def _resolve_stop_paths(session_id: str, t_path: Path | None = None, backend_override: Path | None = None) -> tuple[Path, Path, Path, Path]:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
	resolved = None
	try:
		from agent_tools.runtime import platform_instances, resolve_antigravity_paths, settings
		if None is not backend_override:
			resolved = resolve_antigravity_paths(backend=backend_override, conversation_id=session_id)
		elif None is not t_path:
			cfg = settings()
			ag_insts = platform_instances('antigravity', config=cfg, include_disabled=True) if 'antigravity' in (cfg.get('platforms') or {}) else {}
			t_res = t_path.resolve()
			for inst in ag_insts.values():
				sp = inst['system_paths']
				for key in ('brain_dir', 'backend_dir'):
					val = sp.get(key)
					if val and t_res.is_relative_to(Path(val).resolve()):
						resolved = resolve_antigravity_paths(backend=sp.get('backend_dir'), instance=inst['id'], conversation_id=session_id, config=cfg)
						break
				if None is not resolved:
					break
		if None is resolved and None is t_path:
			resolved = resolve_antigravity_paths(conversation_id=session_id)
	except Exception:
		resolved = None
	if None is not resolved:
		return (Path(resolved['backend_dir']).resolve(), Path(resolved['brain_dir']).resolve(), Path(resolved['conversations_db']).resolve(), Path(resolved['projects_dir']).resolve())
	if None is not backend_override:
		backend = Path(backend_override).resolve()
		return (backend, backend / 'brain', backend / 'conversation_summaries.db', backend.parent / 'config/projects')
	if None is not t_path:
		if len(t_path.parents) >= 5 and 'brain' == t_path.parents[3].name:
			backend = t_path.parents[4]
			brain_dir = t_path.parents[3]
		elif len(t_path.parents) >= 4:
			backend = t_path.parents[3]
			brain_dir = backend / 'brain'
		else:
			backend = t_path.parent
			brain_dir = backend / 'brain'
		return (backend, brain_dir, backend / 'conversation_summaries.db', backend.parent / 'config/projects')
	try:
		from agent_tools.path_registry import default_platform_paths
		defaults = default_platform_paths('antigravity')
		backend = Path(defaults['backend_dir']).resolve()
		projects_dir = Path(defaults['projects_dir']).resolve() if defaults.get('projects_dir') else (backend.parent / 'config/projects')
	except Exception:
		backend = (Path.home() / '.gemini/antigravity').resolve()
		projects_dir = backend.parent / 'config/projects'
	return (backend, backend / 'brain', backend / 'conversation_summaries.db', projects_dir)
def _find_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list | None = None) -> dict | None:
	if not t_dir.is_dir():
		return None
	handed_off_fallback: tuple[int, dict] | None = None
	for sf in t_dir.glob('*.json'):
		if sf.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json')):
			continue
		try:
			st = json.loads(sf.read_text(encoding='utf-8'))
		except Exception:
			continue
		if not isinstance(st, dict) or st.get('conversation_id') != session_id:
			continue
		req_steps = {req.get('native_step') for req in st.get('requests') or [] if isinstance(req, dict)}
		if st.get('native_turn_id') == f'ag-{session_id}-{last_user_step}' or last_user_step in req_steps or st.get('native_start_step') == last_user_step:
			return st
		if None is not rows and 'handed_off' == st.get('status'):
			start_step = st.get('native_start_step')
			if isinstance(start_step, int) and start_step <= last_user_step:
				has_prior_final = any((isinstance(r, dict) and 'PLANNER_RESPONSE' == r.get('type') and (not (r.get('tool_calls') or ())) and str(r.get('content') or '').strip() and isinstance(r.get('step_index'), int) and start_step < r['step_index'] < last_user_step for r in rows))
				if not has_prior_final and (None is handed_off_fallback or start_step > handed_off_fallback[0]):
					handed_off_fallback = (start_step, st)
	return handed_off_fallback[1] if None is not handed_off_fallback else None
def _resolve_backend_fallback(session_id: str) -> Path:
	return _resolve_stop_paths(session_id)[0]
def evaluate_stop_payload(payload: dict, *, backend_override: Path | None = None) -> dict:
	if not isinstance(payload, dict):
		return {'decision': 'allow'}
	if 'NO_TOOL_CALL' != payload.get('terminationReason') or bool(payload.get('error')) or (False is payload.get('fullyIdle')):
		return {'decision': 'allow'}
	cwd_raw = (payload.get('cwd') or '').strip()
	session_id = (payload.get('sessionId') or '').strip()
	t_path_raw = (payload.get('transcriptPath') or '').strip()
	if not cwd_raw or not session_id or (not re.fullmatch('[a-f0-9-]{36}', session_id)):
		return {'decision': 'allow'}
	root = Path(cwd_raw).resolve()
	t_path = Path(t_path_raw).resolve() if t_path_raw else None
	fast_tracked, canon_root = _tracked_workspace(root, projects_dirs=())
	backend, brain_dir, conversations_db, projects_dir = _resolve_stop_paths(session_id, t_path=t_path, backend_override=backend_override)
	if not fast_tracked:
		tracked, canon_root = _tracked_workspace(root, projects_dirs=(projects_dir,))
		if not tracked:
			return {'decision': 'allow'}
	if _is_child_conversation(backend, session_id, conversations_db=conversations_db):
		return {'decision': 'allow'}
	logs_dir = t_path.parent if None is not t_path else (brain_dir / session_id / '.system_generated/logs')
	full_t = logs_dir / 'transcript_full.jsonl'
	compact_t = logs_dir / 'transcript.jsonl'
	log_file = full_t if full_t.is_file() else (t_path if None is not t_path and t_path.is_file() else compact_t)
	if None is log_file or (not log_file.is_file()):
		return {'decision': 'allow'}
	try:
		rows = [json.loads(line) for line in log_file.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except Exception:
		return {'decision': 'allow'}
	user_steps = [r.get('step_index') for r in rows if isinstance(r, dict) and 'USER_INPUT' == r.get('type') and isinstance(r.get('step_index'), int)]
	if not user_steps:
		return {'decision': 'allow'}
	last_user_step = user_steps[-1]
	segment = [r for r in rows if isinstance(r, dict) and isinstance(r.get('step_index'), int) and (r.get('step_index') > last_user_step)]
	spawned = 0
	completed = 0
	last_planner_text = ''
	for r in segment:
		if 'EPHEMERAL_MESSAGE' == r.get('type') and re.search('<SYSTEM_MESSAGE>.*\\bSubagent\\b.*\\bcompleted\\b', str(r.get('content') or ''), re.S):
			completed += 1
		calls = [c for c in r.get('tool_calls') or [] if isinstance(c, dict)]
		for c in calls:
			if 'invoke_subagent' == c.get('name'):
				spawned += 1
		if 'PLANNER_RESPONSE' == r.get('type') and (not calls) and str(r.get('content') or '').strip():
			last_planner_text = str(r.get('content'))
	if completed < spawned:
		return {'decision': 'allow'}
	t_dir = _turns_dir(canon_root)
	matched_state = _find_turn_state(t_dir, session_id, last_user_step, rows=rows)
	if None is not matched_state and 'handed_off' == matched_state.get('status'):
		handoff_info = matched_state.get('handed_off_to') if isinstance(matched_state.get('handed_off_to'), dict) else {}
		handoff_raw = str(handoff_info.get('project_root') or '').strip()
		if handoff_raw:
			handoff_root = Path(handoff_raw).resolve()
			target_state = _find_turn_state(_turns_dir(handoff_root), session_id, last_user_step)
			if None is target_state:
				return {'decision': 'continue', 'reason': f'FILE-3 / SCOPE-3 Stop Gate: Launcher turn was handed off to {handoff_root}, which has no turn-begin / answer-prepare record for the active turn. Run turn-begin and answer-prepare in {handoff_root} before finishing the response.'}
			matched_state = target_state
	if None is matched_state:
		return {'decision': 'continue', 'reason': 'FILE-3 / SCOPE-3 Stop Gate: Active turn has no turn-begin / answer-prepare record. Run turn-begin and answer-prepare before finishing the response.'}
	prep = matched_state.get('prepared')
	if matched_state.get('status') not in ('prepared', 'delivered') or (not isinstance(prep, dict)) or (not matched_state.get('readiness_check', {}).get('verified')):
		detail = (matched_state.get('readiness_check') or {}).get('detail') or 'answer-prepare has not succeeded for the current turn'
		return {'decision': 'continue', 'reason': f'FILE-3 / EXEC-5 Stop Gate: Turn is not prepared ({detail}). Run harness.py answer-prepare and output the exact prepared response.'}
	clc = matched_state.get('code_lifecycle_check') if isinstance(matched_state.get('code_lifecycle_check'), dict) else {}
	if False is clc.get('verified'):
		clc_detail = '; '.join((str(v) for v in (clc.get('violations') or ()))) or 'code/issue or similar_projects parity lifecycle incomplete'
		return {'decision': 'continue', 'reason': f'EXEC-5 Stop Gate: {clc_detail}. Resolve pending code/issue or similar_projects parity checks and re-run harness.py answer-prepare.'}
	tddc = matched_state.get('tdd_check') if isinstance(matched_state.get('tdd_check'), dict) else {}
	if False is tddc.get('verified'):
		tdd_detail = '; '.join((str(v) for v in (tddc.get('violations') or ()))) or 'TDD Red-First / Full-Suite-Green verification failed'
		return {'decision': 'continue', 'reason': f'EXEC-2 Stop Gate: {tdd_detail}. Resolve TDD violations, run the full test suite to GREEN, and re-run harness.py answer-prepare.'}
	if last_planner_text:
		sha = hashlib.sha256(last_planner_text.encode('utf-8')).hexdigest()
		if sha != prep.get('response_sha256'):
			res_file = Path(prep.get('response_file') or '')
			prep_text = res_file.read_text(encoding='utf-8', errors='replace') if res_file.is_file() else ''
			if not prep_text or _strip_local_file_scheme(prep_text) != _strip_local_file_scheme(last_planner_text):
				return {'decision': 'continue', 'reason': 'FILE-3 Stop Gate: Final response text does not match the prepared response in \u227a/<range>/<N>.md (or legacy res/<N>.md). Read back the prepared response file and output its exact bytes without post-prepare edits.'}
	return {'decision': 'allow'}
def main():
	decision = {'decision': 'allow'}
	try:
		raw = sys.stdin.read()
		if raw.strip():
			decision = evaluate_stop_payload(json.loads(raw))
	except Exception:
		decision = {'decision': 'allow'}
	sys.stdout.write(json.dumps(decision, ensure_ascii=False))
if '__main__' == __name__:
	main()
