# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from Df.Core.lib.text.trim import df_trim_text_left
from Df.Harness.lib.research import dfh_readable_reference
import re
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`dfh_iter_inline_segments()`
def _consume_link(tokens, start: int, label_types: tuple[str, ...]) -> tuple[str, str, int]:
	href = tokens[start].attrGet('href') or ''
	parts, depth, pos = ([], 1, start + 1)
	while pos < len(tokens) and 0 < depth:
		inner = tokens[pos]
		if 'link_open' == inner.type:
			depth += 1
		elif 'link_close' == inner.type:
			depth -= 1
		elif 0 < depth and inner.type in label_types:
			parts.append(inner.content)
		pos += 1
	return (href, ''.join(parts), pos)
# @used-by :func:`Df.Harness.lib.grounding.dfh_resolve_local_href()`
# @used-by :func:`agent_tools.links.decode_file_uri()`
# @used-by :func:`agent_tools.markdown_links.decode_file_uri()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_decode_file_uri(reference: str, *, reject_remote: bool=False) -> str:
	raw = urldefrag((reference or '').strip())[0]
	parsed = urlsplit(raw)
	if 'file' != parsed.scheme.lower():
		r = unquote(raw)
	else:
		if reject_remote and parsed.netloc and 'localhost' != parsed.netloc.lower():
			raise ValueError('Remote file URI is not a local project source')
		path = unquote(parsed.path)
		if parsed.netloc and 'localhost' != parsed.netloc.lower():
			path = parsed.netloc + path
		if re.match('^/[A-Za-z]:/', path):
			path = path[1:]
		r = path
	return r
# @used-by :func:`agent_tools.markdown_links.display_address()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_display_address(href: str, *, trim_fn=None) -> str:
	trimmer = df_trim_text_left if None is trim_fn else trim_fn
	value = urlsplit(dfh_readable_reference(href))
	host = str(trimmer(value.hostname or '', 'www.'))
	if value.port and value.port != {'http': 80, 'https': 443}.get(value.scheme):
		host += ':' + str(value.port)
	return host + value.path + ('?' + value.query if value.query else '') + ('#' + value.fragment if value.fragment else '')
# @used-by :func:`agent_tools.markdown_links.inline_links()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_inline_links(tokens, *, include_images: bool=True):
	for item in dfh_iter_inline_segments(tokens, include_images=include_images):
		if 'link' == item[0]:
			yield (item[1], item[2])
# @used-by :func:`agent_tools.markdown_links.iter_inline_segments()`
# @used-by :func:`dfh_inline_links()`
# @used-by :func:`dfh_numeric_text()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__extract_inline_block_refs()`
def dfh_iter_inline_segments(tokens, *, include_images: bool=True):
	label_types = ('text', 'code_inline', 'image') if include_images else ('text', 'code_inline')
	pos = 0
	while pos < len(tokens):
		token = tokens[pos]
		if 'link_open' != token.type:
			yield ('token', token, token.content)
			pos += 1
		else:
			href, label, pos = _consume_link(tokens, pos, label_types)
			yield ('link', href, label)
# @used-by :func:`Df.Harness.lib.grounding.dfh_markdown_parser()`
# @used-by :func:`agent_tools.markdown_links.parser()`
# @used-by :func:`dfh_numeric_text()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__collect_authored_targets()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.references()`
# @used-by :meth:`Df.Harness.Research.MarkdownHeadingParser.MarkdownHeadingParser.__collect_rows()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_markdown_it_parser(*, preserve_links: bool=False, allow_file_links: bool=False, html: bool=True):
	try:
		from markdown_it import MarkdownIt
	except ImportError as exc:
		requirements = Path(__file__).resolve().parents[3] / 'requirements-agent-tools.txt'
		raise RuntimeError(f'Install {requirements} with this Python interpreter') from exc
	r = MarkdownIt('commonmark', {'html': True}) if html else MarkdownIt('commonmark')
	if preserve_links:
		r.normalizeLink = lambda value: value
		r.validateLink = lambda value: True
	elif allow_file_links:
		validate_uri = r.validateLink
		r.validateLink = lambda value: value.lower().startswith('file:') or validate_uri(value)
	return r
# @used-by :func:`agent_tools.markdown_links.numeric_text()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_numeric_text(text: str, *, trim_fn=None) -> str:
	engine = dfh_markdown_it_parser()
	environment: dict = {}
	engine.parse(text, environment)
	result: list[str] = []
	for line in text.splitlines():
		tokens = engine.parseInline(line, environment)[0].children or []
		pieces: list[str] = []
		for item in dfh_iter_inline_segments(tokens):
			if 'link' == item[0]:
				if not dfh_technical_label(item[2], item[1], trim_fn=trim_fn):
					pieces.append(item[2])
			elif item[1].type in ('text', 'code_inline', 'html_inline', 'image'):
				pieces.append(item[2])
		result.append(''.join(pieces))
	return '\n'.join(result)
# @used-by :func:`agent_tools.markdown_links.technical_label()`
# @used-by :func:`dfh_numeric_text()`
# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
def dfh_technical_label(label: str, href: str, *, trim_fn=None) -> bool:
	if not label or any((c.isspace() for c in label)):
		r = False
	else:
		trimmer = df_trim_text_left if None is trim_fn else trim_fn
		try:
			value = urlsplit(label if '://' in label else 'https://' + label)
			target = urlsplit(href)
			r = bool(value.hostname and target.hostname and (str(trimmer(value.hostname, 'www.')).lower() == str(trimmer(target.hostname, 'www.')).lower()))
		except ValueError:
			r = False
	return r