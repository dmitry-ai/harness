# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.Catalog import Catalog
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def catalog_pattern_names(*, catalog: dict | None=None) -> set[str]:
	return Catalog.names(catalog=catalog)
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def load_pattern_catalog(primary: str | Path | None=None) -> dict:
	return Catalog.load(primary)
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def lookup_pattern(name: str, *, catalog: dict | None=None) -> dict | None:
	return Catalog(catalog=catalog).lookup(name)
__all__ = ['catalog_pattern_names', 'load_pattern_catalog', 'lookup_pattern']
