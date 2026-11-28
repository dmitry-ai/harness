# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.RepoLocator import RepoLocator, V2_CODE_RELS
import json
import re
import tempfile
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
_GH_ISSUE_URL_RE = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)$')
_JSON_FENCE_RE = re.compile(r'```json[ \t]*\r?\n([\s\S]*?)\r?\n```')
_REQ_URL_RE = re.compile(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+', re.I)
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_issue_entries()`
class ProblemIssueSpecification:
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_issue_entries()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__validate_problem_issue()`
	def __init__(self, entries: list[dict[str, Any]], *, root: Path | str | None=None, turn: dict[str, Any] | None=None, turn_state: dict[str, Any] | None=None, requests: list | tuple=(), schema_mode: str='problem', strict_evidence: bool=False, conversation_id: str | None=None) -> None:
		self.__entries = entries
		self.__root = Path(root).resolve() if None is not root and str(root).strip() else None
		self.__turn = turn if isinstance(turn, dict) else None
		self.__turn_state = turn_state if isinstance(turn_state, dict) else None
		self.__requests = requests
		self.__schema_mode = schema_mode
		self.__strict_evidence = bool(strict_evidence)
		raw_cid = conversation_id or (self.__turn_state.get('conversation_id') if None is not self.__turn_state else '')
		self.__cid = str(raw_cid or '').strip()
	# @used-by :meth:`ProblemIssueSpecification.__state_created_urls()`
	@staticmethod
	def __action_is_create(entry: dict[str, Any]) -> bool:
		last_act = str(entry.get('last_action') or '').strip().lower()
		acts = [str(a).strip().lower() for a in (entry.get('actions') or ())]
		return 'create' == last_act or 'create' in acts
	# @used-by :meth:`ProblemIssueSpecification.__check_one_issue()`
	@classmethod
	def __check_evidence(cls, prefix: str, url: str, norm_url: str, repo_slug: str, num: int, ctx: dict[str, Any], errs: list[str]) -> None:
		iss_obj = cls.__load_issue_record(cls.find_evidence_files(ctx['root'], repo_slug, num))
		if None is iss_obj:
			errs.append(f'{prefix}DOC-5 / UNVERIFIED_PROBLEM_ISSUE: GitHub issue {url} has no local saved Evidence JSON (issue-{num}.json); create or fetch it via df_github_issue.py first')
		else:
			state = str(iss_obj.get('state') or '').strip().lower()
			if 'open' != state:
				st_lbl = state or 'unknown'
				errs.append(f'{prefix}DOC-5 / CLOSED_PROBLEM_ISSUE: GitHub issue {url} has state "{st_lbl}" (must be "open")')
			pnum = cls.__extract_parent_num(iss_obj, repo_slug, num)
			if None is not pnum:
				errs.append(f'{prefix}DOC-5 / CHILD_PROBLEM_ISSUE: GitHub issue {url} is a child subtask of #{pnum}; problem metadata requires an unparented parent issue')
			cls.__check_provenance(prefix, url, norm_url, iss_obj, ctx, errs)
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@classmethod
	def __check_null_policy(cls, entries: list[dict[str, Any]], root: Path | None, schema_mode: str, errs: list[str]) -> None:
		if cls.has_github_repo(root):
			if 'mixed_problem' == schema_mode:
				for entry in entries:
					if None is entry.get('issue'):
						pfx = str(entry.get('prefix') or '')
						errs.append(f'{pfx}DOC-5 / NULL_PROBLEM_ISSUE: Problem metadata "Issue" cannot be null in a GitHub-tracked workspace; open a dedicated open parent GitHub issue first')
			elif entries and all((None is e.get('issue') for e in entries)):
				errs.append('DOC-5 / NULL_PROBLEM_ISSUE: Problem analysis in a GitHub-tracked workspace cannot set "Issue": null on every track; cite an open parent GitHub issue for the primary defect')
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@classmethod
	def __check_one_issue(cls, entry: dict[str, Any], seen: set[str], ctx: dict[str, Any], errs: list[str]) -> None:
		raw_url = entry.get('issue')
		if None is not raw_url:
			prefix = str(entry.get('prefix') or '')
			parsed = cls.parse_issue_url(raw_url)
			if None is parsed:
				errs.append(f'{prefix}DOC-5 / df-analysis: Problem metadata "Issue" must be a valid GitHub issue URL or null (non-GitHub workspace)')
			else:
				repo_slug, num, clean_url = parsed
				norm_url = clean_url.lower()
				if norm_url in seen:
					errs.append(f'{prefix}DOC-5 / DUPLICATE_PROBLEM_ISSUE: GitHub issue {clean_url} is duplicated across multiple problem blocks; each block requires its own dedicated open parent issue')
				else:
					seen.add(norm_url)
					if ctx['enforce_evidence']:
						cls.__check_evidence(prefix, clean_url, norm_url, repo_slug, num, ctx, errs)
	# @used-by :meth:`ProblemIssueSpecification.__check_evidence()`
	@classmethod
	def __check_provenance(cls, prefix: str, url: str, norm_url: str, iss_obj: dict[str, Any], ctx: dict[str, Any], errs: list[str]) -> None:
		if norm_url not in ctx['requested_urls']:
			active_cid = ctx['active_cid']
			issue_cid = cls.__extract_issue_cid(iss_obj)
			if active_cid and issue_cid and issue_cid.lower() != active_cid.lower():
				errs.append(f'{prefix}DOC-5 / FOREIGN_PROBLEM_ISSUE: GitHub issue {url} belongs to foreign conversation {issue_cid} (active conversation: {active_cid})')
			elif 'mixed_problem' == ctx['schema_mode'] and ctx['has_turn'] and (norm_url not in ctx['created_urls']):
				errs.append(f'{prefix}DOC-5 / FOREIGN_PROBLEM_ISSUE: Newly discovered problem cites {url}, which was not created in the active turn (open a new dedicated parent issue)')
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@classmethod
	def __created_urls(cls, turn: dict[str, Any] | None, turn_state: dict[str, Any] | None, active_cid: str) -> set[str]:
		return cls.__turn_action_created_urls(turn) | cls.__state_created_urls(turn_state, active_cid)
	# @used-by :meth:`ProblemIssueSpecification.find_evidence_files()`
	@classmethod
	def __evidence_roots(cls, rt: Path) -> list[Path]:
		from agent_tools.path_registry import project_paths, store_path
		in_temp = cls.is_temp_path(rt)
		cands = [rt / '_/\ua616/KB/Evidence/GitHub', rt / '\ua616/KB/Evidence/GitHub']
		try:
			ev_dir = project_paths(rt).evidence_dir / 'GitHub'
			if (not in_temp) or cls.is_temp_path(ev_dir):
				cands.insert(0, ev_dir)
		except (OSError, ValueError):
			pass
		if not in_temp:
			cands.append(store_path('github_evidence_dir'))
		return cands
	# @used-by :meth:`ProblemIssueSpecification.__check_provenance()`
	@staticmethod
	def __extract_issue_cid(iss_obj: dict[str, Any]) -> str:
		m = _JSON_FENCE_RE.search(str(iss_obj.get('body') or ''))
		r = ''
		if None is not m:
			try:
				meta = json.loads(m.group(1))
			except ValueError:
				meta = None
			if isinstance(meta, dict) and isinstance(meta.get('Trace'), dict):
				r = str(meta['Trace'].get('Conversation ID') or '').strip()
		return r
	# @used-by :meth:`ProblemIssueSpecification.__check_evidence()`
	# @used-by :meth:`ProblemIssueSpecification.is_valid_open_parent_issue()`
	@staticmethod
	def __extract_parent_num(iss_obj: dict[str, Any], repo_slug: str, issue_num: int) -> int | None:
		pnum = iss_obj.get('parent_number')
		if isinstance(pnum, int) and (not isinstance(pnum, bool)) and pnum != int(issue_num):
			r: int | None = pnum
		else:
			from Df.Harness.Issue.Linter import Linter
			cand = Linter.extract_parent_number(str(iss_obj.get('body') or ''), repo_slug)
			r = cand if None is not cand and cand != int(issue_num) else None
		return r
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@staticmethod
	def __has_local_evidence_dir(root: Path | None) -> bool:
		return None is not root and any(((root / rel).is_dir() for rel in ('\ua616/KB/Evidence/GitHub', '_/\ua616/KB/Evidence/GitHub')))
	# @used-by :meth:`ProblemIssueSpecification.__check_evidence()`
	# @used-by :meth:`ProblemIssueSpecification.is_valid_open_parent_issue()`
	@staticmethod
	def __load_issue_record(paths: list[Path]) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		for path in paths:
			try:
				data = json.loads(path.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
			if isinstance(iss_obj, dict):
				r = iss_obj
				break
		return r
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@staticmethod
	def __requested_urls(requests: list | tuple) -> set[str]:
		out: set[str] = set()
		for req in requests or ():
			raw = str(req.get('text') or req.get('content') or '') if isinstance(req, dict) else str(req or '')
			for found in _REQ_URL_RE.findall(raw):
				out.add(found.strip().rstrip('/').lower())
		return out
	# @used-by :meth:`ProblemIssueSpecification.__created_urls()`
	@classmethod
	def __state_created_urls(cls, turn_state: dict[str, Any] | None, active_cid: str) -> set[str]:
		out: set[str] = set()
		gh_map = (turn_state or {}).get('github_issues')
		if isinstance(gh_map, dict):
			for key_url, entry in gh_map.items():
				if isinstance(entry, dict) and cls.__action_is_create(entry):
					rec_cid = str(entry.get('recorded_conversation_id') or '').strip()
					if (not rec_cid) or (not active_cid) or rec_cid.lower() == active_cid.lower():
						url = str(entry.get('url') or key_url or '').strip().rstrip('/').lower()
						if url:
							out.add(url)
		return out
	# @used-by :meth:`ProblemIssueSpecification.__created_urls()`
	@staticmethod
	def __turn_action_created_urls(turn: dict[str, Any] | None) -> set[str]:
		out: set[str] = set()
		for act in (turn or {}).get('issue_actions') or ():
			if isinstance(act, dict) and 'create' == str(act.get('action') or '').strip().lower():
				url = str(act.get('url') or '').strip()
				if (not url) and act.get('repo') and act.get('number'):
					repo_s, num_s = (act['repo'], act['number'])
					url = f'https://github.com/{repo_s}/issues/{num_s}'
				if url:
					out.add(url.rstrip('/').lower())
		return out
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_has_recorded_hook_issue()`
	# @used-by :meth:`ProblemIssueSpecification.__check_evidence()`
	# @used-by :meth:`ProblemIssueSpecification.is_valid_open_parent_issue()`
	@classmethod
	def find_evidence_files(cls, root: Path | str | None, repo_slug: str, issue_num: int) -> list[Path]:
		ev_files: list[Path] = []
		if None is not root and str(root).strip():
			safe_repo, fname = (repo_slug.replace('/', '__'), f'issue-{int(issue_num)}.json')
			for base_gh in cls.__evidence_roots(Path(root).resolve()):
				p = (base_gh / safe_repo / fname).resolve()
				if p.is_file() and p not in ev_files:
					ev_files.append(p)
		return ev_files
	# @used-by :meth:`ProblemIssueSpecification.__check_null_policy()`
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@classmethod
	def has_github_repo(cls, root: Path | str | None) -> bool:
		return bool(cls.workspace_repo_slugs(root))
	# @used-by :meth:`ProblemIssueSpecification.__evidence_roots()`
	# @used-by :meth:`ProblemIssueSpecification.validate()`
	@staticmethod
	def is_temp_path(path: Path | str | None) -> bool:
		r = False
		if None is not path and str(path).strip():
			try:
				r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
			except (OSError, ValueError):
				r = False
		return r
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_has_recorded_hook_issue()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__has_workspace_parent_issue()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	@classmethod
	def is_valid_open_parent_issue(cls, root: Path | str | None, repo_slug: str, issue_num: int) -> bool:
		rec = cls.__load_issue_record(cls.find_evidence_files(root, repo_slug, int(issue_num)))
		return None is not rec and 'open' == str(rec.get('state') or '').strip().lower() and (None is cls.__extract_parent_num(rec, repo_slug, int(issue_num)))
	# @used-by :meth:`ProblemIssueSpecification.__check_one_issue()`
	@staticmethod
	def parse_issue_url(url: object) -> tuple[str, int, str] | None:
		r: tuple[str, int, str] | None = None
		if isinstance(url, str):
			clean = url.strip().rstrip('/')
			m = _GH_ISSUE_URL_RE.fullmatch(clean)
			if None is not m:
				r = (m.group(1), int(m.group(2)), clean)
		return r
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_issue_entries()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__validate_problem_issue()`
	def validate(self) -> list[str]:
		errs: list[str] = []
		self.__check_null_policy(self.__entries, self.__root, self.__schema_mode, errs)
		enforce_ev = False
		if None is not self.__root:
			enforce_ev = self.__strict_evidence or (not self.is_temp_path(self.__root)) or self.has_github_repo(self.__root) or self.__has_local_evidence_dir(self.__root)
		ctx = {'root': self.__root, 'active_cid': self.__cid, 'schema_mode': self.__schema_mode, 'has_turn': None is not self.__turn or None is not self.__turn_state, 'enforce_evidence': enforce_ev, 'created_urls': self.__created_urls(self.__turn, self.__turn_state, self.__cid), 'requested_urls': self.__requested_urls(self.__requests)}
		seen: set[str] = set()
		for entry in self.__entries:
			self.__check_one_issue(entry, seen, ctx, errs)
		return errs
	# @used-by :meth:`ProblemIssueSpecification.has_github_repo()`
	@staticmethod
	def workspace_repo_slugs(root: Path | str | None) -> set[str]:
		slugs: set[str] = set()
		if None is not root and str(root).strip():
			from agent_tools.path_registry import project_paths
			root_p = Path(root).resolve()
			cands: list[Path] = [root_p, root_p / 'code', *(root_p / rel for rel in V2_CODE_RELS)]
			try:
				cands = [*project_paths(root_p).code_repos, *cands]
			except (OSError, ValueError):
				pass
			locator = RepoLocator()
			for cand in cands:
				if (cand / '.git').exists():
					slug = locator.origin_repo_slug(cand)
					if slug:
						slugs.add(slug.lower())
		return slugs
