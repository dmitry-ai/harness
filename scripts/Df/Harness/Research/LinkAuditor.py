# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from Df.Harness.Research.HtmlReferences import HtmlReferences
from Df.Harness.Research.MarkdownHeadingParser import MarkdownHeadingParser
from Df.Harness.lib.markdown import dfh_markdown_it_parser
from Df.Harness.lib.research import dfh_bare_urls, dfh_document_urls, dfh_readable_reference
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class LinkAuditor:
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.__check_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_link_auditor_and_observation_bundle_scanner()`
	def __init__(self, file_path: Path, **options) -> None:
		self.__file_path = Path(file_path)
		self.__options = options
	# @used-by :meth:`LinkAuditor.validate_content()`
	@staticmethod
	def __check_url_syntax(url: str, available_anchors: set[str], local_anchors: bool) -> str | None:
		r: str | None = None
		try:
			parsed = urlsplit(url)
			if parsed.scheme.lower() in ('http', 'https'):
				if not parsed.hostname or any((c.isspace() for c in url)):
					r = f'Invalid HTTP URL: {url}'
				_ = parsed.port
			elif local_anchors and url.startswith('#') and (unquote(url[1:]) not in available_anchors):
				r = f'Missing local anchor: {url}'
		except ValueError as exc:
			r = f'Invalid URL {url}: {exc}'
		return r
	# @used-by :meth:`LinkAuditor.readable_link_issues()`
	@staticmethod
	def __collect_authored_targets(content: str) -> list[str]:
		targets, quote_depth = ([], 0)
		html = HtmlReferences(authored_only=True)
		for block in dfh_markdown_it_parser(preserve_links=True).parse(content):
			if 'blockquote_open' == block.type:
				quote_depth += 1
			elif 'blockquote_close' == block.type:
				quote_depth -= 1
			elif not quote_depth:
				if 'html_block' == block.type:
					html.feed(block.content)
				LinkAuditor.__collect_authored_tokens(block.children or [], targets, html)
		return list(dict.fromkeys(targets + html.links))
	# @used-by :meth:`LinkAuditor.__collect_authored_targets()`
	@staticmethod
	def __collect_authored_tokens(tokens, targets: list[str], html: HtmlReferences) -> None:
		for token in tokens:
			if 'link_open' == token.type:
				targets.append(token.attrGet('href'))
			elif 'image' == token.type:
				targets.append(token.attrGet('src'))
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type:
				targets.extend(dfh_document_urls(token.content))
	# @used-by :meth:`LinkAuditor.references()`
	@staticmethod
	def __collect_block_refs(tokens, links: list[str], html: HtmlReferences, include_code: bool) -> None:
		depth = 0
		for token in tokens:
			if 'link_open' == token.type:
				depth += 1
				links.append(token.attrGet('href'))
			elif 'link_close' == token.type:
				depth -= 1
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type and 0 == depth:
				links.extend(dfh_bare_urls(token.content))
			elif 'code_inline' == token.type and include_code:
				links.extend(dfh_bare_urls(token.content))
	# @used-by :meth:`LinkAuditor.validate_file()`
	@staticmethod
	def __resolve_local_path_text(href: str) -> tuple[str | None, str]:
		parsed = urlsplit(href)
		win_path = bool(re.match('^[A-Za-z]:[/\\\\]', href))
		if (parsed.scheme and 'file' != parsed.scheme and (not win_path)) or href.startswith('#'):
			r: tuple[str | None, str] = (None, '')
		else:
			path_text = unquote(urldefrag(href)[0] if win_path else parsed.path)
			if 'file' == parsed.scheme:
				if parsed.netloc and 'localhost' != parsed.netloc:
					path_text = parsed.netloc + path_text if re.fullmatch('[A-Za-z]:', parsed.netloc) else f'//{parsed.netloc}{path_text}'
				if re.match('^/[A-Za-z]:/', path_text):
					path_text = path_text[1:]
			r = (path_text or None, unquote(parsed.fragment))
		return r
	# @used-by :meth:`LinkAuditor.validate_file()`
	@classmethod
	def __validate_local_target(cls, file_path: Path, href: str, path_text: str, fragment: str) -> str | None:
		target = (file_path.parent / path_text).resolve()
		if not target.exists():
			from agent_tools.journal import resolve_migrated_step_file
			migrated = resolve_migrated_step_file(target)
			target = migrated if migrated.exists() else target
		if not target.exists():
			r: str | None = f'Missing local file: {href}'
		elif target.is_dir():
			r = f'A directory link cannot have a document anchor: {href}' if fragment else None
		else:
			r = cls.__validate_target_fragment(target, href, fragment) if fragment else None
		return r
	# @used-by :meth:`LinkAuditor.__validate_local_target()`
	@classmethod
	def __validate_target_fragment(cls, target: Path, href: str, fragment: str) -> str | None:
		r: str | None = None
		suf = target.suffix.lower()
		if suf in ('.md', '.html', '.htm'):
			other = target.read_text(encoding='utf-8')
			ids = set(cls.references(other)[1]) | MarkdownHeadingParser(other).parse()[1]
			if fragment not in ids:
				r = f'Missing cross-file anchor: {href}'
		elif '.json' == suf:
			value = json.loads(target.read_text(encoding='utf-8'))
			try:
				from agent_tools.evidence import resolve_pointer
				resolve_pointer(value, fragment)
			except (KeyError, ValueError, IndexError, TypeError):
				r = f'Missing JSON pointer: {href}'
		return r
	# @used-by :func:`agent_tools.links.chat_reply_link_issues()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__init__()`
	@classmethod
	def chat_reply_link_issues(cls, content: str, *, root: Path | None=None) -> list[str]:
		from agent_tools.repo_link_gate import chat_repo_link_issues
		return cls.readable_link_issues(content, allow_unencoded_file_uri=True) + chat_repo_link_issues(content, root=root)
	# @used-by :func:`agent_tools.links.readable_link_issues()`
	# @used-by :meth:`LinkAuditor.chat_reply_link_issues()`
	# @used-by :meth:`LinkAuditor.validate_content()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
	@classmethod
	def readable_link_issues(cls, content: str, *, allow_unencoded_file_uri: bool=False) -> list[str]:
		errors: list[str] = []
		for target in cls.__collect_authored_targets(content):
			if allow_unencoded_file_uri and target.lower().startswith('file:///') and ('%' not in target):
				target_check = re.sub('^file:///+(?=[A-Za-z]:/)', '', target, flags=re.IGNORECASE)
				if dfh_readable_reference(target_check) == target_check:
					continue
			readable = dfh_readable_reference(target)
			if target != readable:
				errors.append(f'LINK-5: Use a readable document link: {readable} (instead of {target})')
		return errors
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_source_links()`
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_urls()`
	# @used-by :func:`agent_tools.links.references()`
	# @used-by :meth:`Df.Harness.Research.MarkdownExtractor.MarkdownExtractor.extract()`
	# @used-by :meth:`LinkAuditor.__validate_target_fragment()`
	# @used-by :meth:`LinkAuditor.validate_content()`
	# @used-by :meth:`LinkAuditor.validate_file()`
	@classmethod
	def references(cls, content: str, include_code: bool=False) -> tuple[list[str], list[str]]:
		links: list[str] = []
		html = HtmlReferences()
		for block in dfh_markdown_it_parser(allow_file_links=True).parse(content):
			if 'html_block' == block.type:
				html.feed(block.content)
			cls.__collect_block_refs(block.children or [], links, html, include_code)
		return (links + html.links, html.anchors)
	# @used-by :func:`agent_tools.links.validate_content()`
	# @used-by :meth:`LinkAuditor.validate_file()`
	@classmethod
	def validate_content(cls, content: str, *, local_anchors: bool=False, unique_urls: bool=False, include_code: bool=False, readable_links: bool=False) -> list[str]:
		links, anchors = cls.references(content, include_code)
		errors = [f'Duplicate explicit HTML anchor: {anchor}' for anchor, count in Counter(anchors).items() if 1 < count]
		avail = set(anchors) | MarkdownHeadingParser(content).parse()[1]
		for url in links:
			err = cls.__check_url_syntax(url, avail, local_anchors)
			if err:
				errors.append(err)
		if unique_urls:
			errors.extend((f'Repeated URL ({count}): {url}' for url, count in Counter(links).items() if 1 < count and url.startswith(('http://', 'https://'))))
		if readable_links:
			errors.extend(cls.readable_link_issues(content))
		return errors
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.__check_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_link_auditor_and_observation_bundle_scanner()`
	def validate_file(self) -> list[str]:
		file_path = self.__file_path
		try:
			file_path = file_path.resolve()
			content = file_path.read_text(encoding='utf-8')
			from agent_tools.repo_link_gate import file_repo_link_issues
			errors = self.validate_content(content, **self.__options) + file_repo_link_issues(file_path, content)
			for href in self.references(content, self.__options.get('include_code', False))[0]:
				path_text, fragment = self.__resolve_local_path_text(href)
				if path_text:
					err = self.__validate_local_target(file_path, href, path_text, fragment)
					if err:
						errors.append(err)
			r = errors
		except (OSError, UnicodeError, ValueError) as exc:
			r = [f'{file_path}: {exc}']
		return r
