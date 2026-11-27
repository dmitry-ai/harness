# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.DomainFactExtractor import ATTR_KEYS, DomainFactExtractor, ID_KEYS, METRIC_LITERAL_SET, METRIC_RE, ORDER_URL_RE, PLAN_RE, TICKET_ID_RE
from Df.Harness.Grounding.FactContradictionChecker import FactContradictionChecker
from Df.Harness.lib.grounding import CLIENT_DELIVERABLE_METRIC_RE, META_REFUTATION_RE, TECHNICAL_SPAN_RE, TIER2_NUMERIC_DOMAIN_RE
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`agent_tools.grounding_domains`
def _collect_json_fact_tuples(obj, default_entity: str, source_loc: str, out: list[dict]) -> None:
	DomainFactExtractor.collect_json_fact_tuples(obj, default_entity, source_loc, out)
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_auditor_and_domain_rules_deduplicate_ledger_tuples()`
# @used-by :mod:`agent_tools.grounding_domains`
def extract_domain_entities(text: str, *, include_substring_metrics: bool=False) -> dict[str, list[str]]:
	return DomainFactExtractor.extract_domain_entities(text, include_substring_metrics=include_substring_metrics)
# @used-by :mod:`agent_tools.grounding_domains`
def extract_fact_tuples(path: Path, raw_text: str | None=None, *, root: Path | None=None) -> list[dict]:
	return DomainFactExtractor(path, raw_text, root=root).extract()
# @used-by :mod:`agent_tools.grounding_domains`
def extract_ticket_metadata(path: Path, raw: str) -> tuple[bool, set[int], str | None]:
	return DomainFactExtractor.extract_ticket_metadata(path, raw)
# @used-by :mod:`agent_tools.grounding_domains`
def fact_tuple_contradictions(sline: str, infos: list[dict], ledger_tuples: list[dict] | None=None) -> list[str]:
	return FactContradictionChecker(sline, infos, ledger_tuples=ledger_tuples).check()
# @used-by :mod:`agent_tools.grounding_domains`
def order_url_issues(sline: str, ev_nums: set[str], combined_raw: str, src_label: str) -> list[str]:
	return DomainFactExtractor.order_url_issues(sline, ev_nums, combined_raw, src_label)
# @used-by :mod:`agent_tools.grounding_domains`
def ticket_author_issues(sline: str, combined_norm: str, src_label: str) -> list[str]:
	return DomainFactExtractor.ticket_author_issues(sline, combined_norm, src_label)
# @used-by :mod:`agent_tools.grounding_domains`
def ticket_message_issues(sline: str, valid_msg_nums: set[int], bound_ticket_ids: set[str]) -> list[str]:
	return DomainFactExtractor.ticket_message_issues(sline, valid_msg_nums, bound_ticket_ids)
__all__ = ['ATTR_KEYS', 'CLIENT_DELIVERABLE_METRIC_RE', 'ID_KEYS', 'META_REFUTATION_RE', 'METRIC_LITERAL_SET', 'METRIC_RE', 'ORDER_URL_RE', 'PLAN_RE', 'TECHNICAL_SPAN_RE', 'TICKET_ID_RE', 'TIER2_NUMERIC_DOMAIN_RE', '_collect_json_fact_tuples', 'extract_domain_entities', 'extract_fact_tuples', 'extract_ticket_metadata', 'fact_tuple_contradictions', 'order_url_issues', 'ticket_author_issues', 'ticket_message_issues']