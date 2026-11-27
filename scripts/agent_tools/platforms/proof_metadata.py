# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.lib.proof_metadata import VOLATILE_META_KEYS as _VOLATILE_META_KEYS, _dict_prefix_match, _history_equivalent, _project_section, dfh_executor_metadata_equivalent as executor_metadata_equivalent, dfh_proof_semantically_equivalent as proof_semantically_equivalent, dfh_reuse_equivalent_proof as reuse_equivalent_proof
