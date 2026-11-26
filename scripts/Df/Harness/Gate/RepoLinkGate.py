# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Harness.Gate.RepoLinkResolver import RepoLinkResolver
from agent_tools.git_gate import run_git_read
import os
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class RepoLinkGate:
	__WIN_DRIVE_RE = re.compile(r'^[A-Za-z]:[/\\]')
	# @used-by :meth:`RepoLinkGate.check_chat()`
	# @used-by :meth:`RepoLinkGate.check_file()`
	@staticmethod
	def __authored_targets(content: str) -> list[str]:
		from agent_tools.links import HTMLReferences
		from agent_tools.markdown_links import parser as md_parser
		targets, quote_depth = ([], 0)
		html = HTMLReferences(authored_only=True)
		for block in md_parser(preserve_links=True).parse(content or ''):
			if 'blockquote_open' == block.type:
				quote_depth += 1
			elif 'blockquote_close' == block.type:
				quote_depth -= 1
			elif 0 == quote_depth:
				RepoLinkGate.__collect_block_targets(block, targets, html)
		return dfa_unique_fast(targets + html.links)
	# @used-by :meth:`RepoLinkGate.__authored_targets()`
	@staticmethod
	def __collect_block_targets(block, targets: list[str], html) -> None:
		from agent_tools.links import _document_urls
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
	# @used-by :meth:`RepoLinkGate.verify_staged()`
	@staticmethod
	def __read_staged_markdown(repo_root: Path, rel: str, use_index: bool) -> str | None:
		if use_index:
			proc = run_git_read(repo_root, ['-c', 'core.quotepath=false', 'show', f':{rel}'], check=False)
			r = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else None
		else:
			fp = repo_root / rel
			r = fp.read_text(encoding='utf-8', errors='replace') if fp.is_file() else None
		return r
	# @used-by :meth:`RepoLinkGate.check_chat()`
	# @used-by :meth:`RepoLinkGate.check_file()`
	@staticmethod
	def __validate_file_uri(href: str) -> list[str]:
		from agent_tools.markdown_links import decode_file_uri
		raw = decode_file_uri(href)
		r: list[str] = []
		if raw:
			target = Path(os.path.abspath(raw))
			repo, slug = RepoLinkResolver.enclosing_github_repo(target)
			if None is not repo and None is not slug:
				rel = target.relative_to(repo).as_posix()
				if not RepoLinkResolver.is_gitignored(repo, rel):
					kind = 'tree' if '.' == rel or target.is_dir() else 'blob'
					suffix = '' if '.' == rel else f'/{rel}'
					r.append(f'LINK-6: Prohibited file:/// link to GitHub repository file ({slug}{suffix}): use a tagged GitHub URL https://github.com/{slug}/{kind}/<tag>{suffix} instead of {href}')
		return r
	# @used-by :meth:`RepoLinkGate.check_file()`
	@staticmethod
	def __validate_relative_cross_repo(href: str, doc_path: Path, doc_repo: Path | None) -> list[str]:
		clean = (href or '').strip()
		parsed = urlsplit(clean)
		r: list[str] = []
		if clean and (not clean.startswith('#')) and (not parsed.scheme) and (not RepoLinkGate.__WIN_DRIVE_RE.match(clean)):
			raw_rel = unquote(urldefrag(clean)[0].split('?', 1)[0])
			if raw_rel:
				target = Path(os.path.abspath(str(doc_path.parent / raw_rel)))
				target_repo, slug = RepoLinkResolver.enclosing_github_repo(target)
				if None is not target_repo and None is not slug and target_repo != doc_repo:
					rel = target.relative_to(target_repo).as_posix()
					if not RepoLinkResolver.is_gitignored(target_repo, rel):
						kind = 'tree' if '.' == rel or target.is_dir() else 'blob'
						suffix = '' if '.' == rel else f'/{rel}'
						r.append(f'LINK-6: Cross-repository relative link {href} targets {slug}{suffix}; use a tagged GitHub URL https://github.com/{slug}/{kind}/<tag>{suffix}')
		return r
	# @used-by :func:`agent_tools.repo_link_gate.chat_repo_link_issues()`
	@staticmethod
	def check_chat(content: str, *, root: Path | None=None) -> list[str]:
		errors: list[str] = []
		for href in RepoLinkGate.__authored_targets(content):
			low = href.lower()
			if low.startswith('file:'):
				errors.extend(RepoLinkGate.__validate_file_uri(href))
			elif low.startswith('https://github.com/'):
				errors.extend(RepoLinkResolver.validate_github_url(href, root))
		return dfa_unique_fast(errors)
	# @used-by :func:`agent_tools.repo_link_gate.file_repo_link_issues()`
	# @used-by :meth:`RepoLinkGate.verify_staged()`
	@staticmethod
	def check_file(doc_path: Path, content: str, *, repo_root: Path | None=None) -> list[str]:
		doc_p = Path(doc_path).resolve()
		doc_repo, _ = RepoLinkResolver.enclosing_github_repo(doc_p)
		search_root = repo_root or doc_repo or doc_p.parent
		errors: list[str] = []
		for href in RepoLinkGate.__authored_targets(content):
			low = href.lower()
			if low.startswith('file:'):
				errors.extend(RepoLinkGate.__validate_file_uri(href))
			elif low.startswith('https://github.com/'):
				errors.extend(RepoLinkResolver.validate_github_url(href, search_root))
			else:
				errors.extend(RepoLinkGate.__validate_relative_cross_repo(href, doc_p, doc_repo))
		return dfa_unique_fast(errors)
	# @used-by :func:`agent_tools.repo_link_gate.verify_staged_repo_links()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	def verify_staged(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
		violations: list[str] = []
		for rel in staged_paths:
			norm = rel.replace('\\', '/')
			if norm.lower().endswith('.md') and (not RepoLinkResolver.is_skipped_doc(norm)):
				text = RepoLinkGate.__read_staged_markdown(repo_root, norm, use_index)
				if None is not text:
					for err in RepoLinkGate.check_file(repo_root / norm, text, repo_root=repo_root):
						violations.append(f'{norm}: {err}')
		return violations
