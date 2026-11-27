# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.array.clean.main import df_clean_null
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Issue.AcceptanceGate import AcceptanceGate
from Df.Harness.Issue.CloseCommentValidator import CloseCommentValidator
from Df.Harness.Issue.CommentGrounder import CommentGrounder
from Df.Harness.Issue.DirtyIssueFirstScanner import DirtyIssueFirstScanner
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.IssueFetcher import IssueFetcher
from Df.Harness.Issue.IssueLintRunner import IssueLintRunner
from Df.Harness.Issue.IssueMetadataPrepender import IssueMetadataPrepender
from Df.Harness.Issue.Linter import Linter
from Df.Harness.Issue.PendingPeerFinder import PendingPeerFinder
from Df.Harness.Issue.RepoAuditor import RepoAuditor
from Df.Harness.Issue.RepoTransferRunner import RepoTransferRunner
from Df.Harness.lib.issue import dfh_build_create_payload, dfh_gh_api_call, dfh_resolve_title
from agent_tools.cli_common import consume_unchanged_files, dump_json
import argparse
import json
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Service:
	__dump_fn = None
	__verify_fn = None
	# @used-by :func:`agent_tools.github_issue._service()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def __init__(self, *, api_fn=None, linter: Linter | None=None, workspace: EvidenceWorkspace | None=None, conversation_id: str | None=None) -> None:
		self.__api = api_fn if None is not api_fn else dfh_gh_api_call
		self.linter = linter if None is not linter else Linter()
		self.workspace = workspace if None is not workspace else EvidenceWorkspace()
		self.__conversation_id = conversation_id
	# @used-by :meth:`Service.__execute_create()`
	def __after_create(self, repo: str, eff_parent: int | None, state: dict[str, Any], fetched: dict[str, Any]) -> dict[str, Any] | None:
		extra: dict[str, Any] = {}
		if state['prepended']:
			extra['metadata_prepended'] = True
		if None is not eff_parent:
			extra['sub_issue_linked'] = self.try_link_sub_issue(repo, eff_parent, fetched.get('id'))
		return extra or None
	# @used-by :meth:`Service.__verify_mutation_readback()`
	def __build_mutation_success_payload(self, action: str, repo: str, id_key: str, ident: Any, kind: str, fetched: dict[str, Any], remote_body: str, removed: list[str], parent_number: int | None, extra_out: Any) -> dict[str, Any]:
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
	# @used-by :meth:`Service.__verify_close_prereqs()`
	def __check_close_commit_readiness(self, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> tuple[Path | None, str | None, str]:
		verify_fn = type(self).__verify_fn
		return AcceptanceGate(None, repo, number, project_root=project_root).check_readiness(self.workspace, args, consumable, verify_fn=verify_fn, is_tracked_fn=lambda p: RepoGate(p).is_issue_tracked())
	# @used-by :meth:`Service.__edit_parent_only()`
	# @used-by :meth:`Service.__execute_edit()`
	# @used-by :meth:`Service.__finalize_close()`
	# @used-by :meth:`Service.__post_close_comment()`
	# @used-by :meth:`Service.__verify_close_prereqs()`
	# @used-by :meth:`Service.__verify_mutation_readback()`
	# @used-by :meth:`Service.cmd_create()`
	# @used-by :meth:`Service.run_verified_mutation()`
	def __dump(self, data: dict[str, Any]) -> None:
		fn = type(self).__dump_fn
		fn(data) if None is not fn else dump_json(data)
	# @used-by :meth:`Service.cmd_edit()`
	def __edit_parent_only(self, repo: str, number: int, parent_num: int, target_locale: str, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int:
		fetched = self.__api(f'repos/{repo}/issues/{number}', method='GET')
		remote_title, remote_body = (fetched.get('title') or '', fetched.get('body') or '')
		t_errs = self.linter.lint(remote_title, is_title=True, target_locale=target_locale)
		b_errs = self.linter.lint(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
		if t_errs or b_errs:
			self.__dump({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'title_errors': t_errs, 'body_errors': b_errs})
			r = 2
		else:
			self.verify_and_persist_parent_issue(consumable, repo, parent_num, self_number=number, project_root=project_root)
			linked = self.try_link_sub_issue(repo, parent_num, fetched.get('id'))
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='issue', action='edit', project_root=project_root, parent_number=parent_num, conversation_id=self.__conversation_id)
			self.__dump({'ok': True, 'action': 'edit', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'verified': True, 'parent_number': int(parent_num), 'parent_url': f'https://github.com/{repo}/issues/{int(parent_num)}', 'sub_issue_linked': linked, 'body_chars': len(remote_body), 'consumed_files': []})
			r = 0
		return r
	# @used-by :meth:`Service.cmd_create()`
	def __execute_create(self, args: argparse.Namespace, repo: str, title: str, body: str, eff_parent: int | None, consumable: list[tuple[Path, bytes]], target_locale: str, project_root: str | Path | None) -> int:
		payload = dfh_build_create_payload(args, title, body)
		state: dict[str, Any] = {'body': body, 'prepended': False}
		no_meta = bool(getattr(args, 'no_metadata', False))
		return self.run_verified_mutation(action='create', repo=repo, consumable=consumable, target_locale=target_locale, container_text=None, expected_title=title, expected_body=body, expected_body_fn=lambda _i: state['body'], write_fn=lambda: self.__write_created_issue(repo, payload, body, eff_parent, no_meta, consumable, project_root, state), read_fn=lambda num: self.__api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, post_write_fn=lambda _i, fetched: self.__after_create(repo, eff_parent, state, fetched))
	# @used-by :meth:`Service.cmd_edit()`
	def __execute_edit(self, args: argparse.Namespace, repo: str, number: int, title: str | None, body: str | None, parent_num: int | None, active_parent: int | None, eff_parent: int | None, consumable: list[tuple[Path, bytes]], target_locale: str, project_root: str | Path | None) -> int:
		b_errs = self.__lint_remote_body_for_parent(repo, number, parent_num, target_locale) if None is not parent_num and None is body else []
		if b_errs:
			self.__dump({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'body_errors': b_errs})
			r = 2
		else:
			container_text = self.workspace.load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
			payload = df_clean_null(dict((('title', title), ('body', body), ('state', args.state))))
			after = (lambda _i, fetched: {'sub_issue_linked': self.try_link_sub_issue(repo, active_parent, fetched.get('id'))}) if None is not active_parent else None
			r = self.run_verified_mutation(action='edit', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=title, expected_body=body, write_fn=lambda: self.__write_edited_issue(repo, number, active_parent, payload, consumable, project_root), read_fn=lambda num: self.__api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, self_number=number, post_write_fn=after)
		return r
	# @used-by :meth:`Service.cmd_close()`
	def __finalize_close(self, args: argparse.Namespace, repo: str, number: int, comment_id: int | None, code_repo: Path | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int:
		self.__api(f'repos/{repo}/issues/{number}', method='PATCH', payload={'state': 'closed', 'state_reason': args.reason})
		fetched = self.__api(f'repos/{repo}/issues/{number}', method='GET')
		if 'closed' != fetched.get('state'):
			self.__dump({'ok': False, 'action': 'close', 'stage': 'post_flight_state_check', 'repo': repo, 'number': number, 'state': fetched.get('state')})
			r = 2
		else:
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='issue', action='close', project_root=project_root, conversation_id=getattr(args, 'conversation', None) or self.__conversation_id)
			removed = consume_unchanged_files(consumable) if args.consume_input else []
			close_repo = code_repo if 'completed' == getattr(args, 'reason', 'completed') else self.workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable)
			pending = PendingPeerFinder(self.workspace, close_repo, repo=repo, project_root=project_root, source_files=consumable).find()
			out: dict[str, Any] = {'ok': True, 'action': 'close', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'verified': True, 'consumed_files': removed}
			if pending:
				out['similar_projects_pending'] = pending
			self.__dump(out)
			r = 0
		return r
	# @used-by :meth:`Service.__execute_edit()`
	def __lint_remote_body_for_parent(self, repo: str, number: int, parent_num: int, target_locale: str) -> list[dict[str, Any]]:
		remote_body = self.__api(f'repos/{repo}/issues/{number}', method='GET').get('body') or ''
		return self.linter.lint(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
	# @used-by :meth:`Service.verify_and_persist_parent_issue()`
	def __load_cached_parent_issue(self, source_files: list[tuple[Path, bytes]], repo: str, pnum: int, project_root: str | Path | None) -> dict[str, Any] | None:
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
	# @used-by :meth:`Service.__verify_mutation_readback()`
	def __mutation_readback_check(self, remote_title: str, remote_body: str, expected_title: str | None, eff_expected_body: str | None, target_locale: str, container_text: str | None, eff_struct: bool, parent_number: int | None, repo: str, eff_self: int | None) -> tuple[bool, list, list]:
		pt_errs = self.linter.lint(remote_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct) if None is not expected_title else []
		pb_errs = self.linter.lint(remote_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct, parent_number=parent_number, repo=repo, self_number=eff_self) if None is not eff_expected_body else []
		exact = (None is expected_title or self.linter.normalize_newlines(remote_title) == self.linter.normalize_newlines(expected_title)) and (None is eff_expected_body or self.linter.normalize_newlines(remote_body) == self.linter.normalize_newlines(eff_expected_body))
		return (exact, pt_errs, pb_errs)
	# @used-by :meth:`Service.cmd_edit()`
	def __parse_edit_inputs(self, args: argparse.Namespace, repo: str, number: int, parent_num: int | None, consumable: list[tuple[Path, bytes]]) -> tuple[str | None, str | None]:
		if None is not parent_num and int(parent_num) == int(number):
			raise ValueError(f'Issue #{number} cannot reference itself as --parent')
		title, body = (dfh_resolve_title(args, consumable), None)
		if args.body_file:
			b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
			consumable.append((b_path, b_raw))
		if None is title and None is body and (None is args.state) and (None is parent_num):
			raise ValueError('At least one of --title/--title-file, --body-file, --state, or --parent must be provided')
		return (title, body)
	# @used-by :meth:`Service.cmd_close()`
	def __post_close_comment(self, repo: str, number: int, comment_body: str, target_locale: str, container_text: str | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> tuple[bool, int | None]:
		created = self.__api(f'repos/{repo}/issues/{number}/comments', method='POST', payload={'body': comment_body})
		comment_id = created['id']
		fetched = self.__api(f'repos/{repo}/issues/comments/{comment_id}', method='GET')
		remote_c = fetched.get('body') or ''
		ok = self.linter.normalize_newlines(remote_c) == self.linter.normalize_newlines(comment_body) and (not self.linter.lint(remote_c, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False))
		if ok:
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind='comment', action='comment', project_root=project_root, conversation_id=self.__conversation_id)
		else:
			self.__dump({'ok': False, 'action': 'close', 'stage': 'post_flight_comment_readback', 'repo': repo, 'number': number, 'comment_id': comment_id})
		return (ok, comment_id)
	# @used-by :meth:`Service.cmd_close()`
	def __verify_close_prereqs(self, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, project_root: str | Path | None) -> tuple[str | None, Path | None, int | None]:
		comment_body, err_rc = CloseCommentValidator(self, args, repo, number, consumable, target_locale, container_text, project_root).validate()
		code_repo, commit_err, err_stage = self.__check_close_commit_readiness(args, repo, number, consumable, project_root) if None is err_rc and 'completed' == getattr(args, 'reason', 'completed') else (None, None, 'pre_flight_commit_check')
		if None is err_rc and commit_err:
			self.__dump({'ok': False, 'action': 'close', 'stage': err_stage, 'repo': repo, 'number': number, 'error': commit_err})
			err_rc = 2
		return (comment_body, code_repo, err_rc)
	# @used-by :meth:`Service.run_verified_mutation()`
	def __verify_mutation_readback(self, action: str, repo: str, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, expected_title: str | None, eff_expected_body: str | None, kind: str, id_key: str, ident: Any, fetched: dict[str, Any], consume_input: bool, project_root: str | Path | None, parent_number: int | None, self_number: int | None, eff_struct: bool, post_write_fn) -> int:
		remote_title, remote_body = (fetched.get('title') or '', fetched.get('body') or '')
		eff_self = self_number if None is not self_number else ident if 'issue' == kind and isinstance(ident, int) else None
		exact, pt_errs, pb_errs = self.__mutation_readback_check(remote_title, remote_body, expected_title, eff_expected_body, target_locale, container_text, eff_struct, parent_number, repo, eff_self)
		if exact and (not pt_errs) and (not pb_errs):
			extra = post_write_fn(ident, fetched) if None is not post_write_fn else None
			self.workspace.persist_issue_evidence(consumable, repo, fetched, kind=kind, action=action, project_root=project_root, parent_number=parent_number, conversation_id=self.__conversation_id)
			removed = consume_unchanged_files(consumable) if consume_input else []
			self.__dump(self.__build_mutation_success_payload(action, repo, id_key, ident, kind, fetched, remote_body, removed, parent_number, extra))
			r = 0
		else:
			post_out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'post_flight_readback', 'repo': repo, id_key: ident, 'html_url': fetched.get('html_url'), 'exact_match': exact, 'body_errors': pb_errs, **({'title_errors': pt_errs} if 'comment' != kind else {})}
			self.__dump(post_out)
			r = 2
		return r
	# @used-by :meth:`Service.cmd_comment()`
	def __write_comment(self, args: argparse.Namespace, repo: str, body: str) -> int:
		if None is not args.comment_id:
			res = self.__api(f'repos/{repo}/issues/comments/{args.comment_id}', method='PATCH', payload={'body': body})
		elif None is args.issue:
			raise ValueError('Either --issue <number> or --comment-id <id> is required')
		else:
			res = self.__api(f'repos/{repo}/issues/{args.issue}/comments', method='POST', payload={'body': body})
		return res['id']
	# @used-by :meth:`Service.__execute_create()`
	def __write_created_issue(self, repo: str, payload: dict[str, Any], body: str, eff_parent: int | None, no_meta: bool, consumable: list[tuple[Path, bytes]], project_root: str | Path | None, state: dict[str, Any]) -> int:
		if None is not eff_parent:
			self.verify_and_persist_parent_issue(consumable, repo, eff_parent, project_root=project_root, require_open=True)
		created = self.__api(f'repos/{repo}/issues', method='POST', payload=payload)
		num = created['number']
		if not no_meta:
			IssueMetadataPrepender(self.workspace, self.__api).prepend(repo, num, created, body, project_root, consumable, state)
		return num
	# @used-by :meth:`Service.__execute_edit()`
	def __write_edited_issue(self, repo: str, number: int, active_parent: int | None, payload: dict[str, Any], consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int:
		if None is not active_parent:
			self.verify_and_persist_parent_issue(consumable, repo, active_parent, self_number=number, project_root=project_root)
		self.__api(f'repos/{repo}/issues/{number}', method='PATCH', payload=payload)
		return number
	# @used-by :mod:`agent_tools.issues.service`
	@classmethod
	def bind_runtime_hooks(cls, *, verify_fn=None, dump_fn=None) -> None:
		cls.__verify_fn = verify_fn
		cls.__dump_fn = dump_fn
	# @used-by :meth:`Df.Harness.Issue.IssueFetcher.IssueFetcher.fetch()`
	def call_api(self, endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False) -> Any:
		return self.__api(endpoint, method=method, payload=payload, paginate=paginate)
	# @used-by :func:`agent_tools.github_issue.cmd_audit_repo()`
	def cmd_audit_repo(self, args: argparse.Namespace) -> int:
		return RepoAuditor(self.__api, self.linter, args).audit()
	# @used-by :func:`agent_tools.github_issue.cmd_close()`
	# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_close_blocks_antigravity_addons_when_companion_unhealthy()`
	# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_service_cmd_close_routes_through_module_gh_api_and_checks_readback()`
	# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_close_blocks_on_unhealthy_repo_health_command()`
	def cmd_close(self, args: argparse.Namespace) -> int:
		repo, number, consumable = (self.linter.validate_repo(args.repo), args.issue, [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		container_text = self.workspace.load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
		comment_body, code_repo, err_rc = self.__verify_close_prereqs(args, repo, number, consumable, target_locale, container_text, project_root)
		if None is not err_rc:
			r = err_rc
		else:
			comment_ok, comment_id = self.__post_close_comment(repo, number, comment_body, target_locale, container_text, consumable, project_root) if None is not comment_body else (True, None)
			r = 2 if not comment_ok else self.__finalize_close(args, repo, number, comment_id, code_repo, consumable, project_root)
		return r
	# @used-by :func:`agent_tools.github_issue.cmd_comment()`
	def cmd_comment(self, args: argparse.Namespace) -> int:
		repo = self.linter.validate_repo(args.repo)
		b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
		consumable = [(b_path, b_raw)]
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		container_text = self.workspace.load_saved_issue_container_text(consumable, repo, getattr(args, 'issue', None), project_root=project_root)
		err_rc = CommentGrounder(self.workspace, repo, consumable, project_root=project_root, repo_root=getattr(args, 'repo_root', None)).check_preflight(args, body)
		if None is not err_rc:
			r = err_rc
		else:
			r = self.run_verified_mutation(action='comment', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=None, expected_body=body, write_fn=lambda: self.__write_comment(args, repo, body), read_fn=lambda cid: self.__api(f'repos/{repo}/issues/comments/{cid}', method='GET'), kind='comment', id_key='comment_id', consume_input=args.consume_input, project_root=project_root)
		return r
	# @used-by :func:`agent_tools.github_issue.cmd_create()`
	def cmd_create(self, args: argparse.Namespace) -> int:
		repo, consumable = (self.linter.validate_repo(args.repo), [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		parent_num = self.linter.parse_parent_arg(getattr(args, 'parent', None), repo)
		title = dfh_resolve_title(args, consumable)
		if not title:
			raise ValueError('Issue title is required (--title or --title-file)')
		b_path, b_raw, body = self.linter.read_utf8_no_bom_file(args.body_file)
		consumable.append((b_path, b_raw))
		eff_parent = parent_num if None is not parent_num else self.linter.extract_parent_number(body, repo)
		dirty = DirtyIssueFirstScanner(self.workspace, repo, project_root=project_root, source_files=consumable, repo_root=getattr(args, 'repo_root', None)).scan() if None is eff_parent else []
		if dirty:
			joined = ', '.join(dirty[:5])
			self.__dump({'ok': False, 'action': 'create', 'stage': 'pre_flight_issue_first', 'repo': repo, 'dirty_files': dirty, 'error': f'EXEC-5 ISSUE-FIRST-GATE: Refusing to create a parent problem issue in {repo} after local code/test files were already modified ({joined}). State the problem as a parent GitHub issue BEFORE writing tests or code (or create a child subtask linked to an existing open parent with --parent <N>).'})
			r = 2
		else:
			r = self.__execute_create(args, repo, title, body, eff_parent, consumable, target_locale, project_root)
		return r
	# @used-by :func:`agent_tools.github_issue.cmd_edit()`
	def cmd_edit(self, args: argparse.Namespace) -> int:
		repo, number, consumable = (self.linter.validate_repo(args.repo), args.issue, [])
		target_locale, project_root = (getattr(args, 'target_locale', 'en-US') or 'en-US', getattr(args, 'project_root', None))
		parent_num = self.linter.parse_parent_arg(getattr(args, 'parent', None), repo)
		title, body = self.__parse_edit_inputs(args, repo, number, parent_num, consumable)
		body_parent = self.linter.extract_parent_number(body, repo) if None is not body else None
		if None is not body_parent and int(body_parent) == int(number):
			raise ValueError(f'Issue #{number} cannot reference itself as --parent')
		active_parent = parent_num if None is not parent_num else body_parent
		eff_parent = active_parent if None is not active_parent else self.workspace.saved_issue_parent_number(consumable, repo, number, project_root=project_root)
		if None is title and None is body and (None is args.state) and (None is not parent_num):
			r = self.__edit_parent_only(repo, number, parent_num, target_locale, consumable, project_root)
		else:
			r = self.__execute_edit(args, repo, number, title, body, parent_num, active_parent, eff_parent, consumable, target_locale, project_root)
		return r
	# @used-by :func:`agent_tools.github_issue.cmd_fetch()`
	def cmd_fetch(self, args: argparse.Namespace) -> int:
		return IssueFetcher(self, args).fetch()
	# @used-by :func:`agent_tools.github_issue.cmd_lint()`
	def cmd_lint(self, args: argparse.Namespace) -> int:
		return IssueLintRunner(self.linter, args).run()
	# @used-by :func:`agent_tools.github_issue.cmd_transfer_repo()`
	def cmd_transfer_repo(self, args: argparse.Namespace) -> int:
		return RepoTransferRunner(self.__api, self.linter, self.workspace, args).transfer()
	# @used-by :meth:`Service.__execute_create()`
	# @used-by :meth:`Service.__execute_edit()`
	# @used-by :meth:`Service.cmd_comment()`
	def run_verified_mutation(self, *, action: str, repo: str, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, expected_title: str | None, expected_body: str | None, write_fn, read_fn, kind: str, id_key: str, consume_input: bool, project_root: str | Path | None, parent_number: int | None=None, self_number: int | None=None, check_structure_policy: bool=True, post_write_fn=None, expected_body_fn=None) -> int:
		eff_struct = check_structure_policy and ('comment' != kind)
		t_errs = self.linter.lint(expected_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct) if None is not expected_title else []
		b_errs = self.linter.lint(expected_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_struct, parent_number=parent_number, repo=repo, self_number=self_number) if None is not expected_body else []
		if t_errs or b_errs:
			self.__dump({'ok': False, 'action': action, 'stage': 'pre_flight_lint', 'repo': repo, 'body_errors': b_errs, **({'title_errors': t_errs} if 'comment' != kind else {})})
			r = 2
		else:
			ident = write_fn()
			r = self.__verify_mutation_readback(action, repo, consumable, target_locale, container_text, expected_title, expected_body_fn(ident) if None is not expected_body_fn else expected_body, kind, id_key, ident, read_fn(ident), consume_input, project_root, parent_number, self_number, eff_struct, post_write_fn)
		return r
	# @used-by :meth:`Service.__after_create()`
	# @used-by :meth:`Service.__edit_parent_only()`
	# @used-by :meth:`Service.__execute_edit()`
	def try_link_sub_issue(self, repo: str, parent_number: int, child_id: Any) -> bool:
		r = False
		if isinstance(child_id, int) and (not isinstance(child_id, bool)) and 0 < child_id:
			try:
				self.__api(f'repos/{repo}/issues/{int(parent_number)}/sub_issues', method='POST', payload={'sub_issue_id': int(child_id)})
				r = True
			except RuntimeError:
				r = False
		return r
	# @used-by :meth:`Service.__edit_parent_only()`
	# @used-by :meth:`Service.__write_created_issue()`
	# @used-by :meth:`Service.__write_edited_issue()`
	def verify_and_persist_parent_issue(self, source_files: list[tuple[Path, bytes]], repo: str, parent_number: int, *, self_number: int | None=None, project_root: str | Path | None=None, require_open: bool=False) -> dict[str, Any]:
		pnum = int(parent_number)
		if None is not self_number and pnum == int(self_number):
			raise ValueError(f'Issue #{self_number} cannot reference itself as --parent')
		existing = self.__load_cached_parent_issue(source_files, repo, pnum, project_root)
		if None is existing:
			fetched = self.__api(f'repos/{repo}/issues/{pnum}', method='GET')
			if not isinstance(fetched, dict) or 'pull_request' in fetched:
				raise ValueError(f'Parent target #{pnum} in {repo} is not a valid GitHub issue')
			self.workspace.persist_issue_evidence(source_files, repo, fetched, kind='issue', action=None, project_root=project_root, conversation_id=self.__conversation_id)
			existing = fetched
		if require_open and 'closed' == str((existing or {}).get('state') or '').strip().lower():
			raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Parent issue #{pnum} in {repo} is closed; open a new parent problem issue before creating new subtasks')
		return existing
