# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
import re
_NAME_PATTERNS = (
	'\\bworking with ([A-Z][a-z]{2,15})\\b',
	'\\bThank you,? ([A-Z][a-z]{2,15})\\b',
	'\\b([A-Z][a-z]{2,15}) is (?:a |an )?(?:very |truly |super )?(?:nice|great|wonderful|excellent|good|supportive|easy|clear|amazing|awesome|fantastic|pleasure)',
	'\\b([A-Z][a-z]{2,15}) was (?:a )?(?:great|wonderful|excellent|very|easy|clear|supportive)',
	'\\b([A-Z][a-z]{2,15}) has been (?:a )?(?:great|wonderful|excellent|very|supportive)',
	'\\b([A-Z][a-z]{2,15}) is the best\\b',
)
_NAME_STOPWORDS = {'This', 'That', 'There', 'Client', 'Working', 'Thank', 'Thanks', 'Everything', 'Communication', 'Overall', 'Project', 'Team', 'He', 'She', 'They'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClientMetadataExtractor:
	# @used-by :meth:`ClientMetadataExtractor.collect_unique_public_past_jobs()`
	@staticmethod
	def __collect_group(items: list[dict], *, nested: bool, current_cid, rel_descs: dict, seen_cids: set[str], out: list[dict]) -> None:
		for item in items:
			src = (item.get('jobInfo') or {}) if nested else item
			cid = src.get('ciphertext')
			if not cid or cid == current_cid or cid in seen_cids:
				continue
			rel = rel_descs.get(cid) or {}
			desc = (rel.get('description') or '').strip()
			title = (src.get('title') or rel.get('title') or '').strip()
			if desc:
				seen_cids.add(cid)
				out.append({'ciphertext': cid, 'url': JobUrlParser.canonical_job_url(cid), 'title': title, 'description': desc})
	# @used-by :meth:`ClientMetadataExtractor.extract_client_names()`
	@staticmethod
	def __scan_comment(idx: int, item: dict, comment: str, found: dict[str, list[dict]]) -> None:
		seen_in_item: set[str] = set()
		for pat in _NAME_PATTERNS:
			for match in re.finditer(pat, comment):
				name = match.group(1)
				if name in _NAME_STOPWORDS or name in seen_in_item:
					continue
				seen_in_item.add(name)
				found.setdefault(name, []).append({'project_index': idx, 'project_title': (item.get('jobInfo') or {}).get('title') or f'Project {idx}', 'quote': comment})
	# @used-by :func:`agent_tools.upwork_data.collect_unique_public_past_jobs()`
	# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def collect_unique_public_past_jobs(cls, data: dict) -> list[dict]:
		current_cid = data.get('job_id')
		rel_descs = data.get('related_descriptions') or {}
		seen_cids: set[str] = set()
		r: list[dict] = []
		cls.__collect_group(data.get('work_history') or [], nested=True, current_cid=current_cid, rel_descs=rel_descs, seen_cids=seen_cids, out=r)
		cls.__collect_group(data.get('open_jobs') or [], nested=False, current_cid=current_cid, rel_descs=rel_descs, seen_cids=seen_cids, out=r)
		return r
	# @used-by :func:`agent_tools.upwork_data.extract_candidate_domains()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__build_result()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def extract_candidate_domains(texts: list[str]) -> list[str]:
		pattern = '(?<![\\w.-])((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63})(?![\\w.-])'
		domains = (m[4:] if m.startswith('www.') else m for text in texts for m in re.findall(pattern, text.lower()))
		return list(dict.fromkeys(domains))
	# @used-by :func:`agent_tools.upwork_data.extract_client_names()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__build_result()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def extract_client_names(cls, work_history: list[dict]) -> list[dict]:
		found: dict[str, list[dict]] = {}
		for idx, item in enumerate(work_history, start=1):
			comment = ((item.get('feedbackToClient') or {}).get('comment') or '').strip()
			if comment:
				cls.__scan_comment(idx, item, comment, found)
		return [{'name': k, 'mentions': v} for k, v in sorted(found.items(), key=lambda x: -len(x[1]))]
