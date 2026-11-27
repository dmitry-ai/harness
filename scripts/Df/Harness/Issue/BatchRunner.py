# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from agent_tools.cli_common import add_arg_specs, consume_unchanged_files, dump_json
import argparse
import io
import json
_BATCH_REPO_SPEC = (('--repo', '-R'), {'help': 'Default repository in owner/repo format for batch items.'})
_BATCH_SPEC_ARG = (('--spec-file', '-S'), {'required': True, 'help': 'UTF-8 JSON file containing batch issue item specifications.'})
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class BatchRunner:
	# @used-by :func:`agent_tools.issues.batch_commands.run_batch_close()`
	# @used-by :func:`agent_tools.issues.batch_commands.run_batch_create()`
	# @used-by :meth:`BatchRunner.register_subparsers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	def __init__(self, service, args: argparse.Namespace, mode: str) -> None:
		self.__service = service
		self.__args = args
		self.__mode = mode
	# @used-by :meth:`BatchRunner.run()`
	@classmethod
	def __build_close_args(cls, item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int) -> argparse.Namespace:
		raw_num = item.get('issue') if None is not item.get('issue') else item.get('number')
		if None is raw_num or isinstance(raw_num, bool):
			raise ValueError(f'Batch close item #{idx + 1} is missing required integer "issue"')
		return argparse.Namespace(comment_file=cls.__materialize_text(item, 'comment_file', 'comment', spec_dir, tmp_files, idx), consume_input=bool(item.get('consume_input', defaults['consume_input'])), conversation=item.get('conversation') or defaults['conversation'], issue=int(raw_num), project_root=item.get('project_root') or defaults['project_root'], reason=item.get('reason') or defaults['reason'], repo=item.get('repo') or defaults['repo'], repo_root=item.get('repo_root') or defaults['repo_root'], target_locale=item.get('target_locale') or defaults['target_locale'])
	# @used-by :meth:`BatchRunner.run()`
	@classmethod
	def __build_create_args(cls, item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int) -> argparse.Namespace:
		parent_val = item['parent'] if 'parent' in item else defaults['parent']
		body_file = cls.__materialize_text(item, 'body_file', 'body', spec_dir, tmp_files, idx)
		if None is body_file:
			raise ValueError(f'Batch create item #{idx + 1} is missing required "body_file" or "body"')
		return argparse.Namespace(assignee=cls.__norm_str_list(item.get('assignees') or item.get('assignee')), body_file=body_file, consume_input=bool(item.get('consume_input', defaults['consume_input'])), conversation=item.get('conversation') or defaults['conversation'], label=cls.__norm_str_list(item.get('labels') or item.get('label')), milestone=item.get('milestone'), no_metadata=bool(item.get('no_metadata', defaults['no_metadata'])), parent=str(parent_val) if None is not parent_val else None, project_root=item.get('project_root') or defaults['project_root'], repo=item.get('repo') or defaults['repo'], repo_root=item.get('repo_root') or defaults['repo_root'], target_locale=item.get('target_locale') or defaults['target_locale'], title=item.get('title'), title_file=cls.__resolve_path(item.get('title_file'), spec_dir))
	# @used-by :meth:`BatchRunner.run()`
	@staticmethod
	def __cleanup_tmp(tmp_files: list[Path]) -> None:
		for fp in tmp_files:
			try:
				fp.unlink(missing_ok=True)
			except OSError:
				pass
	# @used-by :meth:`BatchRunner.run()`
	def __load_spec(self) -> tuple[Path, bytes, list[dict[str, Any]], dict[str, Any]]:
		spec_path, spec_raw, spec_text = self.__service.linter.read_utf8_no_bom_file(self.__args.spec_file)
		parsed = json.loads(spec_text)
		top = parsed if isinstance(parsed, dict) else {}
		items = parsed.get('items') if isinstance(parsed, dict) else parsed
		if not isinstance(items, list) or not items or any((not isinstance(it, dict) for it in items)):
			raise ValueError('Batch spec file must contain a non-empty JSON list of item objects')
		defaults = {'consume_input': bool(getattr(self.__args, 'consume_input', False)), 'conversation': getattr(self.__args, 'conversation', None) or top.get('conversation'), 'no_metadata': bool(getattr(self.__args, 'no_metadata', False) or top.get('no_metadata', False)), 'parent': getattr(self.__args, 'parent', None) or top.get('parent'), 'project_root': getattr(self.__args, 'project_root', None) or top.get('project_root'), 'reason': getattr(self.__args, 'reason', 'completed') or top.get('reason') or 'completed', 'repo': getattr(self.__args, 'repo', None) or top.get('repo'), 'repo_root': getattr(self.__args, 'repo_root', None) or top.get('repo_root'), 'target_locale': getattr(self.__args, 'target_locale', 'en-US') or top.get('target_locale') or 'en-US'}
		return (spec_path, spec_raw, items, defaults)
	# @used-by :meth:`BatchRunner.__build_close_args()`
	# @used-by :meth:`BatchRunner.__build_create_args()`
	@classmethod
	def __materialize_text(cls, item: dict[str, Any], file_key: str, text_key: str, spec_dir: Path, tmp_files: list[Path], idx: int) -> str | None:
		existing = cls.__resolve_path(item.get(file_key), spec_dir)
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
	# @used-by :meth:`BatchRunner.__build_create_args()`
	@staticmethod
	def __norm_str_list(raw: Any) -> list[str] | None:
		if isinstance(raw, str):
			r: list[str] | None = [raw]
		elif isinstance(raw, list):
			r = [str(v) for v in raw if None is not v]
		else:
			r = None
		return r
	# @used-by :meth:`BatchRunner.__build_create_args()`
	# @used-by :meth:`BatchRunner.__materialize_text()`
	@staticmethod
	def __resolve_path(raw: Any, spec_dir: Path) -> str | None:
		r: str | None = None
		if isinstance(raw, str) and raw.strip():
			p = Path(raw.strip())
			r = str(p if p.is_absolute() else (spec_dir / p).resolve())
		return r
	# @used-by :meth:`BatchRunner.run()`
	@staticmethod
	def __run_single(item: dict[str, Any], defaults: dict[str, Any], spec_dir: Path, tmp_files: list[Path], idx: int, item_action: str, build_fn, exec_fn) -> dict[str, Any]:
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
	# @used-by :func:`agent_tools.github_issue.build_parser()`
	# @used-by :func:`agent_tools.issues.batch_commands.register_issue_subparsers()`
	@classmethod
	def register_subparsers(cls, sub, sub_defs, common_tail_specs, service_fn) -> None:
		batch_defs = (
			('batch-create', 'Create multiple GitHub issues from a UTF-8 JSON spec file with verified read-back.', lambda a: cls(service_fn(a), a, 'create').run(), (_BATCH_REPO_SPEC, _BATCH_SPEC_ARG, (('--parent', '-p'), {'help': 'Default parent problem issue number or URL for batch items.'}), ('--no-metadata', {'action': 'store_true', 'help': 'Skip automatic prepending of the Harness JSON metadata header.'}), *common_tail_specs)),
			('batch-close', 'Close multiple GitHub issues from a UTF-8 JSON spec file with pre-flight grounding and read-back.', lambda a: cls(service_fn(a), a, 'close').run(), (_BATCH_REPO_SPEC, _BATCH_SPEC_ARG, (('--reason', '-r'), {'choices': ['completed', 'not_planned'], 'default': 'completed', 'help': 'Default closure reason.'}), *common_tail_specs)),
		)
		for name, help_text, fn, specs in (*sub_defs, *batch_defs):
			p = sub.add_parser(name, help=help_text)
			add_arg_specs(p, specs)
			p.set_defaults(func=fn)
	# @used-by :func:`agent_tools.issues.batch_commands.run_batch_close()`
	# @used-by :func:`agent_tools.issues.batch_commands.run_batch_create()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	def run(self) -> int:
		spec_path, spec_raw, items, defaults = self.__load_spec()
		is_close = 'close' == self.__mode
		batch_action, item_action = (('batch-close', 'close') if is_close else ('batch-create', 'create'))
		build_fn = self.__build_close_args if is_close else self.__build_create_args
		exec_fn = self.__service.cmd_close if is_close else self.__service.cmd_create
		results, tmp_files = ([], [])
		try:
			for idx, item in enumerate(items):
				results.append(self.__run_single(item, defaults, spec_path.parent, tmp_files, idx, item_action, build_fn, exec_fn))
		finally:
			self.__cleanup_tmp(tmp_files)
		succeeded = sum((1 for it in results if it.get('ok')))
		all_ok = len(results) == succeeded
		removed = consume_unchanged_files([(spec_path, spec_raw)]) if all_ok and defaults['consume_input'] else []
		dump_json({'action': batch_action, 'consumed_files': removed, 'failed': len(results) - succeeded, 'ok': all_ok, 'repo': defaults['repo'], 'results': results, 'succeeded': succeeded, 'total': len(results)})
		return 0 if all_ok else 2
