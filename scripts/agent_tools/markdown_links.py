# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import re
from urllib.parse import unquote, urldefrag, urlsplit
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.text.trim import df_trim_text_left
from .links import readable_reference
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`iter_inline_segments()`
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
	r = (href, ''.join(parts), pos)
	return r
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`agent_tools.links.decode_file_uri()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_file_uri()`
def decode_file_uri(reference: str, *, reject_remote: bool=False) -> str:
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
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def display_address(href):
	value = urlsplit(readable_reference(href))
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	host = str(df_trim_text_left(value.hostname or '', 'www.'))
	if value.port and value.port != {'http': 80, 'https': 443}.get(value.scheme):
		host += ':' + str(value.port)
	r = host + value.path + ('?' + value.query if value.query else '') + ('#' + value.fragment if value.fragment else '')
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def inline_links(tokens, *, include_images: bool=True):
	for item in iter_inline_segments(tokens, include_images=include_images):
		if 'link' == item[0]:
			yield (item[1], item[2])
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`inline_links()`
# @used-by :func:`numeric_text()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._extract_markdown_refs()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def iter_inline_segments(tokens, *, include_images: bool=True):
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
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :meth:`Df.Harness.Analysis.Claim.StandaloneNumberExtractor.StandaloneNumberExtractor.extract()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def numeric_text(text):
	engine = parser()
	environment = {}
	engine.parse(text, environment)
	result = []
	for line in text.splitlines():
		tokens = engine.parseInline(line, environment)[0].children or []
		pieces = []
		# 2026-11-23
		# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
		# https://github.com/dmitry-ai/harness/issues/76
		for item in iter_inline_segments(tokens):
			if 'link' == item[0]:
				if not technical_label(item[2], item[1]):
					pieces.append(item[2])
			elif item[1].type in ('text', 'code_inline', 'html_inline', 'image'):
				pieces.append(item[2])
		result.append(''.join(pieces))
	r = '\n'.join(result)
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :func:`agent_tools.links.parse_markdown_headings()`
# @used-by :func:`agent_tools.links.readable_link_issues()`
# @used-by :func:`agent_tools.links.references()`
# @used-by :func:`agent_tools.source_grounding.markdown_parser()`
# @used-by :func:`numeric_text()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__authored_targets()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def parser(*, preserve_links: bool=False, allow_file_links: bool=False, html: bool=True):
	try:
		from markdown_it import MarkdownIt
	except ImportError as exc:
		requirements = Path(__file__).resolve().parents[1] / 'requirements-agent-tools.txt'
		raise RuntimeError(f'Install {requirements} with this Python interpreter') from exc
	r = MarkdownIt('commonmark', {'html': True}) if html else MarkdownIt('commonmark')
	if preserve_links:
		r.normalizeLink = lambda value: value
		r.validateLink = lambda value: True
	elif allow_file_links:
		validate_uri = r.validateLink
		r.validateLink = lambda value: value.lower().startswith('file:') or validate_uri(value)
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`numeric_text()`
def technical_label(label, href):
	if not label or any((c.isspace() for c in label)):
		r = False
	else:
		try:
			value = urlsplit(label if '://' in label else 'https://' + label)
			target = urlsplit(href)
			# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
			r = bool(value.hostname and target.hostname and (str(df_trim_text_left(value.hostname, 'www.')).lower() == str(df_trim_text_left(target.hostname, 'www.')).lower()))
		except ValueError:
			r = False
	return r
