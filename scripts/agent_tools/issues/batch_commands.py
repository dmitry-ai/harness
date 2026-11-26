# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-flight comment grounding and add batch GitHub issue commands":
# https://github.com/dmitry-ai/harness/issues/353
from __future__ import annotations
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from ..cli_common import add_arg_specs, consume_unchanged_files, dump_json
import argparse
import io
import json
import re
_BATCH_ACTIONS = frozenset({'batch-close', 'batch-create'})
_BATCH_REPO_SPEC = (('--repo', '-R'), {'help': 'Default repository in owner/repo format for batch items.'})
_BATCH_SPEC_ARG = (('--spec-file', '-S'), {'required': True, 'help': 'UTF-8 JSON file containing batch issue item specifications.'})
_SINGLE_ACTIONS = frozenset({'close', 'comment', 'create', 'edit', 'fetch'})
_TEMP_PATH_RE = re.compile(r'(?i)(?:[/\\]temp[/\\]|[/\\]tmp[/\\])')
# @used-by :func:`run_batch_close()`
def _build_close_item_args(item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int) -> argparse.Namespace:
	raw_num = item.get('issue') if None is not item.get('issue') else item.get('number')
	if None is raw_num or isinstance(raw_num, bool):
		raise ValueError(f'Batch close item #{idx + 1} is missing required integer "issue"')
	return argparse.Namespace(comment_file=_materialize_text_file(item, 'comment_file', 'comment', spec_dir, tmp_files, idx), consume_input=bool(item.get('consume_input', defaults['consume_input'])), conversation=item.get('conversation') or defaults['conversation'], issue=int(raw_num), project_root=item.get('project_root') or defaults['project_root'], reason=item.get('reason') or defaults['reason'], repo=item.get('repo') or defaults['repo'], repo_root=item.get('repo_root') or defaults['repo_root'], target_locale=item.get('target_locale') or defaults['target_locale'])
# @used-by :func:`run_batch_create()`
def _build_create_item_args(item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int) -> argparse.Namespace:
	parent_val = item['parent'] if 'parent' in item else defaults['parent']
	body_file = _materialize_text_file(item, 'body_file', 'body', spec_dir, tmp_files, idx)
	if None is body_file:
		raise ValueError(f'Batch create item #{idx + 1} is missing required "body_file" or "body"')
	return argparse.Namespace(assignee=_norm_str_list(item.get('assignees') or item.get('assignee')), body_file=body_file, consume_input=bool(item.get('consume_input', defaults['consume_input'])), conversation=item.get('conversation') or defaults['conversation'], label=_norm_str_list(item.get('labels') or item.get('label')), milestone=item.get('milestone'), no_metadata=bool(item.get('no_metadata', defaults['no_metadata'])), parent=str(parent_val) if None is not parent_val else None, project_root=item.get('project_root') or defaults['project_root'], repo=item.get('repo') or defaults['repo'], repo_root=item.get('repo_root') or defaults['repo_root'], target_locale=item.get('target_locale') or defaults['target_locale'], title=item.get('title'), title_file=_resolve_optional_path(item.get('title_file'), spec_dir))
# @used-by :func:`_run_batch_items()`
def _cleanup_tmp_files(tmp_files: list[Path]) -> None:
	for fp in tmp_files:
		try:
			fp.unlink(missing_ok=True)
		except OSError:
			pass
# @used-by :func:`_extract_single_action()`
# @used-by :func:`extract_actions_from_decoded_obj()`
def _consumed_has_temp(obj: dict[str, Any]) -> bool:
	consumed = obj.get('consumed_files')
	return isinstance(consumed, list) and any((bool(_TEMP_PATH_RE.search(str(cf))) for cf in consumed))
# @used-by :func:`extract_actions_from_decoded_obj()`
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
# @used-by :func:`_run_batch_items()`
def _load_batch_spec(service, args: argparse.Namespace) -> tuple[Path, bytes, list[dict[str, Any]], dict[str, Any]]:
	spec_path, spec_raw, spec_text = service.linter.read_utf8_no_bom_file(args.spec_file)
	parsed = json.loads(spec_text)
	top = parsed if isinstance(parsed, dict) else {}
	items = parsed.get('items') if isinstance(parsed, dict) else parsed
	if not isinstance(items, list) or not items or any((not isinstance(it, dict) for it in items)):
		raise ValueError('Batch spec file must contain a non-empty JSON list of item objects')
	defaults = {'consume_input': bool(getattr(args, 'consume_input', False)), 'conversation': getattr(args, 'conversation', None) or top.get('conversation'), 'no_metadata': bool(getattr(args, 'no_metadata', False) or top.get('no_metadata', False)), 'parent': getattr(args, 'parent', None) or top.get('parent'), 'project_root': getattr(args, 'project_root', None) or top.get('project_root'), 'reason': getattr(args, 'reason', 'completed') or top.get('reason') or 'completed', 'repo': getattr(args, 'repo', None) or top.get('repo'), 'repo_root': getattr(args, 'repo_root', None) or top.get('repo_root'), 'target_locale': getattr(args, 'target_locale', 'en-US') or top.get('target_locale') or 'en-US'}
	return (spec_path, spec_raw, items, defaults)
# @used-by :func:`_build_close_item_args()`
# @used-by :func:`_build_create_item_args()`
def _materialize_text_file(item: dict[str, Any], file_key: str, text_key: str, spec_dir: Path, tmp_files: list[Path], idx: int) -> str | None:
	existing = _resolve_optional_path(item.get(file_key), spec_dir)
	if None is not existing:
		r: str | None = existing
	elif isinstance(item.get(text_key), str):
		tmp_p = spec_dir / f'.batch-inline-{idx}-{file_key}.md'
		tmp_p.write_text(item[text_key], encoding='utf-8', newline='\n')
		tmp_files.append(tmp_p)
		r = str(tmp_p)
	else:
		r = None
	return r
# @used-by :func:`_build_create_item_args()`
def _norm_str_list(raw: Any) -> list[str] | None:
	if isinstance(raw, str):
		r: list[str] | None = [raw]
	elif isinstance(raw, list):
		r = [str(v) for v in raw if None is not v]
	else:
		r = None
	return r
# @used-by :func:`_build_create_item_args()`
# @used-by :func:`_materialize_text_file()`
def _resolve_optional_path(raw: Any, spec_dir: Path) -> str | None:
	r: str | None = None
	if isinstance(raw, str) and raw.strip():
		p = Path(raw.strip())
		r = str(p if p.is_absolute() else (spec_dir / p).resolve())
	return r
# @used-by :func:`run_batch_close()`
# @used-by :func:`run_batch_create()`
def _run_batch_items(service, args: argparse.Namespace, batch_action: str, item_action: str, build_fn, exec_fn) -> int:
	spec_path, spec_raw, items, defaults = _load_batch_spec(service, args)
	results: list[dict[str, Any]] = []
	tmp_files: list[Path] = []
	try:
		for idx, item in enumerate(items):
			results.append(_run_single_item(item, defaults, spec_path.parent, tmp_files, idx, item_action, build_fn, exec_fn))
	finally:
		_cleanup_tmp_files(tmp_files)
	succeeded = sum((1 for it in results if it.get('ok')))
	all_ok = len(results) == succeeded
	removed = consume_unchanged_files([(spec_path, spec_raw)]) if all_ok and defaults['consume_input'] else []
	dump_json({'action': batch_action, 'consumed_files': removed, 'failed': len(results) - succeeded, 'ok': all_ok, 'repo': defaults['repo'], 'results': results, 'succeeded': succeeded, 'total': len(results)})
	return 0 if all_ok else 2
# @used-by :func:`_run_batch_items()`
def _run_single_item(item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int, item_action: str, build_fn, exec_fn) -> dict[str, Any]:
	buf = io.StringIO()
	try:
		item_args = build_fn(item, defaults, spec_dir, tmp_files, idx)
		with redirect_stdout(buf):
			rc = exec_fn(item_args)
		raw = buf.getvalue().strip()
		r = json.loads(raw) if raw else {'action': item_action, 'ok': 0 == rc, 'repo': getattr(item_args, 'repo', None)}
	except Exception as exc:
		r = {'action': item_action, 'error': str(exc), 'ok': False, 'repo': item.get('repo') or defaults['repo']}
	return r
# @used-by :meth:`Df.Harness.Git.IssueActionExtractor.IssueActionExtractor.__decode_text()`
def extract_actions_from_decoded_obj(obj: dict[str, Any]) -> list[dict[str, Any]]:
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
# @used-by :func:`agent_tools.github_issue.build_parser()`
def register_issue_subparsers(sub, sub_defs, common_tail_specs, service_fn) -> None:
	batch_defs = (
		('batch-create', 'Create multiple GitHub issues from a UTF-8 JSON spec file with verified read-back.', lambda a: run_batch_create(service_fn(a), a), (_BATCH_REPO_SPEC, _BATCH_SPEC_ARG, (('--parent', '-p'), {'help': 'Default parent problem issue number or URL for batch items.'}), ('--no-metadata', {'action': 'store_true', 'help': 'Skip automatic prepending of the Harness JSON metadata header.'}), *common_tail_specs)),
		('batch-close', 'Close multiple GitHub issues from a UTF-8 JSON spec file with pre-flight grounding and read-back.', lambda a: run_batch_close(service_fn(a), a), (_BATCH_REPO_SPEC, _BATCH_SPEC_ARG, (('--reason', '-r'), {'choices': ['completed', 'not_planned'], 'default': 'completed', 'help': 'Default closure reason.'}), *common_tail_specs)),
	)
	for name, help_text, fn, specs in (*sub_defs, *batch_defs):
		p = sub.add_parser(name, help=help_text)
		add_arg_specs(p, specs)
		p.set_defaults(func=fn)
# @used-by :func:`register_issue_subparsers()`
def run_batch_close(service, args: argparse.Namespace) -> int:
	return _run_batch_items(service, args, 'batch-close', 'close', _build_close_item_args, service.cmd_close)
# @used-by :func:`register_issue_subparsers()`
def run_batch_create(service, args: argparse.Namespace) -> int:
	return _run_batch_items(service, args, 'batch-create', 'create', _build_create_item_args, service.cmd_create)
