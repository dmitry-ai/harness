# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
# https://github.com/dmitry-ai/harness/issues/230
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
# https://github.com/dmitry-ai/harness/issues/181
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/76
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add compact evidence-query command and unify collect-http CLI flags":
# https://github.com/dmitry-ai/harness/issues/118
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ResponseEvidenceAuditor class into response_grounding.py from response_source_and_kb_issues and helpers in completion.py":
# https://github.com/dmitry-ai/harness/issues/56
import json
from pathlib import Path
import re
from urllib.parse import unquote, urldefrag, urlsplit
from .evidence_loader import load_observation_bundle
from .links import _bare_urls, chat_reply_link_issues
from .markdown_links import iter_inline_segments
from .research import MAX_BYTES
from .source_grounding import extract_blockquote_quotes, is_normative_harness_doc, local_source_grounding_issues, markdown_parser, norm_quote_text, quote_segments_present
from .statements import analysis_gate_issues, external_anchor_issues
from .upwork_data import extract_upwork_job_url_id
class ResponseEvidenceAuditor:
	def __init__(self, root: Path, response: str, requests: list[dict], *, touched_files=None):
		self.root = Path(root).resolve()
		self.response = response
		self.requests = requests
		self.touched_files = touched_files
		self.errors = list(chat_reply_link_issues(response))
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
						self.errors.extend(external_anchor_issues(label, href, nu, self.observed_anchors, self.response))
		for href, q_raw in self.attributed_quotes:
			nu = _norm_url(href)
			if nu not in self.client_urls and nu in self.observed_texts and self.observed_texts[nu]:
				obs_blob = ' '.join((norm_quote_text(t) for t in self.observed_texts[nu]))
				if not quote_segments_present(q_raw, obs_blob, 15):
					preview = ' '.join(q_raw.split())[:80]
					self.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {href} is absent from the saved observation in \ua616/KB/Evidence')
	def _check_kb_membership(self) -> None:
		from .path_registry import project_paths
		pp = project_paths(self.root, exact_root=True)
		if pp.project_json.is_file() and pp.kb_dir.is_dir():
			kb_urls = set(self.client_urls)
			kb_topics: set[tuple[str, str]] = set()
			kb_files = list(pp.kb_dir.rglob('*.md')) + (list(pp.manual_kb_dir.rglob('*.md')) if pp.manual_kb_dir.is_dir() else [])
			analysis_file = pp.kb_dir / 'Analysis.json'
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
			if tf_str and tf_norm.endswith('.md') and ('/req/' not in tf_norm) and ('/res/' not in tf_norm) and (not re.search('/\\ua66e/(?:[^/]+/)?[\\u227a\\u227b]/', tf_norm)) and ('/source/' not in tf_norm) and (not tf_norm.endswith('/source.md')) and (not is_normative_harness_doc(Path(tf_norm))):
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
		job_ids: set[str] = set()
		for req in self.requests or []:
			for u in _bare_urls(req.get('text', '') if isinstance(req, dict) else str(req)):
				self.client_urls.add(_norm_url(u))
				jid = extract_upwork_job_url_id(u, allow_query_or_fragment=True)
				if jid:
					job_ids.add(jid)
		from .path_registry import project_paths
		pp = project_paths(self.root, exact_root=True)
		pjson = pp.project_json
		if pjson.is_file():
			try:
				pdata = json.loads(pjson.read_text(encoding='utf-8-sig'))
				if isinstance(pdata, dict) and isinstance(pdata.get('job_id'), str) and pdata['job_id'].startswith('~0'):
					job_ids.add(pdata['job_id'].strip())
			except (OSError, ValueError):
				pass
		for pfile in (pjson, pp.manual_kb_dir / 'Project.md', pp.manual_kb_dir / '.md', pp.kb_dir / 'Project.md'):
			if pfile.is_file():
				try:
					for u in _bare_urls(pfile.read_text(encoding='utf-8')):
						self.client_urls.add(_norm_url(u))
						jid = extract_upwork_job_url_id(u, allow_query_or_fragment=True)
						if jid:
							job_ids.add(jid)
				except OSError:
					pass
		for jid in job_ids:
			self.client_urls.add(_norm_url(f'https://upwork.com/jobs/{jid}'))
			self.client_urls.add(_norm_url(f'https://www.upwork.com/jobs/{jid}'))
			for u in self.authored_urls:
				if extract_upwork_job_url_id(u) == jid:
					self.client_urls.add(_norm_url(u))
	def _extract_markdown_refs(self) -> None:
		parser = markdown_parser()
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
						for gq in extract_blockquote_quotes(block.content, min_guillemet_len=20, allow_backtick_quotes=True, min_orig_len=20):
							self.attributed_quotes.append((target_href, gq))
			elif block.children:
				ext_in_block: list[str] = []
				has_local_link = False
				for seg in iter_inline_segments(block.children, include_images=False):
					if 'link' != seg[0]:
						if 'text' == seg[1].type:
							for u in _bare_urls(seg[2]):
								if u.startswith(('http://', 'https://')):
									self.authored_urls.append(u)
									ext_in_block.append(u)
					else:
						href = seg[1]
						label = ' '.join(seg[2].split())
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
			from .path_registry import project_paths
			pp_ev = project_paths(self.root, exact_root=True).evidence_dir
			if pp_ev.is_dir():
				ev_dirs.append(pp_ev.resolve())
			elif (self.root / '_/\ua616/KB/Evidence').is_dir():
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
		bundle = load_observation_bundle(jfile, data, max_bytes=MAX_BYTES)
		if None is not bundle['json_payload']:
			self._ingest_json_observations(bundle['json_payload'], bundle['host'])
		if not bundle['valid']:
			for u in bundle['urls']:
				self.invalid_observations.setdefault(_norm_url(u), bundle['reason'])
		else:
			for u in bundle['urls']:
				nu = _norm_url(u)
				self.observed_urls.add(nu)
				tk = _discourse_topic_key(nu)
				if tk:
					self.observed_topics.add(tk)
				for t in bundle['titles']:
					self.observed_titles.setdefault(nu, t)
					if tk:
						self.observed_topic_titles.setdefault(tk, t)
				if bundle['has_html_anchors']:
					self.observed_anchors.setdefault(nu, set()).update(bundle['anchors'])
				if bundle['texts']:
					self.observed_texts.setdefault(nu, []).extend(bundle['texts'])
	def validate(self) -> list[str]:
		self._extract_markdown_refs()
		if self.authored_urls:
			self._collect_client_urls()
			self._ingest_evidence_files()
			self._check_kb_membership()
			self._check_external_refs()
		self._check_local_grounding()
		self.errors.extend(analysis_gate_issues(self.response, requests=self.requests))
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
