# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ResponseEvidenceAuditor class into response_grounding.py from response_source_and_kb_issues and helpers in completion.py":
# https://github.com/dmitry-ai/harness/issues/56
import json
from pathlib import Path
import re
from urllib.parse import unquote, urldefrag, urlsplit
from markdown_it import MarkdownIt
from .links import _bare_urls, readable_link_issues
from .research import MAX_BYTES, _CHALLENGE_RE
from .source_grounding import _is_normative_harness_doc, local_source_grounding_issues
class ResponseEvidenceAuditor:
	def __init__(self, root: Path, response: str, requests: list[dict], *, touched_files=None):
		self.root = Path(root).resolve()
		self.response = response
		self.requests = requests
		self.touched_files = touched_files
		self.errors = list(readable_link_issues(response, allow_unencoded_file_uri=True))
		self.authored_links: list[tuple[str, str]] = []
		self.authored_urls: list[str] = []
		self.attributed_quotes: list[tuple[str, str]] = []
		self.client_urls: set[str] = set()
		self.observed_urls: set[str] = set()
		self.observed_topics: set[tuple[str, str]] = set()
		self.observed_titles: dict[str, str] = {}
		self.observed_topic_titles: dict[tuple[str, str], str] = {}
		self.observed_anchors: dict[str, set[str]] = {}
		self.observed_texts: dict[str, list[str]] = {}
		self.invalid_observations: dict[str, str] = {}
	def _check_external_refs(self) -> None:
		for label, href in self.authored_links:
			if _is_descriptive_title_label(label, href):
				nu = _norm_url(href)
				tk = _discourse_topic_key(nu)
				obs_title = self.observed_titles.get(nu) or (self.observed_topic_titles.get(tk) if tk else None)
				if obs_title and (not _titles_compatible(label, obs_title)):
					self.errors.append(f'VERIFY-1 / LINK-1: Link title "{label}" for {href} contradicts saved observation title "{obs_title}"')
		for label, href in self.authored_links:
			host = (urlsplit(href).hostname or '').lower()
			if host not in ('localhost', '127.0.0.1', '::1'):
				nu = _norm_url(href)
				tk = _discourse_topic_key(nu)
				if nu not in self.client_urls:
					if nu not in self.observed_urls and (not tk or tk not in self.observed_topics):
						if nu in self.invalid_observations:
							self.errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no valid saved observation in \ua616/KB/Evidence ({self.invalid_observations[nu]})')
						else:
							self.errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no saved observation in \ua616/KB/Evidence/HTTP or \ua616/KB/Evidence')
					else:
						frag = urlsplit(href).fragment
						if frag and (not re.fullmatch('L\\d+(?:-L?\\d+)?', frag)) and (nu in self.observed_anchors):
							unquoted_frag = unquote(frag)
							if frag not in self.observed_anchors[nu] and unquoted_frag not in self.observed_anchors[nu] and ('anchor_exception' not in self.response):
								self.errors.append(f'VERIFY-1 / LINK-2: External link [{label}]({href}) references anchor "#{frag}" which is absent from the saved observation in \ua616/KB/Evidence')
		for href, q_raw in self.attributed_quotes:
			nu = _norm_url(href)
			if nu not in self.client_urls and nu in self.observed_texts and self.observed_texts[nu]:
				obs_blob = ' '.join((_norm_quote_text(t) for t in self.observed_texts[nu]))
				segments = [_norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[\\u2026\\]|\\(\\u2026\\)|\\.{3,}|\\u2026', q_raw)]
				segments = [s for s in segments if 15 <= len(s)]
				if segments and (not any((s in obs_blob for s in segments))):
					preview = ' '.join(q_raw.split())[:80]
					self.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {href} is absent from the saved observation in \ua616/KB/Evidence')
	def _check_kb_membership(self) -> None:
		if (self.root / '\ua616/project.json').is_file() and (self.root / '\ua616/KB').is_dir():
			kb_urls = set(self.client_urls)
			kb_topics: set[tuple[str, str]] = set()
			kb_files = list((self.root / '\ua616/KB').rglob('*.md')) + (list((self.root / 'KB').rglob('*.md')) if (self.root / 'KB').is_dir() else [])
			analysis_file = self.root / '\ua616/KB/Analysis.json'
			if analysis_file.is_file():
				kb_files.append(analysis_file)
			for kb_file in kb_files:
				try:
					txt = kb_file.read_text(encoding='utf-8')
				except OSError:
					continue
				for u in _bare_urls(txt):
					nu = _norm_url(u)
					kb_urls.add(nu)
					tk = _discourse_topic_key(nu)
					if tk:
						kb_topics.add(tk)
			for u in dict.fromkeys(self.authored_urls):
				nu = _norm_url(u)
				tk = _discourse_topic_key(nu)
				if nu not in kb_urls and (not tk or tk not in kb_topics):
					self.errors.append(f'KB-1 / KB-3: External URL in response is missing from \ua616/KB modules/Analysis.json (record verified sources in \ua616/KB before answer-prepare): {u}')
	def _check_local_grounding(self) -> None:
		grounding_cache: dict = {}
		for iss in local_source_grounding_issues(self.root, self.response, observed_texts=self.observed_texts, cache=grounding_cache):
			if iss not in self.errors:
				self.errors.append(iss)
		for tf in self.touched_files or []:
			tf_str = str(tf).strip()
			tf_norm = '/' + tf_str.replace('\\', '/').lower().lstrip('/')
			if tf_str and tf_norm.endswith('.md') and ('/req/' not in tf_norm) and ('/res/' not in tf_norm) and ('/source/' not in tf_norm) and (not tf_norm.endswith('/source.md')) and (not _is_normative_harness_doc(Path(tf_norm))):
				try:
					tf_path = Path(tf_str)
					tf_path = tf_path.resolve() if tf_path.is_absolute() else (self.root / tf_path).resolve()
					if tf_path.is_file():
						tf_text = tf_path.read_text(encoding='utf-8', errors='replace')
						for iss in local_source_grounding_issues(self.root, tf_text, doc_path=tf_path, observed_texts=self.observed_texts, cache=grounding_cache):
							msg = f'{tf_path.name} ({tf_path.parent.parent.name}): {iss}'
							if msg not in self.errors:
								self.errors.append(msg)
				except OSError:
					pass
	def _collect_client_urls(self) -> None:
		for req in self.requests or []:
			for u in _bare_urls(req.get('text', '') if isinstance(req, dict) else str(req)):
				self.client_urls.add(_norm_url(u))
		for pfile in (self.root / '\ua616/project.json', self.root / 'KB/Project.md', self.root / '\ua616/KB/Project.md'):
			if pfile.is_file():
				try:
					for u in _bare_urls(pfile.read_text(encoding='utf-8')):
						self.client_urls.add(_norm_url(u))
				except OSError:
					pass
	def _extract_markdown_refs(self) -> None:
		parser = MarkdownIt('commonmark', {'html': True})
		parser.normalizeLink = lambda value: value
		parser.validateLink = lambda value: True
		quote_depth = 0
		last_para_ext_href = None
		for block in parser.parse(self.response):
			if 'blockquote_open' == block.type:
				quote_depth += 1
			elif 'blockquote_close' == block.type:
				quote_depth -= 1
			elif block.type in ('fence', 'code_block'):
				last_para_ext_href = None
			elif 0 < quote_depth:
				if 'inline' == block.type and block.content:
					bq_ext_hrefs = [tok.attrGet('href') or '' for tok in (block.children or []) if 'link_open' == tok.type and (tok.attrGet('href') or '').startswith(('http://', 'https://'))]
					target_href = bq_ext_hrefs[-1] if bq_ext_hrefs else last_para_ext_href
					if target_href:
						guillemets = re.findall('\u00ab([^\u00bb]{20,})\u00bb', block.content)
						backtick_quotes = re.findall('`"([^"\\n]{20,})"`', block.content)
						if guillemets or backtick_quotes:
							for gq in guillemets + backtick_quotes:
								self.attributed_quotes.append((target_href, gq))
						else:
							m_orig = re.search('(?:\\u041e\\u0440\\u0438\\u0433\\u0438\\u043d\\u0430\\u043b|Original)\\s*:\\s*["\u00ab]?(.{20,})["\u00bb]?$', block.content.strip(), re.I | re.S)
							if m_orig:
								self.attributed_quotes.append((target_href, m_orig.group(1).strip(' "\u00ab\u00bb')))
			elif block.children:
				children = block.children
				ext_in_block: list[str] = []
				has_local_link = False
				idx = 0
				while idx < len(children):
					token = children[idx]
					if 'link_open' != token.type:
						if 'text' == token.type:
							for u in _bare_urls(token.content):
								if u.startswith(('http://', 'https://')):
									self.authored_urls.append(u)
									ext_in_block.append(u)
						idx += 1
					else:
						href = token.attrGet('href') or ''
						label_parts: list[str] = []
						idx += 1
						depth = 1
						while idx < len(children) and 0 < depth:
							inner = children[idx]
							if 'link_open' == inner.type:
								depth += 1
							elif 'link_close' == inner.type:
								depth -= 1
							elif 0 < depth and inner.type in ('text', 'code_inline'):
								label_parts.append(inner.content)
							idx += 1
						label = ' '.join(''.join(label_parts).split())
						if href.startswith(('http://', 'https://')):
							self.authored_links.append((label, href))
							self.authored_urls.append(href)
							ext_in_block.append(href)
						elif href:
							has_local_link = True
				if has_local_link:
					last_para_ext_href = None
				elif ext_in_block:
					last_para_ext_href = ext_in_block[-1]
					if 1 == len(ext_in_block) and block.content:
						for gq in re.findall('\u00ab([^\u00bb]{25,})\u00bb', block.content):
							self.attributed_quotes.append((ext_in_block[0], gq))
						for bq in re.findall('`"([^"\\n]{25,})"`', block.content):
							self.attributed_quotes.append((ext_in_block[0], bq))
	def _ingest_evidence_files(self) -> None:
		needs_ev_scan = any((_is_descriptive_title_label(label, href) or ((urlsplit(href).hostname or '').lower() not in ('localhost', '127.0.0.1', '::1') and _norm_url(href) not in self.client_urls) for label, href in self.authored_links)) or any((_norm_url(href) not in self.client_urls for href, _ in self.attributed_quotes))
		ev_dirs: list[Path] = []
		if needs_ev_scan:
			if (self.root / '_/\ua616/KB/Evidence').is_dir():
				ev_dirs.append((self.root / '_/\ua616/KB/Evidence').resolve())
			elif (self.root / '\ua616/KB/Evidence').is_dir():
				ev_dirs.append((self.root / '\ua616/KB/Evidence').resolve())
		for ev_dir in ev_dirs:
			for jfile in ev_dir.rglob('*.json'):
				if not jfile.name.startswith('extracted-'):
					try:
						if jfile.stat().st_size <= 4 * 1024 * 1024:
							data = json.loads(jfile.read_text(encoding='utf-8'))
							if isinstance(data, dict):
								if 'observation.json' == jfile.name:
									self._ingest_observation_bundle(jfile, data)
								else:
									src_u = data.get('url') or data.get('html_url') or data.get('source') or ''
									host = (urlsplit(src_u).hostname or '').lower() if isinstance(src_u, str) and src_u.startswith(('http://', 'https://')) else ''
									self._ingest_json_observations(data, host)
					except (OSError, ValueError):
						continue
	def _ingest_json_observations(self, parsed: dict, default_host: str) -> None:
		if isinstance(parsed, dict):
			u = parsed.get('url') or parsed.get('html_url')
			if isinstance(u, str) and u.startswith(('http://', 'https://')):
				nu = _norm_url(u)
				self.observed_urls.add(nu)
				if isinstance(parsed.get('title'), str) and parsed['title'].strip():
					self.observed_titles.setdefault(nu, ' '.join(parsed['title'].split()))
				for field in ('body', 'text', 'title'):
					val = parsed.get(field)
					if isinstance(val, str) and val.strip():
						self.observed_texts.setdefault(nu, []).append(val)
			if isinstance(parsed.get('title'), str) and parsed['title'].strip() and default_host and isinstance(parsed.get('id'), int):
				tk = (default_host.lower(), str(parsed['id']))
				self.observed_topics.add(tk)
				self.observed_topic_titles.setdefault(tk, ' '.join(parsed['title'].split()))
			topics: list = []
			if isinstance(parsed.get('topic_list'), dict) and isinstance(parsed['topic_list'].get('topics'), list):
				topics.extend(parsed['topic_list']['topics'])
			if isinstance(parsed.get('topics'), list):
				topics.extend(parsed['topics'])
			for topic in topics:
				if isinstance(topic, dict) and isinstance(topic.get('id'), int) and isinstance(topic.get('title'), str):
					t = ' '.join(topic['title'].split())
					tid = str(topic['id'])
					host = default_host
					tu = topic.get('url')
					if isinstance(tu, str) and tu.startswith(('http://', 'https://')):
						nu = _norm_url(tu)
						self.observed_urls.add(nu)
						self.observed_titles.setdefault(nu, t)
						host = host or (urlsplit(nu).hostname or '')
					if host:
						tk = (host.lower(), tid)
						self.observed_topics.add(tk)
						self.observed_topic_titles.setdefault(tk, t)
						short_u = f'https://{host.lower()}/t/{tid}'
						self.observed_urls.add(short_u)
						self.observed_titles.setdefault(short_u, t)
						slug = topic.get('slug')
						if isinstance(slug, str) and slug:
							slug_u = f'https://{host.lower()}/t/{slug}/{tid}'
							self.observed_urls.add(slug_u)
							self.observed_titles.setdefault(slug_u, t)
	def _ingest_observation_bundle(self, jfile: Path, data: dict) -> None:
		urls_here = [u for u in (data.get('url'), data.get('final_url')) if isinstance(u, str) and u.startswith(('http://', 'https://'))]
		host = (urlsplit(urls_here[0]).hostname or '').lower() if urls_here else ''
		valid_status = not data.get('error') and ('dom' == data.get('kind') or 200 <= (data.get('status') or 0) < 300)
		is_shell_or_empty = False
		shell_reason = None
		ext_titles: list[str] = []
		ext_anchors: set[str] = set()
		ext_texts: list[str] = []
		has_html_anchors = False
		ext_files = list(jfile.parent.glob('extracted-*.json'))
		for ext_file in ext_files:
			try:
				ext = json.loads(ext_file.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(ext, dict):
				if True is ext.get('browser_check_required'):
					is_shell_or_empty = True
					shell_reason = 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)'
				elif 'headings' in ext and None is ext.get('sitemap') and (0 == ext.get('word_count', 0)):
					is_shell_or_empty = True
					shell_reason = 'word_count=0 (empty HTML shell)'
				t = (ext.get('title') or '').strip()
				if not t and isinstance(ext.get('headings'), list):
					h1s = [h.get('text', '').strip() for h in ext['headings'] if isinstance(h, dict) and 1 == h.get('level') and h.get('text')]
					if h1s:
						t = h1s[0]
				if t:
					ext_titles.append(t)
				if isinstance(ext.get('anchors'), list):
					has_html_anchors = True
					ext_anchors.update((str(a) for a in ext['anchors'] if a))
				if isinstance(ext.get('text'), str) and ext['text'].strip():
					ext_texts.append(ext['text'])
		resp_bin = jfile.parent / 'response.bin'
		if resp_bin.is_file():
			try:
				if resp_bin.stat().st_size <= MAX_BYTES:
					raw_text = resp_bin.read_bytes().decode(data.get('charset') or 'utf-8', errors='replace')
					ctype = (data.get('content_type') or '').lower()
					is_html = 'html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html'))
					if is_html:
						if not ext_files:
							body_plain = re.sub('<(?:script|style|head|title)[^>]*>.*?</(?:script|style|head|title)>|<[^>]+>', ' ', raw_text, flags=re.I | re.S)
							if _CHALLENGE_RE.search(raw_text) or not re.findall('\\w+', body_plain):
								is_shell_or_empty = True
								shell_reason = 'unextracted HTML JS challenge or empty shell'
						has_html_anchors = True
						for m_id in re.finditer('\\b(?:id|name)=["\\\']([^"\\\']+)["\\\']', raw_text, re.I):
							ext_anchors.add(m_id.group(1))
						m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
						if m_t:
							t = ' '.join(m_t.group(1).split())
							if t:
								ext_titles.append(t)
					if raw_text.strip():
						ext_texts.append(raw_text)
					if ('json' in ctype or raw_text.lstrip().startswith('{')) and valid_status and (not is_shell_or_empty):
						self._ingest_json_observations(json.loads(raw_text), host)
			except (OSError, ValueError):
				pass
		if not (valid_status and (not is_shell_or_empty)):
			reason = shell_reason or f"error={data.get('error')} status={data.get('status')}"
			for u in urls_here:
				self.invalid_observations.setdefault(_norm_url(u), reason)
		else:
			for u in urls_here:
				nu = _norm_url(u)
				self.observed_urls.add(nu)
				tk = _discourse_topic_key(nu)
				if tk:
					self.observed_topics.add(tk)
				for t in ext_titles:
					self.observed_titles.setdefault(nu, t)
					if tk:
						self.observed_topic_titles.setdefault(tk, t)
				if has_html_anchors:
					self.observed_anchors.setdefault(nu, set()).update(ext_anchors)
				if ext_texts:
					self.observed_texts.setdefault(nu, []).extend(ext_texts)
	def validate(self) -> list[str]:
		self._extract_markdown_refs()
		if self.authored_urls:
			self._collect_client_urls()
			self._ingest_evidence_files()
			self._check_kb_membership()
			self._check_external_refs()
		self._check_local_grounding()
		return self.errors
def _discourse_topic_key(url: str):
	m = re.match('^https?://([^/:?#]+)/t/(?:[^/?#]+/)?(\\d+)(?:$|[/?#])', url.strip(), re.I)
	return (m.group(1).lower(), m.group(2)) if m else None
def _is_descriptive_title_label(label: str, href: str) -> bool:
	text = (label or '').strip()
	if not text or text.lower().startswith(('http://', 'https://', 'file:')):
		r = False
	else:
		host = (urlsplit(href).hostname or '').lower()
		if text.lower() in (host, f'www.{host}'):
			r = False
		else:
			words = re.findall('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u04510-9]{2,}', text)
			r = not (len(text.split()) < 3 or len(words) < 3 or len(text) < 15)
	return r
def _norm_quote_text(value: str) -> str:
	cleaned = re.sub('[`*_~]+', '', value or '')
	cleaned = cleaned.replace('\u00a0', ' ').replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
	return ' '.join(cleaned.split()).lower()
def _norm_url(url: str) -> str:
	return urldefrag(url.strip())[0].rstrip('/')
def _titles_compatible(claimed: str, observed: str) -> bool:
	c_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', claimed.lower()) if 3 <= len(w)]
	o_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', observed.lower()) if 3 <= len(w)]
	if not c_tokens or not o_tokens:
		r = True
	else:
		c_str = ' '.join(c_tokens)
		o_str = ' '.join(o_tokens)
		if c_str in o_str or o_str in c_str:
			r = True
		else:
			c_set, o_set = (set(c_tokens), set(o_tokens))
			r = 0.6 <= len(c_set & o_set) / max(1, len(c_set))
	return r
def response_source_and_kb_issues(root: Path, response: str, requests: list[dict], *, touched_files=None) -> list[str]:
	return ResponseEvidenceAuditor(root, response, requests, touched_files=touched_files).validate()
