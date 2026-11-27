# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.grounding import META_REFUTATION_RE
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ORDER_URL_RE = re.compile('/sales/order/view/order_id/(\\d+)', re.I)
class FactContradictionChecker:
	# @used-by :func:`agent_tools.grounding_domains.fact_tuple_contradictions()`
	# @used-by :func:`agent_tools.source_grounding.fact_tuple_contradictions()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_prose_line()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	def __init__(self, sline: str, infos: list[dict], ledger_tuples: list[dict] | None=None) -> None:
		self.__sline = sline
		self.__infos = infos
		self.__ledger_tuples = ledger_tuples
	# @used-by :meth:`FactContradictionChecker.check()`
	def __check_load_average(self, all_tuples: list[dict]) -> list[str]:
		r: list[str] = []
		la_tuples = [t for t in all_tuples if 'load_average_1m' == t.get('attribute') and isinstance(t.get('value'), (int, float))]
		cpu_tuples = [t for t in all_tuples if t.get('attribute') in {'cpus', 'vcpu'} and isinstance(t.get('value'), (int, float)) and 0 < t['value']]
		if la_tuples and cpu_tuples:
			la_val, cpu_val = (float(la_tuples[0]['value']), float(cpu_tuples[0]['value']))
			if la_val < cpu_val and re.search('load\\s+average', self.__sline, re.I):
				over_re = '(?:\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437\\w*|overload\\w*|saturat\\w*|\\u043f\\u0440\\u0435\\u0432\\u044b\\u0448\\u0430\\u0435\\u0442\\s+\\u0435\\u043c\\u043a\\u043e\\u0441\\u0442|exceeds\\s+capacity)'
				neg_re = '(?:\\u043d\\u0435\\u0442\\s+\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437|\\u043d\\u0435\\s+\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437|not\\s+overload|below|\\u043c\\u0435\\u043d\\u044c\\u0448\\u0435)'
				if re.search(over_re, self.__sline, re.I) and (not re.search(neg_re, self.__sline, re.I)):
					loc = cpu_tuples[0]['source_locator']
					r.append(f'DOC-1 / VERIFY-3: Unnormalized load average claim ({la_val} on {int(cpu_val)} CPUs = {round(la_val / cpu_val * 100, 1)}% utilization < 100%, below the core count) in {loc}')
		return r
	# @used-by :meth:`FactContradictionChecker.check()`
	def __check_mem(self, all_tuples: list[dict]) -> list[str]:
		r: list[str] = []
		mem_tuples = [t for t in all_tuples if 'mem_total' == t.get('attribute') and isinstance(t.get('value'), (int, float)) and 1024 <= t['value']]
		if mem_tuples:
			mt0 = mem_tuples[0]
			mt_val, mt_loc = (mt0['value'], mt0['source_locator'])
			m_gb = re.search('(?:\\b(?:ram|memory|\\u043e\\u0437\\u0443|\\u043f\\u0430\\u043c\\u044f\\u0442\\w*)\\b[^\\d\\n]{0,25})?(\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)\\s*(?:ram|memory|\\u043e\\u0437\\u0443)?', self.__sline, re.I)
			if m_gb and re.search('\\b(?:ram|memory|\\u043e\\u0437\\u0443|mem_total)\\b', self.__sline, re.I):
				stated_nums = [int(x) for x in re.findall('\\d+', m_gb.group(1))]
				valid_gb = {v for mt in mem_tuples for v in (round(float(mt['value']) / 1024.0), int(float(mt['value']) // 1024), round(float(mt['value']) / 1000.0), int(float(mt['value'])))}
				if stated_nums and (not any((sn in valid_gb for sn in stated_nums))):
					r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt_val} MB in {mt_loc}: prose claims {m_gb.group(0).strip()} (expected ~{round(float(mt_val) / 1024.0, 2)} GiB)')
			if re.search('(?i)\\bburst\\b[^\\n]{0,25}\\b(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)|(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)[^\\n]{0,25}\\bburst\\b', self.__sline):
				if not any(('burst' in str(inf.get('raw') or '').lower() for inf in self.__infos)):
					r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt_val} MB in {mt_loc}: prose characterizes permanent mem_total RAM as "burst" without primary source support')
		return r
	# @used-by :meth:`FactContradictionChecker.check()`
	def __check_null_cpu(self, all_tuples: list[dict]) -> list[str]:
		r: list[str] = []
		null_cpu_entities = {str(t['entity']).lower(): t for t in all_tuples if t.get('attribute') in {'vcpu', 'cpus', 'cores'} and None is t.get('value') and t.get('entity')}
		for tup in null_cpu_entities.values():
			ent = str(tup['entity'])
			if re.search(f'\\b{re.escape(ent)}\\b', self.__sline, re.I):
				m_cpu = re.search('(\\d+)\\s*(?:vcpu|cpu|cores?|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430|\\u0440\\u043e))', self.__sline, re.I)
				if m_cpu and (not re.search('\\b(?:null|\\u043d\\u0435\\s+\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d|unspecified|unknown)\\b', self.__sline, re.I)):
					attr, loc = (tup['attribute'], tup['source_locator'])
					r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for {ent} ({attr}=null in {loc}): prose asserts {m_cpu.group(0)} for a null attribute')
		return r
	# @used-by :meth:`FactContradictionChecker.check()`
	def __check_swap(self, all_tuples: list[dict]) -> list[str]:
		r: list[str] = []
		swap_claim = '(?i)(?:\\b\\u0443\\u0445\\u043e\\u0434\\w*\\s+(?:\\u0441\\u0435\\u0440\\u0432\\u0435\\u0440\\u0430\\s+)?\\u0432\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\u0444\\u0438\\u043a\\u0441\\u0438\\u0440\\u043e\\u0432\\u0430\\u043b\\w*[^\\n]{0,40}\\b(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bswapping\\b)'
		swap_neg = '(?i)(?:\\b\\u0431\\u0435\\u0437\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bno\\s+swap|\\bswap[_ ]total\\s*[:=]\\s*0|\\b\\u043d\\u0435\\s+\\u0443\\u0445\\u043e\\u0434|\\b\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\w*\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f))'
		if re.search(swap_claim, self.__sline) and (not re.search(swap_neg, self.__sline)):
			zero_swap = [t for t in all_tuples if 'swap_total' == t.get('attribute') and 0 == t.get('value')]
			tier0_infos = [inf for inf in self.__infos if 'tier_0' == inf.get('tier') and inf.get('raw')]
			if zero_swap:
				zs_loc = zero_swap[0]['source_locator']
				r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction for swap_total=0 in {zs_loc}: prose asserts server swap activity despite swap_total=0')
			elif tier0_infos and (not any((re.search('(?i)\\b(?:swap\\w*|\\u0441\\u0432\\u043e\\u043f\\w*)', str(inf.get('raw') or '')) for inf in tier0_infos))):
				src_name = tier0_infos[0]['path'].name
				r.append(f'DOC-1 / VERIFY-1: Fact-tuple contradiction in {src_name}: prose asserts server swap activity ("swap"), which is absent from the Tier 0 primary source')
		return r
	# @used-by :meth:`FactContradictionChecker.check()`
	def __dedup_tuples(self) -> list[dict]:
		all_tuples: list[dict] = []
		seen_keys: set[tuple] = set()
		for src_list in ([inf.get('fact_tuples') or [] for inf in self.__infos] + ([self.__ledger_tuples] if self.__ledger_tuples else [])):
			for tup in src_list:
				tkey = (tup.get('entity'), tup.get('attribute'), tup.get('value'), tup.get('source_locator'))
				if tkey not in seen_keys:
					seen_keys.add(tkey)
					all_tuples.append(tup)
		return all_tuples
	# @used-by :func:`agent_tools.grounding_domains.fact_tuple_contradictions()`
	# @used-by :func:`agent_tools.source_grounding.fact_tuple_contradictions()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_prose_line()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_domain_fact_extractor_and_contradiction_checker()`
	def check(self) -> list[str]:
		r: list[str] = []
		if self.__sline and (not META_REFUTATION_RE.search(self.__sline)):
			all_tuples = self.__dedup_tuples()
			r.extend(self.__check_null_cpu(all_tuples))
			r.extend(self.__check_mem(all_tuples))
			r.extend(self.__check_swap(all_tuples))
			r.extend(self.__check_load_average(all_tuples))
		return r
