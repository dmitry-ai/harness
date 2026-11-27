# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class StatementDirValidator:
	# @used-by :func:`agent_tools.statements.validate_statements()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def __init__(self, directory: Path) -> None:
		self.__directory = Path(directory)
	# @used-by :func:`agent_tools.statements.validate_statements()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def validate(self) -> list[str]:
		if not self.__directory.is_dir():
			r = [f'Missing statement directory: {self.__directory}']
		else:
			entries = sorted((p for p in self.__directory.iterdir() if p.is_dir() and p.name.isdigit()))
			if not entries:
				r = [f'No statement directories: {self.__directory}']
			else:
				errors: list[str] = []
				for entry in entries:
					for name in ('.md', 'Test.md'):
						path = entry / name
						try:
							if not path.read_text(encoding='utf-8').strip():
								errors.append(f'Empty file: {path}')
						except (OSError, UnicodeError) as exc:
							errors.append(f'{path}: {exc}')
				r = errors
		return r
