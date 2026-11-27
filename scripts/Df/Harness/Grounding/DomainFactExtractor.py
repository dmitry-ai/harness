# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ATTR_KEYS = {'vcpu', 'cpus', 'cores', 'mem_total', 'ram_gb', 'ram', 'swap_total', 'load_average', 'load_avg', 'disk_gb', 'php_memory_limit'}
ID_KEYS = ('code', 'id', 'plan', 'name', 'tier', 'server', 'host')
METRIC_LITERAL_SET = ('mem_total', 'vcpu', 'cpus', 'swap_total', 'load average')
METRIC_RE = re.compile('\\b(?:mem_total|vcpu|cpus|swap_total|load\\s+average)\\b', re.I)
ORDER_URL_RE = re.compile('/sales/order/view/order_id/(\\d+)', re.I)
PLAN_RE = re.compile('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', re.I)
TICKET_ID_RE = re.compile('\\b(\\d{6,10})\\b')
_KV_FACT_RE = re.compile('(?i)["\']?\\b(mem_total|swap_total|cpus|vcpu)\\b["\']?\\s*[:=]\\s*(null|\\d+(?:\\.\\d+)?)\\b')
_LOAD_AVG_RE = re.compile('(?i)load\\s+average\\s*[:=]\\s*(\\d+(?:\\.\\d+)?)')
_NESTED_ENT_RE = re.compile('^(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL)|server[-_a-z0-9]+)$', re.I)
class DomainFactExtractor:
	# @used-by :func:`agent_tools.grounding_domains.extract_fact_tuples()`
	# @used-by :func:`agent_tools.source_grounding.extract_fact_tuples()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__read_and_index_entry()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.hydrate_standalone()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	def __init__(self, path: Path, raw_text: str | None=None, *, root: Path | None=None) -> None:
		self.__path = path
		self.__raw_text = raw_text
		self.__root = root
	# @used-by :meth:`DomainFactExtractor.collect_json_fact_tuples()`
	@classmethod
	def __collect_dict_fact_tuples(cls, obj: dict, default_entity: str, source_loc: str, out: list[dict]) -> None:
		entities = cls.__extract_entities_from_dict(obj, default_entity)
		for k, v in obj.items():
			kl = str(k).lower()
			if isinstance(v, (dict, list)):
				next_ent = str(k).strip() if isinstance(v, dict) and _NESTED_ENT_RE.match(str(k).strip()) else entities[0]
				cls.collect_json_fact_tuples(v, next_ent, f'{source_loc}/{k}', out)
			elif kl in ATTR_KEYS and (None is v or isinstance(v, (int, float, str))):
				unit = 'MB' if kl in {'mem_total', 'swap_total'} else ('GB' if kl in {'ram_gb', 'disk_gb'} else None)
				for ent in entities:
					out.append({'entity': ent, 'attribute': kl, 'value': v, 'unit': unit, 'source_locator': source_loc})
	# @used-by :meth:`DomainFactExtractor.__collect_dict_fact_tuples()`
	@staticmethod
	def __extract_entities_from_dict(obj: dict, default_entity: str) -> list[str]:
		entities: list[str] = []
		for ik in ID_KEYS:
			val = obj.get(ik)
			if isinstance(val, str) and val.strip():
				v_s = val.strip()
				if v_s not in entities:
					entities.append(v_s)
				if 'tier' == ik and re.fullmatch('(?:XS|S|M|L|XL|XXL)', v_s, re.I):
					plan_alias = f'Plan {v_s.upper()}'
					if plan_alias not in entities:
						entities.append(plan_alias)
		if not entities:
			entities = [default_entity]
		elif default_entity and default_entity not in entities:
			entities.append(default_entity)
		return entities
	# @used-by :meth:`DomainFactExtractor.extract()`
	@classmethod
	def __extract_json_blocks(cls, text: str, path: Path, default_entity: str, loc: str, out: list[dict]) -> None:
		if '.json' == path.suffix.lower() and text.strip():
			try:
				cls.collect_json_fact_tuples(json.loads(text), default_entity, loc, out)
			except ValueError:
				pass
		else:
			for m_fence in re.finditer('```(?:json)?\\s*\\n(.*?)\\n```', text, re.I | re.S):
				try:
					cls.collect_json_fact_tuples(json.loads(m_fence.group(1).strip()), default_entity, loc, out)
				except ValueError:
					pass
	# @used-by :meth:`DomainFactExtractor.extract()`
	@staticmethod
	def __extract_kv_matches(text: str, default_entity: str, doc_plans: list[str], loc: str, out: list[dict]) -> None:
		for m_mem in _KV_FACT_RE.finditer(text):
			attr, val_raw = (m_mem.group(1).lower(), m_mem.group(2).lower())
			val = None if 'null' == val_raw else (int(val_raw) if val_raw.isdigit() else float(val_raw))
			line_start = text.rfind('\n', 0, m_mem.start()) + 1
			line_end = text.find('\n', m_mem.end())
			line_slice = text[line_start:len(text) if -1 == line_end else line_end]
			line_plans = [m.group(0).strip() for m in PLAN_RE.finditer(line_slice)]
			targets = list(dict.fromkeys([default_entity] + (line_plans or (doc_plans if 1 == len(doc_plans) else []))))
			unit = 'MB' if attr in {'mem_total', 'swap_total'} else None
			for ent in targets:
				out.append({'entity': ent, 'attribute': attr, 'value': val, 'unit': unit, 'source_locator': loc})
	# @used-by :meth:`DomainFactExtractor.extract()`
	@staticmethod
	def __extract_load_matches(text: str, default_entity: str, loc: str, out: list[dict]) -> None:
		for m_la in _LOAD_AVG_RE.finditer(text):
			out.append({'entity': default_entity, 'attribute': 'load_average_1m', 'value': float(m_la.group(1)), 'unit': 'load', 'source_locator': loc})
	# @used-by :meth:`DomainFactExtractor.extract()`
	@staticmethod
	def __load_text(path: Path, raw_text: str | None) -> str | None:
		r = raw_text
		if None is r:
			try:
				r = path.read_text(encoding='utf-8', errors='replace')
			except OSError:
				r = None
		return r
	# @used-by :meth:`DomainFactExtractor.extract()`
	@staticmethod
	def __resolve_locator(path: Path, root: Path | None) -> str:
		try:
			r = path.resolve().relative_to(Path(root).resolve()).as_posix() if None is not root else path.name
		except ValueError:
			r = path.as_posix()
		return r
	# @used-by :func:`agent_tools.grounding_domains._collect_json_fact_tuples()`
	# @used-by :meth:`DomainFactExtractor.__collect_dict_fact_tuples()`
	# @used-by :meth:`DomainFactExtractor.__extract_json_blocks()`
	@classmethod
	def collect_json_fact_tuples(cls, obj, default_entity: str, source_loc: str, out: list[dict]) -> None:
		if isinstance(obj, list):
			for idx, item in enumerate(obj):
				cls.collect_json_fact_tuples(item, default_entity, f'{source_loc}[{idx}]', out)
		elif isinstance(obj, dict):
			cls.__collect_dict_fact_tuples(obj, default_entity, source_loc, out)
	# @used-by :func:`agent_tools.grounding_domains.extract_fact_tuples()`
	# @used-by :func:`agent_tools.source_grounding.extract_fact_tuples()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__read_and_index_entry()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.hydrate_standalone()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	def extract(self) -> list[dict]:
		r: list[dict] = []
		loaded_text = self.__load_text(self.__path, self.__raw_text)
		if None is not loaded_text:
			loc = self.__resolve_locator(self.__path, self.__root)
			default_entity = self.__path.parent.parent.name if 'kb' == self.__path.parent.name.lower() else (self.__path.parent.name if 'source.md' == self.__path.name.lower() else self.__path.stem)
			doc_plans = self.extract_domain_entities(loaded_text)['plans']
			self.__extract_json_blocks(loaded_text, self.__path, default_entity, loc, r)
			self.__extract_kv_matches(loaded_text, default_entity, doc_plans, loc, r)
			self.__extract_load_matches(loaded_text, default_entity, loc, r)
		return r
	# @used-by :func:`agent_tools.grounding_domains.extract_domain_entities()`
	# @used-by :func:`agent_tools.source_grounding.extract_domain_entities()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__entry_from_disk()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__read_and_index_entry()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.discover_entities()`
	# @used-by :meth:`DomainFactExtractor.extract()`
	@staticmethod
	def extract_domain_entities(text: str, *, include_substring_metrics: bool=False) -> dict[str, list[str]]:
		raw = text or ''
		plans = sorted({m.group(0).strip() for m in PLAN_RE.finditer(raw)})
		plans_norm = sorted({' '.join(p.split()).upper() for p in plans})
		metric_set = {m.group(0).lower() for m in METRIC_RE.finditer(raw)}
		if include_substring_metrics:
			raw_lower = raw.lower()
			metric_set |= {mt for mt in METRIC_LITERAL_SET if mt in raw_lower}
		return {'metrics': sorted(metric_set), 'plans': plans, 'plans_norm': plans_norm, 'tickets': sorted(set(TICKET_ID_RE.findall(raw)))}
	# @used-by :func:`agent_tools.grounding_domains.extract_ticket_metadata()`
	# @used-by :func:`agent_tools.source_grounding.extract_ticket_metadata()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__build_hydrated_info()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	@staticmethod
	def extract_ticket_metadata(path: Path, raw: str) -> tuple[bool, set[int], str | None]:
		msg_nums: set[int] = set()
		is_ticket_source = False
		if 'source.md' == path.name.lower():
			for m in re.finditer('(?m)^##\\s+(\\d+)\\s+[\\u2014\\u2013-]\\s+(.+?)\\s+\\(', raw):
				msg_nums.add(int(m.group(1)))
				is_ticket_source = True
			for m in re.finditer('(?m)^###\\s+Message\\s+#?(\\d+)\\b', raw, re.I):
				msg_nums.add(int(m.group(1)))
				is_ticket_source = True
		ticket_id = path.parent.parent.name if 'kb' == path.parent.name.lower() and re.fullmatch('\\d{6,10}', path.parent.parent.name) else None
		return (is_ticket_source, msg_nums, ticket_id)
	# @used-by :func:`agent_tools.grounding_domains.order_url_issues()`
	# @used-by :func:`agent_tools.source_grounding.order_url_issues()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_prose_line()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	@staticmethod
	def order_url_issues(sline: str, ev_nums: set[str], combined_raw: str, src_label: str) -> list[str]:
		r: list[str] = []
		for m_oid in ORDER_URL_RE.finditer(sline):
			oid_val = m_oid.group(1)
			if oid_val not in ev_nums and oid_val not in combined_raw:
				r.append(f'VERIFY-1 / DOC-1: Order URL identifier (order_id/{oid_val}) attributed to {src_label} is absent from the primary source')
		return r
	# @used-by :func:`agent_tools.grounding_domains.ticket_author_issues()`
	# @used-by :func:`agent_tools.source_grounding.ticket_author_issues()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_prose_line()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	@staticmethod
	def ticket_author_issues(sline: str, combined_norm: str, src_label: str) -> list[str]:
		r: list[str] = []
		for m_auth in re.finditer('[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+(?:\\s+[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+)+\\s*\\(`([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)`\\)', sline):
			author_name = m_auth.group(1).strip()
			if author_name.lower() not in combined_norm:
				r.append(f'VERIFY-1 / LINK-1: Cited person "{author_name}" is absent from {src_label}')
		return r
	# @used-by :func:`agent_tools.grounding_domains.ticket_message_issues()`
	# @used-by :func:`agent_tools.source_grounding.ticket_message_issues()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.line_grounded_numbers_check()`
	@staticmethod
	def ticket_message_issues(sline: str, valid_msg_nums: set[int], bound_ticket_ids: set[str]) -> list[str]:
		r: list[str] = []
		for m_msg in re.finditer('(?:\\u0441\\u043e\\u043e\\u0431\\u0449\\u0435\\u043d\\u0438[\\u0435\\u044f\\u0438\\u0439\\u044f\\u0445\\u043c]+\\s*(?:\\u2116|#)?\\s*(\\d+)(?:\\s*(?:\\u0438|,|-)\\s*(?:\\u2116|#)?\\s*(\\d+))?|\\bMessage\\s*#?(\\d+)\\b)', sline, re.I):
			prefix = sline[max(0, m_msg.start() - 45):m_msg.start()]
			if not [tid for tid in re.findall('\\b(\\d{7,8})\\b', prefix) if tid not in bound_ticket_ids]:
				for g_idx in (1, 2, 3):
					val = m_msg.group(g_idx)
					if val and int(val) not in valid_msg_nums:
						r.append(f'message #{val} (available: {sorted(valid_msg_nums)})')
		return r