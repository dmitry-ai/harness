# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
from Df.Harness.Grounding.CliCommandAuditor import CliCommandAuditor
from Df.Harness.Grounding.EvidenceBundleIngestor import EvidenceBundleIngestor
from Df.Harness.Grounding.LocalSourceAuditor import LocalSourceAuditor
from Df.Harness.Research.LinkAuditor import LinkAuditor
# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
from Df.Harness.Research.UserUrlPolicy import UserUrlPolicy
from Df.Harness.lib.grounding import dfh_extract_blockquote_quotes, dfh_is_normative_harness_doc, dfh_markdown_parser, dfh_norm_quote_text, dfh_quote_segments_present
from Df.Harness.lib.grounding_md import dfh_external_anchor_issues
from Df.Harness.lib.markdown import dfh_iter_inline_segments
from Df.Harness.lib.research import dfh_bare_urls
from agent_tools.repo_link_gate import hydrate_local_repo_urls
from agent_tools.upwork_data import extract_upwork_job_url_id
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ResponseAuditor:
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :func:`agent_tools.response_grounding.response_source_and_kb_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_evidence_bundle_ingestor_and_response_auditor()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_tail.DfHarnessS11Wave2CCovTailTests.test_grounding_ingestor_kb_membership_and_locale_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_broken_apex_keeps_www_and_blocks_false_alias()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_response_auditor_aliases_www_subpages_and_blocks_authored_www()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_uncaptured_client_intake_www_url_has_no_deadlock()`
	def __init__(self, root: Path, response: str, requests: list[dict], *, touched_files=None, turn=None, native=None, turn_state=None, skip_df_analysis: bool=False) -> None:
		self.root, self.response, self.requests, self.touched_files, self.turn, self.native, self.turn_state, self.skip_df_analysis = (Path(root).resolve(), response, requests, touched_files, turn, native, turn_state, bool(skip_df_analysis))
		self.errors = list(LinkAuditor.chat_reply_link_issues(response, root=self.root))
		self.local_repo_urls: set[str] = set()
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
		# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
		self.user_facing_urls: list[str] = []
		self.working_apex_hosts: set[str] = set()
		self.failed_apex_hosts: set[str] = set()
	# @used-by unused
	def __getattr__(self, name: str):
		if '_extract_markdown_refs' == name:
			return self.extract_markdown_refs
		raise AttributeError(f'{type(self).__name__!r} object has no attribute {name!r}')
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.validate()`
	def __check_external_refs(self, pp) -> None:
		self.__check_link_titles()
		self.__check_link_observations()
		for href, q_raw in self.attributed_quotes:
			nu = EvidenceBundleIngestor.norm_url(href)
			if nu not in self.client_urls and nu in self.observed_texts and self.observed_texts[nu]:
				obs_blob = ' '.join((dfh_norm_quote_text(t) for t in self.observed_texts[nu]))
				if not dfh_quote_segments_present(q_raw, obs_blob, 15):
					preview = ' '.join(q_raw.split())[:80]
					self.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {href} is absent from the saved observation in \ua616/KB/Evidence')
		policy = UserUrlPolicy(working_apex_hosts=self.working_apex_hosts, failed_apex_hosts=self.failed_apex_hosts, client_site_hosts=self.__collect_client_site_hosts(pp))
		self.errors.extend(policy.check_urls(self.user_facing_urls))
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.validate()`
	def __check_kb_membership(self, pp) -> None:
		if pp.project_json.is_file() and pp.kb_dir.is_dir():
			kb_urls, kb_topics = self.__collect_kb_urls(pp)
			for u in dict.fromkeys(self.authored_urls):
				nu = EvidenceBundleIngestor.norm_url(u)
				tk = EvidenceBundleIngestor.discourse_topic_key(nu)
				if nu not in kb_urls and (not tk or tk not in kb_topics):
					self.errors.append(f'KB-1 / KB-3: External URL in response is missing from \ua616/KB modules/Analysis.json (record verified sources in \ua616/KB before answer-prepare): {u}')
	# @used-by :meth:`ResponseAuditor.__check_external_refs()`
	def __check_link_observations(self) -> None:
		for label, href in self.authored_links:
			host = (urlsplit(href).hostname or '').lower()
			nu = EvidenceBundleIngestor.norm_url(href)
			if host not in ('localhost', '127.0.0.1', '::1') and nu not in self.client_urls:
				tk = EvidenceBundleIngestor.discourse_topic_key(nu)
				if nu not in self.observed_urls and (not tk or tk not in self.observed_topics):
					reason = f' ({self.invalid_observations[nu]})' if nu in self.invalid_observations else ''
					qual = ' valid' if reason else ''
					loc = '\ua616/KB/Evidence' if reason else '\ua616/KB/Evidence/HTTP or \ua616/KB/Evidence'
					self.errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no{qual} saved observation in {loc}{reason}')
				else:
					self.errors.extend(dfh_external_anchor_issues(label, href, nu, self.observed_anchors, self.response))
	# @used-by :meth:`ResponseAuditor.__check_external_refs()`
	def __check_link_titles(self) -> None:
		for label, href in self.authored_links:
			if self.is_descriptive_title_label(label, href):
				nu = EvidenceBundleIngestor.norm_url(href)
				tk = EvidenceBundleIngestor.discourse_topic_key(nu)
				obs_title = self.observed_titles.get(nu) or (self.observed_topic_titles.get(tk) if tk else None)
				if obs_title and (not self.titles_compatible(label, obs_title)):
					self.errors.append(f'VERIFY-1 / LINK-1: Link title "{label}" for {href} contradicts saved observation title "{obs_title}"')
	# @used-by :meth:`ResponseAuditor.validate()`
	def __check_local_grounding(self) -> None:
		grounding_cache: dict = {}
		for iss in LocalSourceAuditor(self.root, self.response, observed_texts=self.observed_texts, cache=grounding_cache).run():
			if iss not in self.errors:
				self.errors.append(iss)
		for tf in self.touched_files or []:
			self.__check_touched_markdown(str(tf).strip(), grounding_cache)
	# @used-by :meth:`ResponseAuditor.__check_local_grounding()`
	def __check_touched_markdown(self, tf_str: str, grounding_cache: dict) -> None:
		tf_norm = '/' + tf_str.replace('\\', '/').lower().lstrip('/')
		if tf_str and tf_norm.endswith('.md') and ('/req/' not in tf_norm) and ('/res/' not in tf_norm) and (not re.search('/\\ua66e/(?:[^/]+/)?[\\u227a\\u227b]/', tf_norm)) and ('/source/' not in tf_norm) and (not tf_norm.endswith('/source.md')) and (not dfh_is_normative_harness_doc(Path(tf_norm))):
			try:
				tf_path = Path(tf_str)
				tf_path = tf_path.resolve() if tf_path.is_absolute() else (self.root / tf_path).resolve()
				if tf_path.is_file():
					tf_text = tf_path.read_text(encoding='utf-8', errors='replace')
					for iss in LocalSourceAuditor(self.root, tf_text, doc_path=tf_path, observed_texts=self.observed_texts, cache=grounding_cache).run():
						msg = f'{tf_path.name} ({tf_path.parent.parent.name}): {iss}'
						if msg not in self.errors:
							self.errors.append(msg)
			except OSError:
				pass
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.__check_external_refs()`
	@staticmethod
	def __collect_client_site_hosts(pp) -> frozenset[str]:
		return UserUrlPolicy.collect_client_site_hosts(pp.kb_dir / 'Analysis.json', pp.project_json)
	# @used-by :meth:`ResponseAuditor.validate()`
	def __collect_client_urls(self) -> None:
		from agent_tools.path_registry import project_paths
		job_ids: set[str] = set()
		for req in self.requests or []:
			self.__record_client_text_urls(req.get('text', '') if isinstance(req, dict) else str(req), job_ids)
		pp = project_paths(self.root, exact_root=True)
		self.__read_project_job_id(pp.project_json, job_ids)
		for pfile in (pp.project_json, pp.manual_kb_dir / 'Project.md', pp.manual_kb_dir / '.md', pp.kb_dir / 'Project.md'):
			if pfile.is_file():
				try:
					self.__record_client_text_urls(pfile.read_text(encoding='utf-8'), job_ids)
				except OSError:
					pass
		self.__expand_upwork_job_urls(job_ids)
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.__check_kb_membership()`
	def __collect_kb_urls(self, pp) -> tuple[set[str], set[tuple[str, str]]]:
		kb_urls = set(self.client_urls) | self.local_repo_urls
		kb_topics: set[tuple[str, str]] = set()
		failed = self.failed_apex_hosts - self.working_apex_hosts
		kb_files = list(pp.kb_dir.rglob('*.md')) + (list(pp.manual_kb_dir.rglob('*.md')) if pp.manual_kb_dir.is_dir() else [])
		analysis_file = pp.kb_dir / 'Analysis.json'
		if analysis_file.is_file():
			kb_files.append(analysis_file)
		for kb_file in kb_files:
			try:
				txt = kb_file.read_text(encoding='utf-8')
			except OSError:
				continue
			for u in dfh_bare_urls(txt):
				self.__record_kb_url(u, failed, kb_urls, kb_topics)
		return (kb_urls, kb_topics)
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.validate()`
	def __expand_client_url_aliases(self) -> None:
		failed = self.failed_apex_hosts - self.working_apex_hosts
		for u in list(self.client_urls):
			alias = UserUrlPolicy.non_www_alias(u)
			if alias and UserUrlPolicy.apex_host(u) not in failed:
				self.client_urls.add(alias)
	# @used-by :meth:`ResponseAuditor.__collect_client_urls()`
	def __expand_upwork_job_urls(self, job_ids: set[str]) -> None:
		for jid in job_ids:
			self.client_urls.add(EvidenceBundleIngestor.norm_url(f'https://upwork.com/jobs/{jid}'))
			self.client_urls.add(EvidenceBundleIngestor.norm_url(f'https://www.upwork.com/jobs/{jid}'))
			for u in self.authored_urls:
				if extract_upwork_job_url_id(u) == jid:
					self.client_urls.add(EvidenceBundleIngestor.norm_url(u))
	# @used-by :meth:`ResponseAuditor.extract_markdown_refs()`
	def __extract_blockquote_refs(self, block, last_para_ext_href: str | None) -> None:
		if 'inline' == block.type and block.content:
			bq_hrefs = [tok.attrGet('href') or '' for tok in (block.children or []) if 'link_open' == tok.type and (tok.attrGet('href') or '').startswith(('http://', 'https://'))]
			target_href = bq_hrefs[-1] if bq_hrefs else last_para_ext_href
			if target_href:
				for gq in dfh_extract_blockquote_quotes(block.content, min_guillemet_len=20, allow_backtick_quotes=True, min_orig_len=20):
					self.attributed_quotes.append((target_href, gq))
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.extract_markdown_refs()`
	def __extract_inline_block_refs(self, block) -> str | None:
		ext_in_block: list[str] = []
		has_local_link = False
		in_g, in_d = (False, False)
		for seg in dfh_iter_inline_segments(block.children, include_images=False):
			if 'link' != seg[0]:
				in_g, in_d = self.__record_text_urls(seg, ext_in_block, in_g, in_d)
			elif seg[1].startswith(('http://', 'https://')):
				self.authored_links.append((' '.join(seg[2].split()), seg[1]))
				self.authored_urls.append(seg[1])
				ext_in_block.append(seg[1])
				if (not in_g) and (not in_d):
					self.user_facing_urls.append(seg[1])
			elif seg[1]:
				has_local_link = True
		r = None if has_local_link or (not ext_in_block) else ext_in_block[-1]
		if None is not r and 1 == len(ext_in_block) and block.content:
			self.__record_single_ext_quotes(ext_in_block[0], block.content)
		return r
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.validate()`
	def __needs_evidence_scan(self, pp) -> bool:
		link_hit = any((self.is_descriptive_title_label(label, href) or ((urlsplit(href).hostname or '').lower() not in ('localhost', '127.0.0.1', '::1') and EvidenceBundleIngestor.norm_url(href) not in self.client_urls) for label, href in self.authored_links))
		www_hit = any((UserUrlPolicy.is_www_host(u) for u in self.user_facing_urls))
		kb_hit = pp.project_json.is_file() and pp.kb_dir.is_dir() and bool(self.authored_urls)
		return link_hit or www_hit or kb_hit or any((EvidenceBundleIngestor.norm_url(href) not in self.client_urls for href, _ in self.attributed_quotes))
	# @used-by :meth:`ResponseAuditor.__collect_client_urls()`
	@staticmethod
	def __read_project_job_id(pjson: Path, job_ids: set[str]) -> None:
		if pjson.is_file():
			try:
				pdata = json.loads(pjson.read_text(encoding='utf-8-sig'))
				if isinstance(pdata, dict) and isinstance(pdata.get('job_id'), str) and pdata['job_id'].startswith('~0'):
					job_ids.add(pdata['job_id'].strip())
			except (OSError, ValueError):
				pass
	# @used-by :meth:`ResponseAuditor.__collect_client_urls()`
	def __record_client_text_urls(self, text: str, job_ids: set[str]) -> None:
		for u in dfh_bare_urls(text):
			self.client_urls.add(EvidenceBundleIngestor.norm_url(u))
			jid = extract_upwork_job_url_id(u, allow_query_or_fragment=True)
			if jid:
				job_ids.add(jid)
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.__collect_kb_urls()`
	@staticmethod
	def __record_kb_url(u: str, failed: set[str], kb_urls: set[str], kb_topics: set[tuple[str, str]]) -> None:
		nu = EvidenceBundleIngestor.norm_url(u)
		kb_urls.add(nu)
		tk = EvidenceBundleIngestor.discourse_topic_key(nu)
		if tk:
			kb_topics.add(tk)
		alias = UserUrlPolicy.non_www_alias(nu)
		if alias and UserUrlPolicy.apex_host(nu) not in failed:
			kb_urls.add(alias)
			atk = EvidenceBundleIngestor.discourse_topic_key(alias)
			if atk:
				kb_topics.add(atk)
	# @used-by :meth:`ResponseAuditor.__extract_inline_block_refs()`
	def __record_single_ext_quotes(self, ext_url: str, content: str) -> None:
		for gq in re.findall('\u00ab([^\u00bb]{25,})\u00bb', content):
			self.attributed_quotes.append((ext_url, gq))
		for bq in re.findall('`"([^"\\n]{25,})"`', content):
			self.attributed_quotes.append((ext_url, bq))
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`ResponseAuditor.__extract_inline_block_refs()`
	def __record_text_urls(self, seg, ext_in_block: list[str], in_g: bool, in_d: bool) -> tuple[bool, bool]:
		if 'text' == seg[1].type:
			for raw_u in dfh_bare_urls(seg[2]):
				u = raw_u.rstrip('\u00bb')
				if u.startswith(('http://', 'https://')):
					self.authored_urls.append(u)
					ext_in_block.append(u)
			clean, in_g, in_d = UserUrlPolicy.strip_inline_quotes(seg[2], in_g, in_d)
			for raw_u in dfh_bare_urls(clean):
				u = raw_u.rstrip('\u00bb')
				if u.startswith(('http://', 'https://')):
					self.user_facing_urls.append(u)
		return (in_g, in_d)
	# @used-by :meth:`ResponseAuditor.__getattr__()`
	# @used-by :meth:`ResponseAuditor.validate()`
	def extract_markdown_refs(self) -> None:
		quote_depth = 0
		last_para_ext_href: str | None = None
		for block in dfh_markdown_parser().parse(self.response):
			if 'blockquote_open' == block.type:
				quote_depth += 1
			elif 'blockquote_close' == block.type:
				quote_depth -= 1
			elif block.type in ('fence', 'code_block'):
				last_para_ext_href = None
			elif 0 < quote_depth:
				self.__extract_blockquote_refs(block, last_para_ext_href)
			elif block.children:
				last_para_ext_href = self.__extract_inline_block_refs(block)
	# @used-by :func:`agent_tools.response_grounding._is_descriptive_title_label()`
	# @used-by :meth:`ResponseAuditor.__check_link_titles()`
	# @used-by :meth:`ResponseAuditor.__needs_evidence_scan()`
	@staticmethod
	def is_descriptive_title_label(label: str, href: str) -> bool:
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
	# @used-by :func:`agent_tools.response_grounding._titles_compatible()`
	# @used-by :meth:`ResponseAuditor.__check_link_titles()`
	@staticmethod
	def titles_compatible(claimed: str, observed: str) -> bool:
		c_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', claimed.lower()) if 3 <= len(w)]
		o_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', observed.lower()) if 3 <= len(w)]
		if not c_tokens or not o_tokens:
			r = True
		elif ' '.join(c_tokens) in ' '.join(o_tokens) or ' '.join(o_tokens) in ' '.join(c_tokens):
			r = True
		else:
			c_set = set(c_tokens)
			r = 0.6 <= len(c_set & set(o_tokens)) / max(1, len(c_set))
		return r
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :func:`agent_tools.response_grounding.response_source_and_kb_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_evidence_bundle_ingestor_and_response_auditor()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_tail.DfHarnessS11Wave2CCovTailTests.test_grounding_ingestor_kb_membership_and_locale_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_broken_apex_keeps_www_and_blocks_false_alias()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_response_auditor_aliases_www_subpages_and_blocks_authored_www()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_uncaptured_client_intake_www_url_has_no_deadlock()`
	def validate(self) -> list[str]:
		self.extract_markdown_refs()
		if self.authored_urls:
			from agent_tools.path_registry import project_paths
			pp = project_paths(self.root, exact_root=True)
			self.__collect_client_urls()
			if self.__needs_evidence_scan(pp):
				EvidenceBundleIngestor(self).ingest()
			self.__expand_client_url_aliases()
			self.local_repo_urls = hydrate_local_repo_urls(self)
			self.__check_kb_membership(pp)
			self.__check_external_refs(pp)
		self.__check_local_grounding()
		# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
		self.errors.extend(CliCommandAuditor.response_turn_gate_issues(self.root, self.response, requests=self.requests, turn=self.turn, native=self.native, turn_state=self.turn_state, skip_df_analysis=self.skip_df_analysis))
		return self.errors