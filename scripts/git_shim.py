# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.git_gate import READ_SUBCOMMANDS, classify_git_argv, run_git_hook, verify_git_write_invocation
def resolve_system_git() -> str:
	r = None
	explicit = os.environ.get('UPWORK_REAL_GIT')
	if explicit and Path(explicit).is_file():
		r = str(Path(explicit).resolve())
	else:
		shim_dir = (Path(__file__).resolve().parent / 'shim').resolve()
		script_dir = Path(__file__).resolve().parent.resolve()
		filtered_paths = []
		for entry in os.environ.get('PATH', '').split(os.pathsep):
			if entry.strip():
				try:
					resolved = Path(entry).resolve()
				except OSError:
					continue
				if resolved not in (shim_dir, script_dir):
					filtered_paths.append(entry)
		found = shutil.which('git', path=os.pathsep.join(filtered_paths))
		if found:
			r = found
		else:
			for candidate in (Path('C:/tools/git/cmd/git.exe'), Path('C:/Program Files/Git/cmd/git.exe')):
				if candidate.is_file():
					r = str(candidate)
					break
	if None is r:
		raise FileNotFoundError('System git executable not found outside .agents shim directory')
	return r
def prepare_git_invocation(argv: list[str], *, mode: str | None=None, cwd: Path | None=None) -> tuple[list[str], dict[str, str]]:
	mode = (mode or os.environ.get('GIT_SHIM_MODE') or os.environ.get('UPWORK_GIT_SHIM_MODE') or 'inject').strip().lower()
	subcommand, has_flag = classify_git_argv(argv)
	effective = list(argv)
	if subcommand in READ_SUBCOMMANDS and (not has_flag):
		if 'reject' == mode:
			raise ValueError(f'EXEC-5 violation: git {subcommand} requires --no-optional-locks')
		effective = ['--no-optional-locks', *effective]
	elif subcommand in ('commit', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
		verify_git_write_invocation(effective, cwd=cwd)
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	r = (effective, env)
	return r
normalize_argv = prepare_git_invocation
def main(argv: list[str] | None=None) -> int:
	args = list(sys.argv[1:] if None is argv else argv)
	if len(args) >= 2 and '--hook' == args[0]:
		return run_git_hook(args[1], args[2:])
	try:
		effective, env = prepare_git_invocation(args)
		binary = resolve_system_git()
	except (ValueError, FileNotFoundError) as exc:
		print(f'ERROR: {exc}', file=sys.stderr)
		r = 2
	else:
		completed = subprocess.run([binary, *effective], env=env)
		r = completed.returncode
	return r
if '__main__' == __name__:
	raise SystemExit(main())
