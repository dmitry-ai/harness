# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from Df.Harness.Git.IssueActionExtractor import IssueActionExtractor
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.IssueFirstBgScanner import IssueFirstBgScanner
from Df.Harness.Issue.IssueFirstEvaluator import IssueFirstEvaluator
from Df.Harness.Issue.IssueFirstInheritor import IssueFirstInheritor
from Df.Harness.lib.issue import dfh_is_df_issue_command_text, dfh_is_excluded_meta_rel
from agent_tools.tdd_gate import classify_code_path, shell_write_targets
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueFirstPreToolEvaluator:
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def __init__(self, name: str, args: dict, payload: dict) -> None:
		self.__name = name
		self.__args = args
		self.__payload = payload
		cwd_raw = str(payload.get('cwd') or '').strip()
		self.__cwd = Path(cwd_raw).resolve() if cwd_raw else None
	# @used-by :meth:`IssueFirstPreToolEvaluator.evaluate()`
	def __check_pending_target(self, target_path: Path, info: dict, events: list[dict], requests: list[dict], base_eval: dict, next_step: int, t_path: Path) -> str | None:
		slug_key = info['repo_slug'].lower()
		repo_st = base_eval['repos'].get(slug_key)
		r: str | None = None
		if not (repo_st and repo_st.get('active_parents')):
			pending_ev = {'kind': 'code_write', 'step': next_step, 'path': str(target_path), 'rel_path': info['rel_path'], 'repo_root': str(info['repo_root']), 'repo_slug': info['repo_slug'], 'classification': info['classification']}
			probe = IssueFirstEvaluator([*events, pending_ev], requests=requests, project_root=self.__cwd or info['repo_root']).evaluate()
			probe_st = probe['repos'].get(slug_key)
			if not ((probe_st and probe_st.get('active_parents')) or IssueFirstInheritor(self.__payload, info, self.__cwd, t_path).has_inherited_open_parent()):
				rel, slug = (info['rel_path'], info['repo_slug'])
				r = probe['violations'][-1] if probe['violations'] else f'EXEC-5 ISSUE-FIRST-GATE: Cannot edit "{rel}" in {slug} before establishing an open parent GitHub issue via df_github_issue.py create --repo {slug} (or df_github_issue.py fetch --repo {slug} --issue <N>).'
		return r
	# @used-by :meth:`IssueFirstPreToolEvaluator.evaluate()`
	def __collect_pending_targets(self) -> list[tuple[Path, dict]]:
		r: list[tuple[Path, dict]] = []
		if self.__name in ('write_file', 'edit_file'):
			pair = self.__collect_write_target()
			if None is not pair:
				r.append(pair)
		elif 'run_command' == self.__name:
			for wt in shell_write_targets(str(self.__args.get('CommandLine') or ''), cwd=self.__cwd):
				info = self.resolve_target(wt)
				if None is not info:
					r.append((wt, info))
		return r
	# @used-by :meth:`IssueFirstPreToolEvaluator.__collect_pending_targets()`
	def __collect_write_target(self) -> tuple[Path, dict] | None:
		raw_p = str(self.__args.get('Path') or '').strip()
		r: tuple[Path, dict] | None = None
		if raw_p:
			cand = HostPathNormalizer(raw_p).normalize()
			target_path = cand.resolve() if cand.is_absolute() else (self.__cwd / cand).resolve() if self.__cwd else cand.resolve()
			hint = self.__args.get('Content') if 'write_file' == self.__name and isinstance(self.__args.get('Content'), str) else None
			info = self.resolve_target(target_path, content=hint)
			if None is not info:
				r = (target_path, info)
		return r
	# @used-by :meth:`IssueFirstPreToolEvaluator.__resolve_repo_rel()`
	@staticmethod
	def __find_git_repo_root(path: Path) -> Path | None:
		start = path if path.is_dir() else path.parent
		r: Path | None = None
		for anc in (start, *start.parents):
			if (anc / '.git').exists():
				r = anc
				break
		return r
	# @used-by :meth:`IssueFirstPreToolEvaluator.resolve_target()`
	@classmethod
	def __resolve_repo_rel(cls, path: str | Path) -> tuple[Path, Path, str] | None:
		cand = HostPathNormalizer(path).normalize()
		try:
			full = cand.resolve()
		except OSError:
			full = cand
		repo_root = cls.__find_git_repo_root(full)
		r: tuple[Path, Path, str] | None = None
		if None is not repo_root:
			try:
				rel_posix = full.relative_to(repo_root).as_posix()
			except ValueError:
				rel_posix = None
			if None is not rel_posix and (not dfh_is_excluded_meta_rel(rel_posix)):
				r = (full, repo_root, rel_posix)
		return r
	# @used-by :func:`agent_tools.issue_first_gate.build_code_write_issue_first_event()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.extract_antigravity_events()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	@classmethod
	def build_code_write_event(cls, step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, sub_step: int | None=None, cmd_outputs=None) -> dict | None:
		from agent_tools.tdd.events import is_denied_write_output
		r: dict | None = None
		if not is_denied_write_output(cmd_outputs):
			cand = HostPathNormalizer(raw_path).normalize()
			full = cand.resolve() if cand.is_absolute() else (Path(cwd).resolve() / cand).resolve() if None is not cwd else cand.resolve()
			info = cls.resolve_target(full, content=content)
			if None is not info:
				r = {'kind': 'code_write', 'step': int(step), 'path': str(full), 'rel_path': info['rel_path'], 'repo_root': str(info['repo_root']), 'repo_slug': info['repo_slug'], 'classification': info['classification']}
				if None is not sub_step:
					r['sub_step'] = int(sub_step)
		return r
	# @used-by :func:`agent_tools.issue_first_gate.build_issue_action_events()`
	# @used-by :meth:`Df.Harness.Issue.BgTaskRecorder.BgTaskRecorder.__record_seg_issues()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.extract_antigravity_events()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	@staticmethod
	def build_issue_action_events(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, sub_step: int | None=None) -> list[dict]:
		r: list[dict] = []
		if dfh_is_df_issue_command_text(cmd):
			out_list = [outputs] if isinstance(outputs, str) else [str(o) for o in (outputs or ()) if o]
			for act in IssueActionExtractor(out_list).extract():
				ev: dict = {'kind': 'issue_action', 'step': int(step), 'action': act['action'], 'repo': act['repo'], 'number': int(act['number']), 'url': act['url'], 'state': act.get('state')}
				if isinstance(act.get('parent_number'), int) and (not isinstance(act.get('parent_number'), bool)):
					ev['parent_number'] = act['parent_number']
				if None is not sub_step:
					ev['sub_step'] = int(sub_step)
				r.append(ev)
		return r
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def evaluate(self) -> str | None:
		pending = self.__collect_pending_targets()
		r: str | None = None
		if pending:
			t_raw = str(self.__payload.get('transcriptPath') or '').strip()
			if not t_raw:
				r = IssueFirstInheritor.missing_transcript_error(pending, self.__payload, self.__cwd)
			else:
				t_path = Path(t_raw)
				events, requests = self.extract_antigravity_events(t_path, cwd=self.__cwd)
				base_eval = IssueFirstEvaluator(events, requests=requests, project_root=self.__cwd).evaluate()
				next_step = max((int(e.get('step', 0)) for e in events), default=0) + 1
				for target_path, info in pending:
					err = self.__check_pending_target(target_path, info, events, requests, base_eval, next_step, t_path)
					if None is not err:
						r = err
						break
		return r
	# @used-by :func:`agent_tools.issue_first_gate.extract_antigravity_issue_first_events()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.evaluate()`
	@classmethod
	def extract_antigravity_events(cls, transcript_path: Path, *, cwd: Path | None=None) -> tuple[list[dict], list[dict]]:
		from agent_tools.trace_event_cache import load_transcript_rows_cached
		rows = load_transcript_rows_cached(transcript_path, cwd=cwd)
		if not rows:
			r: tuple[list[dict], list[dict]] = ([], [])
		else:
			last_user = -1
			for idx, row in enumerate(rows):
				if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
					last_user = idx
			requests: list[dict] = []
			if 0 <= last_user:
				u_content = str(rows[last_user].get('content') or '')
				if u_content.strip():
					requests.append({'text': u_content})
			segment = rows[last_user + 1:] if 0 <= last_user else rows
			r = (IssueFirstBgScanner(segment, cwd, cls.build_code_write_event, cls.build_issue_action_events).extract(), requests)
		return r
	# @used-by :func:`agent_tools.issue_first_gate.resolve_issue_first_target()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.__collect_pending_targets()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.__collect_write_target()`
	# @used-by :meth:`IssueFirstPreToolEvaluator.build_code_write_event()`
	@classmethod
	def resolve_target(cls, path: str | Path, *, content: str | None=None) -> dict | None:
		resolved = cls.__resolve_repo_rel(path)
		r: dict | None = None
		if None is not resolved:
			full, repo_root, rel_posix = resolved
			slug = EvidenceWorkspace.origin_repo_slug(repo_root)
			if slug:
				cls_name = classify_code_path(full, content=content)
				if 'non_code' != cls_name or RepoGate(repo_root).is_issue_tracked():
					r = {'repo_root': repo_root, 'repo_slug': slug, 'rel_path': rel_posix, 'classification': cls_name}
		return r
