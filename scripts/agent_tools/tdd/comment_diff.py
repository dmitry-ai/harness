# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/238
from __future__ import annotations
from pathlib import Path
from .classifier import _GIT_HOOK_SCRIPT_NAMES, _has_shebang
from .comment_lexers import lex_batch, lex_c_like, lex_hash_script, lex_php, lex_python, lex_sql, lex_vbscript
import os
import subprocess
COMMENT_LEXER_LANGUAGES: tuple[str, ...] = (
	'awk',
	'batch',
	'c',
	'cpp',
	'csharp',
	'css',
	'java',
	'javascript',
	'kotlin',
	'less',
	'perl',
	'php',
	'powershell',
	'python',
	'ruby',
	'scss',
	'shell',
	'sql',
	'typescript',
	'vbscript',
)
_EXTENSION_LANG: dict[str, str] = {
	'.awk': 'awk',
	'.bash': 'shell',
	'.bat': 'batch',
	'.c': 'c',
	'.cc': 'cpp',
	'.cjs': 'javascript',
	'.cmd': 'batch',
	'.cpp': 'cpp',
	'.cs': 'csharp',
	'.css': 'css',
	'.cxx': 'cpp',
	'.fish': 'shell',
	'.h': 'c',
	'.hpp': 'cpp',
	'.hxx': 'cpp',
	'.java': 'java',
	'.js': 'javascript',
	'.jsx': 'javascript',
	'.kt': 'kotlin',
	'.kts': 'kotlin',
	'.less': 'less',
	'.mjs': 'javascript',
	'.php': 'php',
	'.phtml': 'php',
	'.pl': 'perl',
	'.pm': 'perl',
	'.ps1': 'powershell',
	'.psd1': 'powershell',
	'.psm1': 'powershell',
	'.py': 'python',
	'.pyi': 'python',
	'.pyx': 'python',
	'.rb': 'ruby',
	'.sass': 'scss',
	'.scss': 'scss',
	'.sh': 'shell',
	'.sql': 'sql',
	'.ts': 'typescript',
	'.tsx': 'typescript',
	'.vbs': 'vbscript',
	'.zsh': 'shell',
}
_BASENAME_LANG: dict[str, str] = {
	'gemfile': 'ruby',
	'rakefile': 'ruby',
}
_C_LIKE_CONFIGS: dict[str, dict] = {
	'c': {'line_slash': True, 'single_quote': True},
	'cpp': {'line_slash': True, 'raw_cpp': True, 'single_quote': True},
	'csharp': {'line_slash': True, 'single_quote': True, 'triple_quote': True, 'verbatim_at': True},
	'css': {'css_url': True, 'line_slash': False, 'single_quote': True},
	'java': {'line_slash': True, 'single_quote': True, 'triple_quote': True},
	'javascript': {'line_slash': True, 'regex_slash': True, 'shebang_code': True, 'single_quote': True, 'template_tick': True},
	'kotlin': {'block_nested': True, 'line_slash': True, 'single_quote': True, 'triple_quote': True},
	'less': {'css_url': True, 'line_slash': True, 'single_quote': True},
	'scss': {'css_url': True, 'line_slash': True, 'single_quote': True},
	'typescript': {'line_slash': True, 'regex_slash': True, 'shebang_code': True, 'single_quote': True, 'template_tick': True},
}
_HASH_CONFIGS: dict[str, dict] = {
	'awk': {'regex_slash': True, 'single_quote': False},
	'perl': {'backtick_str': True, 'perl_pod': True, 'regex_slash': True, 'single_quote': True, 'sq_bs': True},
	'powershell': {'ps_block': True, 'ps_here': True, 'single_quote': True},
	'ruby': {'backtick_str': True, 'regex_slash': True, 'ruby_block': True, 'single_quote': True, 'sq_bs': True},
	'shell': {'backtick_str': True, 'sh_hash': True, 'sh_heredoc': True, 'single_quote': True, 'sq_bs': False},
}
_SHEBANG_MAP = (
	('python', 'python'),
	('ruby', 'ruby'),
	('perl', 'perl'),
	('awk', 'awk'),
	('node', 'javascript'),
	('pwsh', 'powershell'),
	('php', 'php'),
)
def _git_read_text(repo: Path, args: list[str]) -> str | None:
	r = None
	if (repo / '.git').exists():
		proc = subprocess.run(
			['git', '--no-optional-locks', '-C', str(repo), *args],
			stdin=subprocess.DEVNULL,
			capture_output=True,
			env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
			timeout=30,
			check=False,
			creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
		)
		if 0 == proc.returncode:
			r = proc.stdout.decode('utf-8', errors='replace')
	return r
def _lang_from_shebang(first_line: str) -> str:
	low = first_line.lower()
	return next((lang for key, lang in _SHEBANG_MAP if key in low), 'shell')
def _read_first_line(path: Path, content: str | None) -> str:
	if isinstance(content, str):
		r = content.splitlines()[0] if content else ''
	else:
		try:
			with path.open('r', encoding='utf-8', errors='replace') as fh:
				r = fh.readline()
		except OSError:
			r = ''
	return r
def detect_comment_language(path: str | Path, *, content: str | None=None) -> str | None:
	p = Path(str(path))
	suffix = p.suffix.lower()
	name_low = p.name.lower()
	if suffix in _EXTENSION_LANG:
		r: str | None = _EXTENSION_LANG[suffix]
	elif name_low in _BASENAME_LANG:
		r = _BASENAME_LANG[name_low]
	elif (not suffix) and (name_low in _GIT_HOOK_SCRIPT_NAMES or _has_shebang(p, content=content)):
		r = _lang_from_shebang(_read_first_line(p, content))
	else:
		r = None
	return r
def is_comment_only_diff(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
	if None is old_text or None is new_text:
		r = False
	else:
		lang = detect_comment_language(path, content=old_text)
		if None is lang:
			r = False
		elif old_text == new_text:
			r = True
		else:
			old_lex = lex_language(lang, old_text)
			new_lex = lex_language(lang, new_text)
			r = (None is not old_lex) and (None is not new_lex) and (old_lex[0] == new_lex[0]) and (old_lex[1] != new_lex[1])
	return r
def is_git_file_comment_only(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False) -> bool:
	repo = Path(repo_root).resolve()
	fpath = repo / rel_posix
	cur = disk_text
	if None is cur:
		cur = _git_read_text(repo, ['show', f':{rel_posix}']) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
	head = _git_read_text(repo, ['show', f'HEAD:{rel_posix}'])
	if None is cur:
		r = False
	elif None is not head and head != cur:
		r = is_comment_only_diff(fpath, head, cur)
	else:
		r = _is_last_commit_comment_only(repo, fpath, rel_posix)
	return r
def _is_last_commit_comment_only(repo: Path, fpath: Path, rel_posix: str) -> bool:
	sha_raw = _git_read_text(repo, ['log', '-n', '1', '--format=%H', '--', f':(literal){rel_posix}'])
	sha = (sha_raw or '').strip()
	if not sha:
		r = False
	else:
		prev_txt = _git_read_text(repo, ['show', f'{sha}^:{rel_posix}'])
		curr_txt = _git_read_text(repo, ['show', f'{sha}:{rel_posix}'])
		r = is_comment_only_diff(fpath, prev_txt, curr_txt)
	return r
def lex_language(lang: str, source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	if 'python' == lang:
		r = lex_python(source)
	elif 'php' == lang:
		r = lex_php(source)
	elif 'sql' == lang:
		r = lex_sql(source)
	elif 'batch' == lang:
		r = lex_batch(source)
	elif 'vbscript' == lang:
		r = lex_vbscript(source)
	elif lang in _C_LIKE_CONFIGS:
		r = lex_c_like(source, _C_LIKE_CONFIGS[lang])
	elif lang in _HASH_CONFIGS:
		r = lex_hash_script(source, _HASH_CONFIGS[lang])
	else:
		r = None
	return r
