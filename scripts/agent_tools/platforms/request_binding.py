# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.lib.path_resolve import dfh_relocated_roots
from Df.Harness.lib.request_binding import _canonical_root, _slash_link_upwork_ids, _strip_user_request_wrapper, dfh_canonical_path as canonical_path, dfh_completion_project_id as completion_project_id, dfh_explicit as _explicit, dfh_explicit_with_ids as _explicit_with_ids, dfh_extract_leading_upwork_init_ids as _extract_leading_upwork_init_ids, dfh_format_binding_diagnostic as format_binding_diagnostic, dfh_native_project_fields as native_project_fields, dfh_native_project_id as native_project_id, dfh_raw_text_project_id as _raw_text_project_id, dfh_review_project_id as review_project_id, dfh_same_root as _same_root, dfh_scoped_inputs as scoped_inputs, dfh_text_project_id as text_project_id
_RELOCATED_ROOTS = dfh_relocated_roots()
