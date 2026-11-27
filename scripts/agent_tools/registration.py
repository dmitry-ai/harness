# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.RegistrationAttemptStarter import RegistrationAttemptStarter
from Df.Harness.Project.RegistrationConflict import RegistrationConflict
from Df.Harness.Project.RegistrationExpectation import RegistrationExpectation
from Df.Harness.Project.RegistrationStore import RegistrationStore
from Df.Harness.Project.RegistrationValidator import RegistrationValidator
from Df.Harness.Project.Registry import Registry
from .runtime import settings
# @used-by :mod:`agent_tools.registration`
def _begin(root, platform, intent):
	return RegistrationAttemptStarter(root, platform, intent).begin()
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_codex_adapter_uses_fallback_and_rejects_wrong_native_name_without_rename()`
# @used-by :meth:`test_registration_portability.RegistrationTests.cx()`
# @used-by :mod:`agent_tools.registration`
def _expected(project, label=None, day=None):
	return RegistrationExpectation(project, label, day).build()
# @used-by :meth:`test_registration_portability.RegistrationTests.test_single_adapter_entry_point_preserves_failure_semantics_and_receipt()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_single_success_only_calls_the_selected_adapter()`
# @used-by :mod:`agent_tools.registration`
def register_project(project, label=None, day=None, *, platform=None):
	return Registry(project, label, day, settings_fn=settings).register(platform=platform, single=True)
# @used-by :func:`test_project_rename._assert_renamed_registrations()`
# @used-by :func:`test_project_rename._seed_dual_antigravity()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_registration_portability.RegistrationTests.run_registration()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_intent_is_saved_before_native_call_and_interrupted_attempt_remains()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_pending_secondary_does_not_gate_active_and_pending_active_does()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_secondary_failure_keeps_current_ready_and_previous_success()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_shared_id_without_selected_profile_native_id_is_not_success()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_slow_previous_success_does_not_erase_a_newer_failed_attempt()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_workflow_registration_status_exposes_all_targets_and_pending_targets()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_wrong_roots_or_folder_are_not_reported_as_registered()`
# @used-by :mod:`agent_tools.registration`
def register_projects(project, label=None, day=None, *, platform=None, targets=None, registrars=None):
	return Registry(project, label, day, settings_fn=settings).register(platform=platform, targets=targets, registrars=registrars, single=False)
# @used-by :meth:`test_registration_portability.RegistrationTests.test_legacy_success_and_direct_save_keep_native_identity_after_failure()`
# @used-by :mod:`agent_tools.registration`
def save_registration(root, platform, result):
	return RegistrationStore(root, platform, result).save()
# @used-by :func:`agent_tools.platforms.codex.register()`
# @used-by :mod:`agent_tools.registration`
def validate_registration(project, label, day, platform, result):
	return RegistrationValidator(project, label, day, platform, result).validate()
__all__ = ['RegistrationConflict', '_begin', '_expected', 'register_project', 'register_projects', 'save_registration', 'settings', 'validate_registration']