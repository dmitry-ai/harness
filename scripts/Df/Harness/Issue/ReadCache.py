# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Core.lib.fs import df_path_suffix
import os
import subprocess
_LOG_MAX_COUNT = 100
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ReadCache:
	# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.verify()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_parity_auditor_pending_peers_read_cache_and_repo_locator()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def __init__(self) -> None:
		self.__diff_cache: dict[tuple[Path, str, tuple[str, ...]], dict[str, set[str]]] = {}
		self.__log_cache: dict[tuple[Path, str], tuple[dict[str, str], dict[str, list[str]], bool]] = {}
		self.__status_cache: dict[tuple[Path, str], list[tuple[str, str]]] = {}
		self.__upstream_cache: dict[tuple[Path, str], tuple[bool, int]] = {}
	# @used-by :meth:`ReadCache.dirty_paths()`
	# @used-by :meth:`ReadCache.dirty_referencing_issue()`
	def __dirty_entries(self, repo: Path) -> list[tuple[str, str]]:
		key = self.__key(repo)
		cached = self.__status_cache.get(key)
		if None is cached:
			proc = self.__git_read(key[0], ['status', '--porcelain', '-z'])
			raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
			cached = self.parse_porcelain_z_entries(raw)
			self.__status_cache[key] = cached
		return cached
	# @used-by :meth:`ReadCache.__parse_diff_changed_urls()`
	@staticmethod
	def __extract_diff_header_path(line: str) -> str:
		raw = line[4:].split('\t', 1)[0].strip().replace('\\', '/')
		return '' if '/dev/null' == raw else raw
	# @used-by :meth:`ReadCache.__tracked_diff_urls()`
	# @used-by :meth:`ReadCache.dirty_referencing_issue()`
	@staticmethod
	def __file_urls(fpath: Path, extract_urls_fn) -> set[str]:
		try:
			r = set(extract_urls_fn(fpath.read_text(encoding='utf-8', errors='replace')))
		except OSError:
			r = set()
		return r
	# @used-by :meth:`ReadCache.__dirty_entries()`
	# @used-by :meth:`ReadCache.__load_log()`
	# @used-by :meth:`ReadCache.__tracked_diff_urls()`
	# @used-by :meth:`ReadCache.find_commit_for_issue()`
	# @used-by :meth:`ReadCache.latest_commit_urls_for_files()`
	# @used-by :meth:`ReadCache.upstream_unpushed()`
	@staticmethod
	def __git_read(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
		env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
		return subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, env=env, check=False, timeout=60, creationflags=_NO_WINDOW)
	# @used-by :meth:`ReadCache.dirty_referencing_issue()`
	@staticmethod
	def __iter_untracked_files(resolved: Path, rel_path: str, suffixes: frozenset[str]) -> list[tuple[str, Path]]:
		fpath = resolved / rel_path
		if fpath.is_file():
			r = [(rel_path, fpath)] if df_path_suffix(fpath) in suffixes else []
		elif fpath.is_dir():
			r = sorted(((p.relative_to(resolved).as_posix(), p) for p in fpath.rglob('*') if p.is_file() and df_path_suffix(p) in suffixes))
		else:
			r = []
		return r
	# @used-by :meth:`ReadCache.__dirty_entries()`
	# @used-by :meth:`ReadCache.__load_log()`
	# @used-by :meth:`ReadCache.__tracked_diff_urls()`
	# @used-by :meth:`ReadCache.upstream_unpushed()`
	def __key(self, repo: Path) -> tuple[Path, str]:
		resolved = Path(repo).resolve()
		return (resolved, self.__read_head_oid(resolved))
	# @used-by :meth:`ReadCache.find_commit_for_issue()`
	# @used-by :meth:`ReadCache.latest_commit_urls_for_files()`
	def __load_log(self, repo: Path, extract_urls_fn) -> tuple[dict[str, str], dict[str, list[str]], bool]:
		key = self.__key(repo)
		cached = self.__log_cache.get(key)
		if None is cached:
			proc = self.__git_read(key[0], ['-c', 'core.quotepath=false', 'log', f'-n{_LOG_MAX_COUNT}', '--format=%x1e%H%x1f%B%x1f', '--name-only'])
			raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
			issue_to_sha, file_to_urls, count = self.__parse_log_index(raw, extract_urls_fn)
			cached = (issue_to_sha, file_to_urls, _LOG_MAX_COUNT > count)
			self.__log_cache[key] = cached
		return cached
	# @used-by :meth:`ReadCache.__tracked_diff_urls()`
	def __parse_diff_changed_urls(self, diff_text: str, extract_urls_fn) -> dict[str, set[str]]:
		changed: dict[str, set[str]] = {}
		cur_path, prev_minus = ('', '')
		for line in (diff_text or '').splitlines():
			if line.startswith('--- '):
				prev_minus = self.__extract_diff_header_path(line)
			elif line.startswith('+++ '):
				plus_path = self.__extract_diff_header_path(line)
				cur_path = plus_path if plus_path else prev_minus
			elif cur_path and line.startswith(('+', '-')):
				urls = extract_urls_fn(line[1:])
				if urls:
					changed.setdefault(cur_path, set()).update(urls)
		return changed
	# @used-by :meth:`ReadCache.__load_log()`
	@staticmethod
	def __parse_log_index(raw_out: str, extract_urls_fn) -> tuple[dict[str, str], dict[str, list[str]], int]:
		issue_to_sha: dict[str, str] = {}
		file_to_urls: dict[str, list[str]] = {}
		rec_count = 0
		for rec in (raw_out or '').split('\x1e'):
			parts = rec.split('\x1f')
			if 3 <= len(parts):
				rec_count += 1
				sha, body, files_blob = (parts[0].strip(), parts[1], parts[2])
				urls = dfa_unique_fast(extract_urls_fn(body))
				for url in urls:
					issue_to_sha.setdefault(url, sha)
				for raw_f in files_blob.splitlines():
					rel = raw_f.strip().replace('\\', '/')
					if rel:
						file_to_urls.setdefault(rel, urls)
		return (issue_to_sha, file_to_urls, rec_count)
	# @used-by :meth:`ReadCache.__key()`
	def __read_head_oid(self, repo: Path) -> str:
		gdir = self.__resolve_git_dir(repo)
		r = ''
		if None is not gdir and (gdir / 'HEAD').is_file():
			try:
				head_txt = (gdir / 'HEAD').read_text(encoding='utf-8', errors='replace').strip()
			except OSError:
				head_txt = ''
			if head_txt.startswith('ref:'):
				ref_name = head_txt.split(':', 1)[1].strip()
				r = self.__read_ref_oid(gdir, ref_name) or head_txt
			else:
				r = head_txt
		return r
	# @used-by :meth:`ReadCache.__read_ref_oid()`
	@staticmethod
	def __read_packed_ref(gdir: Path, ref_name: str) -> str:
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
	# @used-by :meth:`ReadCache.__read_head_oid()`
	def __read_ref_oid(self, gdir: Path, ref_name: str) -> str:
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
				r = self.__read_ref_oid(common, ref_name)
			except OSError:
				r = ''
		if not r:
			r = self.__read_packed_ref(gdir, ref_name)
		return r
	# @used-by :meth:`ReadCache.__read_head_oid()`
	@staticmethod
	def __resolve_git_dir(repo: Path) -> Path | None:
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
	# @used-by :meth:`ReadCache.dirty_referencing_issue()`
	def __tracked_diff_urls(self, resolved: Path, tracked_rels: list[str], extract_urls_fn) -> dict[str, set[str]]:
		if not tracked_rels:
			r: dict[str, set[str]] = {}
		else:
			repo_key, head_oid = self.__key(resolved)
			dkey = (repo_key, head_oid, tuple(tracked_rels))
			cached = self.__diff_cache.get(dkey)
			if None is cached:
				proc = self.__git_read(repo_key, ['-c', 'core.quotepath=false', 'diff', '--unified=0', '--no-prefix', 'HEAD', '--', *tracked_rels])
				if 0 == proc.returncode:
					cached = self.__parse_diff_changed_urls(proc.stdout.decode('utf-8', errors='replace'), extract_urls_fn)
				else:
					cached = {rel: self.__file_urls(repo_key / rel, extract_urls_fn) for rel in tracked_rels if (repo_key / rel).is_file()}
				self.__diff_cache[dkey] = cached
			r = cached
		return r
	# @used-by :meth:`ReadCache.has_dirty_for_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def dirty_paths(self, repo: Path) -> list[str]:
		return [rel_path for _, rel_path in self.__dirty_entries(repo)]
	# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.__ensure_clean()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_parity_auditor_pending_peers_read_cache_and_repo_locator()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo()`
	# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_historical_header_ignored_while_added_removed_and_untracked_refs_caught()`
	def dirty_referencing_issue(self, repo: Path, issue_url: str, suffixes: frozenset[str], extract_urls_fn) -> list[str]:
		resolved = Path(repo).resolve()
		entries = self.__dirty_entries(resolved)
		tracked_rels = [rel for code, rel in entries if '??' != code and df_path_suffix(rel) in suffixes]
		untracked_rels = [rel for code, rel in entries if '??' == code]
		diff_map = self.__tracked_diff_urls(resolved, tracked_rels, extract_urls_fn)
		hits = [rel for rel in tracked_rels if issue_url in diff_map.get(rel, ())]
		for rel in untracked_rels:
			for u_rel, u_path in self.__iter_untracked_files(resolved, rel, suffixes):
				if issue_url in self.__file_urls(u_path, extract_urls_fn):
					hits.append(u_rel)
		return hits
	# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.verify()`
	def find_commit_for_issue(self, repo: Path, issue_url: str, extract_urls_fn) -> str:
		issue_to_sha, _, complete = self.__load_log(repo, extract_urls_fn)
		r = issue_to_sha.get(issue_url, '')
		if (not r) and (not complete):
			proc = self.__git_read(Path(repo).resolve(), ['log', f'--grep={issue_url}', '--fixed-strings', '--format=%H%x1f%B%x1e'])
			if 0 == proc.returncode and proc.stdout:
				for rec in proc.stdout.decode('utf-8', errors='replace').split('\x1e'):
					if '\x1f' in rec:
						sha_cand, msg_cand = rec.split('\x1f', 1)
						if issue_url in extract_urls_fn(msg_cand):
							r = sha_cand.strip()
							break
		return r
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_repo_commits_and_files()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def has_dirty_for_paths(self, repo: Path, rel_paths: list[str]) -> bool:
		dirty = self.dirty_paths(repo)
		norms = [p.replace('\\', '/').lstrip('./') for p in rel_paths]
		return any((d == n or (d.endswith('/') and n.startswith(d)) for d in dirty for n in norms))
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__inspect_latest_commits()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_parity_auditor_pending_peers_read_cache_and_repo_locator()`
	def latest_commit_urls_for_files(self, repo: Path, rel_paths: list[str], extract_urls_fn) -> list[str]:
		_, file_to_urls, complete = self.__load_log(repo, extract_urls_fn)
		found: list[str] = []
		resolved = Path(repo).resolve()
		for rel in rel_paths:
			norm = rel.replace('\\', '/')
			urls = file_to_urls.get(norm)
			if None is urls and (not complete):
				proc = self.__git_read(resolved, ['log', '-n', '1', '--format=%B', '--', f':(literal){rel}'])
				urls = extract_urls_fn(proc.stdout.decode('utf-8', errors='replace')) if 0 == proc.returncode else []
			for cu in urls or ():
				if cu not in found:
					found.append(cu)
		return found
	# @used-by :func:`agent_tools.issues.git_read_cache._parse_porcelain_z()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__dirty_files()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	@staticmethod
	def parse_porcelain_z(status_out: str) -> list[str]:
		return [rel_path for _, rel_path in ReadCache.parse_porcelain_z_entries(status_out)]
	# @used-by :meth:`ReadCache.__dirty_entries()`
	# @used-by :meth:`ReadCache.parse_porcelain_z()`
	@staticmethod
	def parse_porcelain_z_entries(status_out: str) -> list[tuple[str, str]]:
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
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__has_upstream()`
	# @used-by :meth:`ReadCache.verify_commit_pushed()`
	def upstream_unpushed(self, repo: Path) -> tuple[bool, int]:
		key = self.__key(repo)
		cached = self.__upstream_cache.get(key)
		if None is cached:
			up_proc = self.__git_read(key[0], ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
			if 0 != up_proc.returncode:
				cached = (False, 0)
			else:
				cnt_proc = self.__git_read(key[0], ['rev-list', '--count', '@{u}..HEAD'])
				raw_cnt = cnt_proc.stdout.decode('utf-8', errors='replace').strip() if 0 == cnt_proc.returncode else '0'
				cached = (True, int(raw_cnt) if raw_cnt.isdigit() else 0)
			self.__upstream_cache[key] = cached
		return cached
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.finalize_close_check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_parity_auditor_pending_peers_read_cache_and_repo_locator()`
	def verify_commit_pushed(self, repo: Path, commit_sha: str, issue_url: str) -> bool:
		has_upstream, unpushed = self.upstream_unpushed(repo)
		if has_upstream and 0 < unpushed:
			raise ValueError(f'EXEC-5 violation: commit {commit_sha[:12]} referencing {issue_url} in {Path(repo).resolve()} has not been pushed to upstream (run git push before df_github_issue.py close)')
		return True
