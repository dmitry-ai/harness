# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.json_io import df_json_bytes
from Df.Core.lib.sha256 import df_sha256
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Completion.PublicationAdmission import PublicationAdmission, SEAL as _SEAL
from Df.Harness.lib.admission_ops import dfh_admission_binding as binding, dfh_admission_same_binding as _same_binding, dfh_capture_admission as capture, dfh_require_current_admission as require_current, dfh_resolve_admission_proof_file as _resolve_proof_file, dfh_verify_admission as verify
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :mod:`agent_tools.admission`
def _bytes(value):
	return df_json_bytes(value)
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.admission`
def _digest(value):
	return df_sha256(value)
__all__ = ['PublicationAdmission', '_SEAL', '_bytes', '_digest', '_resolve_proof_file', '_same_binding', 'binding', 'capture', 'require_current', 'verify']
