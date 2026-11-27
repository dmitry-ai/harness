# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from Df.Core.lib.array.first import df_first
from Df.Harness.Tdd.CommentDiff import CommentDiff
from Df.Harness.Tdd.RatchetGuard import RatchetGuard
from agent_tools.shell_audit import normalize_commit_message, normalize_host_path, parse_issue_url
from agent_tools.storage import locked, replace_bytes
import json
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.mechanical`
class MechanicalExemption:
	__MECH_SLOP_RE = re.compile(r'(?i)\b(?:bypass|skip|avoid|circumvent)\s+(?:the\s+)?(?:tdd|tests?|testing|gate|hook)\b')
	__MECH_SUFFIX = '-mechanical-exempt.json'
	# @used-by :meth:`MechanicalExemption.__collect_recipe_files()`
	@staticmethod
	def __candidate_recipe_dirs(project_root: Path | None, repo_root: Path | None) -> list[Path]:
		dirs: list[Path] = []
		for base in (project_root, repo_root):
			if None is not base:
				for td in RatchetGuard.turn_receipt_dirs(Path(base)):
					if td not in dirs:
						dirs.append(td)
		try:
			from agent_tools.path_registry import project_paths
			from agent_tools.runtime import PRIMARY
			prim_td = project_paths(PRIMARY).turns_dir
			if prim_td not in dirs:
				dirs.append(prim_td)
		except (OSError, ValueError, ImportError):
			pass
		return [d for d in dirs if d.is_dir()]
	# @used-by :meth:`MechanicalExemption.find_matching_recipes()`
	@staticmethod
	def __collect_recipe_files(project_root: Path | None, repo: Path) -> list[Path]:
		return [rf for td in MechanicalExemption.__candidate_recipe_dirs(project_root, repo) for rf in sorted(td.glob(f'*{MechanicalExemption.__MECH_SUFFIX}'))]
	# @used-by :meth:`MechanicalExemption.__line_matches_recipe()`
	@staticmethod
	def __compile_recipe_regex(recipe: dict) -> re.Pattern[str] | None:
		pat = str(recipe.get('pattern') or '')
		if not pat:
			r = None
		else:
			flags = re.IGNORECASE if recipe.get('ignore_case') else 0
			raw_pat = pat if recipe.get('is_regex') else re.escape(pat)
			try:
				r = re.compile(raw_pat, flags)
			except re.error:
				r = None
		return r
	# @used-by :meth:`MechanicalExemption.__line_matches_partial()`
	@staticmethod
	def __consume_partial_match(m: re.Match[str], old_line: str, new_line: str, pos: int, npos: int, repl: str, is_rx: bool) -> tuple[int, int, bool, bool]:
		gap = old_line[pos:m.start()]
		if not new_line.startswith(gap, npos):
			r = (pos, npos, False, False)
		else:
			npos += len(gap)
			orig_tok = m.group(0)
			repl_tok = m.expand(repl) if is_rx else repl
			if new_line.startswith(repl_tok, npos):
				r = (m.end(), npos + len(repl_tok), True, repl_tok != orig_tok)
			elif new_line.startswith(orig_tok, npos):
				r = (m.end(), npos + len(orig_tok), True, False)
			else:
				r = (pos, npos, False, False)
		return r
	# @used-by :meth:`MechanicalExemption.is_git_file_exempt()`
	@staticmethod
	def __is_last_commit_exempt(repo: Path, rel_posix: str, *, project_root: Path | None) -> bool:
		sha_raw = CommentDiff.git_read_text(repo, ['log', '-n', '1', '--format=%H', '--', f':(literal){rel_posix}'])
		sha = (sha_raw or '').strip()
		if not sha:
			r = False
		else:
			prev_txt = CommentDiff.git_read_text(repo, ['show', f'{sha}^:{rel_posix}'])
			curr_txt = CommentDiff.git_read_text(repo, ['show', f'{sha}:{rel_posix}'])
			msg = CommentDiff.git_read_text(repo, ['log', '-n', '1', '--format=%B', sha])
			r = MechanicalExemption.is_mechanical_diff_exempt(prev_txt, curr_txt, repo_root=repo, message=msg, project_root=project_root)
		return r
	# @used-by :meth:`MechanicalExemption.__line_matches_recipe()`
	@staticmethod
	def __line_matches_partial(old_line: str, new_line: str, compiled: re.Pattern[str], repl: str, is_rx: bool) -> bool:
		matches = list(compiled.finditer(old_line))
		pos, npos, ok, changed = (0, 0, bool(matches), False)
		for m in matches:
			pos, npos, step_ok, step_chg = MechanicalExemption.__consume_partial_match(m, old_line, new_line, pos, npos, repl, is_rx)
			changed = changed or step_chg
			if not step_ok:
				ok = False
				break
		return ok and changed and (new_line[npos:] == old_line[pos:])
	# @used-by :meth:`MechanicalExemption.matches_any_recipes()`
	@staticmethod
	def __line_matches_recipe(old_line: str, new_line: str, recipe: dict) -> bool:
		compiled = MechanicalExemption.__compile_recipe_regex(recipe)
		if None is compiled:
			r = False
		else:
			repl = str(recipe.get('replacement') or '')
			is_rx = bool(recipe.get('is_regex'))
			sub_val = compiled.sub(repl if is_rx else (lambda _m: repl), old_line)
			r = True if (sub_val == new_line and old_line != new_line) else MechanicalExemption.__line_matches_partial(old_line, new_line, compiled, repl, is_rx)
		return r
	# @used-by :meth:`MechanicalExemption.find_matching_recipes()`
	# @used-by :meth:`MechanicalExemption.record_exemption()`
	@staticmethod
	def __load_recipe_entries(rf: Path) -> list[dict]:
		r: list[dict] = []
		try:
			data = json.loads(rf.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			data = None
		raw = data.get('recipes') if isinstance(data, dict) else data
		if isinstance(raw, list):
			r = [item for item in raw if isinstance(item, dict)]
		return r
	# @used-by :meth:`MechanicalExemption.is_git_file_exempt()`
	@staticmethod
	def __read_disk_text(fpath: Path) -> str | None:
		return fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None
	# @used-by :meth:`MechanicalExemption.find_matching_recipes()`
	@staticmethod
	def __recipe_matches_repo(item: dict, repo_posix: str, repo_slug: str | None, msg_norm: str | None) -> bool:
		iss_url = str(item.get('issue_url') or '').strip()
		ok_reason = MechanicalExemption.validate_reason(str(item.get('reason') or ''))[0]
		if None is parse_issue_url(iss_url) or (not ok_reason) or (msg_norm and iss_url != msg_norm):
			r = False
		else:
			item_root = str(item.get('repo_root') or '').replace('\\', '/').rstrip('/').lower()
			item_slug = str(item.get('repo_slug') or '').strip().lower()
			r = (bool(item_root) and item_root == repo_posix.rstrip('/').lower()) or (bool(item_slug) and bool(repo_slug) and item_slug == repo_slug.lower())
		return r
	# @used-by :meth:`MechanicalExemption.__resolve_repo_binding()`
	@staticmethod
	def __resolve_existing_repo(cand: Path, issue_slug: str) -> tuple[str, str]:
		from agent_tools.issue_lifecycle import origin_repo_slug
		resolved = cand.resolve()
		detected = origin_repo_slug(resolved)
		if detected and detected.lower() != issue_slug.lower():
			raise ValueError(f'Repository origin {detected} does not match issue repository {issue_slug}')
		return (resolved.as_posix(), detected or issue_slug)
	# @used-by :meth:`MechanicalExemption.record_exemption()`
	@staticmethod
	def __resolve_repo_binding(repo: str | Path | None, issue_slug: str) -> tuple[str, str]:
		raw = str(repo or '').strip()
		if not raw:
			r = ('', issue_slug)
		else:
			cand = normalize_host_path(raw)
			if cand.exists():
				r = MechanicalExemption.__resolve_existing_repo(cand, issue_slug)
			elif '/' in raw and ('\\' not in raw) and (':' not in raw):
				if raw.lower() != issue_slug.lower():
					raise ValueError(f'Repository slug {raw} does not match issue repository {issue_slug}')
				r = ('', raw)
			else:
				r = (cand.as_posix(), issue_slug)
		return r
	# @used-by :meth:`MechanicalExemption.record_exemption()`
	@staticmethod
	def __resolve_turn_key(root_p: Path, turn_key: str | None, conversation: str | None) -> str:
		if turn_key and str(turn_key).strip():
			r = str(turn_key).strip()
		else:
			from agent_tools import completion as comp
			native = comp._native(root_p, conversation)
			turn = comp._active(native)
			if None is turn:
				raise ValueError('No active primary native turn to record mechanical TDD exemption')
			r = comp._key(native, turn)
		return r
	# @used-by :meth:`MechanicalExemption.record_exemption()`
	@staticmethod
	def __validate_recipe_inputs(issue_url: str, pattern: str, replacement: str, reason: str, is_regex: bool, ignore_case: bool) -> str:
		parsed = parse_issue_url((issue_url or '').strip())
		if None is parsed:
			raise ValueError('Provide a valid --issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
		if not pattern:
			raise ValueError('Provide a non-empty --pattern')
		if (not is_regex) and pattern == replacement:
			raise ValueError('Literal --pattern and --replacement cannot be identical')
		if is_regex:
			try:
				re.compile(pattern, re.IGNORECASE if ignore_case else 0)
			except re.error as exc:
				raise ValueError(f'Invalid regular expression in --pattern: {exc}') from exc
		ok_r, err_r = MechanicalExemption.validate_reason(reason)
		if not ok_r:
			raise ValueError(str(err_r))
		return parsed[0]
	# @used-by :func:`agent_tools.tdd.mechanical.find_matching_mechanical_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__resolve_range_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_shell_prod_writes()`
	# @used-by :meth:`MechanicalExemption.is_git_file_exempt()`
	# @used-by :meth:`MechanicalExemption.is_mechanical_diff_exempt()`
	@staticmethod
	def find_matching_recipes(repo_root: Path | None, *, message: str | None=None, project_root: Path | None=None) -> list[dict]:
		r: list[dict] = []
		if None is not repo_root:
			repo = Path(repo_root).resolve()
			r_files = MechanicalExemption.__collect_recipe_files(project_root, repo)
			if r_files:
				from agent_tools.issues.repo_locator import _extract_config_slugs
				repo_posix = repo.as_posix()
				slugs = _extract_config_slugs(repo) if (repo / '.git').exists() else []
				repo_slug = df_first(slugs)
				msg_norm = normalize_commit_message(message) if None is not message else None
				for rf in r_files:
					r.extend((it for it in MechanicalExemption.__load_recipe_entries(rf) if MechanicalExemption.__recipe_matches_repo(it, repo_posix, repo_slug, msg_norm)))
		return r
	# @used-by :func:`agent_tools.tdd.mechanical.is_git_file_mechanical_exempt()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_mechanical_exemption_clean_disk_and_last_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def is_git_file_exempt(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
		repo = Path(repo_root).resolve()
		recipes = MechanicalExemption.find_matching_recipes(repo, message=message, project_root=project_root)
		if not recipes:
			r = False
		else:
			cur = disk_text if None is not disk_text else (CommentDiff.git_read_text(repo, ['show', f':{rel_posix}']) if use_index else MechanicalExemption.__read_disk_text(repo / rel_posix))
			if None is cur:
				r = False
			else:
				head = CommentDiff.git_read_text(repo, ['show', f'HEAD:{rel_posix}'])
				r = MechanicalExemption.matches_any_recipes(head, cur, recipes) if None is not head and head != cur else MechanicalExemption.__is_last_commit_exempt(repo, rel_posix, project_root=project_root)
		return r
	# @used-by :func:`agent_tools.tdd.mechanical.is_mechanical_diff_exempt()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_text_diff()`
	# @used-by :meth:`MechanicalExemption.__is_last_commit_exempt()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def is_mechanical_diff_exempt(old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
		recipes = MechanicalExemption.find_matching_recipes(repo_root, message=message, project_root=project_root)
		return bool(recipes) and MechanicalExemption.matches_any_recipes(old_text, new_text, recipes)
	# @used-by :func:`agent_tools.tdd.mechanical.matches_any_mechanical_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_modified_entry()`
	# @used-by :meth:`MechanicalExemption.is_git_file_exempt()`
	# @used-by :meth:`MechanicalExemption.is_mechanical_diff_exempt()`
	# @used-by :meth:`MechanicalExemption.matches_recipe()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
	@staticmethod
	def matches_any_recipes(old_text: str | None, new_text: str | None, recipes: list[dict] | tuple[dict, ...]) -> bool:
		if None is old_text or None is new_text:
			r = False
		elif old_text == new_text:
			r = True
		else:
			old_lines, new_lines = (old_text.splitlines(keepends=True), new_text.splitlines(keepends=True))
			r = (len(old_lines) == len(new_lines)) and all((ol == nl or any((MechanicalExemption.__line_matches_recipe(ol, nl, rec) for rec in recipes)) for ol, nl in zip(old_lines, new_lines)))
		return r
	# @used-by :func:`agent_tools.tdd.mechanical.matches_mechanical_recipe()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_diff_executability_and_coverage()`
	@staticmethod
	def matches_recipe(old_text: str | None, new_text: str | None, recipe: dict) -> bool:
		return MechanicalExemption.matches_any_recipes(old_text, new_text, (recipe,))
	# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_mechanical_exemption_clean_disk_and_last_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def record_exemption(project_root: str | Path, *, repo: str | Path | None=None, issue_url: str, pattern: str, replacement: str, reason: str, is_regex: bool=False, ignore_case: bool=False, conversation: str | None=None, turn_key: str | None=None) -> dict:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		issue_slug = MechanicalExemption.__validate_recipe_inputs(issue_url, pattern, replacement, reason, is_regex, ignore_case)
		root_p = canonicalize_root_dir(project_root)
		key = MechanicalExemption.__resolve_turn_key(root_p, turn_key, conversation)
		repo_root_str, repo_slug = MechanicalExemption.__resolve_repo_binding(repo, issue_slug)
		reason_clean = ' '.join((reason or '').strip().split())
		entry = {'ignore_case': bool(ignore_case), 'is_regex': bool(is_regex), 'issue_url': issue_url.strip(), 'pattern': pattern, 'reason': reason_clean, 'recorded_at': datetime.now(timezone.utc).isoformat(), 'replacement': replacement, 'repo_root': repo_root_str, 'repo_slug': repo_slug}
		t_dir = project_paths(root_p).turns_dir
		t_dir.mkdir(parents=True, exist_ok=True)
		rc_path = t_dir / f'{key}{MechanicalExemption.__MECH_SUFFIX}'
		with locked(t_dir / f'turn-{key}.lock'):
			items = [it for it in (MechanicalExemption.__load_recipe_entries(rc_path) if rc_path.is_file() else []) if (it.get('issue_url'), it.get('pattern'), it.get('repo_slug')) != (entry['issue_url'], entry['pattern'], entry['repo_slug'])]
			items.append(entry)
			replace_bytes(rc_path, (json.dumps({'recipes': items, 'turn_key': key}, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
		return {'issue_url': entry['issue_url'], 'pattern': pattern, 'receipt_file': rc_path.as_posix(), 'recipes': items, 'replacement': replacement, 'repo_slug': repo_slug, 'turn_key': key, 'valid': True}
	# @used-by :func:`agent_tools.tdd.mechanical.validate_mechanical_reason()`
	# @used-by :meth:`MechanicalExemption.__recipe_matches_repo()`
	# @used-by :meth:`MechanicalExemption.__validate_recipe_inputs()`
	@staticmethod
	def validate_reason(reason: str) -> tuple[bool, str | None]:
		cleaned = ' '.join((reason or '').strip().split())
		if 30 > len(cleaned):
			r: tuple[bool, str | None] = (False, 'Mechanical TDD exemption reason must be at least 30 characters explaining the requested mechanical replacement.')
		elif MechanicalExemption.__MECH_SLOP_RE.search(cleaned):
			r = (False, 'Mechanical TDD exemption reason cannot be a TDD-bypass excuse; explain the specific mechanical replacement scope.')
		else:
			r = (True, None)
		return r
