# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.Research.EvidenceGrepper import EvidenceGrepper
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.Research.ObservationBundleScanner import ObservationBundleScanner
import json
import re
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class EvidenceQuerier:
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def __init__(self, root, *, urls=None, include_anchors: bool=False, grep_pattern: str | None=None, context_lines: int=2, max_matches: int=20) -> None:
		self.__root = root
		self.__urls = urls
		self.__include_anchors = include_anchors
		self.__grep_pattern = grep_pattern
		self.__context_lines = context_lines
		self.__max_matches = max_matches
	# @used-by :meth:`EvidenceQuerier.__summarize_bundle()`
	@staticmethod
	def __attach_anchors(entry: dict, state: dict) -> None:
		semantic: list[str] = []
		for a in sorted(state['raw_anchors']):
			if a in state['ambiguous_anchors'] or re.fullmatch('L(?:C)?\\d+(?:-L?(?:C)?\\d+)?', a):
				continue
			if a.startswith('user-content-') and 13 < len(a) and (a[13:] in state['raw_anchors']):
				continue
			semantic.append(a)
		entry['anchors'] = semantic
		sec_idx = []
		for h in state['headings']:
			sa = [str(x) for x in (h.get('section_anchors') or ()) if x and str(x) not in state['ambiguous_anchors']]
			sec_idx.append({'level': h.get('level'), 'heading': h.get('text'), 'anchor': f'#{sa[0]}' if sa else (f"#{h['anchor']}" if h.get('anchor') else None)})
		entry['sections'] = sec_idx
	# @used-by :meth:`EvidenceQuerier.__summarize_bundle()`
	def __attach_grep(self, entry: dict, obs_file: Path, data: dict, state: dict, raw_text: str, blob_lines: list[str], has_lc: bool, rx: re.Pattern) -> None:
		resp_bin = obs_file.parent / 'response.bin'
		if blob_lines:
			matches = EvidenceGrepper(rx, context_lines=self.__context_lines, max_matches=self.__max_matches).grep_blob(blob_lines, has_lc_anchors=has_lc)
		elif not rx.search(state['plain_text'] or raw_text):
			matches = []
		else:
			eff_secs = state['sections']
			if eff_secs and all(('content' not in s for s in eff_secs)) and resp_bin.is_file() and raw_text:
				try:
					live = Extractor(resp_bin.read_bytes(), data.get('content_type') or 'text/html', 'html', data.get('charset') or 'utf-8', status=data.get('status')).extract()
					if isinstance(live.get('sections'), list):
						eff_secs = live['sections']
				except Exception:
					pass
			matches = EvidenceGrepper.grep_sections(eff_secs, state['plain_text'] or raw_text, rx, context_lines=self.__context_lines, max_matches=self.__max_matches)
		entry['match_count'] = len(matches)
		entry['matches'] = matches
	# @used-by :meth:`EvidenceQuerier.__summarize_bundle()`
	@classmethod
	def __build_entry(cls, obs_file: Path, kb_dir: Path, data: dict, state: dict, blob_lines: list[str], valid_status: bool) -> tuple[dict, bool]:
		url = str(data.get('url') or '').strip()
		status = data.get('status')
		h1_first = state['h1_list'][0] if state['h1_list'] else None
		gh_range, has_lc = cls.__github_line_range(state['raw_anchors'], blob_lines)
		valid_cite = bool(valid_status and (not state['is_shell']))
		rel_obs = obs_file.parent.relative_to(kb_dir).as_posix() if obs_file.parent.is_relative_to(kb_dir) else obs_file.parent.as_posix()
		entry: dict = {'url': url, 'final_url': str(data.get('final_url') or url).strip(), 'observation': rel_obs, 'kind': data.get('kind') or 'get', 'status': status, 'valid_for_citation': valid_cite, 'observed_at': data.get('observed_at'), 'title': state['title'] or h1_first, 'h1': h1_first, 'h1_headings': state['h1_list'], 'word_count': state['word_count']}
		if not valid_cite:
			entry['invalid_reason'] = state['invalid_reason'] or f"error={data.get('error')} status={status}"
		if gh_range:
			entry['github_line_range'] = gh_range
			if blob_lines and (not has_lc):
				entry['line_anchor_hint'] = f'#L1-L{len(blob_lines)}'
		return (entry, has_lc)
	# @used-by :meth:`EvidenceQuerier.query()`
	@staticmethod
	def __collect_obs_files(pp) -> list[Path]:
		http_dirs = [d for d in (pp.evidence_dir / 'HTTP', pp.root / '_/\ua616/KB/Evidence/HTTP', pp.root / '\ua616/KB/Evidence/HTTP') if d.is_dir()]
		seen_dirs: set[Path] = set()
		obs_files: list[Path] = []
		for hd in http_dirs:
			hd_res = hd.resolve()
			if hd_res not in seen_dirs:
				seen_dirs.add(hd_res)
				obs_files.extend(sorted(hd_res.rglob('observation.json')))
		return obs_files
	# @used-by :meth:`EvidenceQuerier.query()`
	def __compile_grep(self) -> re.Pattern | None:
		r: re.Pattern | None = None
		if None is not self.__grep_pattern and str(self.__grep_pattern).strip():
			try:
				r = re.compile(str(self.__grep_pattern), re.IGNORECASE)
			except re.error as exc:
				raise ValueError(f'Invalid --grep regular expression: {exc}') from exc
		return r
	# @used-by :meth:`EvidenceQuerier.__build_entry()`
	@staticmethod
	def __github_line_range(raw_anchors: set[str], blob_lines: list[str]) -> tuple[str | None, bool]:
		lc_nums = sorted({int(m.group(1)) for a in raw_anchors if (m := re.fullmatch('LC(\\d+)', a))})
		has_lc = bool(lc_nums)
		gh_range = f'#LC{lc_nums[0]}..#LC{lc_nums[-1]}' if lc_nums else (f'#LC1..#LC{len(blob_lines)}' if blob_lines else None)
		return (gh_range, has_lc)
	# @used-by :meth:`EvidenceQuerier.__select_entries()`
	@classmethod
	def __match_query_url(cls, qu: str, deduped: list[dict]) -> list[dict]:
		q_norm = cls.__norm_url(qu).lower()
		exact = [it for it in deduped if q_norm in {cls.__norm_url(it.get('url') or '').lower(), cls.__norm_url(it.get('final_url') or '').lower()}]
		return exact or [it for it in deduped if q_norm in cls.__norm_url(it.get('url') or '').lower() or q_norm in cls.__norm_url(it.get('final_url') or '').lower()]
	# @used-by :meth:`EvidenceQuerier.__match_query_url()`
	# @used-by :meth:`EvidenceQuerier.query()`
	@staticmethod
	def __norm_url(url: str) -> str:
		return urldefrag(str(url or '').strip())[0].rstrip('/')
	# @used-by :meth:`EvidenceQuerier.query()`
	def __select_entries(self, deduped: list[dict], rx: re.Pattern | None) -> tuple[list[dict], list[str]]:
		query_urls = [str(u).strip() for u in (self.__urls or ()) if str(u).strip()]
		missing: list[str] = []
		if not query_urls:
			selected = [it for it in deduped if None is rx or 0 < it.get('match_count', 0)]
		else:
			selected, seen_obs = ([], set())
			for qu in query_urls:
				matched = self.__match_query_url(qu, deduped)
				if not matched:
					missing.append(qu)
				else:
					for it in matched:
						if it['observation'] not in seen_obs:
							seen_obs.add(it['observation'])
							selected.append(it)
		return (selected, missing)
	# @used-by :meth:`EvidenceQuerier.query()`
	def __summarize_bundle(self, obs_file: Path, kb_dir: Path, rx: re.Pattern | None) -> dict | None:
		try:
			data = json.loads(obs_file.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			data = None
		if not isinstance(data, dict):
			r: dict | None = None
		else:
			status = data.get('status')
			valid_status = (not data.get('error')) and ('dom' == (data.get('kind') or 'get') or (isinstance(status, int) and 200 <= status < 300))
			state, raw_text, blob_lines = ObservationBundleScanner(obs_file, data, valid_status).scan()
			entry, has_lc = self.__build_entry(obs_file, kb_dir, data, state, blob_lines, valid_status)
			if self.__include_anchors:
				self.__attach_anchors(entry, state)
			if None is not rx:
				self.__attach_grep(entry, obs_file, data, state, raw_text, blob_lines, has_lc, rx)
			r = entry
		return r
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_question_search()`
	# @used-by :func:`Df.Harness.lib.markdown.dfh_display_address()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.text_browser._checked_ws()`
	# @used-by :func:`agent_tools.text_browser._endpoint_with_meta()`
	# @used-by :meth:`Df.Harness.Upwork.JobUrlParser.JobUrlParser.extract_upwork_job_url_id()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def query(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		kb_dir = pp.kb_dir.resolve()
		rx = self.__compile_grep()
		best_by_url: dict[str, dict] = {}
		for obs_f in self.__collect_obs_files(pp):
			item = self.__summarize_bundle(obs_f, kb_dir, rx)
			if None is not item:
				key = self.__norm_url(item.get('url') or item.get('final_url') or item['observation']).lower()
				prev = best_by_url.get(key)
				if None is prev or (bool(item.get('valid_for_citation')), str(item.get('observed_at') or '')) > (bool(prev.get('valid_for_citation')), str(prev.get('observed_at') or '')):
					best_by_url[key] = item
		selected, missing = self.__select_entries(list(best_by_url.values()), rx)
		return {'valid': not missing, 'observation_count': len(selected), 'missing_urls': missing, 'observations': selected}