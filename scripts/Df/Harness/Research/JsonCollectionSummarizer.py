# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_ISO_RE = re.compile('^\\d{4}-\\d{2}-\\d{2}(?:[T ]\\d{2}:\\d{2}:\\d{2})?')
class JsonCollectionSummarizer:
	# @used-by :func:`agent_tools.research._summarize_json_collections()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_document_text()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_shopify()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def __init__(self, value) -> None:
		self.__value = value
	# @used-by :meth:`JsonCollectionSummarizer.summarize()`
	@staticmethod
	def __collect_item_fields(items: list[dict]) -> tuple[dict, dict]:
		ts_fields: dict = {}
		cat_fields: dict = {}
		for item in items:
			label = next((str(item[k]) for k in ('title', 'name', 'handle', 'slug', 'id') if None is not item.get(k)), None)
			for k, v in item.items():
				if isinstance(v, str) and _ISO_RE.match(v):
					ts_fields.setdefault(k, []).append((v, item.get('id'), label))
				elif 'id' != k and isinstance(v, (str, bool)) and 120 >= len(str(v)):
					cat_fields.setdefault(k, {})[str(v)] = cat_fields.get(k, {}).get(str(v), 0) + 1
				elif isinstance(v, list) and v and all((isinstance(elem, str) and 80 >= len(elem) for elem in v)):
					for elem in v:
						cat_fields.setdefault(k, {})[elem] = cat_fields.get(k, {}).get(elem, 0) + 1
		return (ts_fields, cat_fields)
	# @used-by :meth:`JsonCollectionSummarizer.summarize()`
	@staticmethod
	def __filter_categories(cat_fields: dict, item_count: int) -> dict:
		return {k: dict(sorted(counts.items())) for k, counts in sorted(cat_fields.items()) if 50 >= len(counts) and (1 == item_count or len(counts) < item_count or any((1 < c for c in counts.values())))}
	# @used-by :meth:`JsonCollectionSummarizer.summarize()`
	@staticmethod
	def __summarize_timestamps(ts_fields: dict) -> dict:
		ts_summary: dict = {}
		for k, entries in ts_fields.items():
			ordered = sorted(entries, key=lambda x: x[0])
			by_date: dict[str, int] = {}
			for val, _, _ in ordered:
				day = val[:10]
				by_date[day] = by_date.get(day, 0) + 1
			earliest, latest = (ordered[0], ordered[-1])
			ts_summary[k] = {'min': earliest[0], 'max': latest[0], 'count': len(ordered), 'by_date': dict(sorted(by_date.items())), 'earliest_record': {'id': earliest[1], 'label': earliest[2], k: earliest[0]}, 'latest_record': {'id': latest[1], 'label': latest[2], k: latest[0]}}
		return ts_summary
	# @used-by :meth:`JsonCollectionSummarizer.summarize()`
	@classmethod
	def __walk(cls, node, arrays: dict[str, list[dict]], path: str='', depth: int=0) -> None:
		if 4 >= depth:
			if isinstance(node, list) and node and all((isinstance(x, dict) for x in node)):
				arrays[path or '/items'] = node
				if path.startswith('/') and '/' not in path[1:]:
					arrays[path[1:]] = node
			elif isinstance(node, dict):
				for k, v in node.items():
					escaped = str(k).replace('~', '~0').replace('/', '~1')
					cls.__walk(v, arrays, f'{path}/{escaped}', depth + 1)
	# @used-by :func:`agent_tools.research._summarize_json_collections()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_document_text()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_shopify()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def summarize(self) -> dict:
		arrays: dict[str, list[dict]] = {}
		self.__walk(self.__value, arrays)
		summary: dict = {}
		for name, items in arrays.items():
			ts_fields, cat_fields = self.__collect_item_fields(items)
			summary[name] = {'record_count': len(items), 'timestamp_ranges': self.__summarize_timestamps(ts_fields), 'field_counts': self.__filter_categories(cat_fields, len(items))}
		return summary