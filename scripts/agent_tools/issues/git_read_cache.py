# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
import subprocess
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Core.lib.fs import df_path_suffix
_LOG_MAX_COUNT = 100
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
# @used-by :func:`_parse_diff_changed_urls()`
def _extract_diff_header_path(line: str) -> str:
	raw = line[4:].split('\t', 1)[0].strip().replace('\\', '/')
	return '' if '/dev/null' == raw else raw
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
# @used-by :meth:`RepoReadCache._tracked_diff_urls()`
# @used-by :meth:`RepoReadCache.dirty_referencing_issue()`
def _file_urls(fpath: Path, extract_urls_fn) -> set[str]:
	try:
		r = set(extract_urls_fn(fpath.read_text(encoding='utf-8', errors='replace')))
	except OSError:
		r = set()
	return r
# @used-by :meth:`RepoReadCache._dirty_entries()`
# @used-by :meth:`RepoReadCache._load_log()`
# @used-by :meth:`RepoReadCache._tracked_diff_urls()`
# @used-by :meth:`RepoReadCache.find_commit_for_issue()`
# @used-by :meth:`RepoReadCache.latest_commit_urls_for_files()`
# @used-by :meth:`RepoReadCache.upstream_unpushed()`
def _git_read(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	return subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], capture_output=True, env=env, check=False, creationflags=_NO_WINDOW)
# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_iter_untracked_files()`
# @used-by :meth:`RepoReadCache.dirty_referencing_issue()`
def _effective_suffix(path: str | Path) -> str:
	return df_path_suffix(path)
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
# @used-by :meth:`RepoReadCache.dirty_referencing_issue()`
def _iter_untracked_files(resolved: Path, rel_path: str, suffixes: frozenset[str]) -> list[tuple[str, Path]]:
	fpath = resolved / rel_path
	if fpath.is_file():
		r = [(rel_path, fpath)] if _effective_suffix(fpath) in suffixes else []
	elif fpath.is_dir():
		r = sorted(((p.relative_to(resolved).as_posix(), p) for p in fpath.rglob('*') if p.is_file() and _effective_suffix(p) in suffixes))
	else:
		r = []
	return r
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
# @used-by :meth:`RepoReadCache._tracked_diff_urls()`
def _parse_diff_changed_urls(diff_text: str, extract_urls_fn) -> dict[str, set[str]]:
	changed: dict[str, set[str]] = {}
	cur_path, prev_minus = ('', '')
	for line in (diff_text or '').splitlines():
		if line.startswith('--- '):
			prev_minus = _extract_diff_header_path(line)
		elif line.startswith('+++ '):
			plus_path = _extract_diff_header_path(line)
			cur_path = plus_path if plus_path else prev_minus
		elif cur_path and line.startswith(('+', '-')):
			urls = extract_urls_fn(line[1:])
			if urls:
				changed.setdefault(cur_path, set()).update(urls)
	return changed
# @used-by :meth:`RepoReadCache._load_log()`
def _parse_log_index(raw_out: str, extract_urls_fn) -> tuple[dict[str, str], dict[str, list[str]], int]:
	issue_to_sha: dict[str, str] = {}
	file_to_urls: dict[str, list[str]] = {}
	rec_count = 0
	for rec in (raw_out or '').split('\x1e'):
		parts = rec.split('\x1f')
		if 3 <= len(parts):
			rec_count += 1
			sha, body, files_blob = (parts[0].strip(), parts[1], parts[2])
			# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
			urls = dfa_unique_fast(extract_urls_fn(body))
			for url in urls:
				issue_to_sha.setdefault(url, sha)
			for raw_f in files_blob.splitlines():
				rel = raw_f.strip().replace('\\', '/')
				if rel:
					file_to_urls.setdefault(rel, urls)
	return (issue_to_sha, file_to_urls, rec_count)
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
# @used-by :func:`_parse_porcelain_z()`
# @used-by :meth:`RepoReadCache._dirty_entries()`
def _parse_porcelain_z_entries(status_out: str) -> list[tuple[str, str]]:
	entries = [e for e in (status_out or '').split('\x00') if e]
	parsed: list[tuple[str, str]] = []
	idx = 0
	while idx < len(entries):
		entry = entries[idx]
		status_code = entry[:2]
		rel_path = entry[3:].replace('\\', '/')
		if status_code.startswith(('R', 'C')) and idx + 1 < len(entries):
			idx += 1
		if rel_path:
			parsed.append((status_code, rel_path))
		idx += 1
	return parsed
# @used-by :func:`agent_tools.repo_wait._dirty_files()`
def _parse_porcelain_z(status_out: str) -> list[str]:
	return [rel_path for _, rel_path in _parse_porcelain_z_entries(status_out)]
# @used-by :meth:`RepoReadCache._key()`
def _read_head_oid(repo: Path) -> str:
	gdir = _resolve_git_dir(repo)
	r = ''
	if None is not gdir and (gdir / 'HEAD').is_file():
		try:
			head_txt = (gdir / 'HEAD').read_text(encoding='utf-8', errors='replace').strip()
		except OSError:
			head_txt = ''
		if head_txt.startswith('ref:'):
			ref_name = head_txt.split(':', 1)[1].strip()
			r = _read_ref_oid(gdir, ref_name) or head_txt
		else:
			r = head_txt
	return r
# @used-by :func:`_read_ref_oid()`
def _read_packed_ref(gdir: Path, ref_name: str) -> str:
	r = ''
	packed = gdir / 'packed-refs'
	if packed.is_file():
		try:
			for line in packed.read_text(encoding='utf-8', errors='replace').splitlines():
				if line and (not line.startswith(('#', '^'))) and line.endswith(' ' + ref_name):
					r = line.split(' ', 1)[0].strip()
					break
		except OSError:
			r = ''
	return r
# @used-by :func:`_read_head_oid()`
def _read_ref_oid(gdir: Path, ref_name: str) -> str:
	ref_file = gdir / ref_name
	r = ''
	if ref_file.is_file():
		try:
			r = ref_file.read_text(encoding='utf-8', errors='replace').strip()
		except OSError:
			r = ''
	elif (gdir / 'commondir').is_file():
		try:
			common = (gdir / (gdir / 'commondir').read_text(encoding='utf-8', errors='replace').strip()).resolve()
			r = _read_ref_oid(common, ref_name)
		except OSError:
			r = ''
	if not r:
		r = _read_packed_ref(gdir, ref_name)
	return r
# @used-by :func:`_read_head_oid()`
def _resolve_git_dir(repo: Path) -> Path | None:
	dot = repo / '.git'
	r = None
	if dot.is_dir():
		r = dot
	elif dot.is_file():
		try:
			txt = dot.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				cand = Path(txt.split(':', 1)[1].strip())
				r = cand.resolve() if cand.is_absolute() else (repo / cand).resolve()
		except OSError:
			r = None
	return r
# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
class RepoReadCache:
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.__init__()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_git_read_cache_detects_issue_url_in_untracked_dotpy()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_historical_header_ignored_while_added_removed_and_untracked_refs_caught()`
	def __init__(self) -> None:
		# 2026-11-24
		# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
		# https://github.com/dmitry-ai/harness/issues/196
		self._diff_cache: dict[tuple[Path, str, tuple[str, ...]], dict[str, set[str]]] = {}
		self._log_cache: dict[tuple[Path, str], tuple[dict[str, str], dict[str, list[str]], bool]] = {}
		self._status_cache: dict[tuple[Path, str], list[tuple[str, str]]] = {}
		self._upstream_cache: dict[tuple[Path, str], tuple[bool, int]] = {}
	# 2026-11-24
	# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
	# https://github.com/dmitry-ai/harness/issues/196
	# @used-by :meth:`RepoReadCache.dirty_paths()`
	# @used-by :meth:`RepoReadCache.dirty_referencing_issue()`
	def _dirty_entries(self, repo: Path) -> list[tuple[str, str]]:
		key = self._key(repo)
		cached = self._status_cache.get(key)
		if None is cached:
			proc = _git_read(key[0], ['status', '--porcelain', '-z'])
			raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
			cached = _parse_porcelain_z_entries(raw)
			self._status_cache[key] = cached
		return cached
	# @used-by :meth:`RepoReadCache._dirty_entries()`
	# @used-by :meth:`RepoReadCache._load_log()`
	# @used-by :meth:`RepoReadCache._tracked_diff_urls()`
	# @used-by :meth:`RepoReadCache.upstream_unpushed()`
	def _key(self, repo: Path) -> tuple[Path, str]:
		resolved = Path(repo).resolve()
		return (resolved, _read_head_oid(resolved))
	# @used-by :meth:`RepoReadCache.find_commit_for_issue()`
	# @used-by :meth:`RepoReadCache.latest_commit_urls_for_files()`
	def _load_log(self, repo: Path, extract_urls_fn) -> tuple[dict[str, str], dict[str, list[str]], bool]:
		key = self._key(repo)
		cached = self._log_cache.get(key)
		if None is cached:
			proc = _git_read(key[0], ['-c', 'core.quotepath=false', 'log', f'-n{_LOG_MAX_COUNT}', '--format=%x1e%H%x1f%B%x1f', '--name-only'])
			raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
			issue_to_sha, file_to_urls, count = _parse_log_index(raw, extract_urls_fn)
			cached = (issue_to_sha, file_to_urls, _LOG_MAX_COUNT > count)
			self._log_cache[key] = cached
		return cached
	# 2026-11-24
	# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
	# https://github.com/dmitry-ai/harness/issues/196
	# @used-by :meth:`RepoReadCache.dirty_referencing_issue()`
	def _tracked_diff_urls(self, resolved: Path, tracked_rels: list[str], extract_urls_fn) -> dict[str, set[str]]:
		if not tracked_rels:
			r: dict[str, set[str]] = {}
		else:
			repo_key, head_oid = self._key(resolved)
			dkey = (repo_key, head_oid, tuple(tracked_rels))
			cached = self._diff_cache.get(dkey)
			if None is cached:
				proc = _git_read(repo_key, ['-c', 'core.quotepath=false', 'diff', '--unified=0', '--no-prefix', 'HEAD', '--', *tracked_rels])
				if 0 == proc.returncode:
					cached = _parse_diff_changed_urls(proc.stdout.decode('utf-8', errors='replace'), extract_urls_fn)
				else:
					cached = {rel: _file_urls(repo_key / rel, extract_urls_fn) for rel in tracked_rels if (repo_key / rel).is_file()}
				self._diff_cache[dkey] = cached
			r = cached
		return r
	# 2026-11-24
	# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
	# https://github.com/dmitry-ai/harness/issues/196
	# @used-by :meth:`RepoReadCache.has_dirty_for_paths()`
	def dirty_paths(self, repo: Path) -> list[str]:
		return [rel_path for _, rel_path in self._dirty_entries(repo)]
	# 2026-11-24
	# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
	# https://github.com/dmitry-ai/harness/issues/196
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_git_read_cache_detects_issue_url_in_untracked_dotpy()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_historical_header_ignored_while_added_removed_and_untracked_refs_caught()`
	def dirty_referencing_issue(self, repo: Path, issue_url: str, suffixes: frozenset[str], extract_urls_fn) -> list[str]:
		resolved = Path(repo).resolve()
		entries = self._dirty_entries(resolved)
		# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
		tracked_rels = [rel for code, rel in entries if '??' != code and _effective_suffix(rel) in suffixes]
		untracked_rels = [rel for code, rel in entries if '??' == code]
		diff_map = self._tracked_diff_urls(resolved, tracked_rels, extract_urls_fn)
		hits = [rel for rel in tracked_rels if issue_url in diff_map.get(rel, ())]
		for rel in untracked_rels:
			for u_rel, u_path in _iter_untracked_files(resolved, rel, suffixes):
				if issue_url in _file_urls(u_path, extract_urls_fn):
					hits.append(u_rel)
		return hits
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
	def find_commit_for_issue(self, repo: Path, issue_url: str, extract_urls_fn) -> str:
		issue_to_sha, _, complete = self._load_log(repo, extract_urls_fn)
		r = issue_to_sha.get(issue_url, '')
		if (not r) and (not complete):
			proc = _git_read(Path(repo).resolve(), ['log', f'--grep={issue_url}', '--fixed-strings', '--format=%H%x1f%B%x1e'])
			if 0 == proc.returncode and proc.stdout:
				for rec in proc.stdout.decode('utf-8', errors='replace').split('\x1e'):
					if '\x1f' in rec:
						sha_cand, msg_cand = rec.split('\x1f', 1)
						if issue_url in extract_urls_fn(msg_cand):
							r = sha_cand.strip()
							break
		return r
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_repo_commits_and_files()`
	def has_dirty_for_paths(self, repo: Path, rel_paths: list[str]) -> bool:
		dirty = self.dirty_paths(repo)
		norms = [p.replace('\\', '/').lstrip('./') for p in rel_paths]
		return any((d == n or (d.endswith('/') and n.startswith(d)) for d in dirty for n in norms))
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_latest_commits()`
	def latest_commit_urls_for_files(self, repo: Path, rel_paths: list[str], extract_urls_fn) -> list[str]:
		_, file_to_urls, complete = self._load_log(repo, extract_urls_fn)
		found: list[str] = []
		resolved = Path(repo).resolve()
		for rel in rel_paths:
			norm = rel.replace('\\', '/')
			urls = file_to_urls.get(norm)
			if None is urls and (not complete):
				proc = _git_read(resolved, ['log', '-n', '1', '--format=%B', '--', f':(literal){rel}'])
				urls = extract_urls_fn(proc.stdout.decode('utf-8', errors='replace')) if 0 == proc.returncode else []
			for cu in urls or ():
				if cu not in found:
					found.append(cu)
		return found
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__has_upstream()`
	# @used-by :meth:`RepoReadCache.verify_commit_pushed()`
	def upstream_unpushed(self, repo: Path) -> tuple[bool, int]:
		key = self._key(repo)
		cached = self._upstream_cache.get(key)
		if None is cached:
			up_proc = _git_read(key[0], ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
			if 0 != up_proc.returncode:
				cached = (False, 0)
			else:
				cnt_proc = _git_read(key[0], ['rev-list', '--count', '@{u}..HEAD'])
				raw_cnt = cnt_proc.stdout.decode('utf-8', errors='replace').strip() if 0 == cnt_proc.returncode else '0'
				cached = (True, int(raw_cnt) if raw_cnt.isdigit() else 0)
			self._upstream_cache[key] = cached
		return cached
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.finalize_close_check()`
	def verify_commit_pushed(self, repo: Path, commit_sha: str, issue_url: str) -> bool:
		has_upstream, unpushed = self.upstream_unpushed(repo)
		if has_upstream and 0 < unpushed:
			raise ValueError(f'EXEC-5 violation: commit {commit_sha[:12]} referencing {issue_url} in {Path(repo).resolve()} has not been pushed to upstream (run git push before df_github_issue.py close)')
		return True
