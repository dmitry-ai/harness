# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
from .upwork_project import (
	ANTIGRAVITY_FOLDERS_JSON,
	ANTIGRAVITY_PROJECTS_DIR,
	DAILY_PROPOSALS_ROOT,
	PRIMARY_AGENTS_DIR,
	WORKSPACE_ROOT,
	check_configuration,
	configure_project,
	default_context_config,
	doctor,
	initialize_upwork_project,
	install_global_customizations,
	main,
	register_project,
	resolve_or_create_project_dir,
	run,
	save_registration,
	validate_label,
)
__all__ = [
	'ANTIGRAVITY_FOLDERS_JSON',
	'ANTIGRAVITY_PROJECTS_DIR',
	'DAILY_PROPOSALS_ROOT',
	'PRIMARY_AGENTS_DIR',
	'WORKSPACE_ROOT',
	'check_configuration',
	'configure_project',
	'default_context_config',
	'doctor',
	'initialize_upwork_project',
	'install_global_customizations',
	'main',
	'register_project',
	'resolve_or_create_project_dir',
	'run',
	'save_registration',
	'validate_label',
]
if '__main__' == __name__:
	raise SystemExit(main())
