# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Core.lib.text.trim import df_trim_text_left_right
from Df.Harness.Xref.Js.Tags import Tags
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
# @used-by :mod:`agent_tools.xref.js_tags`
def _parse_jsdoc_lines(lines: list[str], start_idx: int, end_idx: int, rel_path: str) -> dict:
	return Tags.parse_jsdoc_lines(lines, start_idx, end_idx, rel_path, trim_lr_fn=df_trim_text_left_right)
# @used-by :mod:`agent_tools.xref.js_tags`
def collect_file_js_uses(finfo: dict) -> list[dict]:
	return Tags.collect_file_uses(finfo)
# @used-by :mod:`agent_tools.xref.js_tags`
def format_js_ref(caller_key: str, current_rel: str, repo_index: dict) -> str:
	return Tags.format_ref(caller_key, current_rel, repo_index)
# @used-by :mod:`agent_tools.xref.js_tags`
def is_valid_js_external(raw_value: str, repo_root: Path) -> bool:
	return Tags.is_valid_external(raw_value, repo_root)
# @used-by :mod:`agent_tools.xref.js_tags`
def parse_jsdoc_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	return Tags(lines, anchor_line, rel_path).parse_jsdoc_block()
# @used-by :mod:`agent_tools.xref.js_tags`
def parse_jsdoc_tag_line(raw_line: str, lineno: int) -> dict | None:
	return Tags.parse_jsdoc_tag_line(raw_line, lineno)
# @used-by :mod:`agent_tools.xref.js_tags`
def relative_js_spec(from_rel: str, to_rel: str) -> str:
	return Tags.relative_spec(from_rel, to_rel)
# @used-by :mod:`agent_tools.xref.js_tags`
def resolve_js_link(target_raw: str, note: str, current_rel: str, repo_index: dict) -> tuple[bool, str | None]:
	return Tags.resolve_link(target_raw, note, current_rel, repo_index)
# @used-by :mod:`agent_tools.xref.js_tags`
def resolve_js_module_path(from_rel: str, spec: str, files: dict[str, dict]) -> str | None:
	return Tags.resolve_module_path(from_rel, spec, files)
__all__ = ['_parse_jsdoc_lines', 'collect_file_js_uses', 'format_js_ref', 'is_valid_js_external', 'parse_jsdoc_block', 'parse_jsdoc_tag_line', 'relative_js_spec', 'resolve_js_link', 'resolve_js_module_path']
