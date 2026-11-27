# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Core.lib.text.trim import df_trim_text_left_right
from Df.Harness.Xref.Java.Tags import Tags
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
# @used-by :mod:`agent_tools.xref.java_tags`
def _parse_javadoc_lines(lines: list[str], start_idx: int, end_idx: int, rel_path: str) -> dict:
	return Tags.parse_javadoc_lines(lines, start_idx, end_idx, rel_path, trim_lr_fn=df_trim_text_left_right)
# @used-by :mod:`agent_tools.xref.java_tags`
def collect_file_java_uses(finfo: dict) -> list[dict]:
	return Tags.collect_file_uses(finfo)
# @used-by :mod:`agent_tools.xref.java_tags`
def format_java_ref(target_key: str, current_finfo: dict, repo_index: dict, *, wrap_link: bool=True) -> str:
	return Tags.format_ref(target_key, current_finfo, repo_index, wrap_link=wrap_link)
# @used-by :mod:`agent_tools.xref.java_tags`
def is_valid_java_external(raw_value: str, repo_root: Path) -> bool:
	return Tags.is_valid_external(raw_value, repo_root)
# @used-by :mod:`agent_tools.xref.java_tags`
def parse_javadoc_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	return Tags(lines, anchor_line, rel_path).parse_javadoc_block()
# @used-by :mod:`agent_tools.xref.java_tags`
def resolve_java_target(raw_target: str, current_finfo: dict, repo_index: dict) -> tuple[bool, str | None]:
	return Tags.resolve_target(raw_target, current_finfo, repo_index)
__all__ = ['_parse_javadoc_lines', 'collect_file_java_uses', 'format_java_ref', 'is_valid_java_external', 'parse_javadoc_block', 'resolve_java_target']
