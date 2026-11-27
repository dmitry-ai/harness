# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.cleanup_audit_ops import ORDERED_META_KEYS, dfh_resolve_meta_root
from agent_tools.meta.builders import build_github_issue_metadata
from agent_tools.meta.formatting import posix_path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class AuditLogger:
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_write_cleanup_manifest()`
	# @used-by :func:`agent_tools.cleanup_audit.build_cleanup_metadata()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cleanup_subsystem_classes()`
	def __init__(self, *, timestamp: str, project_root: str | Path | None=None, config: dict | None=None, manifest_path: str | Path | None=None, env: dict[str, str] | None=None) -> None:
		self.__timestamp = timestamp
		self.__project_root = project_root
		self.__config = config
		self.__manifest_path = manifest_path
		self.__env = env
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_write_cleanup_manifest()`
	# @used-by :func:`agent_tools.cleanup_audit.build_cleanup_metadata()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cleanup_subsystem_classes()`
	def run(self) -> dict[str, Any]:
		eff_root = dfh_resolve_meta_root(self.__project_root, self.__config)
		try:
			raw = build_github_issue_metadata(issue_url='', project_root=eff_root, env=self.__env)
		except Exception:
			raw = {}
		raw.pop('Issue', None)
		raw['Time'] = self.__timestamp
		if not isinstance(raw.get('Project'), dict) or (not str(raw['Project'].get('Path') or '').strip()):
			raw['Project'] = {'Name': eff_root.name or 'Workspace', 'Path': posix_path(eff_root)}
		if None is not self.__manifest_path and str(self.__manifest_path).strip():
			trace = dict(raw.get('Trace') or {}) if isinstance(raw.get('Trace'), dict) else {}
			trace['Cleanup Manifest'] = posix_path(Path(self.__manifest_path).resolve())
			raw['Trace'] = trace
		return {k: raw[k] for k in ORDERED_META_KEYS if k in raw and raw[k]}
