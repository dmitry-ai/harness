# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from Df.Harness.lib.journal_core import dfh_resolve_migrated_step_file
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_authored_nonquote_hrefs()`
def _collect_inline_hrefs(block, html, hrefs: list[str], bare_urls_fn) -> None:
	depth = 0
	for token in block.children or []:
		if 'link_open' == token.type:
			depth += 1
			if token.attrGet('href'):
				hrefs.append(token.attrGet('href'))
		elif 'link_close' == token.type:
			depth = max(0, depth - 1)
		elif 'html_inline' == token.type:
			html.feed(token.content)
		elif 'text' == token.type and 0 == depth:
			hrefs.extend(bare_urls_fn(token.content))
# @used-by :func:`_validate_local_href()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_compaction_and_response_links()`
def _normalize_file_href_path(href: str, parsed, windows_path: bool) -> str:
	path_text = unquote(urldefrag(href)[0] if windows_path else parsed.path)
	if 'file' == parsed.scheme.lower():
		if parsed.netloc and 'localhost' != parsed.netloc:
			path_text = parsed.netloc + path_text if re.fullmatch('[A-Za-z]:', parsed.netloc) else f'//{parsed.netloc}{path_text}'
		if re.match('^/[A-Za-z]:/', path_text):
			path_text = path_text[1:]
	return path_text
# @used-by :func:`dfh_response_link_issues()`
def _resolve_base_dirs(root_p: Path, response_path: Path | None, scratch_dir: Path | None) -> list[Path]:
	base_dirs = [root_p]
	if None is not response_path and '-' != str(response_path):
		try:
			rp_res = Path(response_path).resolve()
			scr_res = Path(scratch_dir).resolve() if None is not scratch_dir else None
			in_scratch = None is not scr_res and (rp_res == scr_res or rp_res.is_relative_to(scr_res))
			if rp_res.is_relative_to(root_p) and (not in_scratch) and rp_res.parent not in base_dirs:
				base_dirs.append(rp_res.parent)
		except OSError:
			pass
	return base_dirs
# @used-by :func:`_validate_local_href()`
def _resolve_local_target(path_text: str, base_dirs: list[Path]) -> Path | None:
	p_cand = Path(path_text)
	target: Path | None = None
	if p_cand.is_absolute():
		resolved_c = p_cand.resolve()
		target = resolved_c if resolved_c.exists() else dfh_resolve_migrated_step_file(resolved_c)
	else:
		for bdir in base_dirs:
			resolved_c = (bdir / p_cand).resolve()
			if resolved_c.exists():
				target = resolved_c
				break
			mig = dfh_resolve_migrated_step_file(resolved_c)
			if mig.exists():
				target = mig
				break
	return target if None is not target and target.exists() else None
# @used-by :func:`_validate_resolved_target()`
def _validate_fragment(target: Path, fragment: str, href: str, references_fn, heading_anchors_fn) -> str | None:
	r: str | None = None
	m_line = re.fullmatch('L(\\d+)(?:-L?(\\d+))?', fragment)
	if m_line:
		r = _validate_line_fragment(target, m_line, fragment, href)
	elif target.suffix.lower() in ('.md', '.html', '.htm'):
		try:
			other = target.read_text(encoding='utf-8')
			if fragment not in (set(references_fn(other)[1]) | heading_anchors_fn(other)):
				r = f'LINK-4: Missing cross-file anchor: {href}'
		except (OSError, UnicodeDecodeError) as exc:
			r = f'LINK-4: {target}: {exc}'
	elif '.json' == target.suffix.lower():
		try:
			from agent_tools.evidence import resolve_pointer
			resolve_pointer(json.loads(target.read_text(encoding='utf-8')), fragment)
		except (OSError, KeyError, ValueError, IndexError, TypeError):
			r = f'LINK-4: Missing JSON pointer: {href}'
	return r
# @used-by :func:`_validate_fragment()`
def _validate_line_fragment(target: Path, m_line, fragment: str, href: str) -> str | None:
	s_ln, e_ln = (int(m_line.group(1)), int(m_line.group(2) or m_line.group(1)))
	try:
		total_ln = max(1, len(target.read_text(encoding='utf-8', errors='replace').splitlines()))
	except OSError:
		total_ln = 0
	return f'LINK-4: Line anchor #{fragment} is out of bounds (1..{total_ln}) for {href}' if 1 > s_ln or s_ln > e_ln or (0 < total_ln and e_ln > total_ln) else None
# @used-by :func:`_validate_single_href()`
def _validate_local_href(href: str, parsed, windows_path: bool, base_dirs: list[Path], references_fn, heading_anchors_fn) -> str | None:
	path_text = _normalize_file_href_path(href, parsed, windows_path)
	if not path_text:
		r: str | None = None
	else:
		target = _resolve_local_target(path_text, base_dirs)
		r = _validate_resolved_target(target, unquote(parsed.fragment), href, references_fn, heading_anchors_fn)
	return r
# @used-by :func:`_validate_local_href()`
def _validate_resolved_target(target: Path | None, fragment: str, href: str, references_fn, heading_anchors_fn) -> str | None:
	if None is target:
		r: str | None = f'LINK-4: Missing local file: {href}'
	elif target.is_dir():
		r = f'LINK-4: A directory link cannot have a document anchor: {href}' if fragment else None
	elif fragment:
		r = _validate_fragment(target, fragment, href, references_fn, heading_anchors_fn)
	else:
		r = None
	return r
# @used-by :func:`dfh_response_link_issues()`
def _validate_single_href(href: str, available_self: set[str], base_dirs: list[Path], references_fn, heading_anchors_fn) -> str | None:
	if not href:
		r: str | None = None
	elif href.startswith('#'):
		r = f'LINK-4: Missing local anchor: {href}' if unquote(href[1:]) not in available_self else None
	else:
		parsed = urlsplit(href)
		windows_path = bool(re.match('^[A-Za-z]:[/\\\\]', href))
		if parsed.scheme and 'file' != parsed.scheme.lower() and (not windows_path):
			r = f'LINK-4: Invalid HTTP URL: {href}' if parsed.scheme.lower() in ('http', 'https') and (not parsed.hostname or any((c.isspace() for c in href))) else None
		else:
			r = _validate_local_href(href, parsed, windows_path, base_dirs, references_fn, heading_anchors_fn)
	return r
# @used-by :func:`dfh_response_link_issues()`
def dfh_authored_nonquote_hrefs(content: str) -> list[str]:
	from agent_tools.links import HTMLReferences, _bare_urls
	from agent_tools.source_grounding import markdown_parser
	hrefs: list[str] = []
	quote_depth = 0
	html = HTMLReferences(authored_only=True)
	for block in markdown_parser().parse(content):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth = max(0, quote_depth - 1)
		elif 0 == quote_depth:
			if 'html_block' == block.type:
				html.feed(block.content)
			_collect_inline_hrefs(block, html, hrefs, _bare_urls)
	return [*hrefs, *html.links]
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_completion_and_grounding_match_chat_reply_link_policy()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_compaction_and_response_links()`
def dfh_response_link_issues(root_p: Path, response: str, *, response_path: Path | None=None, scratch_dir: Path | None=None) -> list[str]:
	from agent_tools.links import chat_reply_link_issues, heading_anchors, references
	errors: list[str] = list(chat_reply_link_issues(response, root=root_p))
	available_self = set(references(response)[1]) | heading_anchors(response)
	base_dirs = _resolve_base_dirs(root_p, response_path, scratch_dir)
	for href in dict.fromkeys(dfh_authored_nonquote_hrefs(response)):
		err = _validate_single_href(href, available_self, base_dirs, references, heading_anchors)
		if None is not err:
			errors.append(err)
	return errors