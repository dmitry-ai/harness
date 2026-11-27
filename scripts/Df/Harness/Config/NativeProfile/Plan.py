# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.config_blocks import dfh_has_linked_ancestor
from Df.Harness.lib.native_links import dfh_absolute
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Plan:
	# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	def __init__(self) -> None:
		self.details: dict = {}
		self.files: dict = {}
		self.issues: list = []
		self.managed_links: dict = {}
		self.profiles: dict = {}
		self.removed_shared: set = set()
		self.retired_links: dict = {}
		self.shared: dict = {}
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_agents_md()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	def file(self, path, after) -> None:
		path_abs = dfh_absolute(path)
		if dfh_has_linked_ancestor(path_abs):
			self.issue(path_abs, 'Linked native configuration preserved')
		elif path_abs.exists() and (not path_abs.is_file()):
			self.issue(path_abs, 'Expected a regular configuration file; preserved')
		else:
			before = path_abs.read_bytes() if path_abs.exists() else None
			if before != after:
				self.files[path_abs] = (before, after)
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_problem_metadata()`
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_tdd_exempt_mechanical()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_config_json()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_hooks()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_manifests()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_mcp_json()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_plan()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_agents_md()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._handle_existing_codex_link()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_skill()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_shared_role()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_plan_codex_link()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_profile_roles()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_profile_skills()`
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_check()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_prepare()`
	# @used-by :meth:`Plan.file()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_close()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_comment()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_edit()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	def issue(self, path, message) -> None:
		self.issues.append({'file': str(path), 'message': message})
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	def readonly_issues(self) -> list[dict]:
		active = [link.readonly_issue() for link in self.managed_links.values()]
		retired = [link.readonly_issue(retired=True) for link in self.retired_links.values()]
		return self.issues + [{'file': str(path), 'message': 'Native connection is missing, stale or requires owned legacy retirement'} for path in self.files] + active + retired
