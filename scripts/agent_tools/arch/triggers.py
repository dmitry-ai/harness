# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
REGISTRY_PATH_HINTS = TriggerClassifier.REGISTRY_PATH_HINTS
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_code_change_trigger_detects_structural_changes_and_ignores_trivial_fixes()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def classify_code_change_trigger(rel_path: str, old_text: str | None, new_text: str | None, *, changed_prod_files: list[str] | tuple[str, ...]=()) -> dict:
	return TriggerClassifier().classify_code_change(rel_path, old_text, new_text, changed_prod_files=changed_prod_files)
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def classify_markdown_arch_trigger(text: str, *, is_issue: bool=False, is_parent_issue: bool=False) -> dict:
	return TriggerClassifier.classify_markdown(text, is_issue=is_issue, is_parent_issue=is_parent_issue)
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_code_change_trigger_detects_structural_changes_and_ignores_trivial_fixes()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def extract_code_symbols(source: str, *, rel_path: str='') -> dict:
	return TriggerClassifier.extract_symbols(source, rel_path=rel_path)
__all__ = ['REGISTRY_PATH_HINTS', 'classify_code_change_trigger', 'classify_markdown_arch_trigger', 'extract_code_symbols']
