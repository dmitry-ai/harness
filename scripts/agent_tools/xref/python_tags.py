# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Python.Tags import Tags
# @used-by :mod:`agent_tools.xref.python_tags`
def collect_file_uses(file_info: dict) -> list[dict]:
	return Tags.collect_file_uses(file_info)
# @used-by :mod:`agent_tools.xref.python_tags`
def format_ref(target_key: str, target_kind: str, current_module: str) -> str:
	return Tags.format_ref(target_key, target_kind, current_module)
# @used-by :mod:`agent_tools.xref.python_tags`
def is_valid_external_target(raw_value: str, repo_root: Path) -> bool:
	return Tags.is_valid_external_target(raw_value, repo_root)
# @used-by :mod:`agent_tools.xref.python_tags`
def parse_header_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	return Tags(lines, anchor_line, rel_path).parse_header_block()
# @used-by :mod:`agent_tools.xref.python_tags`
def parse_tag_line(raw_line: str, lineno: int) -> dict | None:
	return Tags.parse_tag_line(raw_line, lineno)
# @used-by :mod:`agent_tools.xref.python_tags`
def resolve_sphinx_target(target_raw: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
	return Tags.resolve_sphinx_target(target_raw, current_module, repo_index)
# @used-by :mod:`agent_tools.xref.python_tags`
def resolve_stdlib_symbol(dotted: str) -> bool:
	return Tags.resolve_stdlib_symbol(dotted)
__all__ = ['collect_file_uses', 'format_ref', 'is_valid_external_target', 'parse_header_block', 'parse_tag_line', 'resolve_sphinx_target', 'resolve_stdlib_symbol']
