# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
def _strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
def _ensure_scripts_on_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
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
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
def _turns_dir(root: Path) -> Path:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import project_paths
		# 2026-11-25
		# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
		# https://github.com/dmitry-ai/harness/issues/237
		return project_paths(root, exact_root=True).turns_dir
	except Exception:
		return (root / '_/\ua616/data/turns') if (root / '_/\ua616').is_dir() else (root / '\ua616/data/turns')
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
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
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
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
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	try:
		from agent_tools.path_registry import default_platform_paths
		defaults = default_platform_paths('antigravity')
		backend = Path(defaults['backend_dir']).resolve()
		projects_dir = Path(defaults['projects_dir']).resolve() if defaults.get('projects_dir') else (backend.parent / 'config/projects')
	except Exception:
		backend = (Path.home() / '.gemini/antigravity').resolve()
		projects_dir = backend.parent / 'config/projects'
	return (backend, backend / 'brain', backend / 'conversation_summaries.db', projects_dir)
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# 2026-11-25
# "Unify handed-off turn routing and deterministic state selection across hooks":
# https://github.com/dmitry-ai/harness/issues/231
def _find_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list | None = None) -> dict | None:
	_ensure_scripts_on_path()
	from agent_tools.turn_routing import resolve_active_turn_state
	return resolve_active_turn_state(t_dir, session_id, last_user_step, rows=rows)
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
def _resolve_backend_fallback(session_id: str) -> Path:
	return _resolve_stop_paths(session_id)[0]
# 2026-11-24
# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
# https://github.com/dmitry-ai/harness/issues/197
def _evaluate_prepared_match(matched_state: dict, last_planner_text: str) -> dict:
	r = {'decision': 'allow'}
	prep = matched_state.get('prepared')
	if last_planner_text and isinstance(prep, dict):
		sha = hashlib.sha256(last_planner_text.encode('utf-8')).hexdigest()
		# 2026-11-23
		# "Prepend JSON metadata headers to new journal responses":
		# https://github.com/dmitry-ai/harness/issues/151
		if sha != prep.get('response_sha256') and sha != prep.get('body_sha256'):
			res_file = Path(prep.get('response_file') or '')
			prep_text = res_file.read_text(encoding='utf-8', errors='replace') if res_file.is_file() else ''
			_ensure_scripts_on_path()
			try:
				from agent_tools.metadata import strip_leading_metadata_header
				prep_body = strip_leading_metadata_header(prep_text)
			except Exception:
				prep_body = prep_text
			if not prep_text or (_strip_local_file_scheme(prep_text) != _strip_local_file_scheme(last_planner_text) and _strip_local_file_scheme(prep_body) != _strip_local_file_scheme(last_planner_text)):
				# 2026-11-20
				# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
				# https://github.com/dmitry-ai/harness/issues/101
				# 2026-11-21
				# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
				# https://github.com/dmitry-ai/harness/issues/109
				r = {'decision': 'continue', 'reason': 'FILE-3 Stop Gate: Final response text does not match the prepared response in \u227a/<range>/<N>.md (or legacy res/<N>.md). Read back the prepared response file and output its exact bytes without post-prepare edits.'}
	return r
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
def evaluate_stop_payload(payload: dict, *, backend_override: Path | None = None) -> dict:
	if not isinstance(payload, dict):
		return {'decision': 'allow'}
	if 'NO_TOOL_CALL' != payload.get('terminationReason') or bool(payload.get('error')) or (False is payload.get('fullyIdle')):
		return {'decision': 'allow'}
	_ensure_scripts_on_path()
	# 2026-11-24
	# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
	# https://github.com/dmitry-ai/harness/issues/197
	from agent_tools.stop_hook_guard import apply_continuation_guard, extract_stop_context, is_journal_opt_out
	cwd_raw, session_id, t_path_raw = extract_stop_context(payload)
	if not cwd_raw or not session_id:
		return {'decision': 'allow'}
	root = Path(cwd_raw).resolve()
	t_path = Path(t_path_raw).resolve() if t_path_raw else None
	# 2026-11-23
	# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
	# https://github.com/dmitry-ai/harness/issues/132
	fast_tracked, canon_root = _tracked_workspace(root, projects_dirs=())
	backend, brain_dir, conversations_db, projects_dir = _resolve_stop_paths(session_id, t_path=t_path, backend_override=backend_override)
	if not fast_tracked:
		tracked, canon_root = _tracked_workspace(root, projects_dirs=(projects_dir,))
		if not tracked:
			return {'decision': 'allow'}
	if _is_child_conversation(backend, session_id, conversations_db=conversations_db):
		return {'decision': 'allow'}
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	logs_dir = t_path.parent if None is not t_path else (brain_dir / session_id / '.system_generated/logs')
	full_t = logs_dir / 'transcript_full.jsonl'
	compact_t = logs_dir / 'transcript.jsonl'
	log_file = full_t if full_t.is_file() else (t_path if None is not t_path and t_path.is_file() else compact_t)
	if None is log_file or (not log_file.is_file()):
		return {'decision': 'allow'}
	# 2026-11-24
	# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
	# https://github.com/dmitry-ai/harness/issues/79
	from agent_tools.hook_runtime import read_last_user_segment
	rows, last_user_step, segment = read_last_user_segment(log_file, by_step_index=True)
	if None is last_user_step:
		return {'decision': 'allow'}
	# 2026-11-24
	# "Detect active Antigravity 2.0 subagents in check_stop_gate via summary DB":
	# https://github.com/dmitry-ai/harness/issues/211
	from agent_tools.stop_subagent_check import extract_segment_subagent_state, has_running_subagents
	sub_state = extract_segment_subagent_state(segment)
	last_planner_text = sub_state['last_planner_text']
	if has_running_subagents(sub_state, session_id, conversations_db):
		return {'decision': 'allow'}
	t_dir = _turns_dir(canon_root)
	matched_state = _find_turn_state(t_dir, session_id, last_user_step, rows=rows)
	# 2026-11-24
	# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
	# https://github.com/dmitry-ai/harness/issues/197
	if is_journal_opt_out(payload, rows, last_user_step, matched_state):
		return {'decision': 'allow'}
	# 2026-11-23
	# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
	# https://github.com/dmitry-ai/harness/issues/132
	if None is not matched_state and 'handed_off' == matched_state.get('status'):
		handoff_info = matched_state.get('handed_off_to') if isinstance(matched_state.get('handed_off_to'), dict) else {}
		handoff_raw = str(handoff_info.get('project_root') or '').strip()
		if handoff_raw:
			handoff_root = Path(handoff_raw).resolve()
			target_state = _find_turn_state(_turns_dir(handoff_root), session_id, last_user_step)
			if None is target_state:
				# 2026-11-24
				# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
				# https://github.com/dmitry-ai/harness/issues/197
				# 2026-11-24
				# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
				# https://github.com/dmitry-ai/harness/issues/224
				# 2026-11-24
				# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
				# https://github.com/dmitry-ai/harness/issues/225
				return apply_continuation_guard(t_dir, session_id, last_user_step, matched_state, {'decision': 'continue', 'reason': f'FILE-3 / SCOPE-3 Stop Gate: Launcher turn was handed off to {handoff_root}, which has no turn-begin / answer-prepare record for the active turn. Run turn-begin and answer-prepare (or answer-prepare --blocked-report after saving continuation.md if blocked) in {handoff_root} before finishing the response.'}, payload, segment=segment)
			matched_state = target_state
	if None is matched_state:
		# 2026-11-24
		# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
		# https://github.com/dmitry-ai/harness/issues/197
		# 2026-11-24
		# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
		# https://github.com/dmitry-ai/harness/issues/224
		# 2026-11-24
		# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
		# https://github.com/dmitry-ai/harness/issues/225
		# 2026-11-26
		# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
		# https://github.com/dmitry-ai/harness/issues/255
		return apply_continuation_guard(t_dir, session_id, last_user_step, None, {'decision': 'continue', 'reason': 'FILE-3 / SCOPE-3 Stop Gate: Active turn has no turn-begin / answer-prepare record. Run turn-begin and answer-prepare (or answer-prepare --blocked-report after saving continuation.md for a pre-finalize blocker) before finishing the response.'}, payload, segment=segment, emergency_ctx={'root': canon_root, 'backend': backend, 'rows': rows, 'last_planner_text': last_planner_text, 'log_file': log_file})
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	# 2026-11-23
	# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
	# https://github.com/dmitry-ai/harness/issues/138
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	# 2026-11-23
	# "Extract PreToolUse and completion gates into priority plugin registry":
	# https://github.com/dmitry-ai/harness/issues/167
	from agent_tools.gates import run_stop_gates
	gate_hit = run_stop_gates(matched_state)
	decision = gate_hit if None is not gate_hit else _evaluate_prepared_match(matched_state, last_planner_text)
	# 2026-11-24
	# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
	# https://github.com/dmitry-ai/harness/issues/197
	# 2026-11-24
	# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
	# https://github.com/dmitry-ai/harness/issues/224
	# 2026-11-26
	# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
	# https://github.com/dmitry-ai/harness/issues/255
	return apply_continuation_guard(t_dir, session_id, last_user_step, matched_state, decision, payload, segment=segment, emergency_ctx={'root': canon_root, 'backend': backend, 'rows': rows, 'last_planner_text': last_planner_text, 'log_file': log_file})
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def main():
	_ensure_scripts_on_path()
	from agent_tools.hook_runtime import run_json_hook
	run_json_hook(evaluate_stop_payload)
if '__main__' == __name__:
	main()
