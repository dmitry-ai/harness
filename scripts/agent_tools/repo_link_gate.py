# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs":
# https://github.com/dmitry-ai/harness/issues/264
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
import json
import os
import re
from .git_gate import run_git_read
from .issues.repo_locator import find_local_code_repo, origin_repo_slug
from .repo_tags import is_valid_repo_tag
GITHUB_BLOB_TREE_RE = re.compile(r'^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/(?P<kind>blob|tree)/(?P<ref>[^/?#]+)(?:/(?P<path>[^?#]*))?(?:\?[^#]*)?(?:#(?P<fragment>.*))?$', re.I)
_LINE_FRAG_RE = re.compile(r'^L(\d+)(?:-L?(\d+))?$')
_SKIP_STAGED_RE = re.compile(r'(?:^|/)(?:\ua66e|req|res|evidence|plans|scratch)/', re.I)
_WIN_DRIVE_RE = re.compile(r'^[A-Za-z]:[/\\]')
def _authored_targets(content: str) -> list[str]:
	from .links import HTMLReferences
	from .markdown_links import parser as md_parser
	targets, quote_depth = ([], 0)
	html = HTMLReferences(authored_only=True)
	for block in md_parser(preserve_links=True).parse(content or ''):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth -= 1
		elif 0 == quote_depth:
			_collect_block_targets(block, targets, html)
	return list(dict.fromkeys(targets + html.links))
def _cat_file_type(repo: Path, ref: str, rel_path: str) -> str | None:
	spec = f'{ref}:{rel_path}' if rel_path else f'{ref}^{{tree}}'
	proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'cat-file', '-t', spec], check=False)
	return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else None
def _collect_block_targets(block, targets: list[str], html) -> None:
	from .links import _document_urls
	if 'html_block' == block.type:
		html.feed(block.content)
	for tok in block.children or []:
		if 'link_open' == tok.type:
			targets.append(tok.attrGet('href') or '')
		elif 'image' == tok.type:
			targets.append(tok.attrGet('src') or '')
		elif 'html_inline' == tok.type:
			html.feed(tok.content)
		elif 'text' == tok.type:
			targets.extend(_document_urls(tok.content))
def _enclosing_github_repo(target: Path) -> tuple[Path | None, str | None]:
	abs_p = Path(os.path.abspath(str(target)))
	r: tuple[Path | None, str | None] = (None, None)
	for anc in (abs_p, *abs_p.parents):
		if (anc / '.git').exists():
			slug = origin_repo_slug(anc)
			if slug:
				r = (anc.resolve(), slug)
			break
	return r
def _is_gitignored(repo: Path, rel_path: str) -> bool:
	clean = rel_path.strip('/')
	if not clean or '.' == clean:
		r = False
	elif '.git' == clean or clean.startswith('.git/'):
		r = True
	else:
		proc = run_git_read(repo, ['check-ignore', '-q', '--', clean], check=False)
		r = 0 == proc.returncode
	return r
def _load_blob_text(repo: Path, ref: str, rel_path: str) -> str | None:
	proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'show', f'{ref}:{rel_path}'], check=False)
	return proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else None
def _parse_github_ref_url(url: str) -> dict | None:
	m = GITHUB_BLOB_TREE_RE.fullmatch((url or '').strip())
	if None is m:
		r = None
	else:
		owner, repo_name = (m.group('owner'), m.group('repo'))
		r = {'slug': f'{owner}/{repo_name}', 'kind': m.group('kind').lower(), 'ref': unquote(m.group('ref')), 'path': unquote(m.group('path') or '').strip('/'), 'fragment': unquote(m.group('fragment') or '').strip()}
	return r
def _read_staged_markdown(repo_root: Path, rel: str, use_index: bool) -> str | None:
	if use_index:
		proc = run_git_read(repo_root, ['-c', 'core.quotepath=false', 'show', f':{rel}'], check=False)
		r = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else None
	else:
		fp = repo_root / rel
		r = fp.read_text(encoding='utf-8', errors='replace') if fp.is_file() else None
	return r
def _repo_has_tag(repo: Path, tag: str) -> bool:
	return 0 == run_git_read(repo, ['show-ref', '--verify', '--quiet', f'refs/tags/{tag}'], check=False).returncode
def _validate_blob_anchor(url: str, rel_path: str, blob_text: str, fragment: str) -> list[str]:
	r: list[str] = []
	if fragment:
		m_ln = _LINE_FRAG_RE.fullmatch(fragment)
		if None is not m_ln:
			total = max(1, len(blob_text.splitlines()))
			start, end = (int(m_ln.group(1)), int(m_ln.group(2) or m_ln.group(1)))
			if 1 > start or start > end or end > total:
				r.append(f'LINK-6: Line anchor #{fragment} is out of bounds (1..{total}) in {url}')
		else:
			r = _validate_doc_or_json_anchor(url, rel_path, blob_text, fragment)
	return r
def _validate_doc_or_json_anchor(url: str, rel_path: str, blob_text: str, fragment: str) -> list[str]:
	suffix = Path(rel_path).suffix.lower()
	r: list[str] = []
	if suffix in ('.md', '.html', '.htm'):
		from .links import heading_anchors, references
		if fragment not in (set(references(blob_text)[1]) | heading_anchors(blob_text)):
			r.append(f'LINK-6: Missing Markdown/HTML anchor #{fragment} in {url}')
	elif '.json' == suffix and fragment.startswith('/'):
		try:
			from .evidence import resolve_pointer
			resolve_pointer(json.loads(blob_text), fragment)
		except (KeyError, ValueError, IndexError, TypeError):
			r.append(f'LINK-6: Missing JSON pointer #{fragment} in {url}')
	return r
def _validate_file_uri(href: str) -> list[str]:
	from .markdown_links import decode_file_uri
	raw = decode_file_uri(href)
	r: list[str] = []
	if raw:
		target = Path(os.path.abspath(raw))
		repo, slug = _enclosing_github_repo(target)
		if None is not repo and None is not slug:
			rel = target.relative_to(repo).as_posix()
			if not _is_gitignored(repo, rel):
				kind = 'tree' if '.' == rel or target.is_dir() else 'blob'
				suffix = '' if '.' == rel else f'/{rel}'
				r.append(f'LINK-6: Prohibited file:/// link to GitHub repository file ({slug}{suffix}): use a tagged GitHub URL https://github.com/{slug}/{kind}/<tag>{suffix} instead of {href}')
	return r
def _validate_github_object(url: str, local_repo: Path, info: dict) -> list[str]:
	slug, kind, ref, rel_path, frag = (info['slug'], info['kind'], info['ref'], info['path'], info['fragment'])
	obj_type = _cat_file_type(local_repo, ref, rel_path)
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
		blob_text = _load_blob_text(local_repo, ref, rel_path)
		r = [] if None is blob_text else _validate_blob_anchor(url, rel_path, blob_text, frag)
	return r
def _validate_github_url(url: str, root: Path | None) -> list[str]:
	info = _parse_github_ref_url(url)
	if None is info:
		r: list[str] = []
	else:
		slug, ref = (info['slug'], info['ref'])
		local_repo = find_local_code_repo(slug, project_root=root)
		if None is local_repo:
			r = []
		elif not is_valid_repo_tag(ref) or (not _repo_has_tag(local_repo, ref)):
			r = [f'LINK-6: GitHub link {url} must reference an existing Git tag in {slug} (not "{ref}")']
		else:
			r = _validate_github_object(url, local_repo, info)
	return r
def _validate_relative_cross_repo(href: str, doc_path: Path, doc_repo: Path | None) -> list[str]:
	clean = (href or '').strip()
	parsed = urlsplit(clean)
	r: list[str] = []
	if clean and (not clean.startswith('#')) and (not parsed.scheme) and (not _WIN_DRIVE_RE.match(clean)):
		raw_rel = unquote(urldefrag(clean)[0].split('?', 1)[0])
		if raw_rel:
			target = Path(os.path.abspath(str(doc_path.parent / raw_rel)))
			target_repo, slug = _enclosing_github_repo(target)
			if None is not target_repo and None is not slug and target_repo != doc_repo:
				rel = target.relative_to(target_repo).as_posix()
				if not _is_gitignored(target_repo, rel):
					kind = 'tree' if '.' == rel or target.is_dir() else 'blob'
					suffix = '' if '.' == rel else f'/{rel}'
					r.append(f'LINK-6: Cross-repository relative link {href} targets {slug}{suffix}; use a tagged GitHub URL https://github.com/{slug}/{kind}/<tag>{suffix}')
	return r
def chat_repo_link_issues(content: str, *, root: Path | None=None) -> list[str]:
	errors: list[str] = []
	for href in _authored_targets(content):
		low = href.lower()
		if low.startswith('file:'):
			errors.extend(_validate_file_uri(href))
		elif low.startswith('https://github.com/'):
			errors.extend(_validate_github_url(href, root))
	return list(dict.fromkeys(errors))
def file_repo_link_issues(doc_path: Path, content: str, *, repo_root: Path | None=None) -> list[str]:
	doc_p = Path(doc_path).resolve()
	doc_repo, _ = _enclosing_github_repo(doc_p)
	search_root = repo_root or doc_repo or doc_p.parent
	errors: list[str] = []
	for href in _authored_targets(content):
		low = href.lower()
		if low.startswith('file:'):
			errors.extend(_validate_file_uri(href))
		elif low.startswith('https://github.com/'):
			errors.extend(_validate_github_url(href, search_root))
		else:
			errors.extend(_validate_relative_cross_repo(href, doc_p, doc_repo))
	return list(dict.fromkeys(errors))
def hydrate_local_repo_urls(auditor) -> set[str]:
	local_urls: set[str] = set()
	for url in dict.fromkeys(auditor.authored_urls):
		if url.lower().startswith('https://github.com/'):
			resolved = resolve_local_github_blob(auditor.root, url)
			if None is not resolved:
				nu = urldefrag(url.strip())[0].rstrip('/')
				auditor.observed_urls.add(nu)
				auditor.observed_texts.setdefault(nu, []).append(resolved[1])
				local_urls.add(nu)
	return local_urls
def is_skipped_repo_link_doc(path: Path | str) -> bool:
	norm = '/' + str(path).replace('\\', '/').lower().lstrip('/')
	return bool(_SKIP_STAGED_RE.search(norm)) or '/data/scratch/' in norm
def resolve_local_github_blob(root: Path | None, url: str) -> tuple[str, str] | None:
	info = _parse_github_ref_url(url)
	r: tuple[str, str] | None = None
	if None is not info and 'blob' == info['kind'] and info['path']:
		slug, ref, rel_path = (info['slug'], info['ref'], info['path'])
		local_repo = find_local_code_repo(slug, project_root=root)
		if None is not local_repo and is_valid_repo_tag(ref) and _repo_has_tag(local_repo, ref):
			text = _load_blob_text(local_repo, ref, rel_path)
			if None is not text:
				r = (f'{slug}@{ref}:{rel_path}', text)
	return r
def verify_staged_repo_links(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	violations: list[str] = []
	for rel in staged_paths:
		norm = rel.replace('\\', '/')
		if norm.lower().endswith('.md') and (not is_skipped_repo_link_doc(norm)):
			text = _read_staged_markdown(repo_root, norm, use_index)
			if None is not text:
				for err in file_repo_link_issues(repo_root / norm, text, repo_root=repo_root):
					violations.append(f'{norm}: {err}')
	return violations
