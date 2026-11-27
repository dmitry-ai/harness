# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.text.starts_ends import df_starts_with
from Df.Harness.Git.ShellSegmenter import ShellSegmenter
from agent_tools.cli_common import dump_json
from agent_tools.storage import iter_embedded_json_objects
import argparse
import json
import re
import subprocess
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_BATCH_ACTIONS = frozenset({'batch-close', 'batch-create'})
_DF_ISSUE_CMD_RE = re.compile(r'^\s*(?:&\s*)?(?:["\']?[^\s"\']*python(?:3(?:\.\d+)?)?(?:\.exe)?["\']?\s+(?:-[A-Za-z0-9_]+\s+)*)?["\']?(?:[^"\']*[/\\])?df_github_issue\.py["\']?\s+(create|fetch|edit|comment|close|batch-create|batch-close)\b', re.IGNORECASE)
_DF_ISSUE_VAR_RE = re.compile(r'(\$[A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\'][^"\']*df_github_issue\.py["\']', re.I)
_EXCLUDED_META_PARTS = frozenset((p.casefold() for p in ('.git', '__pycache__', 'node_modules', '\ua616', '\ua66e', '\U0001f56e')))
_EXCLUDED_META_PREFIXES = tuple((p.casefold() for p in ('.git/', '__pycache__/', 'node_modules/', '\ua616/', '\ua66e/', '_/', '\U0001f56e/', '\u2c0f/\u227a/', 'artifacts/\u227a/')))
_PY_INLINE_C_RE = re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\b')
_SINGLE_ACTIONS = frozenset({'close', 'comment', 'create', 'edit', 'fetch'})
_TEMP_PATH_RE = re.compile(r'(?i)(?:[/\\]temp[/\\]|[/\\]tmp[/\\])')
# @used-by :func:`_extract_single_action()`
# @used-by :func:`dfh_extract_actions_from_decoded_obj()`
def _consumed_has_temp(obj: dict[str, Any]) -> bool:
	consumed = obj.get('consumed_files')
	return isinstance(consumed, list) and any((bool(_TEMP_PATH_RE.search(str(cf))) for cf in consumed))
# @used-by :func:`dfh_gh_api_call()`
def _decode_gh_stdout(raw_out: str, paginate: bool) -> Any:
	if not raw_out.strip():
		r: Any = None
	elif not (paginate and raw_out.lstrip().startswith('[')):
		r = json.loads(raw_out)
	else:
		merged: list[Any] = []
		for obj in iter_embedded_json_objects(raw_out):
			merged.extend(obj) if isinstance(obj, list) else merged.append(obj)
		r = merged
	return r
# @used-by :func:`dfh_extract_actions_from_decoded_obj()`
def _extract_single_action(obj: dict[str, Any]) -> dict[str, Any] | None:
	act, repo = (obj.get('action'), obj.get('repo'))
	r: dict[str, Any] | None = None
	if obj.get('ok', True) and (not _consumed_has_temp(obj)) and act in _SINGLE_ACTIONS and isinstance(repo, str) and '/' in repo:
		num = obj.get('number')
		if None is num:
			m = re.search(r'/issues/(\d+)\b', str(obj.get('html_url') or ''))
			num = int(m.group(1)) if None is not m else None
		if isinstance(num, int) and (not isinstance(num, bool)):
			r = {'action': act, 'number': num, 'ok': bool(obj.get('ok', True)), 'repo': repo, 'state': obj.get('state'), 'url': f'https://github.com/{repo}/issues/{num}'}
			if isinstance(obj.get('parent_number'), int) and (not isinstance(obj.get('parent_number'), bool)):
				r['parent_number'] = obj['parent_number']
	return r
# @used-by :func:`dfh_is_df_issue_command_text()`
def _var_issue_matches(cmd: str, segments: list[str]) -> bool:
	r = False
	for vname in _DF_ISSUE_VAR_RE.findall(cmd):
		pat = re.compile(rf'(?i)(?:^|[\s&;])(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+(?:-[A-Za-z0-9_]+\s+)*)?["\']?{re.escape(vname)}["\']?\s+(?:create|fetch|edit|comment|close|batch-create|batch-close)\b')
		if any((pat.search(s) and (not _PY_INLINE_C_RE.search(s)) for s in segments)):
			r = True
			break
	return r
# @used-by :func:`agent_tools.issues.service_helpers.build_create_payload()`
# @used-by :meth:`Df.Harness.Issue.Service.Service.__execute_create()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_build_create_payload(args: argparse.Namespace, title: str, body: str) -> dict[str, Any]:
	payload: dict[str, Any] = {'title': title, 'body': body}
	if getattr(args, 'label', None):
		labels = [lbl.strip() for item in args.label for lbl in item.split(',') if lbl.strip()]
		if labels:
			payload['labels'] = labels
	if getattr(args, 'assignee', None):
		assignees = [a.strip() for item in args.assignee for a in item.split(',') if a.strip()]
		if assignees:
			payload['assignees'] = assignees
	if None is not getattr(args, 'milestone', None):
		payload['milestone'] = args.milestone
	return payload
# @used-by :func:`agent_tools.issues.comment_grounding.emit_grounding_failure()`
# @used-by :meth:`Df.Harness.Issue.CloseCommentValidator.CloseCommentValidator.validate()`
# @used-by :meth:`Df.Harness.Issue.CommentGrounder.CommentGrounder.check_preflight()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_emit_grounding_failure(action: str, repo: str, errors: list[str], *, number: int | None=None, comment_id: int | None=None) -> int:
	out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'pre_flight_grounding', 'repo': repo, 'grounding_errors': errors}
	if None is not number:
		out['number'] = number
	if None is not comment_id:
		out['comment_id'] = comment_id
	dump_json(out)
	return 2
# @used-by :func:`agent_tools.issues.batch_commands.extract_actions_from_decoded_obj()`
# @used-by :meth:`Df.Harness.Git.IssueActionExtractor.IssueActionExtractor.__decode_text()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_extract_actions_from_decoded_obj(obj: dict[str, Any]) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	if obj.get('action') in _BATCH_ACTIONS and isinstance(obj.get('results'), list) and (not _consumed_has_temp(obj)):
		for item in obj['results']:
			if isinstance(item, dict):
				act = _extract_single_action(item)
				if None is not act:
					r.append(act)
	else:
		act = _extract_single_action(obj)
		if None is not act:
			r.append(act)
	return r
# @used-by :func:`agent_tools.github_issue._gh_api()`
# @used-by :func:`agent_tools.issues.service_helpers.gh_api_call()`
# @used-by :meth:`Df.Harness.Issue.Service.Service.__init__()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_gh_api_call(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False, runner=None) -> Any:
	cmd = ['gh', 'api', endpoint]
	if 'GET' != method:
		cmd.extend(['-X', method])
	if paginate:
		cmd.append('--paginate')
	input_bytes = None
	if None is not payload:
		cmd.extend(['--input', '-'])
		input_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
	run_fn = runner if None is not runner else subprocess.run
	proc = run_fn(cmd, input=input_bytes, capture_output=True, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	if 0 != proc.returncode:
		err_msg = proc.stderr.decode('utf-8', errors='replace').strip() or proc.stdout.decode('utf-8', errors='replace').strip()
		raise RuntimeError(f'gh api {method} {endpoint} failed (exit {proc.returncode}): {err_msg}')
	return _decode_gh_stdout(proc.stdout.decode('utf-8'), paginate)
# @used-by :func:`agent_tools.issue_first_bg.is_df_issue_command_text()`
# @used-by :func:`agent_tools.issue_first_gate.is_df_github_issue_command()`
# @used-by :meth:`Df.Harness.Issue.BgTaskRecorder.BgTaskRecorder.__record_seg_issues()`
# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.build_issue_action_events()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_issue_first_pretool_evaluator_bg_scanner_and_var_match()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_is_df_issue_command_text(cmd: str, direct_re=None) -> bool:
	pat = direct_re if None is not direct_re else _DF_ISSUE_CMD_RE
	r = False
	if isinstance(cmd, str) and 'df_github_issue.py' in cmd.lower():
		segs = [seg.strip() for seg in ShellSegmenter(cmd).split() if seg.strip()]
		r = any((pat.match(s) and (not _PY_INLINE_C_RE.search(s)) for s in segs)) or _var_issue_matches(cmd, segs)
	return r
# @used-by :func:`agent_tools.issue_first_gate._is_excluded_meta_rel()`
# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.__parse_dirty_porcelain()`
# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__resolve_repo_rel()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_is_excluded_meta_rel(rel_posix: str, *, starts_with_fn=None) -> bool:
	low = rel_posix.replace('\\', '/').casefold()
	while low.startswith('./'):
		low = low[2:]
	low = low.lstrip('/')
	sw_fn = starts_with_fn if None is not starts_with_fn else df_starts_with
	if (not low) or '.' == low or sw_fn(low, list(_EXCLUDED_META_PREFIXES)):
		r = True
	else:
		r = any((part in _EXCLUDED_META_PARTS for part in low.split('/')[:-1]))
	return r
# @used-by :func:`agent_tools.issues.service_helpers.resolve_title()`
# @used-by :meth:`Df.Harness.Issue.IssueLintRunner.IssueLintRunner.run()`
# @used-by :meth:`Df.Harness.Issue.Service.Service.__parse_edit_inputs()`
# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_create()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
def dfh_resolve_title(args: argparse.Namespace, consumable: list[tuple[Path, bytes]]) -> str | None:
	from Df.Harness.Issue.Linter import Linter
	if getattr(args, 'title_file', None):
		t_path, t_raw, t_text = Linter.read_utf8_no_bom_file(args.title_file)
		consumable.append((t_path, t_raw))
		r = t_text.strip()
	elif None is not getattr(args, 'title', None):
		r = args.title.strip()
	else:
		r = None
	return r
