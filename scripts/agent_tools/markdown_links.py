"""Shared Markdown link parsing for quantities and the formatted article profile."""

from urllib.parse import urlsplit

from .links import readable_reference


def parser():
    from markdown_it import MarkdownIt
    return MarkdownIt('commonmark', {'html': True})


def inline_links(tokens):
    """Yield parsed links, including balanced parentheses and reference links."""
    position = 0
    while position < len(tokens):
        token = tokens[position]
        if token.type == 'link_open':
            end = position + 1
            while end < len(tokens) and tokens[end].type != 'link_close':
                end += 1
            label = ''.join(t.content for t in tokens[position + 1:end]
                            if t.type in ('text', 'code_inline', 'image'))
            yield token.attrGet('href') or '', label
            position = end
        position += 1


def technical_label(label, href):
    """Only address-shaped labels are identifiers; prose labels retain quantities."""
    if not label or any(c.isspace() for c in label):
        return False
    try:
        value = urlsplit(label if '://' in label else 'https://' + label)
        target = urlsplit(href)
        return bool(value.hostname and target.hostname and
                    value.hostname.removeprefix('www.').lower() == target.hostname.removeprefix('www.').lower())
    except ValueError:
        return False


def display_address(href):
    value = urlsplit(readable_reference(href))
    host = (value.hostname or '').removeprefix('www.')
    if value.port and value.port != {'http': 80, 'https': 443}.get(value.scheme):
        host += ':' + str(value.port)
    return host + value.path + ('?' + value.query if value.query else '') + ('#' + value.fragment if value.fragment else '')


def numeric_text(text):
    """Preserve all other prose/literals while removing only URL-shaped labels."""
    engine = parser()
    environment = {}
    engine.parse(text, environment)  # Resolve reference-link definitions too.
    result = []
    for line in text.splitlines():
        tokens = engine.parseInline(line, environment)[0].children or []
        pieces, position = [], 0
        while position < len(tokens):
            token = tokens[position]
            if token.type == 'link_open':
                end = position + 1
                while end < len(tokens) and tokens[end].type != 'link_close':
                    end += 1
                label = ''.join(t.content for t in tokens[position + 1:end]
                                if t.type in ('text', 'code_inline', 'image'))
                if not technical_label(label, token.attrGet('href') or ''):
                    pieces.append(label)
                position = end
            elif token.type in ('text', 'code_inline', 'html_inline', 'image'):
                pieces.append(token.content)
            position += 1
        result.append(''.join(pieces))
    return '\n'.join(result)
