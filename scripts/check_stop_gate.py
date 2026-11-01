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
def _is_tracked_workspace(root: Path) -> bool:
	return (root / '\ua616/project.json').is_file() or (root / '_/\ua66e').is_dir() or (root / '\ua66e').is_dir()
def _turns_dir(root: Path) -> Path:
	return (root / '_/\ua616/data/turns') if (root / '_/\ua616').is_dir() else (root / '\ua616/data/turns')
def _is_child_conversation(backend: Path, conversation_id: str) -> bool:
	db_path = backend / 'conversation_summaries.db'
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
	if not _is_tracked_workspace(root):
		return {'decision': 'allow'}
	t_path = Path(t_path_raw).resolve() if t_path_raw else None
	backend = Path(backend_override).resolve() if None is not backend_override else (t_path.parents[3] if None is not t_path and len(t_path.parents) >= 4 else (Path.home() / '.gemini/antigravity'))
	if _is_child_conversation(backend, session_id):
		return {'decision': 'allow'}
	full_t = t_path.parent / 'transcript_full.jsonl' if None is not t_path else (backend / 'brain' / session_id / '.system_generated/logs/transcript_full.jsonl')
	log_file = full_t if full_t.is_file() else t_path
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
	unwatched = False
	last_planner_text = ''
	for r in segment:
		if 'EPHEMERAL_MESSAGE' == r.get('type') and re.search('<SYSTEM_MESSAGE>.*\\bSubagent\\b.*\\bcompleted\\b', str(r.get('content') or ''), re.S):
			completed += 1
		calls = [c for c in r.get('tool_calls') or [] if isinstance(c, dict)]
		for c in calls:
			if 'invoke_subagent' == c.get('name'):
				spawned += 1
			if 'run_command' == c.get('name'):
				args = c.get('args') or {}
				cmd = args.get('CommandLine', '') if isinstance(args, dict) else str(args)
				if re.search('\\bjournal-unwatch\\b', cmd):
					unwatched = True
		if 'PLANNER_RESPONSE' == r.get('type') and (not calls) and str(r.get('content') or '').strip():
			last_planner_text = str(r.get('content'))
	if unwatched or completed < spawned:
		return {'decision': 'allow'}
	t_dir = _turns_dir(root)
	matched_state = None
	if t_dir.is_dir():
		for sf in t_dir.glob('*.json'):
			if sf.name.endswith('-checkpoint-recovery.json'):
				continue
			try:
				st = json.loads(sf.read_text(encoding='utf-8'))
			except Exception:
				continue
			if not isinstance(st, dict) or st.get('conversation_id') != session_id:
				continue
			req_steps = {req.get('native_step') for req in st.get('requests') or [] if isinstance(req, dict)}
			if st.get('native_turn_id') == f'ag-{session_id}-{last_user_step}' or last_user_step in req_steps or st.get('native_start_step') == last_user_step:
				matched_state = st
				break
	if None is matched_state:
		return {'decision': 'continue', 'reason': 'FILE-3 / SCOPE-3 Stop Gate: Active turn has no turn-begin / answer-prepare record. Run turn-begin and answer-prepare before finishing the response.'}
	prep = matched_state.get('prepared')
	if matched_state.get('status') not in ('prepared', 'delivered') or (not isinstance(prep, dict)) or (not matched_state.get('readiness_check', {}).get('verified')):
		detail = (matched_state.get('readiness_check') or {}).get('detail') or 'answer-prepare has not succeeded for the current turn'
		return {'decision': 'continue', 'reason': f'FILE-3 / EXEC-5 Stop Gate: Turn is not prepared ({detail}). Run harness.py answer-prepare and output the exact prepared response.'}
	if last_planner_text:
		sha = hashlib.sha256(last_planner_text.encode('utf-8')).hexdigest()
		if sha != prep.get('response_sha256'):
			res_file = Path(prep.get('response_file') or '')
			prep_text = res_file.read_text(encoding='utf-8', errors='replace') if res_file.is_file() else ''
			if not prep_text or _strip_local_file_scheme(prep_text) != _strip_local_file_scheme(last_planner_text):
				return {'decision': 'continue', 'reason': 'FILE-3 Stop Gate: Final response text does not match the prepared response in res/<N>.md. Read back res/<N>.md and output its exact bytes without post-prepare edits.'}
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
