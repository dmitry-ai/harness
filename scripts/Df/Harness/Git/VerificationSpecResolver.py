# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from agent_tools.path_registry import expand_template, load_registry, tool_path
import json
import os
import shlex
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class VerificationSpecResolver:
	# @used-by :func:`agent_tools.polyglot_land.resolve_repo_verification_spec()`
	# @used-by :meth:`Df.Harness.Git.PolyglotTestRunner.PolyglotTestRunner.run()`
	# @used-by :meth:`Df.Harness.Git.RepoHealthChecker.RepoHealthChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init__(self, main_repo: Path, wt_path: Path | None=None, *, slug: str | None=None) -> None:
		self.__main_repo = main_repo
		self.__wt_path = wt_path
		self.__slug = slug
	# @used-by :meth:`VerificationSpecResolver.resolve()`
	def __auto_node_spec(self, wt_path: Path) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		for rel_dir in ('.', 'Upgrade'):
			pkg = wt_path / rel_dir / 'package.json'
			if pkg.is_file():
				try:
					data = json.loads(pkg.read_text(encoding='utf-8-sig'))
				except (OSError, ValueError):
					data = {}
				script = str(((data.get('scripts') if isinstance(data, dict) else None) or {}).get('test') or '').strip()
				if script:
					tokens = shlex.split(script, posix=True)
					if tokens and 'node' == tokens[0].lower():
						tokens[0] = self.__resolve_node_exe()
					r = {'test_cwd': rel_dir, 'test_command': tokens, 'watch_host_files': [], 'timeout_seconds': 180}
					break
		return r
	# @used-by :meth:`VerificationSpecResolver.resolve()`
	def __expand_spec(self, raw_spec: dict[str, Any], reg) -> dict[str, Any]:
		out = dict(raw_spec)
		for key in ('test_command', 'health_command', 'watch_host_files'):
			vals = raw_spec.get(key)
			if isinstance(vals, list):
				out[key] = [self.__expand_token(str(v), reg) for v in vals]
		return out
	# @used-by :meth:`VerificationSpecResolver.__expand_spec()`
	@staticmethod
	def __expand_token(raw: str, reg) -> str:
		val = str(raw or '')
		if '${' in val or '%' in val:
			try:
				val = expand_template(val, reg.resolved_variables, env=reg.env, normalize=False)
			except Exception:
				val = os.path.expandvars(val)
		return val
	# @used-by :meth:`VerificationSpecResolver.__auto_node_spec()`
	@staticmethod
	def __resolve_node_exe() -> str:
		try:
			cand = tool_path('node')
			r = str(cand) if cand.is_file() else 'node'
		except Exception:
			r = 'node'
		return r
	# @used-by :func:`agent_tools.polyglot_land.resolve_repo_verification_spec()`
	# @used-by :meth:`Df.Harness.Git.PolyglotTestRunner.PolyglotTestRunner.run()`
	# @used-by :meth:`Df.Harness.Git.RepoHealthChecker.RepoHealthChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def resolve(self) -> dict[str, Any] | None:
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		reg = load_registry()
		eff_slug = (self.__slug or EvidenceWorkspace.origin_repo_slug(self.__main_repo) or '').strip().lower()
		raw_map = reg.raw.get('repo_verification') or {}
		found: dict[str, Any] | None = None
		if eff_slug and isinstance(raw_map, dict):
			for key, val in raw_map.items():
				if str(key).strip().lower() == eff_slug and isinstance(val, dict):
					found = self.__expand_spec(val, reg)
					break
		return found if None is not found else (self.__auto_node_spec(self.__wt_path) if None is not self.__wt_path else None)
