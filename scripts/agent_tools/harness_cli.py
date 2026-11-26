# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
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
