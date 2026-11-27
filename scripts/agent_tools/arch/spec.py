# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.SpecValidator import SpecValidator
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def extract_arch_specs(markdown_text: str) -> list[dict]:
	return SpecValidator.extract_specs(markdown_text)
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def extract_declared_participants(specs: list[dict]) -> list[str]:
	return SpecValidator.extract_declared_participants(specs)
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_rejects_unknown_mismatched_and_incomplete_specs()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def validate_arch_spec_markdown(text: str, *, require_full_fields: bool=True, catalog: dict | None=None) -> dict:
	return SpecValidator(catalog=catalog).validate(text, require_full_fields=require_full_fields)
__all__ = ['extract_arch_specs', 'extract_declared_participants', 'validate_arch_spec_markdown']
