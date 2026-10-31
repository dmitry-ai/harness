# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from urllib.parse import urlsplit
from .links import readable_reference
def parser():
	from markdown_it import MarkdownIt
	r = MarkdownIt('commonmark', {'html': True})
	return r
def inline_links(tokens):
	position = 0
	while position < len(tokens):
		token = tokens[position]
		if 'link_open' == token.type:
			end = position + 1
			while end < len(tokens) and 'link_close' != tokens[end].type:
				end += 1
			label = ''.join((t.content for t in tokens[position + 1:end] if t.type in ('text', 'code_inline', 'image')))
			yield (token.attrGet('href') or '', label)
			position = end
		position += 1
def technical_label(label, href):
	if not label or any((c.isspace() for c in label)):
		r = False
	else:
		try:
			value = urlsplit(label if '://' in label else 'https://' + label)
			target = urlsplit(href)
			r = bool(value.hostname and target.hostname and (value.hostname.removeprefix('www.').lower() == target.hostname.removeprefix('www.').lower()))
		except ValueError:
			r = False
	return r
def display_address(href):
	value = urlsplit(readable_reference(href))
	host = (value.hostname or '').removeprefix('www.')
	if value.port and value.port != {'http': 80, 'https': 443}.get(value.scheme):
		host += ':' + str(value.port)
	r = host + value.path + ('?' + value.query if value.query else '') + ('#' + value.fragment if value.fragment else '')
	return r
def numeric_text(text):
	engine = parser()
	environment = {}
	engine.parse(text, environment)
	result = []
	for line in text.splitlines():
		tokens = engine.parseInline(line, environment)[0].children or []
		pieces, position = ([], 0)
		while position < len(tokens):
			token = tokens[position]
			if 'link_open' == token.type:
				end = position + 1
				while end < len(tokens) and 'link_close' != tokens[end].type:
					end += 1
				label = ''.join((t.content for t in tokens[position + 1:end] if t.type in ('text', 'code_inline', 'image')))
				if not technical_label(label, token.attrGet('href') or ''):
					pieces.append(label)
				position = end
			elif token.type in ('text', 'code_inline', 'html_inline', 'image'):
				pieces.append(token.content)
			position += 1
		result.append(''.join(pieces))
	r = '\n'.join(result)
	return r
