# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
def validate_statements(directory: Path) -> list[str]:
	directory = Path(directory)
	if not directory.is_dir():
		r = [f'Missing statement directory: {directory}']
	else:
		entries = sorted((p for p in directory.iterdir() if p.is_dir() and p.name.isdigit()))
		if not entries:
			r = [f'No statement directories: {directory}']
		else:
			errors = []
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
