# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.DiagnosticsScanner import DiagnosticsScanner as SourceDiagnosticsScanner
from .runtime import PRIMARY
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.report()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_explicit_root_required_and_sibling_not_discovered()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_profile_instructions_are_separate_candidates_without_guessing_active_account()`
def diagnose_sources(root, *, platform=None, profile=None, config=None, primary=PRIMARY):
	return SourceDiagnosticsScanner(root, platform=platform, profile=profile, config=config, primary=primary).run()
