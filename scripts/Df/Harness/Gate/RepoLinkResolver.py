# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag
from agent_tools.git_gate import run_git_read
from agent_tools.issues.repo_locator import find_local_code_repo, origin_repo_slug
from agent_tools.repo_tags import is_valid_repo_tag
import json
import os
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class RepoLinkResolver:
	GITHUB_BLOB_TREE_RE = re.compile(r'^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/(?P<kind>blob|tree)/(?P<ref>[^/?#]+)(?:/(?P<path>[^?#]*))?(?:\?[^#]*)?(?:#(?P<fragment>.*))?$', re.I)
	__LINE_FRAG_RE = re.compile(r'^L(\d+)(?:-L?(\d+))?$')
	__SKIP_STAGED_RE = re.compile(r'(?:^|/)(?:\ua66e|req|res|evidence|plans|scratch)/', re.I)
	# @used-by :func:`agent_tools.repo_link_gate.resolve_local_github_blob()`
	# @used-by :meth:`RepoLinkResolver.hydrate_local_urls()`
	def __init__(self, root: Path | None) -> None:
		self.__root = root
	# @used-by :meth:`RepoLinkResolver.__validate_github_object()`
	@staticmethod
	def __cat_file_type(repo: Path, ref: str, rel_path: str) -> str | None:
		spec = f'{ref}:{rel_path}' if rel_path else f'{ref}^{{tree}}'
		proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'cat-file', '-t', spec], check=False)
		return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else None
	# @used-by :meth:`RepoLinkResolver.__validate_github_object()`
	# @used-by :meth:`RepoLinkResolver.resolve_blob()`
	@staticmethod
	def __load_blob_text(repo: Path, ref: str, rel_path: str) -> str | None:
		proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'show', f'{ref}:{rel_path}'], check=False)
		return proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else None
	# @used-by :meth:`RepoLinkResolver.resolve_blob()`
	# @used-by :meth:`RepoLinkResolver.validate_github_url()`
	@staticmethod
	def __parse_github_ref_url(url: str) -> dict | None:
		m = RepoLinkResolver.GITHUB_BLOB_TREE_RE.fullmatch((url or '').strip())
		if None is m:
			r = None
		else:
			owner, repo_name = (m.group('owner'), m.group('repo'))
			r = {'slug': f'{owner}/{repo_name}', 'kind': m.group('kind').lower(), 'ref': unquote(m.group('ref')), 'path': unquote(m.group('path') or '').strip('/'), 'fragment': unquote(m.group('fragment') or '').strip()}
		return r
	# @used-by :meth:`RepoLinkResolver.resolve_blob()`
	# @used-by :meth:`RepoLinkResolver.validate_github_url()`
	@staticmethod
	def __repo_has_tag(repo: Path, tag: str) -> bool:
		return 0 == run_git_read(repo, ['show-ref', '--verify', '--quiet', f'refs/tags/{tag}'], check=False).returncode
	# @used-by :meth:`RepoLinkResolver.__validate_github_object()`
	@staticmethod
	def __validate_blob_anchor(url: str, rel_path: str, blob_text: str, fragment: str) -> list[str]:
		r: list[str] = []
		if fragment:
			m_ln = RepoLinkResolver.__LINE_FRAG_RE.fullmatch(fragment)
			if None is not m_ln:
				total = max(1, len(blob_text.splitlines()))
				start, end = (int(m_ln.group(1)), int(m_ln.group(2) or m_ln.group(1)))
				if 1 > start or start > end or end > total:
					r.append(f'LINK-6: Line anchor #{fragment} is out of bounds (1..{total}) in {url}')
			else:
				r = RepoLinkResolver.__validate_doc_or_json_anchor(url, rel_path, blob_text, fragment)
		return r
	# @used-by :meth:`RepoLinkResolver.__validate_blob_anchor()`
	@staticmethod
	def __validate_doc_or_json_anchor(url: str, rel_path: str, blob_text: str, fragment: str) -> list[str]:
		suffix = Path(rel_path).suffix.lower()
		r: list[str] = []
		if suffix in ('.md', '.html', '.htm'):
			from agent_tools.links import heading_anchors, references
			if fragment not in (set(references(blob_text)[1]) | heading_anchors(blob_text)):
				r.append(f'LINK-6: Missing Markdown/HTML anchor #{fragment} in {url}')
		elif '.json' == suffix and fragment.startswith('/'):
			try:
				from agent_tools.evidence import resolve_pointer
				resolve_pointer(json.loads(blob_text), fragment)
			except (KeyError, ValueError, IndexError, TypeError):
				r.append(f'LINK-6: Missing JSON pointer #{fragment} in {url}')
		return r
	# @used-by :meth:`RepoLinkResolver.validate_github_url()`
	@staticmethod
	def __validate_github_object(url: str, local_repo: Path, info: dict) -> list[str]:
		slug, kind, ref, rel_path, frag = (info['slug'], info['kind'], info['ref'], info['path'], info['fragment'])
		obj_type = RepoLinkResolver.__cat_file_type(local_repo, ref, rel_path)
		if None is obj_type:
			r = [f'LINK-6: Path "{rel_path}" does not exist at Git tag "{ref}" in {slug} ({url})']
		elif 'tree' == obj_type:
			if 'tree' != kind:
				r = [f'LINK-6: Directory path "{rel_path}" at tag "{ref}" must use /tree/ instead of /blob/ ({url})']
			elif frag:
				r = [f'LINK-6: Directory link cannot carry fragment #{frag} ({url})']
			else:
				r = []
		elif 'blob' != kind:
			r = [f'LINK-6: File path "{rel_path}" at tag "{ref}" must use /blob/ instead of /tree/ ({url})']
		else:
			blob_text = RepoLinkResolver.__load_blob_text(local_repo, ref, rel_path)
			r = [] if None is blob_text else RepoLinkResolver.__validate_blob_anchor(url, rel_path, blob_text, frag)
		return r
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_file_uri()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_relative_cross_repo()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.check_file()`
	@staticmethod
	def enclosing_github_repo(target: Path) -> tuple[Path | None, str | None]:
		abs_p = Path(os.path.abspath(str(target)))
		r: tuple[Path | None, str | None] = (None, None)
		for anc in (abs_p, *abs_p.parents):
			if (anc / '.git').exists():
				slug = origin_repo_slug(anc)
				if slug:
					r = (anc.resolve(), slug)
				break
		return r
	# @used-by :func:`agent_tools.repo_link_gate.hydrate_local_repo_urls()`
	@staticmethod
	def hydrate_local_urls(auditor) -> set[str]:
		local_urls: set[str] = set()
		resolver = RepoLinkResolver(auditor.root)
		for url in dict.fromkeys(auditor.authored_urls):
			if url.lower().startswith('https://github.com/'):
				resolved = resolver.resolve_blob(url)
				if None is not resolved:
					nu = urldefrag(url.strip())[0].rstrip('/')
					auditor.observed_urls.add(nu)
					auditor.observed_texts.setdefault(nu, []).append(resolved[1])
					local_urls.add(nu)
		return local_urls
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_file_uri()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_relative_cross_repo()`
	@staticmethod
	def is_gitignored(repo: Path, rel_path: str) -> bool:
		clean = rel_path.strip('/')
		if not clean or '.' == clean:
			r = False
		elif '.git' == clean or clean.startswith('.git/'):
			r = True
		else:
			proc = run_git_read(repo, ['check-ignore', '-q', '--', clean], check=False)
			r = 0 == proc.returncode
		return r
	# @used-by :func:`agent_tools.repo_link_gate.is_skipped_repo_link_doc()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.verify_staged()`
	@staticmethod
	def is_skipped_doc(path: Path | str) -> bool:
		norm = '/' + str(path).replace('\\', '/').lower().lstrip('/')
		return bool(RepoLinkResolver.__SKIP_STAGED_RE.search(norm)) or '/data/scratch/' in norm
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.check_chat()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.check_file()`
	@staticmethod
	def validate_github_url(url: str, root: Path | None) -> list[str]:
		info = RepoLinkResolver.__parse_github_ref_url(url)
		if None is info:
			r: list[str] = []
		else:
			slug, ref = (info['slug'], info['ref'])
			local_repo = find_local_code_repo(slug, project_root=root)
			if None is local_repo:
				r = []
			elif not is_valid_repo_tag(ref) or (not RepoLinkResolver.__repo_has_tag(local_repo, ref)):
				r = [f'LINK-6: GitHub link {url} must reference an existing Git tag in {slug} (not "{ref}")']
			else:
				r = RepoLinkResolver.__validate_github_object(url, local_repo, info)
		return r
	# @used-by :func:`agent_tools.repo_link_gate.resolve_local_github_blob()`
	# @used-by :meth:`RepoLinkResolver.hydrate_local_urls()`
	def resolve_blob(self, url: str) -> tuple[str, str] | None:
		info = RepoLinkResolver.__parse_github_ref_url(url)
		r: tuple[str, str] | None = None
		if None is not info and 'blob' == info['kind'] and info['path']:
			slug, ref, rel_path = (info['slug'], info['ref'], info['path'])
			local_repo = find_local_code_repo(slug, project_root=self.__root)
			if None is not local_repo and is_valid_repo_tag(ref) and RepoLinkResolver.__repo_has_tag(local_repo, ref):
				text = RepoLinkResolver.__load_blob_text(local_repo, ref, rel_path)
				if None is not text:
					r = (f'{slug}@{ref}:{rel_path}', text)
		return r
