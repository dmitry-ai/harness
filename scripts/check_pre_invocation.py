# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
# https://github.com/dmitry-ai/harness/issues/116
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
def _ensure_scripts_on_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
def _resolve_root(payload: dict) -> Path | None:
	_ensure_scripts_on_path()
	from agent_tools.platforms.trace_common import local_uri_to_path
	cwd_raw = str(payload.get('cwd') or '').strip()
	if cwd_raw:
		cand = local_uri_to_path(cwd_raw) if cwd_raw.lower().startswith('file://') else Path(cwd_raw)
		return Path(cand).resolve()
	ws = payload.get('workspacePaths')
	if isinstance(ws, list) and 1 == len(ws) and isinstance(ws[0], str) and ws[0].strip():
		raw = ws[0].strip()
		cand = local_uri_to_path(raw) if raw.lower().startswith('file://') else Path(raw)
		return Path(cand).resolve()
	return None
def _is_tracked_and_non_umbrella(root: Path) -> tuple[bool, Path]:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import canonicalize_root_dir, load_registry, project_paths
		canon = canonicalize_root_dir(root)
		if None is not load_registry().workspace_override(canon):
			return (False, canon)
		pp = project_paths(canon, exact_root=True)
		if pp.has_overlay or pp.project_json.is_file() or pp.journal_dir.is_dir() or pp.turns_dir.is_dir():
			return (True, canon)
	except Exception:
		canon = root
	tracked = (canon / '\ua616/project.json').is_file() or (canon / '_/\ua66e').is_dir() or (canon / '\ua66e').is_dir()
	return (tracked, canon)
def _turns_dir(canon_root: Path) -> Path:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import project_paths
		from agent_tools.storage import data_dir_for
		pp = project_paths(canon_root, exact_root=True)
		return pp.turns_dir if pp.has_explicit_path('turns_dir') else (data_dir_for(canon_root) / 'turns')
	except Exception:
		return (canon_root / '_/\ua616/data/turns') if (canon_root / '_/\ua616').is_dir() else (canon_root / '\ua616/data/turns')
def _scratch_answer_path(canon_root: Path, turn_key: str) -> str:
	_ensure_scripts_on_path()
	try:
		from agent_tools.path_registry import project_paths
		return (project_paths(canon_root, exact_root=True).scratch_dir / f'answer-{turn_key}.md').as_posix()
	except Exception:
		return (canon_root / '\ua616/data/scratch' / f'answer-{turn_key}.md').as_posix()
def _resolve_ag_paths(conversation_id: str, t_path: Path | None = None, backend_override: Path | None = None) -> tuple[Path, Path, Path, Path]:
	_ensure_scripts_on_path()
	resolved = None
	from agent_tools.runtime import platform_instances, resolve_antigravity_paths, settings
	if None is not backend_override:
		resolved = resolve_antigravity_paths(backend=backend_override, conversation_id=conversation_id)
	elif None is not t_path:
		cfg = settings()
		ag_insts = platform_instances('antigravity', config=cfg, include_disabled=True) if 'antigravity' in (cfg.get('platforms') or {}) else {}
		t_res = t_path.resolve()
		for inst in ag_insts.values():
			sp = inst['system_paths']
			for key in ('brain_dir', 'backend_dir'):
				val = sp.get(key)
				if val and t_res.is_relative_to(Path(val).resolve()):
					resolved = resolve_antigravity_paths(backend=sp.get('backend_dir'), instance=inst['id'], conversation_id=conversation_id, config=cfg)
					break
			if None is not resolved:
				break
	if None is resolved and None is t_path:
		resolved = resolve_antigravity_paths(conversation_id=conversation_id)
	if None is not resolved:
		return (Path(resolved['backend_dir']).resolve(), Path(resolved['brain_dir']).resolve(), Path(resolved['conversations_db']).resolve(), Path(resolved['conversations_dir']).resolve())
	if None is not backend_override:
		backend = Path(backend_override).resolve()
	elif None is not t_path:
		if len(t_path.parents) >= 5 and 'brain' == t_path.parents[3].name:
			backend = t_path.parents[4].resolve()
		elif len(t_path.parents) >= 4:
			backend = t_path.parents[3].resolve()
		else:
			backend = t_path.parent.resolve()
	else:
		from agent_tools.path_registry import default_platform_paths
		backend = Path(default_platform_paths('antigravity')['backend_dir']).resolve()
	return (backend, backend / 'brain', backend / 'conversation_summaries.db', backend / 'conversations')
def _summary_primary_status(conversations_db: Path, conversation_id: str) -> str:
	if not conversations_db.is_file():
		return 'unavailable'
	conn = sqlite3.connect(conversations_db.resolve().as_uri() + '?mode=ro', uri=True)
	try:
		row = conn.execute('SELECT parent_conversation_id FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
		if None is row:
			return 'unavailable'
		return 'child' if bool(row[0]) else 'primary'
	except Exception:
		return 'unavailable'
	finally:
		conn.close()
def _latest_completed_user_step(conversations_dir: Path, conversation_id: str) -> int | None:
	conv_db = conversations_dir / f'{conversation_id}.db'
	if not conv_db.is_file():
		return None
	conn = sqlite3.connect(conv_db.resolve().as_uri() + '?mode=ro', uri=True)
	try:
		row = conn.execute('SELECT MAX(idx) FROM steps WHERE step_type=14 AND status IN (3,5)').fetchone()
		return int(row[0]) if row and None is not row[0] else None
	except Exception:
		return None
	finally:
		conn.close()
def _has_planner_steps(conversations_dir: Path, conversation_id: str) -> bool:
	conv_db = conversations_dir / f'{conversation_id}.db'
	if not conv_db.is_file():
		return False
	conn = sqlite3.connect(conv_db.resolve().as_uri() + '?mode=ro', uri=True)
	try:
		return None is not conn.execute('SELECT 1 FROM steps WHERE step_type=15 LIMIT 1').fetchone()
	except Exception:
		return False
	finally:
		conn.close()
@contextmanager
def _pre_flush_begin_context(brain_dir: Path, conversations_dir: Path, conversation_id: str):
	logs_dir = brain_dir / conversation_id / '.system_generated/logs'
	full_t = logs_dir / 'transcript_full.jsonl'
	comp_t = logs_dir / 'transcript.jsonl'
	if full_t.is_file() or comp_t.is_file() or _has_planner_steps(conversations_dir, conversation_id):
		yield
		return
	_ensure_scripts_on_path()
	from agent_tools.platforms import antigravity as ag_mod
	orig_reader = ag_mod.read_jsonl_objects
	allowed = {full_t.resolve(), comp_t.resolve()}
	def _empty_if_unflushed(source, *, partial_error=None):
		if not isinstance(source, (bytes, bytearray)):
			src_p = Path(source)
			if not src_p.is_file() and src_p.resolve() in allowed:
				return []
		return orig_reader(source, partial_error=partial_error)
	ag_mod.read_jsonl_objects = _empty_if_unflushed
	try:
		yield
	finally:
		ag_mod.read_jsonl_objects = orig_reader
def _expected_turn_key(backend: Path, conversation_id: str, start_step: int) -> str:
	identity = ['antigravity', str(backend.resolve()), conversation_id, f'ag-{conversation_id}-{start_step}']
	raw = (json.dumps(identity, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	return hashlib.sha256(raw).hexdigest()[:40]
def _turn_step_already_covered(t_dir: Path, backend: Path, conversation_id: str, max_user_step: int) -> bool:
	if not t_dir.is_dir():
		return False
	direct = t_dir / f'{_expected_turn_key(backend, conversation_id, max_user_step)}.json'
	candidates = [direct] if direct.is_file() else []
	for sf in t_dir.glob('*.json'):
		if sf != direct and (not sf.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json'))):
			candidates.append(sf)
	for sf in candidates:
		try:
			st = json.loads(sf.read_text(encoding='utf-8'))
		except Exception:
			continue
		if not isinstance(st, dict) or st.get('conversation_id') != conversation_id:
			continue
		req_steps = {req.get('native_step') for req in st.get('requests') or [] if isinstance(req, dict)}
		if st.get('native_turn_id') == f'ag-{conversation_id}-{max_user_step}' or max_user_step in req_steps or st.get('native_start_step') == max_user_step:
			if st.get('status') in ('open', 'prepared', 'delivered', 'conflict'):
				return True
	return False
def _terminate_error(message: str) -> dict:
	return {'injectSteps': [{'errorMessage': {'userMessage': f'Harness PreInvocation turn-begin blocked: {message}'}}], 'terminationBehavior': 'terminate'}
def _is_binding_violation(exc: ValueError, canon_root: Path, conversation_id: str, backend: Path) -> bool:
	msg = str(exc)
	if any((tok in msg for tok in ('partial record', 'primary/child identity is unavailable', 'Exact current native conversation UUID required', 'Exact native Antigravity conversation UUID required'))):
		return False
	if any((tok in msg for tok in ('do not identify', 'bound to another project', 'already has a different journal', 'different native owner', 'exists in multiple Antigravity instances', 'A prepared answer does not cover'))):
		return True
	if 'No active native user turn belonging entirely to this project' in msg:
		try:
			from agent_tools.platforms import antigravity
			native = antigravity.native_answers(canon_root, conversation_id, backend=backend)
			return any((not t.get('completed') and (not t.get('aborted')) for t in native.get('turns') or []))
		except Exception:
			return False
	return False
def evaluate_pre_invocation_payload(payload: dict, *, backend_override: Path | None = None) -> dict:
	if not isinstance(payload, dict):
		return {}
	conversation_id = str(payload.get('conversationId') or payload.get('sessionId') or '').strip().lower()
	if not conversation_id or (not re.fullmatch('[a-f0-9-]{36}', conversation_id)):
		return {}
	root = _resolve_root(payload)
	if None is root:
		return {}
	tracked, canon_root = _is_tracked_and_non_umbrella(root)
	if not tracked:
		return {}
	t_path_raw = str(payload.get('transcriptPath') or '').strip()
	t_path = Path(t_path_raw).resolve() if t_path_raw else None
	try:
		backend, brain_dir, conversations_db, conversations_dir = _resolve_ag_paths(conversation_id, t_path=t_path, backend_override=backend_override)
	except ValueError as exc:
		if 'exists in multiple Antigravity instances' in str(exc):
			return _terminate_error(str(exc))
		return {}
	except Exception:
		return {}
	role = _summary_primary_status(conversations_db, conversation_id)
	if 'primary' != role:
		return {}
	max_user_step = _latest_completed_user_step(conversations_dir, conversation_id)
	if None is max_user_step:
		return {}
	t_dir = _turns_dir(canon_root)
	if _turn_step_already_covered(t_dir, backend, conversation_id, max_user_step):
		return {}
	with _pre_flush_begin_context(brain_dir, conversations_dir, conversation_id):
		try:
			from agent_tools import completion
			res = completion.begin(canon_root, conversation_id, platform='antigravity', backend=backend)
		except ValueError as exc:
			if _is_binding_violation(exc, canon_root, conversation_id, backend):
				return _terminate_error(str(exc))
			return {}
		except Exception:
			return {}
	if 'primary' == res.get('role') and res.get('turn_key'):
		turn_key = str(res['turn_key'])
		scratch_ans = _scratch_answer_path(canon_root, turn_key)
		return {'injectSteps': [{'systemMessage': {'systemMessage': f'Harness PreInvocation: turn-begin initialized (turn_key={turn_key}, scratch_answer={scratch_ans}).'}}]}
	return {}
def main() -> None:
	out: dict = {}
	try:
		raw = sys.stdin.read()
		if raw.strip():
			out = evaluate_pre_invocation_payload(json.loads(raw))
	except Exception:
		out = {}
	sys.stdout.write(json.dumps(out, ensure_ascii=False))
if '__main__' == __name__:
	main()
