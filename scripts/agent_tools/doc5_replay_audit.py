# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce historical feature-turn regression audit before worktree landing":
# https://github.com/dmitry-ai/harness/issues/373
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import os
import re
import subprocess
import sys
import tempfile
from . import doc5_context
from .git_gate import _NO_WINDOW
from .path_registry import project_paths
from .platforms import adapter
_ANSWER_GATE_PATHS = frozenset({
	'scripts/agent_tools/cli_command_grounding.py',
	'scripts/agent_tools/cli_output_json.py',
	'scripts/agent_tools/doc5_context.py',
	'scripts/agent_tools/doc5_replay_audit.py',
	'scripts/agent_tools/gates/answer_checks.py',
	'scripts/agent_tools/problem_tracks.py',
	'scripts/agent_tools/response_grounding.py',
	'scripts/agent_tools/statements.py',
	'scripts/agent_tools/verification_observability.py',
})
_PROBLEM_HEADING_RE = re.compile(r'(?m)^#\s*0\.')
# @used-by :func:`audit_feature_turn_corpus()`
def _audit_one_fixture(path: Path, tmp_dir: Path) -> dict[str, Any]:
	data = json.loads(path.read_text(encoding='utf-8'))
	name = str(data.get('name') or path.stem)
	expected = bool(data.get('expected_doc5'))
	case_dir = tmp_dir / path.stem
	case_dir.mkdir(parents=True, exist_ok=True)
	local_repo = str(data.get('local_repo') or '').strip()
	if local_repo:
		git_dir = case_dir / '.git'
		git_dir.mkdir(parents=True, exist_ok=True)
		(git_dir / 'config').write_text(f'[remote "origin"]\n\turl = https://github.com/{local_repo}.git\n', encoding='utf-8')
	tx = case_dir / 'transcript.jsonl'
	tx.write_text(''.join((json.dumps(row, ensure_ascii=False) + '\n' for row in data.get('rows') or ())), encoding='utf-8')
	turn = {'turn_id': f'fixture-{name}', 'start_step': 0, 'requests': [str(data.get('request') or '')], 'issue_actions': list(data.get('issue_actions') or ())}
	actual = bool(doc5_context.turn_requires_doc5_problem_analysis({'root': case_dir, 'turn': turn, 'native': {'source_file': str(tx)}}))
	return {'name': name, 'file': path.name, 'expected': expected, 'actual': actual, 'matched': expected == actual}
# @used-by :func:`verify_worktree_answer_gate_corpus()`
def _changed_files_in_worktree(wt_path: Path, target_branch: str) -> list[str]:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(wt_path), 'diff', '--name-only', f'{target_branch}..HEAD'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, creationflags=_NO_WINDOW, check=False)
	return [ln.strip().replace('\\', '/') for ln in proc.stdout.splitlines() if ln.strip()] if 0 == proc.returncode else []
# @used-by :func:`_load_saved_turn_entry()`
def _is_problem_response(state: dict[str, Any]) -> bool:
	rf = str((state.get('prepared') or {}).get('response_file') or '').strip()
	r = False
	if rf:
		p = Path(rf)
		if p.is_file():
			try:
				r = bool(_PROBLEM_HEADING_RE.search(p.read_text(encoding='utf-8', errors='replace')))
			except OSError:
				r = False
	return r
# @used-by :func:`audit_local_saved_turns()`
def _load_saved_turn_entry(root_p: Path, state_file: Path) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	try:
		state = json.loads(state_file.read_text(encoding='utf-8'))
	except (OSError, ValueError):
		state = None
	if isinstance(state, dict) and 'delivered' == state.get('status') and state.get('conversation_id') and (not _is_problem_response(state)):
		try:
			native = adapter(state.get('platform')).native_answers(root_p, str(state['conversation_id']), backend=state.get('native_backend'))
		except (FileNotFoundError, OSError, ValueError):
			native = None
		if isinstance(native, dict):
			turn_obj = _match_native_turn(native, state)
			if None is not turn_obj:
				r = {'key': str(state.get('key') or state_file.stem), 'turn': turn_obj, 'native': native}
	return r
# @used-by :func:`_load_saved_turn_entry()`
def _match_native_turn(native: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
	turns = [t for t in (native.get('turns') or ()) if isinstance(t, dict)]
	tid = str(state.get('native_turn_id') or '').strip()
	r: dict[str, Any] | None = None
	for t in turns:
		if tid and tid == str(t.get('turn_id') or ''):
			r = t
			break
	if None is r and 1 == len(turns):
		r = turns[0]
	return r
# @used-by :func:`verify_worktree_answer_gate_corpus()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_tracked_feature_turn_corpus_has_zero_false_positives_and_catches_regression()`
def _run_worktree_corpus_subprocess(wt_path: Path, fixtures_dir: Path, *, timeout: float=120.0) -> dict[str, Any]:
	code = 'import json, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from agent_tools.doc5_replay_audit import audit_feature_turn_corpus; print(json.dumps(audit_feature_turn_corpus(Path(sys.argv[2]))))'
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
	proc = subprocess.run([sys.executable, '-c', code, str(wt_path / 'scripts'), str(fixtures_dir)], cwd=str(wt_path), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=_NO_WINDOW, check=False)
	lines = [ln.strip() for ln in (proc.stdout or '').splitlines() if ln.strip()]
	r: dict[str, Any] = {'valid': False, 'skipped': False, 'checked': 0, 'false_positives': [], 'false_negatives': [], 'error': (proc.stderr or proc.stdout or f'exit {proc.returncode}').strip()}
	if 0 == proc.returncode and lines:
		try:
			parsed = json.loads(lines[-1])
			if isinstance(parsed, dict):
				parsed.setdefault('skipped', False)
				r = parsed
		except ValueError:
			pass
	return r
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_tracked_feature_turn_corpus_has_zero_false_positives_and_catches_regression()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def audit_feature_turn_corpus(fixtures_dir: Path | str) -> dict[str, Any]:
	root = Path(fixtures_dir).resolve()
	files = sorted(root.glob('*.json')) if root.is_dir() else []
	results: list[dict[str, Any]] = []
	with tempfile.TemporaryDirectory() as td:
		tmp_dir = Path(td)
		for fpath in files:
			results.append(_audit_one_fixture(fpath, tmp_dir))
	fps = [x['file'] for x in results if (not x['expected']) and x['actual']]
	fns = [x['file'] for x in results if x['expected'] and (not x['actual'])]
	return {'valid': (0 < len(results)) and (not fps) and (not fns), 'checked': len(results), 'false_positives': fps, 'false_negatives': fns, 'results': results}
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_audit_local_saved_turns_flags_false_positives_and_passes_clean_history()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def audit_local_saved_turns(project_root: Path | str, *, limit: int=20) -> dict[str, Any]:
	root_p = Path(project_root).resolve()
	turns_dir = project_paths(root_p, exact_root=True).turns_dir
	files = sorted((p for p in turns_dir.glob('*.json') if '-' not in p.stem), key=lambda p: p.stat().st_mtime, reverse=True) if turns_dir.is_dir() else []
	results: list[dict[str, Any]] = []
	for sf in files:
		if len(results) >= limit:
			break
		entry = _load_saved_turn_entry(root_p, sf)
		if None is not entry:
			req = bool(doc5_context.turn_requires_doc5_problem_analysis({'root': root_p, 'turn': entry['turn'], 'native': entry['native']}))
			results.append({'turn_key': entry['key'], 'requires_doc5': req})
	fps = [x['turn_key'] for x in results if x['requires_doc5']]
	return {'valid': not fps, 'checked': len(results), 'false_positives': fps, 'results': results}
# @used-by :func:`agent_tools.worktree_flow._check_land_diff_coverage()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def verify_worktree_answer_gate_corpus(wt_path: Path, target_branch: str) -> dict[str, Any]:
	changed = set(_changed_files_in_worktree(wt_path, target_branch))
	touched_gates = sorted(changed & _ANSWER_GATE_PATHS)
	fixtures_dir = Path(wt_path).resolve() / 'tests/fixtures/feature_turns'
	if (not touched_gates) or (not fixtures_dir.is_dir()):
		r: dict[str, Any] = {'valid': True, 'skipped': True, 'checked': 0, 'false_positives': [], 'false_negatives': [], 'touched_gates': touched_gates}
	else:
		r = _run_worktree_corpus_subprocess(Path(wt_path).resolve(), fixtures_dir)
		r['touched_gates'] = touched_gates
	return r
__all__ = ['audit_feature_turn_corpus', 'audit_local_saved_turns', 'verify_worktree_answer_gate_corpus']
