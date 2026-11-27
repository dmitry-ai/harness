# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Python.Overrides import Overrides
# @used-by :mod:`agent_tools.xref.python_overrides`
def find_overridden_method(file_info: dict, cls_info: dict, method_name: str, repo_index: dict) -> str | None:
	return Overrides(file_info, cls_info, repo_index).find_overridden_method(method_name)
# @used-by :mod:`agent_tools.xref.python_overrides`
def is_unittest_testcase_subclass(file_info: dict, cls_info: dict, repo_index: dict) -> bool:
	return Overrides.is_unittest_testcase_subclass(file_info, cls_info, repo_index)
__all__ = ['find_overridden_method', 'is_unittest_testcase_subclass']
