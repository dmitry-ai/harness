# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate dual Tier 0 source caches into Tier0SourceIndex, extract LocalSourceGroundingAuditor, and isolate hosting domain rules in source_grounding.py":
# https://github.com/dmitry-ai/harness/issues/54
import json
from pathlib import Path
import re
ATTR_KEYS = {'vcpu', 'cpus', 'cores', 'mem_total', 'ram_gb', 'ram', 'swap_total', 'load_average', 'load_avg', 'disk_gb', 'php_memory_limit'}
CLIENT_DELIVERABLE_METRIC_RE = re.compile('(?i)(?:/sales/order/view/order_id/\\d+|\\b(?:auth_code|trans_id)\\b|#31\\d{6,8}|`[0-9]{5}[0-9A-Z]`|\\b\\d+\\s+(?:rows|records|orders|transactions|events|occurrences|\\u0437\\u0430\\u043f\\u0438\\u0441\\w*|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*|\\u0437\\u0430\\u043a\\u0430\\u0437\\w*|\\u0442\\u0440\\u0430\\u043d\\u0437\\u0430\\u043a\\u0446\\w*)\\b)')
ID_KEYS = ('code', 'id', 'plan', 'name', 'tier', 'server', 'host')
META_REFUTATION_RE = re.compile('(?:^|\\b)(?:\\u044f\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0443\\u043a\\u0430\\u0437\\u0430\\u043b|\\u043e\\u0448\\u0438\\u0431\\u043e\\u0447\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|\\u0430\\u0433\\u0435\\u043d\\u0442\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|\\u043c\\u043e\\u0434\\u0435\\u043b\\u044c\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b\\u0430)|\\u0431\\u044b\\u043b\\u043e\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0434\\u043e\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e)|\\u0431\\u044b\\u043b\\u0438\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u044b|\\u00ab?\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u044b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u044b)|\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u0430\\s+(?:\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430|\\u0434\\u0430\\u0442\\u0430|\\u0441\\u0442\\u0440\\u043e\\u043a\\u0430)|\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u043d\\w+\\s+(?:\\u043c\\u043d\\u043e\\u0439\\s+)?(?:\\u043f\\u0440\\u0435\\u0434\\u043b\\u043e\\u0436\\u0435\\u043d|\\u0446\\u0438\\u0442\\u0430\\u0442|\\u0441\\u0447\\u0451\\u0442|\\u0441\\u0442\\u0440\\u043e\\u043a|\\u0444\\u0440\\u0430\\u0437)|\\u0431\\u044b\\u043b\\u0430\\s+\\u0438\\u0441\\u043a\\u0430\\u0436\\u0435\\u043d\\u0430\\s+\\u043a\\u0430\\u043a|\\u044f\\s+\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b,\\s+\\u0447\\u0442\\u043e|\\u043a\\u043e\\u0442\\u043e\\u0440(?:\\u043e\\u0433\\u043e|\\u043e\\u0439|\\u044b\\u0445)\\s+\\u043d\\u0435\\u0442\\s+\\u0432|\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443(?:\\u0435\\u0442|\\u044e\\u0442|\\u044e\\u0449\\w*)\\s+\\u0432\\s+(?:source|nexcess|evidence|\\u043f\\u0435\\u0440\\u0432\\u043e\\u0438\\u0441\\u0442\\u043e\\u0447\\u043d\\u0438\\u043a)|\\u0433\\u0430\\u043b\\u043b\\u044e\\u0446\\u0438\\u043d\\u0430\\u0446\\w*|\\u043f\\u0438\\u0437\\u0434\\u043e\\u043d\\u044c\\u043a\\w*|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\w*|\\u0432\\s+\\u043e\\u0442\\u0432\\u0435\\u0442(?:\\u0435|\\u0430\\u0445)\\s+`?\\d+`?|\\bres/\\d+\\.md\\b|\\bresponse-\\d+\\.md\\b|hallucinat\\w*|fabricat\\w*|absent\\s+from\\s+the\\s+saved|missing\\s+from\\s+source\\.md)', re.I)
METRIC_LITERAL_SET = ('mem_total', 'vcpu', 'cpus', 'swap_total', 'load average')
METRIC_RE = re.compile('\\b(?:mem_total|vcpu|cpus|swap_total|load\\s+average)\\b', re.I)
ORDER_URL_RE = re.compile('/sales/order/view/order_id/(\\d+)', re.I)
PLAN_RE = re.compile('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', re.I)
TECHNICAL_SPAN_RE = re.compile('^(?:/dev/[A-Za-z0-9/_-]+|[a-z][a-z0-9_]{3,}:\\d{3,}|[A-Za-z][A-Za-z0-9_.-]+\\s+\\d+\\.\\d+(?:\\.\\d+)*(?:-[A-Za-z0-9._-]+)?|#?31\\d{6,8}|[0-9]{5}[0-9A-Z]|order_id/\\d+)$')
TICKET_ID_RE = re.compile('\\b(\\d{6,10})\\b')
TIER2_NUMERIC_DOMAIN_RE = re.compile('(?i)\\b(?:mem_total|vcpu|cpus|swap_total|swap|\\u0441\\u0432\\u043e\\u043f|worker\\w*|\\u0432\\u043e\\u0440\\u043a\\u0435\\u0440\\w*|load\\s+average|ram|\\u043e\\u0437\\u0443|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430)|plan\\s+(?:xs|s|m|l|xl|xxl)|m[1-9]|gb|gib|\\u0433\\u0431|mb|mib|\\u043c\\u0431)\\b')
def _check_load_average_tuples(sline: str, all_tuples: list[dict]) -> list[str]:
	r: list[str] = []
	la_tuples = [t for t in all_tuples if 'load_average_1m' == t.get('attribute') and isinstance(t.get('value'), (int, float))]
	cpu_tuples = [t for t in all_tuples if t.get('attribute') in {'cpus', 'vcpu'} and isinstance(t.get('value'), (int, float)) and 0 < t['value']]
	if la_tuples and cpu_tuples:
		la_val = float(la_tuples[0]['value'])
		cpu_val = float(cpu_tuples[0]['value'])
		if la_val < cpu_val and re.search('load\\s+average', sline, re.I):
			if re.search('(?:\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437\\w*|overload\\w*|saturat\\w*|\\u043f\\u0440\\u0435\\u0432\\u044b\\u0448\\u0430\\u0435\\u0442\\s+\\u0435\\u043c\\u043a\\u043e\\u0441\\u0442|exceeds\\s+capacity)', sline, re.I) and (not re.search('(?:\\u043d\\u0435\\u0442\\s+\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437|\\u043d\\u0435\\s+\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437|not\\s+overload|below|\\u043c\\u0435\\u043d\\u044c\\u0448\\u0435)', sline, re.I)):
				r.append(f'DOC-1 / VERIFY-3: Unnormalized load average claim ({la_val} on {int(cpu_val)} CPUs = {round(la_val / cpu_val * 100, 1)}% utilization < 100%, below the core count) in {cpu_tuples[0]["source_locator"]}')
	return r
def _check_mem_tuples(sline: str, infos: list[dict], all_tuples: list[dict]) -> list[str]:
	r: list[str] = []
	mem_tuples = [t for t in all_tuples if 'mem_total' == t.get('attribute') and isinstance(t.get('value'), (int, float)) and 1024 <= t['value']]
	if mem_tuples:
		m_gb = re.search('(?:\\b(?:ram|memory|\\u043e\\u0437\\u0443|\\u043f\\u0430\\u043c\\u044f\\u0442\\w*)\\b[^\\d\\n]{0,25})?(\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)\\s*(?:ram|memory|\\u043e\\u0437\\u0443)?', sline, re.I)
		if m_gb and re.search('\\b(?:ram|memory|\\u043e\\u0437\\u0443|mem_total)\\b', sline, re.I):
			stated_nums = [int(x) for x in re.findall('\\d+', m_gb.group(1))]
			valid_gb = set()
			for mt in mem_tuples:
				mb_val = float(mt['value'])
				valid_gb.update({round(mb_val / 1024.0), int(mb_val // 1024), round(mb_val / 1000.0), int(mb_val)})
			if stated_nums and (not any((sn in valid_gb for sn in stated_nums))):
				mt0 = mem_tuples[0]
				r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt0["value"]} MB in {mt0["source_locator"]}: prose claims {m_gb.group(0).strip()} (expected ~{round(float(mt0["value"]) / 1024.0, 2)} GiB)')
		if re.search('(?i)\\bburst\\b[^\\n]{0,25}\\b(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)|(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)[^\\n]{0,25}\\bburst\\b', sline):
			if not any(('burst' in str(inf.get('raw') or '').lower() for inf in infos)):
				mt0 = mem_tuples[0]
				r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt0["value"]} MB in {mt0["source_locator"]}: prose characterizes permanent mem_total RAM as "burst" without primary source support')
	return r
def _check_null_cpu_tuples(sline: str, all_tuples: list[dict]) -> list[str]:
	r: list[str] = []
	null_cpu_entities = {str(t['entity']).lower(): t for t in all_tuples if t.get('attribute') in {'vcpu', 'cpus', 'cores'} and None is t.get('value') and t.get('entity')}
	for tup in null_cpu_entities.values():
		ent = str(tup['entity'])
		if re.search(f'\\b{re.escape(ent)}\\b', sline, re.I):
			m_cpu = re.search('(\\d+)\\s*(?:vcpu|cpu|cores?|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430|\\u0440\\u043e))', sline, re.I)
			if m_cpu and (not re.search('\\b(?:null|\\u043d\\u0435\\s+\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d|unspecified|unknown)\\b', sline, re.I)):
				r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for {ent} ({tup["attribute"]}=null in {tup["source_locator"]}): prose asserts {m_cpu.group(0)} for a null attribute')
	return r
def _check_swap_tuples(sline: str, infos: list[dict], all_tuples: list[dict]) -> list[str]:
	r: list[str] = []
	if re.search('(?i)(?:\\b\\u0443\\u0445\\u043e\\u0434\\w*\\s+(?:\\u0441\\u0435\\u0440\\u0432\\u0435\\u0440\\u0430\\s+)?\\u0432\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\u0444\\u0438\\u043a\\u0441\\u0438\\u0440\\u043e\\u0432\\u0430\\u043b\\w*[^\\n]{0,40}\\b(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bswapping\\b)', sline) and (not re.search('(?i)(?:\\b\\u0431\\u0435\\u0437\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bno\\s+swap|\\bswap[_ ]total\\s*[:=]\\s*0|\\b\\u043d\\u0435\\s+\\u0443\\u0445\\u043e\\u0434|\\b\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\w*\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f))', sline)):
		zero_swap = [t for t in all_tuples if 'swap_total' == t.get('attribute') and 0 == t.get('value')]
		tier0_infos = [inf for inf in infos if 'tier_0' == inf.get('tier') and inf.get('raw')]
		if zero_swap:
			zs0 = zero_swap[0]
			r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for swap_total=0 in {zs0["source_locator"]}: prose asserts server swap activity despite swap_total=0')
		elif tier0_infos and (not any((re.search('(?i)\\b(?:swap\\w*|\\u0441\\u0432\\u043e\\u043f\\w*)', str(inf.get('raw') or '')) for inf in tier0_infos))):
			src_name = tier0_infos[0]['path'].name
			r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction in {src_name}: prose asserts server swap activity ("swap"), which is absent from the Tier 0 primary source')
	return r
def _collect_json_fact_tuples(obj, default_entity: str, source_loc: str, out: list[dict]) -> None:
	if isinstance(obj, list):
		for idx, item in enumerate(obj):
			_collect_json_fact_tuples(item, default_entity, f'{source_loc}[{idx}]', out)
	elif isinstance(obj, dict):
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
		for k, v in obj.items():
			kl = str(k).lower()
			if isinstance(v, (dict, list)):
				next_ent = str(k).strip() if isinstance(v, dict) and re.match('^(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL)|server[-_a-z0-9]+)$', str(k).strip(), re.I) else entities[0]
				_collect_json_fact_tuples(v, next_ent, f'{source_loc}/{k}', out)
			elif kl in ATTR_KEYS and (None is v or isinstance(v, (int, float, str))):
				unit = 'MB' if kl in {'mem_total', 'swap_total'} else ('GB' if kl in {'ram_gb', 'disk_gb'} else None)
				for ent in entities:
					out.append({'entity': ent, 'attribute': kl, 'value': v, 'unit': unit, 'source_locator': source_loc})
def extract_domain_entities(text: str, *, include_substring_metrics: bool=False) -> dict[str, list[str]]:
	raw = text or ''
	plans = sorted({m.group(0).strip() for m in PLAN_RE.finditer(raw)})
	plans_norm = sorted({' '.join(p.split()).upper() for p in plans})
	metric_set = {m.group(0).lower() for m in METRIC_RE.finditer(raw)}
	if include_substring_metrics:
		raw_lower = raw.lower()
		metric_set |= {mt for mt in METRIC_LITERAL_SET if mt in raw_lower}
	return {'metrics': sorted(metric_set), 'plans': plans, 'plans_norm': plans_norm, 'tickets': sorted(set(TICKET_ID_RE.findall(raw)))}
def extract_fact_tuples(path: Path, raw_text: str | None=None, *, root: Path | None=None) -> list[dict]:
	r: list[dict] = []
	loaded_text = raw_text
	if None is loaded_text:
		try:
			loaded_text = path.read_text(encoding='utf-8', errors='replace')
		except OSError:
			loaded_text = None
	if None is not loaded_text:
		try:
			loc = path.resolve().relative_to(Path(root).resolve()).as_posix() if None is not root else path.name
		except ValueError:
			loc = path.as_posix()
		default_entity = path.parent.parent.name if 'kb' == path.parent.name.lower() else (path.parent.name if 'source.md' == path.name.lower() else path.stem)
		doc_plans = extract_domain_entities(loaded_text)['plans']
		if '.json' == path.suffix.lower() and loaded_text.strip():
			try:
				_collect_json_fact_tuples(json.loads(loaded_text), default_entity, loc, r)
			except ValueError:
				pass
		else:
			for m_fence in re.finditer('```(?:json)?\\s*\\n(.*?)\\n```', loaded_text, re.I | re.S):
				try:
					_collect_json_fact_tuples(json.loads(m_fence.group(1).strip()), default_entity, loc, r)
				except ValueError:
					pass
		for m_mem in re.finditer('(?i)["\']?\\b(mem_total|swap_total|cpus|vcpu)\\b["\']?\\s*[:=]\\s*(null|\\d+(?:\\.\\d+)?)\\b', loaded_text):
			attr = m_mem.group(1).lower()
			val_raw = m_mem.group(2).lower()
			val = None if 'null' == val_raw else (int(val_raw) if val_raw.isdigit() else float(val_raw))
			line_start = loaded_text.rfind('\n', 0, m_mem.start()) + 1
			line_end = loaded_text.find('\n', m_mem.end())
			line_slice = loaded_text[line_start:len(loaded_text) if -1 == line_end else line_end]
			line_plans = [m.group(0).strip() for m in PLAN_RE.finditer(line_slice)]
			target_entities = list(dict.fromkeys([default_entity] + (line_plans or (doc_plans if 1 == len(doc_plans) else []))))
			unit = 'MB' if attr in {'mem_total', 'swap_total'} else None
			for ent in target_entities:
				r.append({'entity': ent, 'attribute': attr, 'value': val, 'unit': unit, 'source_locator': loc})
		for m_la in re.finditer('(?i)load\\s+average\\s*[:=]\\s*(\\d+(?:\\.\\d+)?)', loaded_text):
			r.append({'entity': default_entity, 'attribute': 'load_average_1m', 'value': float(m_la.group(1)), 'unit': 'load', 'source_locator': loc})
	return r
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
def fact_tuple_contradictions(sline: str, infos: list[dict], ledger_tuples: list[dict] | None=None) -> list[str]:
	r: list[str] = []
	if sline and (not META_REFUTATION_RE.search(sline)):
		all_tuples: list[dict] = []
		seen_keys: set[tuple] = set()
		for src_list in ([inf.get('fact_tuples') or [] for inf in infos] + ([ledger_tuples] if ledger_tuples else [])):
			for tup in src_list:
				tkey = (tup.get('entity'), tup.get('attribute'), tup.get('value'), tup.get('source_locator'))
				if tkey not in seen_keys:
					seen_keys.add(tkey)
					all_tuples.append(tup)
		r.extend(_check_null_cpu_tuples(sline, all_tuples))
		r.extend(_check_mem_tuples(sline, infos, all_tuples))
		r.extend(_check_swap_tuples(sline, infos, all_tuples))
		r.extend(_check_load_average_tuples(sline, all_tuples))
	return r
def order_url_issues(sline: str, ev_nums: set[str], combined_raw: str, src_label: str) -> list[str]:
	r: list[str] = []
	for m_oid in ORDER_URL_RE.finditer(sline):
		oid_val = m_oid.group(1)
		if oid_val not in ev_nums and oid_val not in combined_raw:
			r.append(f'VERIFY-1 / DOC-1: Order URL identifier (order_id/{oid_val}) attributed to {src_label} is absent from the primary source')
	return r
def ticket_author_issues(sline: str, combined_norm: str, src_label: str) -> list[str]:
	r: list[str] = []
	for m_auth in re.finditer('[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+(?:\\s+[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+)+\\s*\\(`([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)`\\)', sline):
		author_name = m_auth.group(1).strip()
		if author_name.lower() not in combined_norm:
			r.append(f'VERIFY-1 / LINK-1: Cited person "{author_name}" is absent from {src_label}')
	return r
def ticket_message_issues(sline: str, valid_msg_nums: set[int], bound_ticket_ids: set[str]) -> list[str]:
	r: list[str] = []
	for m_msg in re.finditer('(?:\\u0441\\u043e\\u043e\\u0431\\u0449\\u0435\\u043d\\u0438[\\u0435\\u044f\\u0438\\u0439\\u044f\\u0445\\u043c]+\\s*(?:\\u2116|#)?\\s*(\\d+)(?:\\s*(?:\\u0438|,|-)\\s*(?:\\u2116|#)?\\s*(\\d+))?|\\bMessage\\s*#?(\\d+)\\b)', sline, re.I):
		prefix = sline[max(0, m_msg.start() - 45):m_msg.start()]
		other_tickets = [tid for tid in re.findall('\\b(\\d{7,8})\\b', prefix) if tid not in bound_ticket_ids]
		if not other_tickets:
			for g_idx in (1, 2, 3):
				val = m_msg.group(g_idx)
				if val and int(val) not in valid_msg_nums:
					r.append(f'message #{val} (available: {sorted(valid_msg_nums)})')
	return r
