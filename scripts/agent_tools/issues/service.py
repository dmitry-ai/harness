# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
from ..cli_common import consume_unchanged_files, dump_json
from ..git_gate import is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
from .linter import IssueMarkdownLinter
from .repo_commands import run_audit_repo, run_transfer_repo
from .service_helpers import build_create_payload, dirty_issue_first_files, gh_api_call, pending_similar_peer_slugs, resolve_metadata_project_root, resolve_title
from .workspace import IssueEvidenceWorkspace
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
class GitHubIssueService:
	# 2026-11-24
	# "Isolate per-conversation github_issues recording and turn-state filtering":
	# https://github.com/dmitry-ai/harness/issues/195
	def __init__(self, *, api_fn=None, linter: IssueMarkdownLinter | None=None, workspace: IssueEvidenceWorkspace | None=None, conversation_id: str | None=None) -> None:
		self._api = api_fn if None is not api_fn else gh_api_call
		self.linter = linter if None is not linter else IssueMarkdownLinter()
		self.workspace = workspace if None is not workspace else IssueEvidenceWorkspace()
		self._conversation_id = conversation_id
	def _build_mutation_success_payload(self, action: str, repo: str, id_key: str, ident: Any, kind: str, fetched: dict[str, Any], remote_body: str, removed: list[str], parent_number: int | None, extra_out: Any) -> dict[str, Any]:
		out: dict[str, Any] = {'ok': True, 'action': action, 'repo': repo, id_key: ident, 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(remote_body), 'consumed_files': removed}
		if 'issue' == kind:
			if fetched.get('state'):
				out['state'] = fetched.get('state')
			eff_parent = parent_number if None is not parent_number else self.linter.extract_parent_number(remote_body, repo)
			if None is not eff_parent and eff_parent != ident:
				out.update(parent_number=int(eff_parent), parent_url=f'https://github.com/{repo}/issues/{int(eff_parent)}')
		if isinstance(extra_out, dict):
			out.update(extra_out)
		return out
	def _check_close_commit_readiness(self, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> tuple[Path | None, str | None]:
		code_repo = self.workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable, repo_root=getattr(args, 'repo_root', None))
		commit_err: str | None = None
		if None is not code_repo and is_issue_tracked_code_repo(code_repo):
			try:
				verify_repo_issue_ready_for_close(code_repo, repo, number, project_root=project_root)
			except (ValueError, RuntimeError) as exc:
				commit_err = str(exc)
		return (code_repo, commit_err)
	def _edit_parent_only(self, repo: str, number: int, parent_num: int, target_locale: str, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int:
		fetched = self._api(f'repos/{repo}/issues/{number}', method='GET')
		remote_title, remote_body = (fetched.get('title') or '', fetched.get('body') or '')
		t_errs = self.linter.lint(remote_title, is_title=True, target_locale=target_locale)
		b_errs = self.linter.lint(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
		if t_errs or b_errs:
			dump_json({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'title_errors': t_errs, 'body_errors': b_errs})
			r = 2
		else:
			self.verify_and_persist_parent_issue(consumable, repo, parent_num, self_number=number, project_root=project_root)
			linked = self.try_link_sub_issue(repo, parent_num, fetched.get('id'))
			# 2026-11-24
			# "Isolate per-conversation github_issues recording and turn-state filtering":
			# https://github.com/dmitry-ai/harness/issues/195
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='issue', action='edit', project_root=project_root, parent_number=parent_num, conversation_id=self._conversation_id)
			dump_json({'ok': True, 'action': 'edit', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'verified': True, 'parent_number': int(parent_num), 'parent_url': f'https://github.com/{repo}/issues/{int(parent_num)}', 'sub_issue_linked': linked, 'body_chars': len(remote_body), 'consumed_files': []})
			r = 0
		return r
	def _execute_create(self, args: argparse.Namespace, repo: str, title: str, body: str, eff_parent: int | None, consumable: list[tuple[Path, bytes]], target_locale: str, project_root: str | Path | None) -> int:
		payload = build_create_payload(args, title, body)
		state: dict[str, Any] = {'body': body, 'prepended': False}
		no_meta = bool(getattr(args, 'no_metadata', False))
		def _write_issue() -> int:
			if None is not eff_parent:
				self.verify_and_persist_parent_issue(consumable, repo, eff_parent, project_root=project_root, require_open=True)
			created = self._api(f'repos/{repo}/issues', method='POST', payload=payload)
			num = created['number']
			if not no_meta:
				self._prepend_issue_metadata(repo, num, created, body, project_root, consumable, state)
			return num
		def _after_create(_ident: int, fetched: dict[str, Any]) -> dict[str, Any] | None:
			extra: dict[str, Any] = {}
			if state['prepended']:
				extra['metadata_prepended'] = True
			if None is not eff_parent:
				extra['sub_issue_linked'] = self.try_link_sub_issue(repo, eff_parent, fetched.get('id'))
			return extra or None
		return self.run_verified_mutation(action='create', repo=repo, consumable=consumable, target_locale=target_locale, container_text=None, expected_title=title, expected_body=body, expected_body_fn=lambda _i: state['body'], write_fn=_write_issue, read_fn=lambda num: self._api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, post_write_fn=_after_create)
	def _execute_edit(self, args: argparse.Namespace, repo: str, number: int, title: str | None, body: str | None, parent_num: int | None, active_parent: int | None, eff_parent: int | None, consumable: list[tuple[Path, bytes]], target_locale: str, project_root: str | Path | None) -> int:
		if None is not parent_num and None is body:
			remote_body = self._api(f'repos/{repo}/issues/{number}', method='GET').get('body') or ''
			b_errs = self.linter.lint(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
			if b_errs:
				dump_json({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'body_errors': b_errs})
				return 2
		container_text = self.workspace.load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
		payload = {k: v for k, v in (('title', title), ('body', body), ('state', args.state)) if None is not v}
		def _write_edit() -> int:
			if None is not active_parent:
				self.verify_and_persist_parent_issue(consumable, repo, active_parent, self_number=number, project_root=project_root)
			self._api(f'repos/{repo}/issues/{number}', method='PATCH', payload=payload)
			return number
		after = (lambda _i, fetched: {'sub_issue_linked': self.try_link_sub_issue(repo, active_parent, fetched.get('id'))}) if None is not active_parent else None
		return self.run_verified_mutation(action='edit', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=title, expected_body=body, write_fn=_write_edit, read_fn=lambda num: self._api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, self_number=number, post_write_fn=after)
	def _finalize_close(self, args: argparse.Namespace, repo: str, number: int, comment_id: int | None, code_repo: Path | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int:
		self._api(f'repos/{repo}/issues/{number}', method='PATCH', payload={'state': 'closed', 'state_reason': args.reason})
		fetched = self._api(f'repos/{repo}/issues/{number}', method='GET')
		if 'closed' != fetched.get('state'):
			dump_json({'ok': False, 'action': 'close', 'stage': 'post_flight_state_check', 'repo': repo, 'number': number, 'state': fetched.get('state')})
			r = 2
		else:
			# 2026-11-24
			# "Isolate per-conversation github_issues recording and turn-state filtering":
			# https://github.com/dmitry-ai/harness/issues/195
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='issue', action='close', project_root=project_root, conversation_id=getattr(args, 'conversation', None) or self._conversation_id)
			removed = consume_unchanged_files(consumable) if args.consume_input else []
			close_repo = code_repo if 'completed' == getattr(args, 'reason', 'completed') else self.workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable)
			pending = pending_similar_peer_slugs(self.workspace, close_repo, repo=repo, project_root=project_root, source_files=consumable)
			out: dict[str, Any] = {'ok': True, 'action': 'close', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'verified': True, 'consumed_files': removed}
			if pending:
				out['similar_projects_pending'] = pending
			dump_json(out)
			r = 0
		return r
	def _load_cached_parent_issue(self, source_files: list[tuple[Path, bytes]], repo: str, pnum: int, project_root: str | Path | None) -> dict[str, Any] | None:
		r, safe_repo = (None, repo.replace('/', '__'))
		for gh_root, _ in self.workspace.resolve_issue_targets(source_files, repo, project_root=project_root):
			cand = gh_root / safe_repo / f'issue-{pnum}.json'
			if cand.is_file():
				try:
					loaded = json.loads(cand.read_text(encoding='utf-8'))
					if isinstance(loaded, dict) and (loaded.get('html_url') or loaded.get('url')):
						r = loaded.get('issue') if isinstance(loaded.get('issue'), dict) else loaded
						break
				except (OSError, ValueError):
					continue
		return r
	def _mutation_readback_check(self, remote_title: str, remote_body: str, expected_title: str | None, eff_expected_body: str | None, target_locale: str, container_text: str | None, eff_struct: bool, parent_number: int | None, repo: str, eff_self: int | None) -> tuple[bool, list, list]:
		pt_errs = self.linter.lint(remote_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct) if None is not expected_title else []
		pb_errs = self.linter.lint(remote_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct, parent_number=parent_number, repo=repo, self_number=eff_self) if None is not eff_expected_body else []
		exact = (None is expected_title or self.linter.normalize_newlines(remote_title) == self.linter.normalize_newlines(expected_title)) and (None is eff_expected_body or self.linter.normalize_newlines(remote_body) == self.linter.normalize_newlines(eff_expected_body))
		return (exact, pt_errs, pb_errs)
	def _parse_edit_inputs(self, args: argparse.Namespace, repo: str, number: int, parent_num: int | None, consumable: list[tuple[Path, bytes]]) -> tuple[str | None, str | None]:
		if None is not parent_num and int(parent_num) == int(number):
			raise ValueError(f'Issue #{number} cannot reference itself as --parent')
		title, body = (resolve_title(args, consumable), None)
		if args.body_file:
			b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
			consumable.append((b_path, b_raw))
		if None is title and None is body and (None is args.state) and (None is parent_num):
			raise ValueError('At least one of --title/--title-file, --body-file, --state, or --parent must be provided')
		return (title, body)
	def _post_close_comment(self, repo: str, number: int, comment_body: str, target_locale: str, container_text: str | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> tuple[bool, int | None]:
		created = self._api(f'repos/{repo}/issues/{number}/comments', method='POST', payload={'body': comment_body})
		comment_id = created['id']
		fetched = self._api(f'repos/{repo}/issues/comments/{comment_id}', method='GET')
		remote_c = fetched.get('body') or ''
		ok = self.linter.normalize_newlines(remote_c) == self.linter.normalize_newlines(comment_body) and (not self.linter.lint(remote_c, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False))
		if ok:
			# 2026-11-24
			# "Isolate per-conversation github_issues recording and turn-state filtering":
			# https://github.com/dmitry-ai/harness/issues/195
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='comment', action='comment', project_root=project_root, conversation_id=self._conversation_id)
		else:
			dump_json({'ok': False, 'action': 'close', 'stage': 'post_flight_comment_readback', 'repo': repo, 'number': number, 'comment_id': comment_id})
		return (ok, comment_id)
	def _prepend_issue_metadata(self, repo: str, num: int, created: dict[str, Any], body: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]], state: dict[str, Any]) -> None:
		from ..metadata import build_github_issue_metadata, extract_leading_metadata_header, prepend_metadata_header
		existing_meta, _ = extract_leading_metadata_header(body)
		if None is existing_meta:
			issue_url = str(created.get('html_url') or f'https://github.com/{repo}/issues/{num}')
			meta_obj = build_github_issue_metadata(issue_url=issue_url, project_root=resolve_metadata_project_root(self.workspace, repo, project_root, consumable))
			prefixed = prepend_metadata_header(body, meta_obj)
			self._api(f'repos/{repo}/issues/{num}', method='PATCH', payload={'body': prefixed})
			state['body'], state['prepended'] = (prefixed, True)
	def _verify_close_prereqs(self, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, project_root: str | Path | None) -> tuple[str | None, Path | None, int | None]:
		comment_body, c_errors = (None, [])
		if args.comment_file:
			c_path, c_raw, comment_body = self.linter.read_utf8_no_bom_file(args.comment_file)
			consumable.append((c_path, c_raw))
			c_errors = self.linter.lint(comment_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False)
		code_repo, commit_err = self._check_close_commit_readiness(args, repo, number, consumable, project_root) if (not c_errors) and 'completed' == getattr(args, 'reason', 'completed') else (None, None)
		if c_errors:
			dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_comment_lint', 'repo': repo, 'number': number, 'comment_errors': c_errors})
			err_rc: int | None = 2
		elif commit_err:
			dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_commit_check', 'repo': repo, 'number': number, 'error': commit_err})
			err_rc = 2
		else:
			err_rc = None
		return (comment_body, code_repo, err_rc)
	def _verify_mutation_readback(self, action: str, repo: str, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, expected_title: str | None, eff_expected_body: str | None, kind: str, id_key: str, ident: Any, fetched: dict[str, Any], consume_input: bool, project_root: str | Path | None, parent_number: int | None, self_number: int | None, eff_struct: bool, post_write_fn) -> int:
		remote_title, remote_body = (fetched.get('title') or '', fetched.get('body') or '')
		eff_self = self_number if None is not self_number else ident if 'issue' == kind and isinstance(ident, int) else None
		exact, pt_errs, pb_errs = self._mutation_readback_check(remote_title, remote_body, expected_title, eff_expected_body, target_locale, container_text, eff_struct, parent_number, repo, eff_self)
		if exact and (not pt_errs) and (not pb_errs):
			extra = post_write_fn(ident, fetched) if None is not post_write_fn else None
			# 2026-11-24
			# "Isolate per-conversation github_issues recording and turn-state filtering":
			# https://github.com/dmitry-ai/harness/issues/195
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind=kind, action=action, project_root=project_root, parent_number=parent_number, conversation_id=self._conversation_id)
			removed = consume_unchanged_files(consumable) if consume_input else []
			dump_json(self._build_mutation_success_payload(action, repo, id_key, ident, kind, fetched, remote_body, removed, parent_number, extra))
			r = 0
		else:
			post_out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'post_flight_readback', 'repo': repo, id_key: ident, 'html_url': fetched.get('html_url'), 'exact_match': exact, 'body_errors': pb_errs, **({'title_errors': pt_errs} if 'comment' != kind else {})}
			dump_json(post_out)
			r = 2
		return r
	def cmd_audit_repo(self, args: argparse.Namespace) -> int:
		return run_audit_repo(self._api, self.linter, args)
	def cmd_close(self, args: argparse.Namespace) -> int:
		repo, number, consumable = (self.linter.validate_repo(args.repo), args.issue, [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		container_text = self.workspace.load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
		comment_body, code_repo, err_rc = self._verify_close_prereqs(args, repo, number, consumable, target_locale, container_text, project_root)
		if None is not err_rc:
			r = err_rc
		else:
			comment_ok, comment_id = self._post_close_comment(repo, number, comment_body, target_locale, container_text, consumable, project_root) if None is not comment_body else (True, None)
			r = 2 if not comment_ok else self._finalize_close(args, repo, number, comment_id, code_repo, consumable, project_root)
		return r
	def cmd_comment(self, args: argparse.Namespace) -> int:
		repo = self.linter.validate_repo(args.repo)
		b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
		consumable = [(b_path, b_raw)]
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		container_text = self.workspace.load_saved_issue_container_text(consumable, repo, getattr(args, 'issue', None), project_root=project_root)
		existing_cids = self.workspace.find_existing_issue_comments(consumable, repo, args.issue, project_root=project_root) if None is args.comment_id and None is not args.issue and (not getattr(args, 'allow_additional_comment', False)) else []
		if existing_cids:
			dump_json({'ok': False, 'action': 'comment', 'stage': 'idempotent_comment_gate', 'repo': repo, 'issue': args.issue, 'existing_comment_ids': existing_cids, 'error': f'EXEC-5 / SCOPE-2: Issue #{args.issue} already has tracked comment(s) {existing_cids} in KB/Evidence/GitHub; use --comment-id {existing_cids[-1]} to update the existing comment in place instead of posting a duplicate comment (or pass --allow-additional-comment if explicitly instructed)'})
			r = 2
		else:
			def _write_comment() -> int:
				if None is not args.comment_id:
					res = self._api(f'repos/{repo}/issues/comments/{args.comment_id}', method='PATCH', payload={'body': body})
				elif None is args.issue:
					raise ValueError('Either --issue <number> or --comment-id <id> is required')
				else:
					res = self._api(f'repos/{repo}/issues/{args.issue}/comments', method='POST', payload={'body': body})
				return res['id']
			r = self.run_verified_mutation(action='comment', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=None, expected_body=body, write_fn=_write_comment, read_fn=lambda cid: self._api(f'repos/{repo}/issues/comments/{cid}', method='GET'), kind='comment', id_key='comment_id', consume_input=args.consume_input, project_root=project_root)
		return r
	def cmd_create(self, args: argparse.Namespace) -> int:
		repo, consumable = (self.linter.validate_repo(args.repo), [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		parent_num = self.linter.parse_parent_arg(getattr(args, 'parent', None), repo)
		title = resolve_title(args, consumable)
		if not title:
			raise ValueError('Issue title is required (--title or --title-file)')
		b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
		consumable.append((b_path, b_raw))
		eff_parent = parent_num if None is not parent_num else self.linter.extract_parent_number(body, repo)
		dirty = dirty_issue_first_files(self.workspace, repo, project_root=project_root, source_files=consumable, repo_root=getattr(args, 'repo_root', None)) if None is eff_parent else []
		if dirty:
			dump_json({'ok': False, 'action': 'create', 'stage': 'pre_flight_issue_first', 'repo': repo, 'dirty_files': dirty, 'error': f'EXEC-5 ISSUE-FIRST-GATE: Refusing to create a parent problem issue in {repo} after local code/test files were already modified ({", ".join(dirty[:5])}). State the problem as a parent GitHub issue BEFORE writing tests or code (or create a child subtask linked to an existing open parent with --parent <N>).'})
			r = 2
		else:
			r = self._execute_create(args, repo, title, body, eff_parent, consumable, target_locale, project_root)
		return r
	def cmd_edit(self, args: argparse.Namespace) -> int:
		repo, number, consumable = (self.linter.validate_repo(args.repo), args.issue, [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		parent_num = self.linter.parse_parent_arg(getattr(args, 'parent', None), repo)
		title, body = self._parse_edit_inputs(args, repo, number, parent_num, consumable)
		body_parent = self.linter.extract_parent_number(body, repo) if None is not body else None
		if None is not body_parent and int(body_parent) == int(number):
			raise ValueError(f'Issue #{number} cannot reference itself as --parent')
		active_parent = parent_num if None is not parent_num else body_parent
		eff_parent = active_parent if None is not active_parent else self.workspace.saved_issue_parent_number(consumable, repo, number, project_root=project_root)
		if None is title and None is body and (None is args.state) and (None is not parent_num):
			r = self._edit_parent_only(repo, number, parent_num, target_locale, consumable, project_root)
		else:
			r = self._execute_edit(args, repo, number, title, body, parent_num, active_parent, eff_parent, consumable, target_locale, project_root)
		return r
	def cmd_fetch(self, args: argparse.Namespace) -> int:
		from .repo_commands import run_fetch
		return run_fetch(self, args)
	def cmd_lint(self, args: argparse.Namespace) -> int:
		from .repo_commands import run_lint
		return run_lint(self.linter, args)
	def cmd_transfer_repo(self, args: argparse.Namespace) -> int:
		return run_transfer_repo(self._api, self.linter, self.workspace, args)
	def run_verified_mutation(self, *, action: str, repo: str, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, expected_title: str | None, expected_body: str | None, write_fn, read_fn, kind: str, id_key: str, consume_input: bool, project_root: str | Path | None, parent_number: int | None=None, self_number: int | None=None, check_structure_policy: bool=True, post_write_fn=None, expected_body_fn=None) -> int:
		eff_struct = check_structure_policy and ('comment' != kind)
		t_errs = self.linter.lint(expected_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct) if None is not expected_title else []
		b_errs = self.linter.lint(expected_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct, parent_number=parent_number, repo=repo, self_number=self_number) if None is not expected_body else []
		if t_errs or b_errs:
			dump_json({'ok': False, 'action': action, 'stage': 'pre_flight_lint', 'repo': repo, 'body_errors': b_errs, **({'title_errors': t_errs} if 'comment' != kind else {})})
			r = 2
		else:
			ident = write_fn()
			r = self._verify_mutation_readback(action, repo, consumable, target_locale, container_text, expected_title, expected_body_fn(ident) if None is not expected_body_fn else expected_body, kind, id_key, ident, read_fn(ident), consume_input, project_root, parent_number, self_number, eff_struct, post_write_fn)
		return r
	def try_link_sub_issue(self, repo: str, parent_number: int, child_id: Any) -> bool:
		r = False
		if isinstance(child_id, int) and (not isinstance(child_id, bool)) and 0 < child_id:
			try:
				self._api(f'repos/{repo}/issues/{int(parent_number)}/sub_issues', method='POST', payload={'sub_issue_id': int(child_id)})
				r = True
			except RuntimeError:
				r = False
		return r
	def verify_and_persist_parent_issue(self, source_files: list[tuple[Path, bytes]], repo: str, parent_number: int, *, self_number: int | None=None, project_root: str | Path | None=None, require_open: bool=False) -> dict[str, Any]:
		pnum = int(parent_number)
		if None is not self_number and pnum == int(self_number):
			raise ValueError(f'Issue #{self_number} cannot reference itself as --parent')
		existing = self._load_cached_parent_issue(source_files, repo, pnum, project_root)
		if None is existing:
			fetched = self._api(f'repos/{repo}/issues/{pnum}', method='GET')
			if not isinstance(fetched, dict) or 'pull_request' in fetched:
				raise ValueError(f'Parent target #{pnum} in {repo} is not a valid GitHub issue')
			# 2026-11-24
			# "Isolate per-conversation github_issues recording and turn-state filtering":
			# https://github.com/dmitry-ai/harness/issues/195
			self.workspace.persist_issue_evidence(source_files, repo, fetched, kind='issue', action=None, project_root=project_root, conversation_id=self._conversation_id)
			existing = fetched
		if require_open and 'closed' == str((existing or {}).get('state') or '').strip().lower():
			raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Parent issue #{pnum} in {repo} is closed; open a new parent problem issue before creating new subtasks')
		return existing
