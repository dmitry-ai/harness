# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
from __future__ import annotations
from pathlib import Path
import os
import subprocess
_LOG_MAX_COUNT = 100
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
def _git_read(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	return subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], capture_output=True, env=env, check=False, creationflags=_NO_WINDOW)
def _parse_log_index(raw_out: str, extract_urls_fn) -> tuple[dict[str, str], dict[str, list[str]], int]:
	issue_to_sha: dict[str, str] = {}
	file_to_urls: dict[str, list[str]] = {}
	rec_count = 0
	for rec in (raw_out or '').split('\x1e'):
		parts = rec.split('\x1f')
		if 3 <= len(parts):
			rec_count += 1
			sha, body, files_blob = (parts[0].strip(), parts[1], parts[2])
			urls = list(dict.fromkeys(extract_urls_fn(body)))
			for url in urls:
				issue_to_sha.setdefault(url, sha)
			for raw_f in files_blob.splitlines():
				rel = raw_f.strip().replace('\\', '/')
				if rel:
					file_to_urls.setdefault(rel, urls)
	return (issue_to_sha, file_to_urls, rec_count)
def _parse_porcelain_z(status_out: str) -> list[str]:
	entries = [e for e in (status_out or '').split('\x00') if e]
	paths: list[str] = []
	idx = 0
	while idx < len(entries):
		entry = entries[idx]
		status_code = entry[:2]
		rel_path = entry[3:].replace('\\', '/')
		if status_code.startswith(('R', 'C')) and idx + 1 < len(entries):
			idx += 1
		if rel_path:
			paths.append(rel_path)
		idx += 1
	return paths
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
class RepoReadCache:
	def __init__(self) -> None:
		self._log_cache: dict[tuple[Path, str], tuple[dict[str, str], dict[str, list[str]], bool]] = {}
		self._status_cache: dict[tuple[Path, str], list[str]] = {}
		self._upstream_cache: dict[tuple[Path, str], tuple[bool, int]] = {}
	def _key(self, repo: Path) -> tuple[Path, str]:
		resolved = Path(repo).resolve()
		return (resolved, _read_head_oid(resolved))
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
	def dirty_paths(self, repo: Path) -> list[str]:
		key = self._key(repo)
		cached = self._status_cache.get(key)
		if None is cached:
			proc = _git_read(key[0], ['status', '--porcelain', '-z'])
			raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
			cached = _parse_porcelain_z(raw)
			self._status_cache[key] = cached
		return cached
	def dirty_referencing_issue(self, repo: Path, issue_url: str, suffixes: frozenset[str], extract_urls_fn) -> list[str]:
		resolved = Path(repo).resolve()
		hits: list[str] = []
		for rel_path in self.dirty_paths(resolved):
			fpath = resolved / rel_path
			if fpath.is_file() and fpath.suffix.lower() in suffixes:
				try:
					if issue_url in extract_urls_fn(fpath.read_text(encoding='utf-8', errors='replace')):
						hits.append(rel_path)
				except OSError:
					pass
		return hits
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
	def has_dirty_for_paths(self, repo: Path, rel_paths: list[str]) -> bool:
		dirty = self.dirty_paths(repo)
		norms = [p.replace('\\', '/').lstrip('./') for p in rel_paths]
		return any((d == n or (d.endswith('/') and n.startswith(d)) for d in dirty for n in norms))
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
	def verify_commit_pushed(self, repo: Path, commit_sha: str, issue_url: str) -> bool:
		has_upstream, unpushed = self.upstream_unpushed(repo)
		if has_upstream and 0 < unpushed:
			raise ValueError(f'EXEC-5 violation: commit {commit_sha[:12]} referencing {issue_url} in {Path(repo).resolve()} has not been pushed to upstream (run git push before df_github_issue.py close)')
		return True
