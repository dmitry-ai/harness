# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Plan:
	# @used-by :func:`agent_tools.native_profiles.build_shared_native()`
	# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
	# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	def __init__(self) -> None:
		self.details = {}
		self.files = {}
		self.issues = []
		self.managed_links = {}
		self.profiles = {}
		self.removed_shared = set()
		self.retired_links = {}
		self.shared = {}
	# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
	def file(self, path, after) -> None:
		from agent_tools import native_profiles as np
		path = np._absolute(path)
		if np._linked_ancestor(path):
			self.issue(path, 'Linked native configuration preserved')
		elif path.exists() and (not path.is_file()):
			self.issue(path, 'Expected a regular configuration file; preserved')
		else:
			before = path.read_bytes() if path.exists() else None
			if before != after:
				self.files[path] = (before, after)
	# @used-by :func:`agent_tools.cli_registry._exec_problem_metadata()`
	# @used-by :func:`agent_tools.cli_registry._exec_tdd_exempt_mechanical()`
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
	# @used-by :func:`agent_tools.native_profiles._codex_plan()`
	# @used-by :func:`agent_tools.native_profiles._plan_codex_link()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_roles()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_skills()`
	# @used-by :func:`agent_tools.native_profiles._retire_shared_roles()`
	# @used-by :func:`agent_tools.native_profiles._shared_plan()`
	# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
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
