# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.Linter import Linter
from Df.Harness.Issue.RepoLocator import RepoLocator
from Df.Harness.Issue.SessionDetector import SessionDetector
from Df.Harness.Issue.TurnScopeResolver import TurnScopeResolver
from agent_tools.storage import locked, replace_bytes
import json
import re
_SKIP_TURN_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class EvidenceWorkspace:
	# @used-by :meth:`EvidenceWorkspace.persist_issue_evidence()`
	def __build_issue_record(self, source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], ident: Any, kind: str, project_root: str | Path | None, parent_number: int | None) -> dict[str, Any]:
		m_iss = re.search('/issues/(\\d+)\\b', str(fetched.get('html_url') or fetched.get('issue_url') or ''))
		issue_number = fetched.get('number') or (int(m_iss.group(1)) if m_iss else None)
		record: dict[str, Any] = {'url': fetched.get('html_url'), 'html_url': fetched.get('html_url'), 'repo': repo, 'kind': kind, 'number': fetched.get('number'), 'issue_number': issue_number, 'id': fetched.get('id'), 'title': fetched.get('title') or f'{repo}#{ident}', 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'body': fetched.get('body') or ''}
		for ts_key in ('created_at', 'updated_at'):
			if fetched.get(ts_key):
				record[ts_key] = fetched[ts_key]
		if 'issue' == kind:
			eff_parent = parent_number if None is not parent_number else self.saved_issue_parent_number(source_files, repo, issue_number, project_root=project_root) or Linter.extract_parent_number(record['body'], repo)
			if None is not eff_parent and eff_parent != issue_number:
				record.update(parent_number=int(eff_parent), parent_url=f'https://github.com/{repo}/issues/{int(eff_parent)}')
		return record
	# @used-by :meth:`EvidenceWorkspace.find_tracked_child_issues()`
	@classmethod
	def __collect_child_issue_file(cls, ifile: Path, repo: str, pnum: int, by_num: dict[int, dict[str, Any]]) -> None:
		try:
			data = json.loads(ifile.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			data = None
		iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
		if isinstance(iss_obj, dict):
			num = iss_obj.get('number') or iss_obj.get('issue_number')
			if isinstance(num, int) and (not isinstance(num, bool)) and num != pnum and (num not in by_num) and cls.__parse_parent(iss_obj, repo, num) == pnum:
				url = str(iss_obj.get('html_url') or iss_obj.get('url') or f'https://github.com/{repo}/issues/{num}')
				by_num[num] = {'number': num, 'url': url, 'state': str(iss_obj.get('state') or 'open').strip().lower(), 'state_reason': iss_obj.get('state_reason'), 'parent_number': pnum}
	# @used-by :meth:`EvidenceWorkspace.find_existing_issue_comments()`
	# @used-by :meth:`EvidenceWorkspace.record_issue_in_open_turns()`
	@staticmethod
	def __extract_issue_num(record: dict[str, Any]) -> int | None:
		r = record.get('number') or record.get('issue_number')
		if None is r:
			m = re.search('/issues/(\\d+)\\b', str(record.get('html_url') or record.get('url') or ''))
			r = int(m.group(1)) if m else None
		return r
	# @used-by :meth:`EvidenceWorkspace.__update_turn_entry()`
	@staticmethod
	def __merge_entry_lists(prev: dict[str, Any], record: dict[str, Any], action: str | None) -> tuple[str, list, list]:
		act_name = action or record.get('kind', 'issue')
		comment_ids = list(prev.get('comment_ids') or [])
		if 'comment' == record.get('kind') and None is not record.get('id') and (record.get('id') not in comment_ids):
			comment_ids.append(record.get('id'))
		actions = list(prev.get('actions') or [])
		if act_name and act_name not in actions:
			actions.append(act_name)
		return (act_name, actions, comment_ids)
	# @used-by :meth:`EvidenceWorkspace.__collect_child_issue_file()`
	# @used-by :meth:`EvidenceWorkspace.saved_issue_parent_number()`
	@staticmethod
	def __parse_parent(iss_obj: dict[str, Any], repo: str, issue_num: int) -> int | None:
		pnum = iss_obj.get('parent_number')
		if isinstance(pnum, int) and (not isinstance(pnum, bool)) and pnum != int(issue_num):
			r = pnum
		else:
			cand = Linter.extract_parent_number(str(iss_obj.get('body') or ''), repo)
			r = cand if None is not cand and cand != int(issue_num) else None
		return r
	# @used-by :meth:`EvidenceWorkspace.record_issue_in_open_turns()`
	@staticmethod
	def __scan_open_turn_files(turns_dir: Path) -> list[tuple[Path, str, str]]:
		open_files: list[tuple[Path, str, str]] = []
		for tfile in turns_dir.glob('*.json'):
			if tfile.name.endswith(_SKIP_TURN_SUFFIXES):
				continue
			try:
				tdata = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(tdata, dict) and 'open' == tdata.get('status'):
				plat = str(tdata.get('platform') or '').strip().lower()
				open_files.append((tfile, plat, str(tdata.get('conversation_id') or '').strip()))
		return open_files
	# @used-by :meth:`EvidenceWorkspace.resolve_issue_targets()`
	def __target_for_project_root(self, project_root: str | Path | None) -> tuple[Path, Path] | None:
		from agent_tools.path_registry import project_paths, store_path, workspace_override
		r = None
		if None is not project_root and str(project_root).strip():
			pr = Path(project_root).resolve()
			r = self.issue_target_for_path(pr)
			if None is r:
				pp = project_paths(pr)
				r = (store_path('github_evidence_dir'), pp.turns_dir) if None is not workspace_override(pp.root) else (pp.evidence_dir / 'GitHub', pp.turns_dir)
		return r
	# @used-by :meth:`EvidenceWorkspace.record_issue_in_open_turns()`
	@classmethod
	def __update_single_turn_locked(cls, turns_dir: Path, tfile: Path, repo: str, issue_num: int, record: dict[str, Any], action: str | None, recorded_cid: str, recorded_plat: str) -> None:
		try:
			with locked(turns_dir / f'turn-{tfile.stem}.lock'):
				tdata = json.loads(tfile.read_text(encoding='utf-8'))
				if isinstance(tdata, dict) and 'open' == tdata.get('status'):
					cls.__update_turn_entry(tdata, repo, issue_num, record, action, recorded_cid, recorded_plat)
					replace_bytes(tfile, (json.dumps(tdata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
		except (OSError, ValueError):
			pass
	# @used-by :meth:`EvidenceWorkspace.__update_single_turn_locked()`
	@classmethod
	def __update_turn_entry(cls, tdata: dict[str, Any], repo: str, issue_num: int, record: dict[str, Any], action: str | None, recorded_cid: str, recorded_plat: str) -> None:
		issue_url = f'https://github.com/{repo}/issues/{issue_num}'
		gh_issues = tdata.setdefault('github_issues', {})
		prev = gh_issues.get(issue_url) if isinstance(gh_issues.get(issue_url), dict) else {}
		act_name, actions, comment_ids = cls.__merge_entry_lists(prev, record, action)
		state = record.get('state') or prev.get('state') or ('closed' if 'close' == action else 'open')
		parent_num = record.get('parent_number') if isinstance(record.get('parent_number'), int) else prev.get('parent_number')
		entry: dict[str, Any] = {'repo': repo, 'number': issue_num, 'url': issue_url, 'state': state, 'state_reason': record.get('state_reason') or prev.get('state_reason'), 'last_action': act_name, 'actions': actions, 'comment_ids': comment_ids}
		if recorded_cid:
			entry['recorded_conversation_id'] = recorded_cid
		if recorded_plat:
			entry['recorded_platform'] = recorded_plat
		if isinstance(parent_num, int) and parent_num != issue_num:
			entry.update(parent_number=parent_num, parent_url=f'https://github.com/{repo}/issues/{parent_num}')
		gh_issues[issue_url] = entry
	# @used-by :func:`agent_tools.issue_lifecycle.evidence_issue_files()`
	# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.__verify_single_url()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstEvaluator.IssueFirstEvaluator.__load_evidence_info()`
	# @used-by :meth:`Df.Harness.Issue.ParityAuditor.ParityAuditor.__find_peer_issue()`
	# @used-by :meth:`EvidenceWorkspace.evidence_issue_state()`
	@staticmethod
	def evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()) -> list[Path]:
		from agent_tools.path_registry import project_paths, store_path
		safe_repo = repo_slug.replace('/', '__')
		roots = [Path(root).resolve()] + [Path(rep).resolve() for rep in candidate_repos] + [Path(rep).resolve().parent for rep in candidate_repos]
		ev_files: list[Path] = []
		for rt in roots:
			cands = [rt / '_/\ua616/KB/Evidence/GitHub', rt / '\ua616/KB/Evidence/GitHub']
			try:
				cands.insert(0, project_paths(rt).evidence_dir / 'GitHub')
			except (OSError, ValueError):
				pass
			for base_gh in cands:
				p = (base_gh / safe_repo / fname).resolve()
				if p.is_file() and p not in ev_files:
					ev_files.append(p)
		hm = (store_path('github_evidence_dir') / safe_repo / fname).resolve()
		if hm.is_file() and hm not in ev_files:
			ev_files.append(hm)
		return ev_files
	# @used-by :func:`agent_tools.issue_lifecycle.evidence_issue_state()`
	# @used-by :meth:`Df.Harness.Issue.ScopeCompletenessChecker.ScopeCompletenessChecker.__flag_unclosed_parent()`
	# @used-by :meth:`Df.Harness.Issue.ScopeCompletenessChecker.ScopeCompletenessChecker.find_open_deferred_children()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	@staticmethod
	def evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()) -> str | None:
		r = None
		for p in EvidenceWorkspace.evidence_issue_files(root, repo_slug, f'issue-{int(number)}.json', candidate_repos):
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
				issue_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
				st = str(issue_obj.get('state') or '').strip().lower()
				if st:
					r = st
					break
			except (OSError, ValueError):
				continue
		return r
	# @used-by :func:`agent_tools.github_issue._find_existing_issue_comments()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	def find_existing_issue_comments(self, source_files: list[tuple[Path, bytes]], repo: str, issue_num: int, project_root: str | Path | None=None) -> list[int]:
		safe_repo, r = (repo.replace('/', '__'), [])
		for gh_root, _ in self.resolve_issue_targets(source_files, repo, project_root=project_root):
			gh_dir = gh_root / safe_repo
			for cfile in sorted(gh_dir.glob('comment-*.json')) if gh_dir.is_dir() else ():
				try:
					data = json.loads(cfile.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if isinstance(data, dict) and int(issue_num) == self.__extract_issue_num(data) and isinstance(data.get('id'), int) and (data['id'] not in r):
					r.append(data['id'])
		return r
	# @used-by :meth:`Df.Harness.Issue.IssueMetadataPrepender.IssueMetadataPrepender.resolve_project_root()`
	# @used-by :meth:`EvidenceWorkspace.resolve_issue_targets()`
	@staticmethod
	def find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
		return RepoLocator().find_local_code_repo(repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
	# @used-by :func:`agent_tools.github_issue.find_tracked_child_issues()`
	# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.verify()`
	# @used-by :meth:`Df.Harness.Issue.ScopeCompletenessChecker.ScopeCompletenessChecker.__flag_unclosed_parent()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_find_tracked_child_issues_passes_code_repo_without_rescanning()`
	def find_tracked_child_issues(self, repo: str, parent_number: int, *, project_root: str | Path | None=None, code_repo: Path | None=None) -> list[dict[str, Any]]:
		pnum = int(parent_number)
		targets = self.resolve_issue_targets([], repo, project_root=project_root, code_repo=code_repo)
		if None is not code_repo:
			extra = self.issue_target_for_path(Path(code_repo).resolve().parent)
			if None is not extra and (extra[0].resolve(), extra[1].resolve()) not in targets:
				targets.append((extra[0].resolve(), extra[1].resolve()))
		by_num, safe_repo = ({}, repo.replace('/', '__'))
		for gh_root, _ in targets:
			for ifile in sorted((gh_root / safe_repo).glob('issue-*.json')) if (gh_root / safe_repo).is_dir() else ():
				self.__collect_child_issue_file(ifile, repo, pnum, by_num)
		return [by_num[k] for k in sorted(by_num)]
	# @used-by :func:`agent_tools.github_issue._issue_target_for_path()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstInheritor.IssueFirstInheritor.__turns_and_evidence_dirs()`
	# @used-by :meth:`EvidenceWorkspace.__target_for_project_root()`
	# @used-by :meth:`EvidenceWorkspace.find_tracked_child_issues()`
	# @used-by :meth:`EvidenceWorkspace.resolve_issue_targets()`
	@staticmethod
	def issue_target_for_path(target_path: Path) -> tuple[Path, Path] | None:
		from agent_tools.path_registry import project_paths, store_path, workspace_override
		target_path, r = (target_path.resolve(), None)
		try:
			pp = project_paths(target_path)
			if None is not workspace_override(pp.root):
				r = (store_path('github_evidence_dir'), pp.turns_dir)
			elif pp.agent_dir.is_dir() or pp.has_overlay or 2 <= pp.fs_version or (pp.root / '_').is_dir() or pp.turns_dir.is_dir() or pp.evidence_dir.is_dir():
				r = (pp.evidence_dir / 'GitHub', pp.turns_dir)
		except (OSError, ValueError):
			pass
		if None is r:
			if (target_path / '_/\ua616').is_dir() or (target_path / '_').is_dir():
				r = (target_path / '_/\ua616/KB/Evidence/GitHub', target_path / '_/\ua616/data/turns')
			elif (target_path / '\ua616').is_dir():
				r = (target_path / '\ua616/KB/Evidence/GitHub', target_path / '\ua616/data/turns')
		return r
	# @used-by :func:`agent_tools.github_issue._load_saved_issue_container_text()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	def load_saved_issue_container_text(self, source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> str | None:
		r = None
		if None is not issue_num:
			safe_repo = repo.replace('/', '__')
			for gh_root, _ in self.resolve_issue_targets(source_files, repo, project_root=project_root):
				cand = gh_root / safe_repo / f'issue-{int(issue_num)}.json'
				if cand.is_file():
					try:
						data = json.loads(cand.read_text(encoding='utf-8'))
						if isinstance(data, dict):
							r = f"{data.get('title') or ''}\n{data.get('body') or ''}".strip() or None
							break
					except (OSError, ValueError):
						continue
		return r
	# @used-by :func:`agent_tools.github_issue._meta_dir_for_project_root()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	@staticmethod
	def meta_dir_for_project_root(proj_root: Path) -> Path | None:
		from agent_tools.path_registry import project_paths
		proj_root, r = (proj_root.resolve(), None)
		try:
			pp = project_paths(proj_root)
			if pp.agent_dir.is_dir() or pp.has_overlay or 2 <= pp.fs_version or (pp.root / '_').is_dir():
				r = pp.agent_dir
		except (OSError, ValueError):
			pass
		if None is r:
			r = proj_root / '_/\ua616' if (proj_root / '_/\ua616').is_dir() or (proj_root / '_').is_dir() else proj_root / '\ua616' if (proj_root / '\ua616').is_dir() else None
		return r
	# @used-by :func:`agent_tools.issue_lifecycle.origin_repo_slug()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.build()`
	# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.__verify_tracked_evidence()`
	# @used-by :meth:`Df.Harness.Git.VerificationSpecResolver.VerificationSpecResolver.resolve()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.resolve_target()`
	# @used-by :meth:`Df.Harness.Issue.ParityAuditor.ParityAuditor.similar_project_repo_slugs()`
	@staticmethod
	def origin_repo_slug(code_repo: Path) -> str | None:
		return RepoLocator().origin_repo_slug(code_repo)
	# @used-by :func:`agent_tools.github_issue._persist_issue_evidence()`
	# @used-by :meth:`Df.Harness.Issue.IssueFetcher.IssueFetcher.fetch()`
	def persist_issue_evidence(self, source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], *, kind: str='issue', action: str | None=None, project_root: str | Path | None=None, parent_number: int | None=None, conversation_id: str | None=None) -> str | None:
		ident = fetched.get('number') if isinstance(fetched, dict) and 'issue' == kind else fetched.get('id') if isinstance(fetched, dict) else None
		r: str | None = None
		if isinstance(fetched, dict) and fetched.get('html_url') and (None is not ident):
			record = self.__build_issue_record(source_files, repo, fetched, ident, kind, project_root, parent_number)
			payload_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
			safe_repo = repo.replace('/', '__')
			for gh_root, turns_dir in self.resolve_issue_targets(source_files, repo, project_root=project_root):
				target = gh_root / safe_repo / f'{kind}-{ident}.json'
				replace_bytes(target, payload_bytes)
				if None is r:
					r = str(target)
				self.record_issue_in_open_turns(turns_dir, repo, record, action, conversation_id=conversation_id)
		return r
	# @used-by :meth:`Df.Harness.Issue.RepoTransferRunner.RepoTransferRunner.transfer()`
	def persist_repo_transfer_evidence(self, source_repo: str, target_repo: str, transfer_response: dict[str, Any] | None, verified_repo: dict[str, Any] | None, *, project_root: str | Path | None=None) -> Path | None:
		safe_target, safe_source = (target_repo.replace('/', '__'), source_repo.replace('/', '__'))
		ev_dirs = [ev for ev, _ in self.resolve_issue_targets([], target_repo, project_root=project_root)]
		encoded = (json.dumps({'kind': 'repo_transfer', 'source_repo': source_repo, 'target_repo': target_repo, 'transfer_response': transfer_response, 'verified_repo': verified_repo}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		primary_out = None
		for ev_root in ev_dirs:
			out_file = ev_root / safe_target / f'transfer-{safe_source}-to-{safe_target}.json'
			replace_bytes(out_file, encoded)
			if None is primary_out:
				primary_out = out_file
		return primary_out
	# @used-by :func:`agent_tools.github_issue._record_issue_in_open_turns()`
	# @used-by :meth:`EvidenceWorkspace.persist_issue_evidence()`
	# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_record_issue_isolates_by_antigravity_env_metadata_and_explicit_arg()`
	# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_record_issue_skips_broadcast_when_env_unknown_with_multiple_open_turns()`
	# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_evidence_workspace_uses_locked_atomic_turn_updates()`
	def record_issue_in_open_turns(self, turns_dir: Path, repo: str, record: dict[str, Any], action: str | None, *, conversation_id: str | None=None) -> None:
		issue_num = self.__extract_issue_num(record)
		if turns_dir.is_dir() and None is not issue_num:
			active_plat, active_cid = SessionDetector(conversation_id=conversation_id).detect()
			open_files = self.__scan_open_turn_files(turns_dir)
			targets, rec_cid, rec_plat = TurnScopeResolver(open_files, active_plat, active_cid).select()
			for tfile in targets:
				self.__update_single_turn_locked(turns_dir, tfile, repo, int(issue_num), record, action, rec_cid, rec_plat)
	# @used-by :func:`agent_tools.github_issue._repo_matches_github_slug()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
	@staticmethod
	def repo_matches_slug(code_repo: Path, repo: str) -> bool:
		return RepoLocator.repo_matches_slug(code_repo, repo)
	# @used-by :func:`agent_tools.github_issue._resolve_issue_targets()`
	# @used-by :meth:`EvidenceWorkspace.find_existing_issue_comments()`
	# @used-by :meth:`EvidenceWorkspace.find_tracked_child_issues()`
	# @used-by :meth:`EvidenceWorkspace.load_saved_issue_container_text()`
	# @used-by :meth:`EvidenceWorkspace.persist_issue_evidence()`
	# @used-by :meth:`EvidenceWorkspace.persist_repo_transfer_evidence()`
	# @used-by :meth:`EvidenceWorkspace.saved_issue_parent_number()`
	def resolve_issue_targets(self, source_files: list[tuple[Path, bytes]], repo: str, project_root: str | Path | None=None, *, code_repo: Path | None=None) -> list[tuple[Path, Path]]:
		from agent_tools.path_registry import store_path, store_value
		r: list[tuple[Path, Path]] = []
		# @used-by :meth:`EvidenceWorkspace.resolve_issue_targets()`
		def _add(pair: tuple[Path, Path] | None) -> None:
			if None is not pair and (pair[0].resolve(), pair[1].resolve()) not in r:
				r.append((pair[0].resolve(), pair[1].resolve()))
		_add(self.__target_for_project_root(project_root))
		resolved_repo = Path(code_repo).resolve() if None is not code_repo else self.find_local_code_repo(repo, project_root=project_root, source_files=source_files)
		if None is not resolved_repo:
			_add(self.issue_target_for_path(resolved_repo))
		for fpath, _ in source_files:
			_add(self.issue_target_for_path(fpath))
		primary_repo = str(store_value('primary_github_repo') or '').lower()
		if not r or (primary_repo and primary_repo == repo.lower()):
			_add((store_path('github_evidence_dir'), store_path('data_dir') / 'turns'))
		return r
	# @used-by :func:`agent_tools.github_issue._saved_issue_parent_number()`
	# @used-by :meth:`EvidenceWorkspace.__build_issue_record()`
	def saved_issue_parent_number(self, source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> int | None:
		r = None
		if None is not issue_num:
			safe_repo = repo.replace('/', '__')
			for gh_root, _ in self.resolve_issue_targets(source_files, repo, project_root=project_root):
				cand = gh_root / safe_repo / f'issue-{int(issue_num)}.json'
				if cand.is_file():
					try:
						data = json.loads(cand.read_text(encoding='utf-8'))
					except (OSError, ValueError):
						continue
					iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
					if isinstance(iss_obj, dict):
						r = self.__parse_parent(iss_obj, repo, int(issue_num))
						if None is not r:
							break
		return r
