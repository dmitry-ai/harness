# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations

import json
from pathlib import Path
import re
from .git_gate import is_issue_tracked_code_repo
from .github_issue import extract_parent_issue_number
from .issue_lifecycle import evidence_issue_files, origin_repo_slug
from .shell_audit import _GITHUB_ISSUE_URL_RE, _split_shell_segments, extract_issue_actions_from_outputs, normalize_host_path, parse_issue_url
from .tdd_gate import _normalize_args_dict, classify_code_path, shell_write_targets

_EXCLUDED_META_PREFIXES = tuple(p.casefold() for p in (
	'.git/', '__pycache__/', 'node_modules/',
	'\ua616/', '\ua66e/', '_/', '\U0001f56e/',
	'\u2c0f/\u227a/', 'artifacts/\u227a/',
))
_EXCLUDED_META_PARTS = frozenset(p.casefold() for p in (
	'.git', '__pycache__', 'node_modules', '\ua616', '\ua66e', '\U0001f56e',
))
_DF_ISSUE_CMD_RE = re.compile(
	r'^\s*(?:&\s*)?(?:["\']?[^\s"\']*python(?:3(?:\.\d+)?)?(?:\.exe)?["\']?\s+(?:-[A-Za-z0-9_]+\s+)*)?'
	r'["\']?(?:[^"\']*[/\\])?df_github_issue\.py["\']?\s+(create|fetch|edit|comment|close)\b',
	re.IGNORECASE,
)
_HASH_ISSUE_REF_RE = re.compile(r'(?<![A-Za-z0-9_/])#(\d+)\b')
_USER_REQUEST_BLOCK_RE = re.compile(r'<USER_REQUEST>\r?\n([\s\S]*?)\r?\n</USER_REQUEST>')


# @used-by :func:`resolve_issue_first_target()`
def _find_git_repo_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			return anc
	return None


# @used-by :func:`agent_tools.issues.service_helpers._parse_dirty_porcelain()`
# @used-by :func:`resolve_issue_first_target()`
def _is_excluded_meta_rel(rel_posix: str) -> bool:
	low = rel_posix.replace('\\', '/').casefold()
	while low.startswith('./'):
		low = low[2:]
	low = low.lstrip('/')
	if not low or '.' == low:
		return True
	if any(low.startswith(pref) for pref in _EXCLUDED_META_PREFIXES):
		return True
	parts = low.split('/')
	return any(part in _EXCLUDED_META_PARTS for part in parts[:-1])


# @used-by :func:`build_code_write_issue_first_event()`
# @used-by :func:`evaluate_pre_tool_use_issue_first()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_resolve_issue_first_target_distinguishes_github_backed_local_and_metadata_paths()`
def resolve_issue_first_target(path: str | Path, *, content: str | None = None) -> dict | None:
	cand = normalize_host_path(path)
	try:
		full = cand.resolve()
	except OSError:
		full = cand
	repo_root = _find_git_repo_root(full)
	if None is repo_root:
		return None
	try:
		rel_posix = full.relative_to(repo_root).as_posix()
	except ValueError:
		return None
	if _is_excluded_meta_rel(rel_posix):
		return None
	slug = origin_repo_slug(repo_root)
	if not slug:
		return None
	cls = classify_code_path(full, content=content)
	if 'non_code' == cls and (not is_issue_tracked_code_repo(repo_root)):
		return None
	return {
		'repo_root': repo_root,
		'repo_slug': slug,
		'rel_path': rel_posix,
		'classification': cls,
	}


# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
# @used-by :func:`agent_tools.completion._scan_child_trace_turn()`
# @used-by :func:`agent_tools.issue_first_bg._record_bg_seg_issues()`
# @used-by :func:`build_issue_action_events()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._scan_primary_turns()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._visit_subagent_rows()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_extract_issue_actions_recognizes_fetch_and_anti_spoofing_command_check()`
def is_df_github_issue_command(cmd: str) -> bool:
	from .issue_first_bg import is_df_issue_command_text
	return is_df_issue_command_text(cmd, _DF_ISSUE_CMD_RE)


# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :func:`extract_antigravity_issue_first_events()`
def build_code_write_issue_first_event(
	step: int,
	raw_path: str | Path,
	*,
	cwd: Path | None = None,
	content: str | None = None,
	sub_step: int | None = None,
	cmd_outputs=None,
) -> dict | None:
	from .tdd.events import is_denied_write_output
	r: dict | None = None
	if not is_denied_write_output(cmd_outputs):
		cand = normalize_host_path(raw_path)
		full = cand.resolve() if cand.is_absolute() else ((Path(cwd).resolve() / cand).resolve() if None is not cwd else cand.resolve())
		info = resolve_issue_first_target(full, content=content)
		if None is not info:
			r = {'kind': 'code_write', 'step': int(step), 'path': str(full), 'rel_path': info['rel_path'], 'repo_root': str(info['repo_root']), 'repo_slug': info['repo_slug'], 'classification': info['classification']}
			if None is not sub_step:
				r['sub_step'] = int(sub_step)
	return r


# @used-by :func:`agent_tools.completion._scan_child_trace_turn()`
# @used-by :func:`agent_tools.issue_first_bg._record_bg_seg_issues()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :func:`extract_antigravity_issue_first_events()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._scan_primary_turns()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._visit_subagent_rows()`
def build_issue_action_events(
	step: int,
	cmd: str,
	outputs: list[str] | tuple[str, ...] | str,
	*,
	sub_step: int | None = None,
) -> list[dict]:
	if not is_df_github_issue_command(cmd):
		return []
	out_list = [outputs] if isinstance(outputs, str) else [str(o) for o in (outputs or ()) if o]
	out_events: list[dict] = []
	for act in extract_issue_actions_from_outputs(out_list):
		ev: dict = {
			'kind': 'issue_action',
			'step': int(step),
			'action': act['action'],
			'repo': act['repo'],
			'number': int(act['number']),
			'url': act['url'],
			'state': act.get('state'),
		}
		if isinstance(act.get('parent_number'), int) and (not isinstance(act.get('parent_number'), bool)):
			ev['parent_number'] = act['parent_number']
		if None is not sub_step:
			ev['sub_step'] = int(sub_step)
		out_events.append(ev)
	return out_events


# @used-by :func:`_seed_open_issues_from_requests()`
# @used-by :func:`evaluate_issue_first_events()`
def _load_evidence_issue_info(
	project_root: Path | None,
	slug: str,
	number: int,
	candidate_repos: list[Path],
) -> dict | None:
	base = Path(project_root).resolve() if None is not project_root else (candidate_repos[0] if candidate_repos else Path.cwd().resolve())
	files = evidence_issue_files(base, slug, f'issue-{int(number)}.json', candidate_repos=candidate_repos)
	for ev_path in files:
		try:
			data = json.loads(ev_path.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			continue
		if not isinstance(data, dict):
			continue
		iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
		if not isinstance(iss_obj, dict):
			continue
		state = str(iss_obj.get('state') or data.get('state') or '').strip().lower()
		raw_parent = data.get('parent_number')
		if not isinstance(raw_parent, int) or isinstance(raw_parent, bool):
			raw_parent = iss_obj.get('parent_number')
		if not isinstance(raw_parent, int) or isinstance(raw_parent, bool):
			raw_parent = extract_parent_issue_number(str(iss_obj.get('body') or ''), slug)
		parent_num = int(raw_parent) if isinstance(raw_parent, int) and (not isinstance(raw_parent, bool)) and int(raw_parent) != int(number) else None
		return {
			'number': int(number),
			'state': state or None,
			'parent_number': parent_num,
			'path': str(ev_path),
		}
	return None


# @used-by :func:`_seed_open_issues_from_requests()`
def _extract_request_text(req) -> str:
	raw = ''
	if isinstance(req, str):
		raw = req
	elif isinstance(req, dict):
		raw = str(req.get('text') or req.get('content') or '')
	m = _USER_REQUEST_BLOCK_RE.search(raw)
	return m.group(1) if m else raw


# @used-by :func:`evaluate_issue_first_events()`
def _seed_open_issues_from_requests(
	requests: list | tuple | None,
	known_repos: dict[str, tuple[str, list[Path]]],
	project_root: Path | None,
) -> tuple[dict[str, dict[int, tuple[int, int | None]]], dict[str, dict[int, int]]]:
	seeded_parents: dict[str, dict[int, tuple[int, int | None]]] = {}
	seeded_children: dict[str, dict[int, int]] = {}
	if not requests or not known_repos:
		return (seeded_parents, seeded_children)
	combined = '\n'.join(_extract_request_text(r) for r in requests if r)
	if not combined.strip():
		return (seeded_parents, seeded_children)
	explicit_refs: dict[str, set[int]] = {}
	for url in _GITHUB_ISSUE_URL_RE.findall(combined):
		parsed = parse_issue_url(url)
		if None is not parsed:
			slug_u, num_u = parsed
			if slug_u.lower() in known_repos:
				explicit_refs.setdefault(slug_u.lower(), set()).add(int(num_u))
	hash_nums = {int(m.group(1)) for m in _HASH_ISSUE_REF_RE.finditer(combined)}
	if hash_nums:
		for slug_key in known_repos:
			explicit_refs.setdefault(slug_key, set()).update(hash_nums)
	for slug_key, nums in explicit_refs.items():
		canon_slug, cand_repos = known_repos[slug_key]
		for num in sorted(nums):
			info = _load_evidence_issue_info(project_root, canon_slug, num, cand_repos)
			if None is info or 'open' != info.get('state'):
				continue
			pnum = info.get('parent_number')
			if None is pnum:
				seeded_parents.setdefault(slug_key, {})[num] = (-1, None)
			else:
				pinfo = _load_evidence_issue_info(project_root, canon_slug, pnum, cand_repos)
				if None is not pinfo and 'open' == pinfo.get('state'):
					seeded_parents.setdefault(slug_key, {})[pnum] = (-1, None)
					seeded_children.setdefault(slug_key, {})[num] = pnum
	return (seeded_parents, seeded_children)


# @used-by :func:`evaluate_issue_first_events()`
def _is_established_before(est: tuple[int, int | None], step: int, sub_step: int | None) -> bool:
	est_step, est_sub = est
	if est_step < step:
		return True
	if est_step == step and None is not est_sub and None is not sub_step and est_sub < sub_step:
		return True
	return False


# 2026-11-23
# "Implement core Issue-First verification engine in agent_tools/issue_first_gate.py":
# https://github.com/dmitry-ai/harness/issues/143
# @used-by :func:`agent_tools.completion._issue_first_status()`
# @used-by :func:`evaluate_pre_tool_use_issue_first()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_first_skips_denied_writes_and_reads_background_task_issue_actions()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_chronological_state_machine_enforces_parent_issue_before_tests_and_code()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_user_input_seeding_accepts_referenced_open_evidence_and_rejects_closed_or_unreferenced()`
def evaluate_issue_first_events(
	events: list[dict] | tuple[dict, ...] | None,
	*,
	requests: list | tuple | None = None,
	project_root: Path | None = None,
) -> dict:
	known_repos: dict[str, tuple[str, list[Path]]] = {}
	for ev in events or ():
		if not isinstance(ev, dict):
			continue
		kind = ev.get('kind')
		if 'code_write' == kind:
			slug = str(ev.get('repo_slug') or '').strip()
			rroot_raw = str(ev.get('repo_root') or '').strip()
			if slug:
				key = slug.lower()
				entry = known_repos.setdefault(key, (slug, []))
				if rroot_raw:
					rp = Path(rroot_raw).resolve()
					if rp not in entry[1]:
						entry[1].append(rp)
		elif 'issue_action' == kind:
			slug = str(ev.get('repo') or '').strip()
			if slug:
				known_repos.setdefault(slug.lower(), (slug, []))

	seeded_parents, seeded_children = _seed_open_issues_from_requests(requests, known_repos, project_root)
	repos: dict[str, dict] = {}
	violations: list[str] = []

	# @used-by :func:`evaluate_issue_first_events()`
	def _ensure_repo(slug: str, repo_root: str | None = None) -> dict:
		key = slug.lower()
		st = repos.get(key)
		if None is st:
			canon_slug = known_repos.get(key, (slug, []))[0]
			st = {
				'repo_slug': canon_slug,
				'repo_root': repo_root or '',
				'active_parents': dict(seeded_parents.get(key) or {}),
				'closed_parents': set(),
				'established_parents': sorted(seeded_parents.get(key) or ()),
				'child_to_parent': dict(seeded_children.get(key) or {}),
				'unauthorized_write_steps': [],
				'code_write_count': 0,
				'issue_action_count': 0,
			}
			repos[key] = st
		elif repo_root and (not st['repo_root']):
			st['repo_root'] = repo_root
		return st

	for ev in events or ():
		if not isinstance(ev, dict):
			continue
		kind = ev.get('kind')
		step = int(ev.get('step', 0))
		sub_step = ev.get('sub_step')
		if None is not sub_step:
			sub_step = int(sub_step)

		if 'code_write' == kind:
			slug = str(ev.get('repo_slug') or '').strip()
			if not slug:
				continue
			st = _ensure_repo(slug, str(ev.get('repo_root') or ''))
			st['code_write_count'] += 1
			rel_path = str(ev.get('rel_path') or Path(str(ev.get('path') or '')).name)
			cls = str(ev.get('classification') or 'production')
			authorized = any(
				_is_established_before(est, step, sub_step)
				for est in st['active_parents'].values()
			)
			if not authorized:
				st['unauthorized_write_steps'].append(step)
				if 'test' == cls:
					violations.append(
						f'EXEC-5 ISSUE-FIRST-GATE: Test file "{rel_path}" in {st["repo_slug"]} edited at step {step} '
						f'before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via '
						f'df_github_issue.py create --repo {st["repo_slug"]} (or fetch an existing open issue via '
						f'df_github_issue.py fetch --repo {st["repo_slug"]} --issue <N>) BEFORE developing tests or code.'
					)
				elif 'production' == cls:
					violations.append(
						f'EXEC-5 ISSUE-FIRST-GATE: Production code "{rel_path}" in {st["repo_slug"]} edited at step {step} '
						f'before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via '
						f'df_github_issue.py create --repo {st["repo_slug"]} BEFORE writing tests or production code.'
					)
				else:
					violations.append(
						f'EXEC-5 ISSUE-FIRST-GATE: Repository file "{rel_path}" in {st["repo_slug"]} edited at step {step} '
						f'before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via '
						f'df_github_issue.py create --repo {st["repo_slug"]} BEFORE editing repository files.'
					)
		elif 'issue_action' == kind:
			slug = str(ev.get('repo') or '').strip()
			num = ev.get('number')
			action = str(ev.get('action') or '').strip().lower()
			if not slug or not isinstance(num, int) or isinstance(num, bool) or not action:
				continue
			st = _ensure_repo(slug)
			st['issue_action_count'] += 1
			cand_repos = known_repos.get(slug.lower(), (slug, []))[1]
			ev_info = _load_evidence_issue_info(project_root, st['repo_slug'], num, cand_repos)
			raw_p = ev.get('parent_number')
			parent_num = int(raw_p) if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) and int(raw_p) != num else (
				ev_info.get('parent_number') if None is not ev_info else st['child_to_parent'].get(num)
			)
			raw_state = str(ev.get('state') or '').strip().lower()
			if not raw_state:
				if 'create' == action:
					raw_state = 'open'
				elif 'close' == action:
					raw_state = 'closed'
				elif None is not ev_info and ev_info.get('state'):
					raw_state = str(ev_info['state']).lower()

			if 'create' == action:
				if None is parent_num:
					if st['unauthorized_write_steps'] and (not st['active_parents']):
						first_bad = st['unauthorized_write_steps'][0]
						violations.append(
							f'EXEC-5 ISSUE-FIRST-GATE: Parent issue https://github.com/{st["repo_slug"]}/issues/{num} was created at step {step} '
							f'AFTER code/test edits already occurred at step {first_bad}. State the problem as a parent GitHub issue BEFORE writing tests or code.'
						)
					st['active_parents'][num] = (step, sub_step)
					if num not in st['established_parents']:
						st['established_parents'].append(num)
				else:
					st['child_to_parent'][num] = parent_num
					if parent_num not in st['active_parents']:
						pinfo = _load_evidence_issue_info(project_root, st['repo_slug'], parent_num, cand_repos)
						if None is not pinfo and 'open' == pinfo.get('state') and parent_num not in st['closed_parents']:
							st['active_parents'][parent_num] = (step, sub_step)
							if parent_num not in st['established_parents']:
								st['established_parents'].append(parent_num)
						elif None is not pinfo and 'closed' == pinfo.get('state'):
							violations.append(
								f'EXEC-5 ISSUE-FIRST-GATE: Child issue https://github.com/{st["repo_slug"]}/issues/{num} links to closed parent issue '
								f'#{parent_num}; open a new parent problem issue before working on new changes.'
							)
			elif action in ('fetch', 'edit', 'comment'):
				if 'open' == raw_state:
					if None is parent_num:
						if num not in st['active_parents']:
							st['active_parents'][num] = (step, sub_step)
						if num not in st['established_parents']:
							st['established_parents'].append(num)
					else:
						st['child_to_parent'][num] = parent_num
						if parent_num not in st['active_parents']:
							pinfo = _load_evidence_issue_info(project_root, st['repo_slug'], parent_num, cand_repos)
							if None is not pinfo and 'open' == pinfo.get('state') and parent_num not in st['closed_parents']:
								st['active_parents'][parent_num] = (step, sub_step)
								if parent_num not in st['established_parents']:
									st['established_parents'].append(parent_num)
			elif 'close' == action:
				if num in st['active_parents']:
					st['active_parents'].pop(num, None)
					st['closed_parents'].add(num)
				elif None is parent_num:
					st['closed_parents'].add(num)

	serialized_repos = {
		key: {
			'repo_slug': st['repo_slug'],
			'repo_root': st['repo_root'],
			'active_parents': sorted(st['active_parents'].keys()),
			'established_parents': list(st['established_parents']),
			'closed_parents': sorted(st['closed_parents']),
			'code_write_count': st['code_write_count'],
			'issue_action_count': st['issue_action_count'],
		}
		for key, st in sorted(repos.items())
	}
	return {'verified': not violations, 'repos': serialized_repos, 'violations': violations}


# @used-by :func:`evaluate_pre_tool_use_issue_first()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_first_skips_denied_writes_and_reads_background_task_issue_actions()`
def extract_antigravity_issue_first_events(transcript_path: Path, *, cwd: Path | None = None) -> tuple[list[dict], list[dict]]:
	t_path = Path(transcript_path)
	if 'transcript.jsonl' == t_path.name:
		full_sib = t_path.parent / 'transcript_full.jsonl'
		if full_sib.is_file():
			t_path = full_sib
	if not t_path.is_file():
		return ([], [])
	try:
		rows = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except (OSError, ValueError):
		return ([], [])
	last_user = -1
	for idx, row in enumerate(rows):
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
			last_user = idx
	requests: list[dict] = []
	if 0 <= last_user:
		u_row = rows[last_user]
		u_content = str(u_row.get('content') or '')
		if u_content.strip():
			requests.append({'text': u_content})
	segment = rows[last_user + 1:] if 0 <= last_user else rows
	# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
	from .issue_first_bg import extract_segment_issue_first_events
	events = extract_segment_issue_first_events(segment, cwd, build_code_write_issue_first_event, build_issue_action_events)
	return (events, requests)


# @used-by :func:`agent_tools.gates.issue_first.check()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_evaluate_pre_tool_use_issue_first_blocks_spoofing_and_enforces_live_order()`
def evaluate_pre_tool_use_issue_first(name: str, args: dict, payload: dict) -> str | None:
	cwd_raw = str(payload.get('cwd') or '').strip()
	cwd = Path(cwd_raw).resolve() if cwd_raw else None
	pending_targets: list[tuple[Path, dict]] = []
	if name in ('write_file', 'edit_file'):
		raw_p = str(args.get('Path') or '').strip()
		if not raw_p:
			return None
		cand = normalize_host_path(raw_p)
		target_path = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
		content_hint = args.get('Content') if 'write_file' == name and isinstance(args.get('Content'), str) else None
		info = resolve_issue_first_target(target_path, content=content_hint)
		if None is not info:
			pending_targets.append((target_path, info))
	elif 'run_command' == name:
		cmd = str(args.get('CommandLine') or '')
		for wt in shell_write_targets(cmd, cwd=cwd):
			info = resolve_issue_first_target(wt)
			if None is not info:
				pending_targets.append((wt, info))
	else:
		return None

	if not pending_targets:
		return None

	t_raw = str(payload.get('transcriptPath') or '').strip()
	if not t_raw:
		# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
		from .issue_first_inherit import missing_transcript_issue_first_error
		return missing_transcript_issue_first_error(pending_targets, payload, cwd)

	events, requests = extract_antigravity_issue_first_events(Path(t_raw), cwd=cwd)
	base_eval = evaluate_issue_first_events(events, requests=requests, project_root=cwd)
	next_step = max((int(e.get('step', 0)) for e in events), default=0) + 1
	for target_path, info in pending_targets:
		slug_key = info['repo_slug'].lower()
		repo_st = base_eval['repos'].get(slug_key)
		if repo_st and repo_st.get('active_parents'):
			continue
		# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
		from .issue_first_inherit import has_inherited_open_parent_issue
		pending_ev = {'kind': 'code_write', 'step': next_step, 'path': str(target_path), 'rel_path': info['rel_path'], 'repo_root': str(info['repo_root']), 'repo_slug': info['repo_slug'], 'classification': info['classification']}
		probe = evaluate_issue_first_events([*events, pending_ev], requests=requests, project_root=cwd or info['repo_root'])
		probe_st = probe['repos'].get(slug_key)
		if (probe_st and probe_st.get('active_parents')) or has_inherited_open_parent_issue(payload, info, cwd, Path(t_raw)):
			continue
		if probe['violations']:
			return probe['violations'][-1]
		return (
			f'EXEC-5 ISSUE-FIRST-GATE: Cannot edit "{info["rel_path"]}" in {info["repo_slug"]} '
			f'before establishing an open parent GitHub issue via df_github_issue.py create --repo {info["repo_slug"]} '
			f'(or df_github_issue.py fetch --repo {info["repo_slug"]} --issue <N>).'
		)
	return None
