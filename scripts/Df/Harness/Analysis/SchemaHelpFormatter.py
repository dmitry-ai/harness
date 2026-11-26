# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SchemaHelpFormatter:
	# @used-by :func:`agent_tools.schema_help.format_schema_help_text()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, res: dict) -> None:
		self.__res = res
	# @used-by :func:`agent_tools.schema_help.format_schema_help_text()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def render_text(self) -> str:
		lines = [f"Schema Help: {self.__res['topic']} (schema_version: {self.__res['schema_version']})", 'Commands:']
		lines.extend((f'  - {cmd}' for cmd in self.__res.get('commands') or ()))
		lines.append('Required fields: ' + json.dumps(self.__res.get('required_fields') or {}, ensure_ascii=False))
		lines.append('Enums: ' + json.dumps(self.__res.get('enums') or {}, ensure_ascii=False))
		lines.append('Common pitfalls:')
		lines.extend((f'  - {tip}' for tip in self.__res.get('common_pitfalls') or ()))
		lines.append('Minimal example:')
		lines.append(json.dumps(self.__res.get('minimal_example') or {}, ensure_ascii=False, indent='\t'))
		return '\n'.join(lines) + '\n'