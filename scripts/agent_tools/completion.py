# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce local_source_grounding_issues across touched client deliverables, require post-compaction re-read of evicted tool outputs, and close A.A review bypass":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate turn scratch answer files, decouple turn/journal locks, allow pre-delivery re-preparation, and add preemptive step/compaction budget gate":
# https://github.com/dmitry-ai/harness/issues/49
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce typed source provenance tiers (Tier 0/1/2), entity Tier 0 auto-discovery, and post-CHECKPOINT re-read gates":
# https://github.com/dmitry-ai/harness/issues/45
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
# https://github.com/dmitry-ai/harness/issues/30
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urldefrag, urlsplit
from . import journal
from .platforms import adapter
from .research import MAX_BYTES, _CHALLENGE_RE
from .runtime import PRIMARY, platform_name, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes
COMMANDS = ('turn-begin', 'answer-prepare', 'recover-checkpoint', 'recover-turn-violation', 'journal-sync', 'journal-watch', 'journal-unwatch', 'reconcile-unprepared-delivery')
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'), 'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'), 'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}
RULE_REQUIREMENTS = {'FILE-3': 'Before publication, the primary agent saves the exact request and complete final response via answer-prepare.', 'EXEC-5': 'Run read-only Git checks with `--no-optional-locks` to avoid updating the index as a side effect.', 'DOC-2': 'Frame any unknown or unproven explanation as a hypothesis with arguments for/against and an expert score in %.'}
def _now():
	return datetime.now(timezone.utc).isoformat()
def _hash(value):
	return hashlib.sha256(value).hexdigest()
def _json(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _read(path):
	value = json.loads(path.read_bytes().decode('utf-8'))
	if not isinstance(value, dict):
		raise ValueError('Completion metadata must be a JSON object: ' + str(path))
	r = value
	return r
def _folder(root):
	return data_dir_for(root) / 'turns'
def _turn_lock(root, key):
	return _folder(root) / f'turn-{key}.lock'
def _journal_lock(root):
	return _folder(root) / 'journal.lock'
def _directory(root, selected=None):
	root = Path(root).resolve()
	if selected:
		r = (root / selected).resolve()
	elif (root / '_/ꙮ').is_dir():
		r = (root / '_/ꙮ').resolve()
	elif (root / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').is_dir() and (not (root / 'ꙮ/1 - Analysis').is_dir()):
		r = (root / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').resolve()
	elif (root / 'ꙮ/README.md').is_file() and (not (root / 'ꙮ/1 - Analysis').is_dir()):
		r = (root / 'ꙮ').resolve()
	else:
		r = (root / 'ꙮ/1 - Analysis').resolve()
	return r
def _key(native, turn):
	identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
	r = _hash(_json(identity))[:40]
	return r
def _native(root, conversation=None, *, platform=None, backend=None):
	platform = platform_name(platform)
	conversation = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == platform else None)
	if not conversation:
		raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
	r = adapter(platform).native_answers(Path(root).resolve(), conversation, backend=backend)
	return r
def _policy():
	return {ident: {'source': relative, 'anchor': anchor, 'sha256': _hash((PRIMARY / relative).read_bytes()), 'requirement': RULE_REQUIREMENTS[ident]} for ident, (relative, anchor) in RULES.items()}
def _violation_recovery(root, key):
	if None is root or not key:
		return {}
	path = _folder(root) / f'{key}-violation-recovery.json'
	if not path.is_file():
		return {}
	try:
		return _read(path)
	except (OSError, ValueError):
		return {}
def _exec5_status(turn, root=None, key=None):
	violations = list(turn.get('exec5_violations') or [])
	rec = _violation_recovery(root, key) if violations else {}
	covered = set(rec.get('covered_exec5_steps') or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
def _http_fetch_status(turn, root=None, key=None):
	violations = list(turn.get('http_fetch_violations') or [])
	rec = _violation_recovery(root, key) if violations else {}
	covered = set(rec.get('covered_http_fetch_steps') or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
def _compaction_status(root, key, turn):
	comp = dict(turn.get('compaction') or {})
	occurred = bool(comp.get('occurred'))
	last_cp = comp.get('last_checkpoint_step')
	pre_steps = list(comp.get('pre_checkpoint_tool_steps') or [])
	post_rec = list(comp.get('post_checkpoint_recovery_steps') or [])
	pre_reads = list(comp.get('pre_checkpoint_read_files') or [])
	post_reads = list(comp.get('post_checkpoint_read_files') or [])
	post_writes = list(comp.get('post_checkpoint_written_files') or [])
	evicted_unreread = list(comp.get('evicted_unreread_files') or [])
	evicted_lower = {p.replace('\\', '/').lower(): p for p in evicted_unreread}
	unreread_analysis_sources = []
	writes_client_deliverable = False
	for w in post_writes:
		wnorm = w.replace('\\', '/')
		wlow = wnorm.lower()
		if wlow.endswith('/kb/analysis.md'):
			sib = (Path(wnorm).parent / 'source.md').as_posix()
			if sib.lower() in evicted_lower and evicted_lower[sib.lower()] not in unreread_analysis_sources:
				unreread_analysis_sources.append(evicted_lower[sib.lower()])
		elif any((seg in wlow for seg in ('/letters/', '/result/', '/defects/'))) and '/\ua616/' not in wlow and '/\ua66e/' not in wlow:
			writes_client_deliverable = True
	if writes_client_deliverable:
		for ev_l, ev_orig in evicted_lower.items():
			if ('/.system_generated/steps/' in ev_l or ev_l.endswith('/kb/source.md') or '/source/' in ev_l or '/\ua616/kb/evidence/' in ev_l) and ev_orig not in unreread_analysis_sources:
				unreread_analysis_sources.append(ev_orig)
	recovered_in_trace = bool(comp.get('recovered_in_trace', True))
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	recovered_via_receipt = False
	if receipt_path.is_file():
		try:
			rec_data = _read(receipt_path)
			cov = rec_data.get('covered_checkpoint_step')
			if None is last_cp or (isinstance(cov, int) and cov >= last_cp):
				recovered_via_receipt = True
		except (OSError, ValueError):
			pass
	verified = bool((not occurred or not pre_steps or recovered_in_trace or recovered_via_receipt) and (not unreread_analysis_sources))
	r = {'verified': verified, 'occurred': occurred, 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_steps, 'post_checkpoint_recovery_steps': post_rec, 'recovered_in_trace': recovered_in_trace, 'recovered_via_receipt': recovered_via_receipt, 'pre_checkpoint_read_files': pre_reads, 'post_checkpoint_read_files': post_reads, 'post_checkpoint_written_files': post_writes, 'evicted_unreread_files': evicted_unreread, 'unreread_analysis_sources': unreread_analysis_sources}
	return r
DEL_MAX_UNPERSISTED_STEPS = 40
DEL_MAX_UNPERSISTED_SOURCE_READS = 10
DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS = 60
DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS = 3
def _delegation_status(root, turn):
	del_info = dict(turn.get('delegation') or {})
	tool_steps = int(del_info.get('tool_step_count') or 0)
	sub_steps = int(del_info.get('subagent_step_count') or 0)
	aa_steps = int(del_info.get('aa_subagent_step_count') if 'aa_subagent_step_count' in del_info else sub_steps)
	af_steps = int(del_info.get('af_subagent_step_count') or 0)
	kb_steps = int(del_info.get('kb_persistence_step_count') or 0)
	cur_streak = int(del_info.get('unpersisted_step_streak') if 'unpersisted_step_streak' in del_info else tool_steps if 0 == sub_steps and 0 == kb_steps else 0)
	max_streak = int(del_info.get('max_unpersisted_step_streak') if 'max_unpersisted_step_streak' in del_info else cur_streak)
	max_src_reads = int(del_info.get('max_unpersisted_source_reads') or 0)
	issue_actions_count = len(turn.get('issue_actions') or [])
	aa_part_errs = list(del_info.get('aa_partial_read_violations') or [])
	is_upwork_project = (Path(root).resolve() / '\ua616/project.json').is_file()
	unpersisted_bulk = bool(is_upwork_project and ((tool_steps > DEL_MAX_UNPERSISTED_STEPS and 0 == sub_steps and 0 == kb_steps) or cur_streak > DEL_MAX_UNPERSISTED_STEPS or (max_src_reads >= DEL_MAX_UNPERSISTED_SOURCE_READS and 0 == sub_steps) or (tool_steps > DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS and 0 == sub_steps) or (issue_actions_count > DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS and 0 == sub_steps)))
	r = {'verified': not unpersisted_bulk, 'tool_step_count': tool_steps, 'subagent_step_count': sub_steps, 'aa_subagent_step_count': aa_steps, 'aa_partial_read_violations': aa_part_errs, 'af_subagent_step_count': af_steps, 'kb_persistence_step_count': kb_steps, 'issue_actions_count': issue_actions_count, 'max_unpersisted_steps': DEL_MAX_UNPERSISTED_STEPS, 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads, 'max_allowed_unpersisted_source_reads': DEL_MAX_UNPERSISTED_SOURCE_READS}
	return r
BUDGET_MAX_CHECKPOINTS = 2
BUDGET_MAX_TOOL_STEPS = 120
BUDGET_WINDOW_5H_MAX_STEPS = 400
def _budget_status(root, turn):
	comp = dict(turn.get('compaction') or {})
	del_info = dict(turn.get('delegation') or {})
	cp_count = len(comp.get('checkpoint_steps') or [])
	tool_steps = int(del_info.get('tool_step_count') or 0)
	now_ts = datetime.now(timezone.utc).timestamp()
	window_5h_steps = tool_steps
	turns_dir = _folder(root)
	cur_tid = turn.get('turn_id')
	if turns_dir.is_dir():
		for tf in turns_dir.glob('*.json'):
			if '-' in tf.stem:
				continue
			try:
				if now_ts - tf.stat().st_mtime <= 18000:
					td = _read(tf)
					if td.get('native_turn_id') != cur_tid:
						window_5h_steps += int((td.get('delegation_check') or {}).get('tool_step_count') or 0)
			except (OSError, ValueError):
				pass
	touched = [str(x).replace('\\', '/').lower() for x in (turn.get('touched_files') or [])]
	continuation_saved = any((x.endswith('/data/continuation.md') or x.endswith('\ua616/data/continuation.md') for x in touched))
	kb_saved = any(('/\ua616/kb/' in x or x.endswith('/kb/analysis.md') or x.endswith('/kb/analysis.json') for x in touched))
	exceeded = bool(cp_count >= BUDGET_MAX_CHECKPOINTS or tool_steps >= BUDGET_MAX_TOOL_STEPS or window_5h_steps >= BUDGET_WINDOW_5H_MAX_STEPS)
	r = {'verified': True, 'checkpoint_count': cp_count, 'max_checkpoints': BUDGET_MAX_CHECKPOINTS, 'tool_step_count': tool_steps, 'max_tool_steps': BUDGET_MAX_TOOL_STEPS, 'window_5h_tool_steps': window_5h_steps, 'max_window_5h_tool_steps': BUDGET_WINDOW_5H_MAX_STEPS, 'graceful_checkpoint_required': exceeded, 'continuation_saved': continuation_saved, 'kb_saved': kb_saved}
	return r
def _origin_repo_slug(code_repo: Path):
	cfg_file = Path(code_repo) / '.git/config'
	if cfg_file.is_file():
		try:
			cfg_text = cfg_file.read_text(encoding='utf-8', errors='replace')
			cm = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?/?(?:\\s|$)', cfg_text)
			if cm:
				return cm.group(1)
		except OSError:
			pass
	from .git_gate import run_git_read
	proc = run_git_read(code_repo, ['remote', 'get-url', 'origin'], check=False)
	if 0 != proc.returncode:
		return None
	remote = proc.stdout.decode('utf-8', errors='replace').strip()
	m = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?$', remote)
	return m.group(1) if m else None
def _evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()):
	from .runtime import HARNESS_META
	safe_repo = repo_slug.replace('/', '__')
	roots = [Path(root).resolve()] + [Path(r).resolve().parent for r in candidate_repos]
	ev_files = []
	for rt in roots:
		for rel in ('_/ꘖ/KB/Evidence/GitHub', 'ꘖ/KB/Evidence/GitHub'):
			p = rt / rel / safe_repo / fname
			if p.is_file() and p not in ev_files:
				ev_files.append(p)
	hm = (HARNESS_META / 'ꘖ/KB/Evidence/GitHub' / safe_repo / fname).resolve()
	if hm.is_file() and hm not in ev_files:
		ev_files.append(hm)
	return ev_files
def _evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()):
	for p in _evidence_issue_files(root, repo_slug, f'issue-{int(number)}.json', candidate_repos):
		try:
			data = json.loads(p.read_text(encoding='utf-8'))
			issue_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
			st = str(issue_obj.get('state') or '').strip().lower()
			if st:
				return st
		except (OSError, ValueError):
			continue
	return None
def _code_and_issue_lifecycle_status(root, turn, turn_state=None, response=None):
	from .git_gate import extract_issue_urls, is_code_file, is_issue_tracked_code_repo, run_git_read, verify_repo_issue_ready_for_close
	from .github_issue import _find_local_code_repo, lint_issue_markdown
	from .source_grounding import local_source_grounding_issues
	root = Path(root).resolve()
	repo_touched = {}
	for raw_p in turn.get('touched_files') or []:
		if not isinstance(raw_p, str) or not raw_p.strip():
			continue
		try:
			p = Path(raw_p.strip())
			p = p.resolve() if p.is_absolute() else (root / p).resolve()
		except OSError:
			continue
		for anc in (p, *p.parents):
			if is_issue_tracked_code_repo(anc):
				try:
					rel = p.relative_to(anc).as_posix()
				except ValueError:
					break
				if rel and rel != '.' and (not rel.startswith(('.git/', 'ꘖ/', 'ꙮ/', '_/'))):
					repo_touched.setdefault(anc, set()).add(rel)
				break
	turn_issues = {}
	gh_raw = (turn_state or {}).get('github_issues') or []
	gh_items = list(gh_raw.values()) if isinstance(gh_raw, dict) else list(gh_raw)
	for item in gh_items + list(turn.get('issue_actions') or []):
		if not isinstance(item, dict):
			continue
		url = (item.get('url') or '').strip()
		m = re.match('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$', url)
		if not m:
			continue
		slug, num = (m.group(1), int(m.group(2)))
		st = str(item.get('state') or '').strip().lower()
		act = item.get('action') or item.get('last_action')
		if 'close' == act:
			st = 'closed'
		prev_entry = turn_issues.get(url, {})
		cids = list(prev_entry.get('comment_ids') or [])
		for cid in item.get('comment_ids') or []:
			if cid not in cids:
				cids.append(cid)
		turn_issues[url] = {'url': url, 'repo': slug, 'number': num, 'state': st or prev_entry.get('state') or 'open', 'last_action': act or prev_entry.get('last_action') or 'issue', 'comment_ids': cids}
	candidate_repos = list(repo_touched.keys())
	for cand in (root, root / 'code', root.parent / 'code'):
		cand_res = cand.resolve()
		if is_issue_tracked_code_repo(cand_res) and cand_res not in candidate_repos:
			candidate_repos.append(cand_res)
	for info in turn_issues.values():
		found_repo = _find_local_code_repo(info['repo'], project_root=root)
		if None is not found_repo:
			found_res = found_repo.resolve()
			if is_issue_tracked_code_repo(found_res) and found_res not in candidate_repos:
				candidate_repos.append(found_res)
	workspace_code_repos = {c.resolve() for c in (root, root / 'code', root.parent / 'code') if is_issue_tracked_code_repo(c.resolve())}
	required_issues_by_repo = {r: set() for r in candidate_repos}
	repo_by_issue_url = {}
	for url, info in turn_issues.items():
		for cand in candidate_repos:
			slug = _origin_repo_slug(cand)
			if slug and slug.lower() == info['repo'].lower():
				repo_by_issue_url[url] = cand
				if bool(repo_touched.get(cand)) or 'close' == info.get('last_action'):
					required_issues_by_repo.setdefault(cand, set()).add(url)
					repo_touched.setdefault(cand, set())
	violations = []
	checked_issues = []
	checked_urls = set()
	if isinstance(response, str) and response.strip() and workspace_code_repos and (not repo_touched):
		has_diag_causes = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)(?:C|H)-[1-9]\\d*\\b', response))
		has_diag_methods = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)M-[1-9]\\d*\\b', response))
		has_py_targets = bool(re.search('\\b[A-Za-z0-9_/-]+\\.py\\b', response))
		if has_diag_causes and has_diag_methods and has_py_targets:
			for ws_repo in sorted(workspace_code_repos, key=str):
				ws_slug = _origin_repo_slug(ws_repo)
				if not ws_slug:
					continue
				has_ws_issue = any((info['repo'].lower() == ws_slug.lower() for info in turn_issues.values()))
				if not has_ws_issue:
					for resp_url in extract_issue_urls(response):
						m_ru = re.match('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$', resp_url)
						if m_ru and m_ru.group(1).lower() == ws_slug.lower() and _evidence_issue_files(root, m_ru.group(1), f'issue-{int(m_ru.group(2))}.json', candidate_repos):
							has_ws_issue = True
							break
				if not has_ws_issue:
					violations.append(f'EXEC-5 / SCOPE-2: Diagnostic audit of {ws_slug} identifies repository defects (C-/H-) and remediation methods (M-) without recording corresponding GitHub Issues via df_github_issue.py')
	for code_repo, rel_set in sorted(repo_touched.items(), key=lambda x: str(x[0])):
		rel_paths = sorted(rel_set)
		if rel_paths:
			st_proc = run_git_read(code_repo, ['status', '--porcelain', '-z', '--', *rel_paths], check=False)
			if 0 == st_proc.returncode and st_proc.stdout.strip(b'\x00'):
				violations.append(f'Modified files in {code_repo} are not committed: {", ".join(rel_paths)}')
			for rel in rel_paths:
				fpath = code_repo / rel
				if fpath.is_file() and is_code_file(rel):
					try:
						urls_in_file = extract_issue_urls(fpath.read_text(encoding='utf-8', errors='replace'))
					except OSError:
						urls_in_file = []
					if not urls_in_file:
						violations.append(f'Modified code file {fpath} does not reference a GitHub Issue URL')
			existing_rels = [rel for rel in rel_paths if (code_repo / rel).exists()]
			if existing_rels:
				log_proc = run_git_read(code_repo, ['log', '-n', '1', '--format=%B', '--', *existing_rels], check=False)
				commit_urls = extract_issue_urls(log_proc.stdout.decode('utf-8', errors='replace')) if 0 == log_proc.returncode else []
				if not commit_urls:
					violations.append(f'Latest commit for {", ".join(existing_rels)} in {code_repo} does not reference a GitHub Issue URL')
				for cu in commit_urls:
					required_issues_by_repo.setdefault(code_repo, set()).add(cu)
		for issue_url in sorted(required_issues_by_repo.get(code_repo, set())):
			m = re.match('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$', issue_url)
			if not m:
				continue
			slug, num = (m.group(1), int(m.group(2)))
			try:
				ready = verify_repo_issue_ready_for_close(code_repo, slug, num)
			except (ValueError, RuntimeError) as exc:
				ready = {'verified': False, 'violations': [str(exc)]}
			for v in ready.get('violations') or []:
				if v not in violations:
					violations.append(v)
			ev_state = _evidence_issue_state(root, slug, num, candidate_repos)
			eff_state = ev_state or turn_issues.get(issue_url, {}).get('state') or 'open'
			checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(code_repo), 'commit_and_push_verified': bool(ready.get('verified'))})
			checked_urls.add(issue_url)
			if 'closed' != eff_state:
				violations.append(f'GitHub issue {issue_url} remains {eff_state}; close it via df_github_issue.py close after git push before answer-prepare')
	for issue_url, info in sorted(turn_issues.items()):
		slug, num = (info['repo'], int(info['number']))
		ev_state = _evidence_issue_state(root, slug, num, candidate_repos)
		eff_state = ev_state or info.get('state') or 'open'
		if issue_url not in checked_urls:
			mapped_repo = repo_by_issue_url.get(issue_url)
			checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(mapped_repo) if mapped_repo else None, 'commit_and_push_verified': False})
			checked_urls.add(issue_url)
		iss_files = _evidence_issue_files(root, slug, f'issue-{num}.json', candidate_repos)
		if not iss_files and info.get('last_action') in ('create', 'edit'):
			violations.append(f'GitHub issue {issue_url} is missing saved API read-back Evidence JSON (issue-{num}.json)')
		container_text = None
		for p in iss_files[:1]:
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
				iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
				t_txt = str(iss_obj.get('title') or '')
				b_txt = str(iss_obj.get('body') or '')
				container_text = f'{t_txt}\n{b_txt}'.strip()
				if t_txt and ('create' == info.get('last_action') or 'edit' == info.get('last_action')):
					for err in lint_issue_markdown(t_txt, is_title=True):
						violations.append(f'GitHub issue {issue_url} title lint error ({err.get("code")}): {err.get("message")}')
				if b_txt and ('create' == info.get('last_action') or 'edit' == info.get('last_action')):
					for err in lint_issue_markdown(b_txt, is_title=False):
						violations.append(f'GitHub issue {issue_url} body lint error ({err.get("code")}): {err.get("message")}')
					for g_err in local_source_grounding_issues(root, b_txt, doc_path=p):
						violations.append(f'GitHub issue {issue_url} body grounding error: {g_err}')
			except (OSError, ValueError):
				continue
		for cid in info.get('comment_ids') or []:
			for cp in _evidence_issue_files(root, slug, f'comment-{cid}.json', candidate_repos)[:1]:
				try:
					cdata = json.loads(cp.read_text(encoding='utf-8'))
					c_body = str(cdata.get('body') or '')
					if c_body:
						for err in lint_issue_markdown(c_body, is_title=False, container_text=container_text):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} lint error ({err.get("code")}): {err.get("message")}')
						for g_err in local_source_grounding_issues(root, c_body, doc_path=cp):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} grounding error: {g_err}')
				except (OSError, ValueError):
					continue
	return {'verified': not violations, 'touched_repos': {str(k): sorted(v) for k, v in repo_touched.items()}, 'issues': checked_issues, 'violations': violations}
def _norm_url(url: str) -> str:
	r = urldefrag(url.strip())[0].rstrip('/')
	return r
def _discourse_topic_key(url: str):
	m = re.match('^https?://([^/:?#]+)/t/(?:[^/?#]+/)?(\\d+)(?:$|[/?#])', url.strip(), re.I)
	r = (m.group(1).lower(), m.group(2)) if m else None
	return r
def _is_descriptive_title_label(label: str, href: str) -> bool:
	text = (label or '').strip()
	if not text or text.lower().startswith(('http://', 'https://', 'file:')):
		r = False
	else:
		host = (urlsplit(href).hostname or '').lower()
		if text.lower() in (host, f'www.{host}'):
			r = False
		else:
			words = re.findall('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u04510-9]{2,}', text)
			if len(text.split()) < 3 or len(words) < 3 or len(text) < 15:
				r = False
			else:
				r = True
	return r
def _titles_compatible(claimed: str, observed: str) -> bool:
	c_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', claimed.lower()) if len(w) >= 3]
	o_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', observed.lower()) if len(w) >= 3]
	if not c_tokens or not o_tokens:
		r = True
	else:
		c_str = ' '.join(c_tokens)
		o_str = ' '.join(o_tokens)
		if c_str in o_str or o_str in c_str:
			r = True
		else:
			c_set, o_set = (set(c_tokens), set(o_tokens))
			overlap = len(c_set & o_set) / max(1, len(c_set))
			r = overlap >= 0.6
	return r
def _norm_quote_text(value: str) -> str:
	cleaned = re.sub('[`*_~]+', '', value or '')
	cleaned = cleaned.replace('\u00a0', ' ').replace('—', '-').replace('–', '-').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
	r = ' '.join(cleaned.split()).lower()
	return r
def _ingest_json_observations(parsed, default_host, observed_urls, observed_topics, observed_titles, observed_topic_titles, observed_texts=None):
	if not isinstance(parsed, dict):
		return
	u = parsed.get('url') or parsed.get('html_url')
	if isinstance(u, str) and u.startswith(('http://', 'https://')):
		nu = _norm_url(u)
		observed_urls.add(nu)
		if isinstance(parsed.get('title'), str) and parsed['title'].strip():
			t = ' '.join(parsed['title'].split())
			observed_titles.setdefault(nu, t)
		if None is not observed_texts:
			for field in ('body', 'text', 'title'):
				val = parsed.get(field)
				if isinstance(val, str) and val.strip():
					observed_texts.setdefault(nu, []).append(val)
	if isinstance(parsed.get('title'), str) and parsed['title'].strip():
		t = ' '.join(parsed['title'].split())
		if default_host and isinstance(parsed.get('id'), int):
			tk = (default_host.lower(), str(parsed['id']))
			observed_topics.add(tk)
			observed_topic_titles.setdefault(tk, t)
	topics = []
	if isinstance(parsed.get('topic_list'), dict) and isinstance(parsed['topic_list'].get('topics'), list):
		topics.extend(parsed['topic_list']['topics'])
	if isinstance(parsed.get('topics'), list):
		topics.extend(parsed['topics'])
	for topic in topics:
		if not isinstance(topic, dict) or not isinstance(topic.get('id'), int) or (not isinstance(topic.get('title'), str)):
			continue
		t = ' '.join(topic['title'].split())
		tid = str(topic['id'])
		host = default_host
		tu = topic.get('url')
		if isinstance(tu, str) and tu.startswith(('http://', 'https://')):
			nu = _norm_url(tu)
			observed_urls.add(nu)
			observed_titles.setdefault(nu, t)
			host = host or (urlsplit(nu).hostname or '')
		if host:
			tk = (host.lower(), tid)
			observed_topics.add(tk)
			observed_topic_titles.setdefault(tk, t)
			short_u = f'https://{host.lower()}/t/{tid}'
			observed_urls.add(short_u)
			observed_titles.setdefault(short_u, t)
			slug = topic.get('slug')
			if isinstance(slug, str) and slug:
				slug_u = f'https://{host.lower()}/t/{slug}/{tid}'
				observed_urls.add(slug_u)
				observed_titles.setdefault(slug_u, t)
def response_source_and_kb_issues(root: Path, response: str, requests: list[dict], *, touched_files=None) -> list[str]:
	from markdown_it import MarkdownIt
	from .links import readable_link_issues, _bare_urls
	from .source_grounding import _is_normative_harness_doc, local_source_grounding_issues
	root = Path(root).resolve()
	errors = list(readable_link_issues(response, allow_unencoded_file_uri=True))
	parser = MarkdownIt('commonmark', {'html': True})
	parser.normalizeLink = lambda value: value
	parser.validateLink = lambda value: True
	authored_links = []
	authored_urls = []
	attributed_quotes = []
	quote_depth = 0
	last_para_ext_href = None
	for block in parser.parse(response):
		if 'blockquote_open' == block.type:
			quote_depth += 1
			continue
		if 'blockquote_close' == block.type:
			quote_depth -= 1
			continue
		if block.type in ('fence', 'code_block'):
			last_para_ext_href = None
			continue
		if quote_depth > 0:
			if 'inline' == block.type and block.content:
				bq_ext_hrefs = []
				for tok in block.children or []:
					if 'link_open' == tok.type:
						h = tok.attrGet('href') or ''
						if h.startswith(('http://', 'https://')):
							bq_ext_hrefs.append(h)
				target_href = bq_ext_hrefs[-1] if bq_ext_hrefs else last_para_ext_href
				if target_href:
					guillemets = re.findall('«([^»]{20,})»', block.content)
					backtick_quotes = re.findall('`"([^"\\n]{20,})"`', block.content)
					if guillemets or backtick_quotes:
						for gq in guillemets + backtick_quotes:
							attributed_quotes.append((target_href, gq))
					else:
						m_orig = re.search('(?:\u041e\u0440\u0438\u0433\u0438\u043d\u0430\u043b|Original)\\s*:\\s*["«]?(.{20,})["»]?$', block.content.strip(), re.I | re.S)
						if m_orig:
							attributed_quotes.append((target_href, m_orig.group(1).strip(' "«»')))
			continue
		children = block.children or []
		if not children:
			continue
		ext_in_block = []
		has_local_link = False
		idx = 0
		while idx < len(children):
			token = children[idx]
			if 'link_open' == token.type:
				href = token.attrGet('href') or ''
				label_parts = []
				idx += 1
				depth = 1
				while idx < len(children) and depth > 0:
					inner = children[idx]
					if 'link_open' == inner.type:
						depth += 1
					elif 'link_close' == inner.type:
						depth -= 1
					elif depth > 0 and inner.type in ('text', 'code_inline'):
						label_parts.append(inner.content)
					idx += 1
				label = ' '.join(''.join(label_parts).split())
				if href.startswith(('http://', 'https://')):
					authored_links.append((label, href))
					authored_urls.append(href)
					ext_in_block.append(href)
				elif href:
					has_local_link = True
				continue
			elif 'text' == token.type:
				for u in _bare_urls(token.content):
					if u.startswith(('http://', 'https://')):
						authored_urls.append(u)
						ext_in_block.append(u)
			idx += 1
		if ext_in_block and (not has_local_link):
			last_para_ext_href = ext_in_block[-1]
			if 1 == len(ext_in_block) and block.content:
				for gq in re.findall('«([^»]{25,})»', block.content):
					attributed_quotes.append((ext_in_block[0], gq))
				for bq in re.findall('`"([^"\\n]{25,})"`', block.content):
					attributed_quotes.append((ext_in_block[0], bq))
		elif has_local_link:
			last_para_ext_href = None
	observed_texts = {}
	if authored_urls:
		observed_urls = set()
		observed_topics = set()
		observed_titles = {}
		observed_topic_titles = {}
		observed_anchors = {}
		invalid_observations = {}
		client_urls = set()
		for req in requests or []:
			for u in _bare_urls(req.get('text', '') if isinstance(req, dict) else str(req)):
				client_urls.add(_norm_url(u))
		for pfile in (root / 'ꘖ/project.json', root / 'KB/Project.md', root / 'ꘖ/KB/Project.md'):
			if pfile.is_file():
				try:
					txt = pfile.read_text(encoding='utf-8')
					for u in _bare_urls(txt):
						client_urls.add(_norm_url(u))
				except OSError:
					pass
		needs_ev_scan = any(
			_is_descriptive_title_label(label, href)
			or (
				(urlsplit(href).hostname or '').lower() not in ('localhost', '127.0.0.1', '::1')
				and _norm_url(href) not in client_urls
			)
			for label, href in authored_links
		) or any(_norm_url(href) not in client_urls for href, _ in attributed_quotes)
		ev_dirs = []
		if needs_ev_scan:
			if (root / '_/ꘖ/KB/Evidence').is_dir():
				ev_dirs.append((root / '_/ꘖ/KB/Evidence').resolve())
			elif (root / 'ꘖ/KB/Evidence').is_dir():
				ev_dirs.append((root / 'ꘖ/KB/Evidence').resolve())
		for ev_dir in ev_dirs:
			for jfile in ev_dir.rglob('*.json'):
				if jfile.name.startswith('extracted-'):
					continue
				try:
					if jfile.stat().st_size > 4 * 1024 * 1024:
						continue
					data = json.loads(jfile.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if 'observation.json' == jfile.name and isinstance(data, dict):
					urls_here = [u for u in (data.get('url'), data.get('final_url')) if isinstance(u, str) and u.startswith(('http://', 'https://'))]
					host = (urlsplit(urls_here[0]).hostname or '').lower() if urls_here else ''
					valid_status = not data.get('error') and ('dom' == data.get('kind') or 200 <= (data.get('status') or 0) < 300)
					is_shell_or_empty = False
					shell_reason = None
					ext_titles = []
					ext_anchors = set()
					ext_texts = []
					has_html_anchors = False
					ext_files = list(jfile.parent.glob('extracted-*.json'))
					for ext_file in ext_files:
						try:
							ext = json.loads(ext_file.read_text(encoding='utf-8'))
						except (OSError, ValueError):
							continue
						if not isinstance(ext, dict):
							continue
						if True is ext.get('browser_check_required'):
							is_shell_or_empty = True
							shell_reason = 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)'
						elif 'headings' in ext and None is ext.get('sitemap') and (0 == ext.get('word_count', 0)):
							is_shell_or_empty = True
							shell_reason = 'word_count=0 (empty HTML shell)'
						t = (ext.get('title') or '').strip()
						if not t and isinstance(ext.get('headings'), list):
							h1s = [h.get('text', '').strip() for h in ext['headings'] if isinstance(h, dict) and 1 == h.get('level') and h.get('text')]
							if h1s:
								t = h1s[0]
						if t:
							ext_titles.append(t)
						if isinstance(ext.get('anchors'), list):
							has_html_anchors = True
							ext_anchors.update((str(a) for a in ext['anchors'] if a))
						if isinstance(ext.get('text'), str) and ext['text'].strip():
							ext_texts.append(ext['text'])
					resp_bin = jfile.parent / 'response.bin'
					if resp_bin.is_file():
						try:
							if resp_bin.stat().st_size <= MAX_BYTES:
								raw_text = resp_bin.read_bytes().decode(data.get('charset') or 'utf-8', errors='replace')
								ctype = (data.get('content_type') or '').lower()
								is_html = 'html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html'))
								if is_html:
									if not ext_files:
										body_plain = re.sub('<(?:script|style|head|title)[^>]*>.*?</(?:script|style|head|title)>|<[^>]+>', ' ', raw_text, flags=re.I | re.S)
										if _CHALLENGE_RE.search(raw_text) or not re.findall('\\w+', body_plain):
											is_shell_or_empty = True
											shell_reason = 'unextracted HTML JS challenge or empty shell'
									has_html_anchors = True
									for m_id in re.finditer('\\b(?:id|name)=["\\\']([^"\\\']+)["\\\']', raw_text, re.I):
										ext_anchors.add(m_id.group(1))
									m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
									if m_t:
										t = ' '.join(m_t.group(1).split())
										if t:
											ext_titles.append(t)
								if raw_text.strip():
									ext_texts.append(raw_text)
								if ('json' in ctype or raw_text.lstrip().startswith('{')) and valid_status and (not is_shell_or_empty):
									_ingest_json_observations(json.loads(raw_text), host, observed_urls, observed_topics, observed_titles, observed_topic_titles, observed_texts)
						except (OSError, ValueError):
							pass
					if valid_status and (not is_shell_or_empty):
						for u in urls_here:
							nu = _norm_url(u)
							observed_urls.add(nu)
							tk = _discourse_topic_key(nu)
							if tk:
								observed_topics.add(tk)
							for t in ext_titles:
								observed_titles.setdefault(nu, t)
								if tk:
									observed_topic_titles.setdefault(tk, t)
							if has_html_anchors:
								observed_anchors.setdefault(nu, set()).update(ext_anchors)
							if ext_texts:
								observed_texts.setdefault(nu, []).extend(ext_texts)
					else:
						reason = shell_reason or f"error={data.get('error')} status={data.get('status')}"
						for u in urls_here:
							nu = _norm_url(u)
							invalid_observations.setdefault(nu, reason)
				elif isinstance(data, dict) and (not jfile.name.startswith('extracted-')):
					src_u = data.get('url') or data.get('html_url') or data.get('source') or ''
					host = (urlsplit(src_u).hostname or '').lower() if isinstance(src_u, str) and src_u.startswith(('http://', 'https://')) else ''
					_ingest_json_observations(data, host, observed_urls, observed_topics, observed_titles, observed_topic_titles, observed_texts)
		for label, href in authored_links:
			if not _is_descriptive_title_label(label, href):
				continue
			nu = _norm_url(href)
			tk = _discourse_topic_key(nu)
			obs_title = observed_titles.get(nu) or (observed_topic_titles.get(tk) if tk else None)
			if obs_title and (not _titles_compatible(label, obs_title)):
				errors.append(f'VERIFY-1 / LINK-1: Link title "{label}" for {href} contradicts saved observation title "{obs_title}"')
		is_upwork_project = (root / 'ꘖ/project.json').is_file() and (root / 'ꘖ/KB').is_dir()
		if is_upwork_project:
			kb_urls = set(client_urls)
			kb_topics = set()
			for kb_file in list((root / 'ꘖ/KB').rglob('*.md')) + (list((root / 'KB').rglob('*.md')) if (root / 'KB').is_dir() else []):
				try:
					txt = kb_file.read_text(encoding='utf-8')
				except OSError:
					continue
				for u in _bare_urls(txt):
					nu = _norm_url(u)
					kb_urls.add(nu)
					tk = _discourse_topic_key(nu)
					if tk:
						kb_topics.add(tk)
			analysis_file = root / 'ꘖ/KB/Analysis.json'
			if analysis_file.is_file():
				try:
					txt = analysis_file.read_text(encoding='utf-8')
					for u in _bare_urls(txt):
						nu = _norm_url(u)
						kb_urls.add(nu)
						tk = _discourse_topic_key(nu)
						if tk:
							kb_topics.add(tk)
				except OSError:
					pass
			for u in dict.fromkeys(authored_urls):
				nu = _norm_url(u)
				tk = _discourse_topic_key(nu)
				if nu not in kb_urls and (not tk or tk not in kb_topics):
					errors.append(f'KB-1 / KB-3: External URL in response is missing from ꘖ/KB modules/Analysis.json (record verified sources in ꘖ/KB before answer-prepare): {u}')
		for label, href in authored_links:
			host = (urlsplit(href).hostname or '').lower()
			if host in ('localhost', '127.0.0.1', '::1'):
				continue
			nu = _norm_url(href)
			tk = _discourse_topic_key(nu)
			if nu in client_urls:
				continue
			if nu not in observed_urls and (not tk or tk not in observed_topics):
				if nu in invalid_observations:
					errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no valid saved observation in ꘖ/KB/Evidence ({invalid_observations[nu]})')
				else:
					errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no saved observation in ꘖ/KB/Evidence/HTTP or ꘖ/KB/Evidence')
				continue
			frag = urlsplit(href).fragment
			if frag and (not re.fullmatch('L\\d+(?:-L?\\d+)?', frag)) and (nu in observed_anchors):
				unquoted_frag = unquote(frag)
				if frag not in observed_anchors[nu] and unquoted_frag not in observed_anchors[nu] and ('anchor_exception' not in response):
					errors.append(f'VERIFY-1 / LINK-2: External link [{label}]({href}) references anchor "#{frag}" which is absent from the saved observation in ꘖ/KB/Evidence')
		for href, q_raw in attributed_quotes:
			nu = _norm_url(href)
			if nu in client_urls or nu not in observed_texts or (not observed_texts[nu]):
				continue
			obs_blob = ' '.join((_norm_quote_text(t) for t in observed_texts[nu]))
			segments = [_norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[…\\]|\\(…\\)|\\.{3,}|…', q_raw)]
			segments = [s for s in segments if len(s) >= 15]
			if segments and (not any((s in obs_blob for s in segments))):
				preview = ' '.join(q_raw.split())[:80]
				errors.append(f'VERIFY-1 / LINK-1: Verbatim quote «{preview}» attributed to {href} is absent from the saved observation in \ua616/KB/Evidence')
	grounding_cache = {}
	for iss in local_source_grounding_issues(root, response, observed_texts=observed_texts, cache=grounding_cache):
		if iss not in errors:
			errors.append(iss)
	for tf in touched_files or []:
		tf_str = str(tf).strip()
		tf_norm = '/' + tf_str.replace('\\', '/').lower().lstrip('/')
		if (
			not tf_str
			or not tf_norm.endswith('.md')
			or '/req/' in tf_norm
			or '/res/' in tf_norm
			or '/source/' in tf_norm
			or tf_norm.endswith('/source.md')
			or _is_normative_harness_doc(Path(tf_norm))
		):
			continue
		try:
			tf_path = Path(tf_str)
			tf_path = tf_path.resolve() if tf_path.is_absolute() else (root / tf_path).resolve()
			if tf_path.is_file():
				tf_text = tf_path.read_text(encoding='utf-8', errors='replace')
				for iss in local_source_grounding_issues(root, tf_text, doc_path=tf_path, observed_texts=observed_texts, cache=grounding_cache):
					msg = f'{tf_path.name} ({tf_path.parent.parent.name}): {iss}'
					if msg not in errors:
						errors.append(msg)
		except OSError:
			pass
	r = errors
	return r
def _instruction_snapshot(root, native, *, stage):
	from .configuration import _project_rule_paths
	root = Path(root).resolve()
	sources = {path: 'canonical' for path in sorted((PRIMARY / 'rules').glob('*.md'))}
	sources.update({PRIMARY / 'runtime.json': 'runtime', PRIMARY / 'platforms' / (native['platform'] + '.md'): 'adapter'})
	errors = []
	manifest = root / '.agents/rules.json'
	if manifest.exists():
		sources[manifest] = 'project-registration'
	try:
		sources.update({path: 'project-rule' for path in _project_rule_paths(root, PRIMARY)})
	except (OSError, ValueError) as exc:
		errors.append(str(exc))
	if 'codex' == native['platform']:
		workspace = Path(settings()['workspace_root']).resolve()
		folders = [root]
		if root.is_relative_to(workspace):
			folders += [parent for parent in root.parents if parent == workspace or parent.is_relative_to(workspace)]
		folders.append(Path(native['native_backend']))
		for folder in folders:
			for name in ('AGENTS.md', 'AGENTS.override.md'):
				path = folder / name
				if path.is_file():
					sources[path] = 'native-guidance-candidate'
	files = []
	for path, kind in sorted(sources.items(), key=lambda item: str(item[0])):
		try:
			files.append({'path': str(path.resolve()), 'kind': kind, 'sha256': _hash(path.read_bytes())})
		except OSError as exc:
			errors.append(str(exc))
	r = {'captured_at': _now(), 'capture_stage': stage, 'sources': files, 'errors': errors, 'selection_verified': False, 'delivery_to_model_verified': False}
	return r
def _new(root, native, turn, *, recovered=False, journal_directory=None):
	key = _key(native, turn)
	lifecycle = {'verified': True, 'touched_repos': {}, 'issues': [], 'violations': []} if recovered else _code_and_issue_lifecycle_status(root, turn)
	r = {'schema_version': 1, 'key': key, 'project_root': str(Path(root).resolve()), 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'], 'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary', 'journal_required': True, 'journal': str(_directory(root, journal_directory)), 'applicable_rules': _policy(), 'git_optional_locks_env': os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0'), 'exec5_check': _exec5_status(turn, root, key), 'http_fetch_check': _http_fetch_status(turn, root, key), 'compaction_check': _compaction_status(root, key, turn), 'delegation_check': _delegation_status(root, turn), 'budget_check': _budget_status(root, turn), 'code_lifecycle_check': lifecycle, 'instruction_snapshot': _instruction_snapshot(root, native, stage='recovery' if recovered else 'turn-begin'), 'format_independent': True, 'rule_comprehension_verified': False, 'required_completion': ['answer-prepare', 'native-delivery-check'], 'status': 'open', 'prepared': None, 'delivery': None, 'recovered_after_delivery': recovered, 'created_at': _now()}
	return r
def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
	key = _key(native, turn)
	path = _folder(root) / (key + '.json')
	value = _read(path) if path.exists() else _new(root, native, turn, recovered=recovered, journal_directory=journal_directory)
	active_validation = not recovered and not (turn.get('completed') and value.get('status') in ('delivered', 'conflict'))
	if 'instruction_snapshot' not in value and active_validation:
		value['instruction_snapshot'] = _instruction_snapshot(root, native, stage='existing-state-upgrade')
	if 'applicable_rules' not in value:
		value['applicable_rules'] = _policy()
	if 'git_optional_locks_env' not in value:
		value['git_optional_locks_env'] = os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
	for name, check in (('exec5_check', lambda: _exec5_status(turn, root, key)), ('http_fetch_check', lambda: _http_fetch_status(turn, root, key)), ('compaction_check', lambda: _compaction_status(root, key, turn)), ('delegation_check', lambda: _delegation_status(root, turn)), ('budget_check', lambda: _budget_status(root, turn))):
		if active_validation or name not in value:
			value[name] = check()
	if active_validation:
		value['code_lifecycle_check'] = _code_and_issue_lifecycle_status(root, turn, value)
	elif 'code_lifecycle_check' not in value:
		value['code_lifecycle_check'] = {'verified': True, 'touched_repos': {}, 'issues': [], 'violations': []}
	if value.get('readiness_check', {}).get('verified') is False and (not value.get('admission_failure')):
		rc_detail = str(value.get('readiness_check', {}).get('detail') or '')
		resolved_gate = (
			(rc_detail.startswith('EXEC-5 violation in active turn (git read') and value.get('exec5_check', {}).get('verified'))
			or (rc_detail.startswith('KB-3 / EXEC-1 violation') and value.get('http_fetch_check', {}).get('verified'))
			or (rc_detail.startswith('COMPACT-1 / KB-3 violation') and value.get('compaction_check', {}).get('verified'))
			or (rc_detail.startswith('REVIEW-1 / KB-3 violation') and value.get('delegation_check', {}).get('verified'))
			or (rc_detail.startswith('EXEC-5 violation in active turn (code/issue') and value.get('code_lifecycle_check', {}).get('verified'))
			or (rc_detail.startswith(('TEXT-1:', 'FILE-3 / REVIEW-1:')) and value.get('language_and_stub_check', {}).get('verified'))
			or (rc_detail.startswith(('VERIFY-1', 'LINK-', 'KB-1 / KB-3:')) and value.get('source_kb_check', {}).get('verified'))
		)
		if resolved_gate and all((value.get(k, {}).get('verified', True) for k in ('exec5_check', 'http_fetch_check', 'compaction_check', 'delegation_check', 'code_lifecycle_check', 'language_and_stub_check', 'source_kb_check'))):
			value.pop('readiness_check', None)
	saved_directory = _directory(root, value['journal'])
	if strict_journal and None is not journal_directory and (saved_directory != _directory(root, journal_directory)):
		raise ValueError('The native turn already has a different journal; preserve its original binding')
	value['journal'] = str(saved_directory)
	for name, expected in [('project_root', str(Path(root).resolve())), ('platform', native['platform']), ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']), ('native_turn_id', turn['turn_id'])]:
		if value.get(name) != expected:
			raise ValueError('Completion state has a different native owner; preserved')
	old, current = (value['requests'], turn['requests'])
	if current[:len(old)] != old:
		raise ValueError('Native requests changed before the saved boundary; preserved')
	if not (value.get('prepared') and current != old):
		value['requests'] = current
		r = (path, value)
	else:
		if not allow_extended:
			raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
		value['uncovered_requests'] = current[len(old):]
		r = (path, value)
	return r
def _persist(path, value):
	if path.exists() and _read(path) == value:
		return
	value['updated_at'] = _now()
	replace_bytes(path, _json(value))
def _active(native):
	if not native['primary']:
		r = None
	else:
		turn = next((turn for turn in native['turns'] if turn['turn_id'] == native['active_turn_id']), None)
		if None is turn or not turn['owned'] or turn['aborted']:
			raise ValueError('No active native user turn belonging entirely to this project')
		r = turn
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def begin(root, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		r = {'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
	else:
		with locked(_turn_lock(root, _key(native, turn))):
			path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
			_persist(path, value)
		result = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), 'role': 'primary', 'journal_required': True, 'status': value['status'], 'native_requests_sha256': _hash(_json(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': value['compaction_check'], 'delegation_check': value['delegation_check'], 'budget_check': value['budget_check'], 'code_lifecycle_check': value['code_lifecycle_check'], 'rule_comprehension_verified': False, 'required_completion': value['required_completion']}
		result['execution_mode'] = 'foreground-only'
		if any((t.get('owned') and t.get('completed') and (not t.get('aborted')) and (t.get('start_step', 0) <= turn['start_step']) for t in native.get('turns', []))):
			try:
				result['native_reconciliation'] = sync(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'], journal_directory=value['journal'])
				current = next((item for item in result['native_reconciliation']['turns'] if item['turn_key'] == value['key']), None)
				if current:
					result['status'] = current['status']
			except (OSError, ValueError, sqlite3.Error) as exc:
				result['native_reconciliation'] = {'valid': False, 'error': str(exc)}
		r = result
	return r
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def recover_checkpoint(root, conversation=None, *, platform=None, backend=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	comp = dict(turn.get('compaction') or {})
	raw_records = list(comp.get('pre_checkpoint_records') or [])
	rec_dir = _folder(root) / f'{key}-recovery'
	rec_dir.mkdir(parents=True, exist_ok=True)
	stdout_records = []
	compact_mode = len(raw_records) > 5
	for rec in raw_records:
		st = rec.get('step')
		outs = list(rec.get('outputs') or [])
		step_file = rec_dir / f'step-{st}.txt'
		if outs:
			replace_bytes(step_file, ('\n--- OUTPUT ---\n'.join(outs) + '\n').encode('utf-8'))
		rel_step = step_file.relative_to(root).as_posix() if step_file.is_relative_to(root) else str(step_file)
		if compact_mode:
			stdout_records.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step if outs else None, 'output_preview': [o[:200] for o in outs[:2]]})
		else:
			stdout_records.append({**rec, 'output_file': rel_step if outs else None})
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	receipt = {'turn_key': key, 'recovered_at': _now(), 'compact_mode': compact_mode, 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'pre_checkpoint_tool_steps': list(comp.get('pre_checkpoint_tool_steps') or []), 'pre_checkpoint_read_files': list(comp.get('pre_checkpoint_read_files') or []), 'post_checkpoint_read_files': list(comp.get('post_checkpoint_read_files') or []), 'evicted_unreread_files': list(comp.get('evicted_unreread_files') or []), 'recovery_dir': rec_dir.relative_to(root).as_posix() if rec_dir.is_relative_to(root) else str(rec_dir), 'pre_checkpoint_records': raw_records}
	with locked(_turn_lock(root, key)):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		value.pop('admission_failure', None)
		_persist(path, value)
	r = {**receipt, 'pre_checkpoint_records': stdout_records, 'recovery_file': receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path), 'compaction_check': value['compaction_check']}
	return r
def recover_turn_violation(root, conversation=None, *, reason=None, platform=None, backend=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	exec5_v = list(turn.get('exec5_violations') or [])
	http_v = list(turn.get('http_fetch_violations') or [])
	receipt_path = _folder(root) / f'{key}-violation-recovery.json'
	receipt = {'turn_key': key, 'recovered_at': _now(), 'reason': (reason or 'Retrospective turn violation acknowledged for journal completion').strip(), 'covered_exec5_steps': [item.get('step') for item in exec5_v if None is not item.get('step')], 'covered_http_fetch_steps': [item.get('step') for item in http_v if None is not item.get('step')], 'exec5_violations': exec5_v, 'http_fetch_violations': http_v}
	with locked(_turn_lock(root, key)):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		_persist(path, value)
	r = {**receipt, 'recovery_file': receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path), 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check']}
	return r
def _norm_journal_text(text: str) -> str:
	return _strip_local_file_scheme((text or '').replace('\r\n', '\n'))
def _find_orphan_or_overwritten_steps(directory: Path, requests: list[str], response: str, native_ids: list[str]):
	n = len(requests or [])
	req_dir, res_dir = (directory / 'req', directory / 'res')
	if 0 == n or (not req_dir.is_dir()) or (not res_dir.is_dir()):
		return (None, None, None)
	norm_reqs = [_norm_journal_text(r) for r in requests]
	norm_resp = _norm_journal_text(response)
	groups_dir = journal.state_dir(directory) / 'answer-groups'
	claimed_by_step = {}
	if groups_dir.is_dir():
		for g_file in groups_dir.glob('*.json'):
			try:
				g_val = _read(g_file)
				for st in g_val.get('steps') or []:
					if type(st) is int:
						claimed_by_step[st] = g_val
			except (OSError, ValueError):
				continue
	pair_ids = sorted({int(p.stem) for p in req_dir.glob('*.md') if p.stem.isascii() and p.stem.isdigit() and (res_dir / p.name).is_file()})
	pair_set = set(pair_ids)
	overwritten_conflict = None
	for start in pair_ids:
		cand_steps = list(range(start, start + n))
		if not all((st in pair_set for st in cand_steps)):
			continue
		try:
			disk_reqs = [(req_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
			disk_resps = [(res_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
		except (OSError, UnicodeDecodeError):
			continue
		if len(set(disk_resps)) != 1:
			continue
		if [_norm_journal_text(x) for x in disk_reqs] != norm_reqs or _norm_journal_text(disk_resps[0]) != norm_resp:
			continue
		if all((st not in claimed_by_step and (not (journal.state_dir(directory) / f'{st}.json').exists()) for st in cand_steps)):
			return (cand_steps, disk_reqs, disk_resps[0])
		for st in cand_steps:
			owner = claimed_by_step.get(st)
			if owner and owner.get('request_ids') != native_ids:
				o_steps = owner.get('steps') or []
				o_reqs = owner.get('requests') or []
				o_sha = owner.get('response_sha256')
				matches_owner = o_steps == cand_steps and len(o_reqs) == len(cand_steps) and all((d_req == o_req for d_req, o_req in zip(disk_reqs, o_reqs))) and (_hash(disk_resps[0].encode('utf-8')) == o_sha)
				if not matches_owner and None is overwritten_conflict:
					overwritten_conflict = (cand_steps, owner.get('turn'))
	if None is not overwritten_conflict:
		c_steps, o_turn = overwritten_conflict
		raise ValueError(f'Journal step(s) {c_steps} match this native turn but are claimed by another answer group ({o_turn}); preserve the conflict')
	return (None, None, None)
def _group(root, native, turn, response, directory, *, allow_reprepare=False):
	key = 'native-' + _key(native, turn)
	legacy = turn['turn_id']
	groups = journal.state_dir(directory) / 'answer-groups'
	native_ids = [r['id'] for r in turn['requests']]
	norm_turn_reqs = [_norm_journal_text(r['text']) for r in turn['requests']]
	norm_turn_resp = _norm_journal_text(response)
	matches = []
	for file in groups.glob('*.json'):
		old = _read(file)
		if old.get('request_ids') == native_ids:
			old_reqs = old.get('requests') or []
			reqs_ok = old_reqs == [r['text'] for r in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
			resp_ok = old.get('response_sha256') == _hash(response.encode('utf-8'))
			if not resp_ok and old.get('steps'):
				res_p = directory / 'res' / f"{old['steps'][0]}.md"
				if res_p.is_file():
					try:
						disk_r = res_p.read_bytes().decode('utf-8')
						resp_ok = _hash(disk_r.encode('utf-8')) == old.get('response_sha256') and _norm_journal_text(disk_r) == norm_turn_resp
					except (OSError, UnicodeDecodeError):
						pass
			if not reqs_ok or (not resp_ok and not allow_reprepare):
				raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
			matches.append(old)
	if len(matches) > 1:
		raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
	if matches:
		return (matches[0]['turn'], native_ids)
	if re.fullmatch('[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
		old = _read(groups / (legacy + '.json'))
		old_reqs = old.get('requests') or []
		reqs_ok = old_reqs == [r['text'] for r in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
		if not reqs_ok or (old.get('response_sha256') != _hash(response.encode('utf-8')) and not allow_reprepare):
			raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
		return (legacy, old.get('request_ids'))
	return (key, native_ids)
def _recorded(value):
	return next((receipt for receipt in (value.get('prepared'), value.get('journal_record'), value.get('delivery')) if isinstance(receipt, dict) and 'journal_steps' in receipt), None)
def _strip_code_and_urls(text: str) -> str:
	clean = re.sub('```[\\s\\S]*?```', ' ', text or '')
	clean = re.sub('`[^`\\n]+`', ' ', clean)
	clean = re.sub('https?://\\S+', ' ', clean)
	return clean
def _intermediate_or_language_issues(requests, response: str) -> list[str]:
	from .source_grounding import detect_prose_locale, extract_authored_prose
	issues = []
	if re.search('(?i)(?:^|\\n)\\s*waiting\\s+for\\s+(?:the\\s+)?(?:remaining\\s+)?(?:\\d+\\s+)?(?:subagents?|background\\s+tasks?|tasks?|commands?)\\b[^\\n]{0,120}\\bto\\s+(?:complete|finish)\\b', response or ''):
		issues.append('FILE-3 / REVIEW-1: Response is an intermediate subagent/task waiting status stub rather than a complete final response')
	req_raw = '\n'.join((r.get('text', '') if isinstance(r, dict) else str(r) for r in requests or []))
	req_info = detect_prose_locale(extract_authored_prose(req_raw))
	resp_info = detect_prose_locale(extract_authored_prose(response or ''))
	english_requested = bool(re.search('(?i)\\b(?:in\\s+english|translate\\s+to\\s+english|\\u043d\\u0430\\s+\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u043e\\u043c|\\u043f\\u043e-\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u0438)\\b', req_raw))
	req_script = req_info['dominant_script']
	if req_script not in ('NONE', 'LATIN') and req_info['script_counts'].get(req_script, 0) >= 6 and (not english_requested):
		resp_target_chars = resp_info['script_counts'].get(req_script, 0)
		if 0 == resp_target_chars and resp_info['total_alpha'] >= 20:
			issues.append(f'TEXT-1: Request dominant script is {req_script}, but the response authored prose contains zero {req_script} characters (dominant: {resp_info["dominant_script"]})')
	return issues
def _record(root, native, turn, response, directory, *, existing=None, purpose='publication', allow_reprepare=False):
	if purpose not in ('publication', 'observation'):
		raise ValueError('Choose publication admission or historical observation')
	directory = _directory(root, directory)
	from . import admission
	token, request_ids = _group(root, native, turn, response, directory, allow_reprepare=allow_reprepare)
	group_file = journal.state_dir(directory) / 'answer-groups' / (token + '.json')
	already_complete = group_file.exists() and 'complete' == _read(group_file).get('status')
	if not already_complete or allow_reprepare:
		lang_issues = _intermediate_or_language_issues(turn['requests'], response)
		if lang_issues:
			raise ValueError('; '.join(lang_issues))
	if existing:
		if not already_complete:
			raise ValueError('Recorded answer-group receipt is missing or incomplete; preserve journal history')
		if _read(group_file).get('steps') != existing['journal_steps']:
			raise ValueError('Recorded answer-group steps changed; preserve journal history')
	effective_requests = [r['text'] for r in turn['requests']]
	effective_response = response
	adopt_steps = None
	adopted_existing = False
	reprepared_before_delivery = False
	if already_complete:
		g_data = _read(group_file)
		g_reqs = g_data.get('requests') or []
		if [_norm_journal_text(x) for x in g_reqs] == [_norm_journal_text(x) for x in effective_requests]:
			effective_requests = list(g_reqs)
		if g_data.get('steps') and _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256'):
			res_p = directory / 'res' / f"{g_data['steps'][0]}.md"
			if res_p.is_file():
				try:
					disk_r = res_p.read_bytes().decode('utf-8')
					if _hash(disk_r.encode('utf-8')) == g_data.get('response_sha256') and _norm_journal_text(disk_r) == _norm_journal_text(effective_response):
						effective_response = disk_r
				except (OSError, UnicodeDecodeError):
					pass
			if _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256') and allow_reprepare:
				reprepared_before_delivery = True
	elif None is existing:
		adopt_steps, disk_reqs, disk_resp = _find_orphan_or_overwritten_steps(directory, effective_requests, effective_response, request_ids)
		if None is not adopt_steps:
			effective_requests = disk_reqs
			effective_response = disk_resp
			adopted_existing = True
	identity = admission.binding(directory, effective_requests, effective_response, token, request_ids)
	if already_complete and not reprepared_before_delivery:
		if purpose == 'publication':
			from .text_workflow import gate_requests
			gate_requests([root, directory], effective_requests, effective_response)
		steps = journal.verify_answer(directory, effective_requests, effective_response, token, request_ids)
		proof = _read(group_file).get('admission')
		if existing and existing.get('admission') != proof:
			raise ValueError('Recorded admission differs from the original answer group; preserve history')
		verification = admission.verify(proof, identity) if proof else {'status': 'legacy_proof_gap', 'scope': 'journal_and_native_identity_only'}
	else:
		capability = admission.capture([root, directory], effective_requests, effective_response, identity)
		steps = journal.record_answer(directory, effective_requests, effective_response, token, request_ids, adopt_steps=adopt_steps, admission=capability, allow_reprepare=reprepared_before_delivery)
		proof = capability.reference
		verification = {'status': 'verified', 'scope': 'original_publication_admission' if purpose == 'observation' else 'current_publication_readiness'}
	for step, request in zip(steps, effective_requests):
		if (directory / 'req' / f'{step}.md').read_bytes() != request.encode('utf-8'):
			raise ValueError('Recorded request read-back differs from native text')
		if (directory / 'res' / f'{step}.md').read_bytes() != effective_response.encode('utf-8'):
			raise ValueError('Recorded response read-back differs from prepared text')
	recorded = {'journal_steps': steps, 'response_sha256': _hash(effective_response.encode('utf-8')), 'response_file': str(directory / 'res' / f'{steps[0]}.md'), 'group_file': str(group_file)}
	if existing:
		if any((existing.get(name) != expected for name, expected in recorded.items())):
			raise ValueError('Recorded answer receipt differs from its verified journal identity; preserve history')
		if existing.get('group_sha256') and existing['group_sha256'] != _hash(group_file.read_bytes()):
			raise ValueError('Recorded answer-group bytes changed; preserve history')
		return dict(existing), verification
	res_receipt = {**recorded, 'group_sha256': _hash(group_file.read_bytes()), 'recorded_at': _now(), 'reused_complete_journal_group': bool((already_complete and not reprepared_before_delivery) or adopted_existing), 'admission': proof}
	if reprepared_before_delivery:
		res_receipt['reprepared_before_delivery'] = True
	return res_receipt, verification
def _unchanged(root, native, turn):
	latest = _native(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'])
	current = _active(latest)
	if None is current or _key(latest, current) != _key(native, turn) or current['requests'] != turn['requests']:
		raise ValueError('The active native turn or requests changed during preparation; readiness was not granted')
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None):
	if not isinstance(response, str) or not response.strip():
		raise ValueError('An exact nonempty UTF-8 final response is required')
	from .causal_checks import unsupported_probability_claims
	issues = unsupported_probability_claims(response)
	if issues:
		raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
	result = begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory)
	if not result['journal_required']:
		raise ValueError('A child executor cannot prepare the primary user journal')
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn or _key(native, turn) != result['turn_key'] or _hash(_json(turn['requests'])) != result['native_requests_sha256']:
		raise ValueError('The active native turn changed during preparation; no answer was recorded')
	with locked(_turn_lock(root, result['turn_key'])):
		_unchanged(root, native, turn)
		path, value = _state(root, native, turn)
		if 'delivered' == value['status']:
			recorded = _recorded(value)
			if not recorded or recorded['response_sha256'] != _hash(response.encode('utf-8')):
				raise ValueError('Delivered response bytes are immutable; preserve the completed turn')
			if not turn.get('completed') or value['delivery'].get('native_response_sha256') != _hash(turn['response'].encode('utf-8')):
				raise ValueError('The saved native delivery requires foreground reconciliation before preparation')
			recorded, admission_check = _record(root, native, turn, response, value['journal'], existing=recorded, purpose='observation')
			return {**result, **recorded, 'ready': True, 'status': 'delivered', 'delivery_verified': True, 'preparation_verified': value['delivery'].get('preparation_verified', False), 'admission_verification': admission_check}
		if not value['exec5_check']['verified']:
			commands = [cmd for item in value['exec5_check']['violations'] for cmd in item.get('commands', [])]
			detail = 'EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if not value['http_fetch_check']['verified']:
			commands = [cmd for item in value['http_fetch_check']['violations'] for cmd in item.get('commands', [])]
			detail = 'KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection; use collect/collect-http or run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if not value['compaction_check']['verified']:
			unreread_src = value['compaction_check'].get('unreread_analysis_sources') or []
			if unreread_src:
				detail = 'COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread_src)
			else:
				detail = 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare'
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if value['compaction_check'].get('occurred') and value['compaction_check'].get('evicted_unreread_files'):
			scratch_ans = root / f'\ua616/data/scratch/answer-{result["turn_key"]}.md'
			post_cp_w_low = {str(w).replace('\\', '/').lower() for w in (value['compaction_check'].get('post_checkpoint_written_files') or [])}
			pre_cp_authored = False
			if scratch_ans.is_file() and scratch_ans.resolve().as_posix().lower() not in post_cp_w_low:
				try:
					pre_cp_authored = scratch_ans.read_text(encoding='utf-8') == response
				except OSError:
					pre_cp_authored = False
			if not pre_cp_authored:
				from markdown_it import MarkdownIt
				from .source_grounding import _extract_block_links
				ev_map = {p.replace('\\', '/').lower(): p for p in value['compaction_check']['evicted_unreread_files']}
				unreread_cited = []
				md_parser = MarkdownIt('commonmark', {'html': True})
				md_parser.normalizeLink = lambda v: v
				md_parser.validateLink = lambda v: True
				for blk in md_parser.parse(response):
					if 'inline' == blk.type:
						lpaths, _ = _extract_block_links(blk, root, None)
						for rp in lpaths:
							rlow = rp.as_posix().lower()
							if rlow in ev_map and (rlow.endswith('/kb/source.md') or '/source/' in rlow or '/res/' in rlow or '/kb/' in rlow) and (ev_map[rlow] not in unreread_cited):
								unreread_cited.append(ev_map[rlow])
				for ev_low, ev_orig in ev_map.items():
					m_res = re.search('/res/(\\d+\\.md)$', ev_low)
					if m_res and re.search(f'\\bres/{re.escape(m_res.group(1))}\\b', response, re.I) and (ev_orig not in unreread_cited):
						unreread_cited.append(ev_orig)
				if unreread_cited:
					detail = 'COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(unreread_cited)
					value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
					_persist(path, value)
					raise ValueError(detail)
		if not value['delegation_check']['verified']:
			detail = f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={value['delegation_check']['tool_step_count']}, max_streak={value['delegation_check'].get('max_unpersisted_step_streak', 0)} > {value['delegation_check']['max_unpersisted_steps']}, or unpersisted_source_reads={value['delegation_check'].get('max_unpersisted_source_reads', 0)} >= {value['delegation_check'].get('max_allowed_unpersisted_source_reads', 10)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence"
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		value['code_lifecycle_check'] = _code_and_issue_lifecycle_status(root, turn, value, response=response)
		if not value['code_lifecycle_check']['verified']:
			detail = 'EXEC-5 violation in active turn (code/issue lifecycle incomplete): ' + '; '.join(value['code_lifecycle_check']['violations'])
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		lang_issues = _intermediate_or_language_issues(turn['requests'], response)
		value['language_and_stub_check'] = {'verified': not lang_issues, 'issues': lang_issues}
		if lang_issues:
			detail = '; '.join(lang_issues)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		sha = _hash(response.encode('utf-8'))
		allow_reprepare = False
		if value['prepared'] and value['prepared']['response_sha256'] != sha:
			if None is not value.get('delivery') or 'delivered' == value.get('status') or turn.get('completed'):
				raise ValueError('Prepared response bytes are immutable after delivery; preserve the earlier version and reconcile before a corrective turn')
			allow_reprepare = True
		if 'conflict' == value['status']:
			raise ValueError('Resolve the native delivery conflict without overwriting journal history')
		aa_part_errs = value['delegation_check'].get('aa_partial_read_violations') or []
		if aa_part_errs:
			detail = 'REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(aa_part_errs)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		workflow = root / '\ua616/data/workflow.json'
		wf_state = None
		wf_identifiers = set()
		wf_covered = set()
		is_finalized = False
		has_substantive_hm = False
		if workflow.exists():
			from .workflow import load
			wf_state = load(root)
			wf_identifiers = {r['id'] for r in turn['requests']}
			wf_covered = {r['id'] for r in wf_state['requests']} & wf_identifiers
			is_finalized = wf_state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
			has_normative_kb_mutation = False
			has_analysis_kb_mutation = False
			factual_kb_issues = []
			from .knowledge import validate_kb_factual_note
			for tf in turn.get('touched_files') or []:
				tf_norm = str(tf).replace('\\', '/').lower()
				if ('/\ua616/kb/' in tf_norm or tf_norm.endswith('/kb/analysis.md') or tf_norm.endswith('/kb/analysis.json')) and '/\ua616/kb/evidence/' not in tf_norm:
					basename = Path(tf).name.lower()
					if basename in ('analysis.md', 'analysis.json'):
						has_analysis_kb_mutation = True
						has_normative_kb_mutation = True
					elif basename in ('project.md', 'projects.md'):
						has_normative_kb_mutation = True
					else:
						fpath = Path(tf)
						if not fpath.is_absolute():
							fpath = root / fpath
						if fpath.is_file():
							try:
								note_text = fpath.read_text(encoding='utf-8', errors='replace')
								issues = validate_kb_factual_note(fpath, note_text)
								if issues:
									factual_kb_issues.extend(issues)
							except OSError:
								pass
			if factual_kb_issues:
				detail = 'KB-2 / DOC-1 violation in factual research note: ' + '; '.join(factual_kb_issues)
				value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
				_persist(path, value)
				raise ValueError(detail)
			has_kb_or_issue_mutation = has_normative_kb_mutation or bool(turn.get('issue_actions')) or bool(value.get('github_issues'))
			touches_client_deliverable = any((any((seg in str(tf).replace('\\', '/').lower() for seg in ('/letters/', '/result/', '/defects/'))) and '/\ua616/' not in str(tf).replace('\\', '/').lower() for tf in (turn.get('touched_files') or [])))
			has_hm_tags = bool(re.search('\\b(?:H|M)-(?:[A-Za-z0-9]+-)*\\d+\\b', response))
			if is_finalized:
				has_substantive_hm = has_analysis_kb_mutation or (has_hm_tags and 0 == value['delegation_check'].get('aa_subagent_step_count', 0))
			else:
				has_substantive_hm = has_hm_tags or has_kb_or_issue_mutation or touches_client_deliverable
			if wf_covered and wf_covered != wf_identifiers:
				raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
			if not wf_covered and (root / '\ua616/project.json').is_file() and (not any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', r.get('text', '')) for r in turn['requests']))) and (not is_finalized or has_substantive_hm):
				detail = 'REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project'
				value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
				_persist(path, value)
				raise ValueError(detail)
		source_issues = response_source_and_kb_issues(root, response, turn['requests'], touched_files=turn.get('touched_files'))
		value['source_kb_check'] = {'verified': not source_issues, 'issues': source_issues}
		if source_issues:
			detail = '; '.join(source_issues)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		recorded_early = False
		if not workflow.exists() or is_finalized:
			try:
				value['prepared'], admission_check = _record(root, native, turn, response, value['journal'], existing=None if allow_reprepare else _recorded(value), allow_reprepare=allow_reprepare)
				recorded_early = True
			except (OSError, ValueError) as exc:
				value['admission_failure'] = {'detail': str(exc), 'checked_at': _now()}
				value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': str(exc)}
				_persist(path, value)
				raise
			value.pop('admission_failure', None)
		if None is not wf_state and wf_covered:
			if not is_finalized or has_substantive_hm:
				from .review import authorize
				try:
					authorize(root, wf_state, response=response, request_ids=wf_identifiers)
				except (OSError, ValueError) as exc:
					value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': str(exc)}
					_persist(path, value)
					raise
				pending = {r['id'] for r in wf_state['requests'] if not r.get('response_prepared') and (r.get('native_conversation_id') in (None, native['conversation_id']) or r['id'] in wf_identifiers)}
				if pending:
					if pending != wf_identifiers:
						raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
					from .workflow import record_current_answer
					record_current_answer(root, response, journal_directory=value['journal'], request_ids=wf_identifiers)
				elif any((r['response_prepared']['sha256'] != sha for r in wf_state['requests'] if r['id'] in wf_identifiers)):
					if not allow_reprepare:
						raise ValueError('Tracked analysis requests already have different prepared response bytes')
					from .workflow import update
					def update_reprepared(s):
						for req in s.get('requests', []):
							if req['id'] in wf_identifiers:
								req['response_prepared'] = {'sha256': sha, 'prepared_at': _now()}
					update(root, {'action': 'reprepare_before_delivery', 'request_ids': sorted(wf_identifiers)}, update_reprepared)
			else:
				from .workflow import update
				def change(s):
					for req in s.get('requests', []):
						if req['id'] in wf_identifiers and (not req.get('response_prepared') or allow_reprepare):
							req['response_prepared'] = {'sha256': sha, 'prepared_at': _now()}
				update(root, {'action': 'post_finalize_answer', 'request_ids': sorted(wf_identifiers)}, change)
		if not recorded_early:
			try:
				value['prepared'], admission_check = _record(root, native, turn, response, value['journal'], existing=None if allow_reprepare else _recorded(value), allow_reprepare=allow_reprepare)
			except (OSError, ValueError) as exc:
				value['admission_failure'] = {'detail': str(exc), 'checked_at': _now()}
				value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': str(exc)}
				_persist(path, value)
				raise
			value.pop('admission_failure', None)
		try:
			_unchanged(root, native, turn)
		except (OSError, ValueError, sqlite3.Error) as exc:
			value['status'] = 'preparation_unverified'
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': str(exc)}
			_persist(path, value)
			raise
		value['status'] = 'prepared'
		if not value.get('readiness_check', {}).get('verified'):
			value['readiness_check'] = {'verified': True, 'checked_at': _now()}
		_persist(path, value)
	return {**result, **value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False, 'admission_verification': admission_check}
def _conflict(root, path, value, native, turn, response, detail, *, retryable=False):
	payload = response.encode('utf-8')
	evidence = _folder(root) / 'conflicts' / (value['key'] + '-' + _hash(payload) + '.txt')
	evidence.parent.mkdir(parents=True, exist_ok=True)
	if evidence.exists() and evidence.read_bytes() != payload:
		raise ValueError('Immutable native conflict evidence changed')
	if not evidence.exists():
		create_bytes(evidence, payload)
	if _recorded(value):
		value['journal_record'] = _recorded(value)
	prior_verified = value.get('delivery') if (value.get('delivery') or {}).get('verified') else value.get('prior_verified_delivery')
	if prior_verified:
		value['prior_verified_delivery'] = deepcopy(prior_verified)
	value['status'] = 'conflict'
	value['delivery'] = {'verified': False, 'native_response_sha256': _hash(payload), 'source_file': native['source_file'], 'final_step': turn['final_step'], 'native_requests': turn['requests'], 'conflict_evidence': evidence.relative_to(root).as_posix(), 'detail': detail, 'retryable': retryable}
	_persist(path, value)
	r = {'turn_key': value['key'], 'status': 'conflict', 'detail': detail, 'evidence': evidence.relative_to(root).as_posix(), 'retryable': retryable}
	return r
def _strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None, adopt_conflict=False):
	if type(from_step) is not int or from_step < 0:
		raise ValueError('Native from-step must be a nonnegative integer')
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	if not native['primary']:
		raise ValueError('A child executor has no primary user journal to synchronize')
	if not any((turn['owned'] for turn in native['turns'])):
		raise ValueError('Native conversation has no user turns owned by this project')
	eligible = [turn for turn in native['turns'] if turn['owned'] and turn['completed'] and (not turn['aborted']) and (turn['start_step'] >= from_step)]
	if not eligible:
		return {'valid': True, 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': [], 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
	results = []
	with locked(_journal_lock(root)):
		for turn in eligible:
			with locked(_turn_lock(root, _key(native, turn))):
				path, value = _state(root, native, turn, recovered=True, allow_extended=True, journal_directory=journal_directory)
				response = turn['response']
				sha = _hash(response.encode('utf-8'))
				if value.get('uncovered_requests') and not adopt_conflict:
					results.append(_conflict(root, path, value, native, turn, response, 'Prepared answer does not cover newly received native requests'))
					continue
				if not _recorded(value) and (value.get('admission_failure') or value.get('readiness_check', {}).get('verified') is False) and not adopt_conflict:
					results.append(_conflict(root, path, value, native, turn, response, 'A prior preparation/admission gate failed; recovery cannot grant publication approval'))
					continue
				try:
					effective_response = response
					if value['prepared'] and value['prepared']['response_sha256'] != sha:
						prep_file = Path(value['prepared'].get('response_file') or '')
						prep_text = prep_file.read_bytes().decode('utf-8') if prep_file.is_file() else ''
						if prep_text and _norm_journal_text(prep_text) == _norm_journal_text(response):
							effective_response = prep_text
						elif not adopt_conflict:
							results.append(_conflict(root, path, value, native, turn, response, 'Prepared and delivered response bytes differ'))
							continue
					elif not value['prepared']:
						j_dir = _directory(root, value['journal'])
						req_ids = [r['id'] for r in turn['requests']]
						for g_file in (journal.state_dir(j_dir) / 'answer-groups').glob('*.json'):
							g_val = _read(g_file)
							if g_val.get('request_ids') == req_ids and g_val.get('steps'):
								res_path = j_dir / 'res' / f"{g_val['steps'][0]}.md"
								res_text = res_path.read_bytes().decode('utf-8') if res_path.is_file() else ''
								if res_text and _norm_journal_text(res_text) == _norm_journal_text(response):
									effective_response = res_text
								break
					recorded, admission_check = _record(root, native, turn, effective_response, value['journal'], existing=_recorded(value), purpose='observation')
				except (OSError, ValueError) as exc:
					results.append(_conflict(root, path, value, native, turn, response, str(exc), retryable=isinstance(exc, OSError) and (not isinstance(exc, FileNotFoundError))))
					continue
				if admission_check['status'] == 'legacy_proof_gap' and value['status'] in ('delivered', 'conflict'):
					results.append({'turn_key': value['key'], 'status': value['status'], 'delivery_verified': bool(value.get('delivery', {}).get('verified')), 'journal_steps': recorded['journal_steps'], 'completion_provenance': value.get('delivery', {}).get('completion_provenance'), 'preparation_verified': value.get('delivery', {}).get('preparation_verified', False), 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check})
					continue
				if adopt_conflict:
					value.pop('admission_failure', None)
					if (value.get('delivery') or {}).get('conflict_evidence'):
						conflict_file = root / value['delivery']['conflict_evidence']
						if conflict_file.is_file():
							try:
								conflict_file.unlink()
							except OSError:
								pass
				if not _recorded(value):
					value['recovered_after_delivery'] = not bool(value['prepared']) and (not recorded['reused_complete_journal_group'])
				if adopt_conflict:
					value['recovered_after_delivery'] = True
				provenance = 'prepared' if value['prepared'] and not adopt_conflict else 'recovered_native' if value['recovered_after_delivery'] else 'existing_journal'
				preparation_verified = bool(value['prepared']) and value.get('readiness_check', {}).get('verified', True) and not adopt_conflict
				value['journal_record'] = recorded
				delivery = {**recorded, 'verified': True, 'source_file': native['source_file'], 'final_step': turn['final_step'], 'completion_step': turn['completion_step'], 'native_response_sha256': sha, 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'exec5_check': value['exec5_check']}
				previous_delivery = value.get('delivery') or {}
				prior_verified = value.get('prior_verified_delivery') or {}
				if 'delivered' == value['status'] and all((previous_delivery.get(name) == expected for name, expected in delivery.items())):
					delivery = previous_delivery
				elif prior_verified and all((prior_verified.get(name) == expected for name, expected in delivery.items() if name != 'verified_at')):
					delivery = prior_verified
				else:
					delivery['verified_at'] = _now()
				value.pop('prior_verified_delivery', None)
				value['delivery'] = delivery
				value['status'] = 'delivered'
				if adopt_conflict:
					value['readiness_check'] = {'verified': True, 'checked_at': _now(), 'detail': 'Adopted into journal via --adopt-conflict'}
				_persist(path, value)
				results.append({'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True, 'journal_steps': recorded['journal_steps'], 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check})
	return {'valid': not any(('conflict' == r['status'] for r in results)), 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': results, 'retryable': any((r.get('retryable') for r in results)), 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def reconcile_unprepared_delivery(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
	return sync(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=True)
def add_parser_arguments(parser, command):
	if 'journal-watch' == command:
		parser.add_argument('--action', choices=('start', 'status', 'stop', 'once', 'run'), default='status')
		parser.add_argument('--state-dir', type=Path)
		parser.add_argument('--interval', type=float, default=5)
		parser.add_argument('--token', help='Internal watcher ownership token')
		parser.add_argument('--dry-run', action='store_true')
		return
	parser.add_argument('project', type=Path)
	parser.add_argument('--conversation', help='Actual current native conversation UUID; Codex can use CODEX_THREAD_ID')
	if 'recover-turn-violation' == command:
		parser.add_argument('--reason', help='Audit note for retrospective turn violation recovery')
	if command not in ('journal-unwatch', 'recover-checkpoint', 'recover-turn-violation'):
		parser.add_argument('--journal', type=Path, help='User-selected journal; otherwise preserve the turn binding or use ꙮ/1 - Analysis')
	if command in ('turn-begin', 'answer-prepare'):
		parser.add_argument('--no-watch', action='store_true', help='Compatibility option; all completion operations are foreground-only')
	if 'answer-prepare' == command:
		parser.add_argument('--response-file', type=Path, required=True, help='Exact UTF-8 final response, or - for stdin')
		parser.add_argument('--consume-input', action='store_true')
		parser.add_argument('--expected-sha256', help='Optional expected SHA-256 hex digest of response file')
	if command in ('journal-sync', 'reconcile-unprepared-delivery'):
		parser.add_argument('--from-step', type=int, default=0)
	if 'journal-sync' == command:
		parser.add_argument('--adopt-conflict', action='store_true', help='Adopt turns that experienced preparation or admission failures into the journal as recovered deliveries')
def execute(args):
	if 'turn-begin' == args.command:
		r = begin(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal)
	elif 'recover-checkpoint' == args.command:
		r = recover_checkpoint(args.project, args.conversation)
	elif 'recover-turn-violation' == args.command:
		r = recover_turn_violation(args.project, args.conversation, reason=args.reason)
	elif 'answer-prepare' == args.command:
		from .operations import _operation_input, _consumed
		payload = _operation_input(args, args.response_file)
		result = prepare(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal)
		r = _consumed(args, args.response_file, payload, result)
	elif 'reconcile-unprepared-delivery' == args.command:
		r = reconcile_unprepared_delivery(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal)
	elif 'journal-sync' == args.command:
		r = sync(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal, adopt_conflict=getattr(args, 'adopt_conflict', False))
	elif 'journal-unwatch' == args.command:
		from .journal_watch import unregister
		native = _native(args.project, args.conversation)
		if not native['primary'] or not any((turn['owned'] for turn in native['turns'])):
			raise ValueError('Only the owned primary conversation can remove its watcher binding')
		r = unregister(args.project, native)
	elif 'journal-watch' != args.command:
		raise ValueError('Unknown completion operation')
	else:
		from . import journal_watch
		if 'run' == args.action:
			r = journal_watch.run(state_dir=args.state_dir, token=args.token, interval=args.interval)
		elif 'once' == args.action:
			r = journal_watch.once(state_dir=args.state_dir, dry_run=args.dry_run)
		else:
			r = getattr(journal_watch, args.action)(state_dir=args.state_dir)
	return r
