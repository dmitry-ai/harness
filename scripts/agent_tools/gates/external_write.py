# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
import json
from pathlib import Path
import re
from ..path_registry import project_paths
NAME = 'SCOPE-2-EXTERNAL-WRITE-GATE'
PRIORITY = 40
EXTERNAL_WRITE_INTENT_RE = re.compile('(?i)\\b(?:github|gh\\s+issue|df_github_issue|df-github-issue|issue\\s*#?\\d+|create\\s+(?:an?\\s+)?issue|open\\s+(?:an?\\s+)?issue|close\\s+(?:the\\s+)?issue|edit\\s+(?:the\\s+)?issue|comment\\s+on\\s+issue|git\\s+push|commit|pull\\s+request|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\w+|\\u0441\\u0434\\u0435\\u043b\\u0430\\u0439\\w*|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u0443\\u0439\\w*|\\u043f\\u0435\\u0440\\u0435\\u0434\\u0435\\u043b\\u0430\\u0439\\w*|\\u0437\\u0430\\u043a\\u043e\\u043c\\u043c\\u0438\\u0442\\w+|\\u043e\\u043f\\u0443\\u0431\\u043b\\u0438\\u043a\\u0443\\u0439\\w*|\\u0441\\u043e\\u0437\\u0434\\u0430\\u0439\\w*\\s+issue|\\u0437\\u0430\\u043a\\u0440\\u043e\\u0439\\w*\\s+issue|\\u043e\\u0431\\u043d\\u043e\\u0432\\u0438\\w*\\s+issue)\\b')
_AUX_SUFFIXES = ('-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json')
def _cand_paths_from_cmd(cmd: str) -> list[Path]:
	cands: list[Path] = []
	for m in re.finditer('(?:--project-root|--body-file|-F|--title-file|--comment-file)\\s+(?:"([^"]+)"|\'([^\']+)\'|(\\S+))', cmd):
		raw_p = m.group(1) or m.group(2) or m.group(3)
		if raw_p:
			try:
				cands.append(Path(raw_p).resolve())
			except OSError:
				pass
	try:
		cands.append(Path.cwd().resolve())
	except OSError:
		pass
	return cands
def _has_uninstructed_open_turn(tfile: Path) -> bool:
	r = False
	if not tfile.name.endswith(_AUX_SUFFIXES):
		try:
			tdata = json.loads(tfile.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			tdata = None
		if isinstance(tdata, dict) and 'open' == tdata.get('status') and (True is not tdata.get('external_write_authorized')):
			req_text = '\n'.join((item.get('text', '') if isinstance(item, dict) else str(item) for item in tdata.get('requests') or []))
			r = bool(req_text.strip()) and (not EXTERNAL_WRITE_INTENT_RE.search(req_text))
	return r
def _check_df_issue_turn_intent(cmd: str) -> str | None:
	r = None
	proj_root = _upwork_project_root_for_command(cmd)
	turns_dir = project_paths(proj_root).turns_dir if None is not proj_root else None
	if None is not turns_dir and turns_dir.is_dir() and any((_has_uninstructed_open_turn(tf) for tf in turns_dir.glob('*.json'))):
		r = 'SCOPE-2 / EXEC-5: Uninstructed external GitHub write (df_github_issue.py create/edit/comment/close) during a read-only analysis turn is prohibited without an explicit user instruction.'
	return r
def _match_upwork_root(cand: Path) -> Path | None:
	r = None
	try:
		pp = project_paths(cand)
		if pp.project_json.is_file():
			r = pp.root
	except (OSError, ValueError):
		pass
	if None is r:
		r = next((anc for anc in (cand, *cand.parents) if (anc / '\ua616/project.json').is_file()), None)
	return r
def _upwork_project_root_for_command(cmd: str) -> Path | None:
	return next((hit for cand in _cand_paths_from_cmd(cmd) if None is not (hit := _match_upwork_root(cand))), None)
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		cmd = args.get('CommandLine') or ''
		if re.search('(?:^|[;|\\n&]|\\s)gh(?:\\.exe)?\\s+issue\\s+(?:create|edit|comment|close|reopen|delete)\\b', cmd, re.I):
			r = 'EXEC-5 / SCOPE-2: Direct gh issue write commands in the shell are prohibited; use df_github_issue.py with UTF-8 file input and mandatory API read-back verification.'
		elif re.search('(?:^|[;|\\n&]|\\s)gh(?:\\.exe)?\\s+api\\b[^;|\\n]*(?:--method(?:\\s+|=)|-X\\s*)(?:POST|PATCH|PUT|DELETE)\\b', cmd, re.I):
			r = 'EXEC-5 / SCOPE-2: Direct mutating gh api calls (POST/PATCH/PUT/DELETE) in the shell are prohibited; use df_github_issue.py.'
		elif any((re.search('(?:--input|-f|--raw-field|-F|--field)(?:\\s|=|$)', m.group(1)) and (not re.search('(?:--method(?:\\s+|=)|-X\\s*)GET\\b', m.group(1), re.I)) for m in re.finditer('(?:^|[;|\\n&]|\\s)(gh(?:\\.exe)?\\s+api\\b[^;|\\n]*)', cmd, re.I))):
			r = 'EXEC-5 / SCOPE-2: Direct mutating gh api calls with input/field arguments are prohibited; use df_github_issue.py.'
		elif re.search('\\bdf_github_issue\\.py\\s+(?:create|edit|comment|close)\\b', cmd, re.I):
			r = _check_df_issue_turn_intent(cmd)
	return r
