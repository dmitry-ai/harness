# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Core.lib.git import df_git_read_text
from .classifier import _GIT_HOOK_SCRIPT_NAMES, _has_shebang
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
from .comment_lexers import lex_batch, lex_c_like, lex_cmake, lex_dockerfile, lex_fsharp, lex_hash_script, lex_hcl, lex_indent_hash, lex_lua, lex_php, lex_python, lex_rust, lex_sass, lex_sed, lex_sfc, lex_sql, lex_tcl, lex_vbscript, lex_zig
COMMENT_LEXER_LANGUAGES: tuple[str, ...] = (
	'awk',
	'batch',
	'c',
	'cmake',
	'cpp',
	'csharp',
	'css',
	'dockerfile',
	'fsharp',
	'go',
	'graphql',
	'groovy',
	'hcl',
	'java',
	'javascript',
	'justfile',
	'kotlin',
	'less',
	'lua',
	'makefile',
	'objc',
	'perl',
	'php',
	'powershell',
	'proto',
	'python',
	'ruby',
	'rust',
	'sass',
	'scala',
	'scss',
	'sed',
	'sfc',
	'shell',
	'sql',
	'swift',
	'tcl',
	'typescript',
	'vb',
	'vbscript',
	'zig',
)
_EXTENSION_LANG: dict[str, str] = {
	'.astro': 'sfc',
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
	'.dockerfile': 'dockerfile',
	'.fish': 'shell',
	'.fs': 'fsharp',
	'.go': 'go',
	'.gql': 'graphql',
	'.graphql': 'graphql',
	'.groovy': 'groovy',
	'.h': 'c',
	'.hcl': 'hcl',
	'.hpp': 'cpp',
	'.hxx': 'cpp',
	'.java': 'java',
	'.js': 'javascript',
	'.jsx': 'javascript',
	'.kt': 'kotlin',
	'.kts': 'kotlin',
	'.less': 'less',
	'.lua': 'lua',
	'.m': 'objc',
	'.mjs': 'javascript',
	'.mm': 'objc',
	'.php': 'php',
	'.phtml': 'php',
	'.pl': 'perl',
	'.pm': 'perl',
	'.proto': 'proto',
	'.ps1': 'powershell',
	'.psd1': 'powershell',
	'.psm1': 'powershell',
	'.py': 'python',
	'.pyi': 'python',
	'.pyx': 'python',
	'.rb': 'ruby',
	'.rs': 'rust',
	'.sass': 'sass',
	'.scala': 'scala',
	'.scss': 'scss',
	'.sed': 'sed',
	'.sh': 'shell',
	'.sql': 'sql',
	'.svelte': 'sfc',
	'.swift': 'swift',
	'.tcl': 'tcl',
	'.tf': 'hcl',
	'.tfvars': 'hcl',
	'.ts': 'typescript',
	'.tsx': 'typescript',
	'.vb': 'vb',
	'.vbs': 'vbscript',
	'.vue': 'sfc',
	'.zig': 'zig',
	'.zsh': 'shell',
}
_BASENAME_LANG: dict[str, str] = {
	'cmakelists.txt': 'cmake',
	'dockerfile': 'dockerfile',
	'gemfile': 'ruby',
	'justfile': 'justfile',
	'makefile': 'makefile',
	'rakefile': 'ruby',
	'vagrantfile': 'ruby',
}
_C_LIKE_CONFIGS: dict[str, dict] = {
	'c': {'line_slash': True, 'single_quote': True},
	'cpp': {'line_slash': True, 'raw_cpp': True, 'single_quote': True},
	# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
	'csharp': {'line_slash': True, 'nl_significant': False, 'single_quote': True, 'triple_quote': True, 'verbatim_at': True},
	'css': {'css_url': True, 'line_slash': False, 'nl_significant': False, 'single_quote': True},
	'go': {'line_slash': True, 'raw_tick': True, 'single_quote': True},
	'groovy': {'line_slash': True, 'shebang_code': True, 'single_quote': True, 'triple_quote': True, 'triple_single': True},
	'java': {'line_slash': True, 'nl_significant': False, 'single_quote': True, 'triple_quote': True},
	'javascript': {'line_slash': True, 'regex_slash': True, 'shebang_code': True, 'single_quote': True, 'template_tick': True},
	'kotlin': {'block_nested': True, 'line_slash': True, 'single_quote': True, 'triple_quote': True},
	'less': {'css_url': True, 'line_slash': True, 'nl_significant': False, 'single_quote': True},
	'objc': {'line_slash': True, 'raw_cpp': True, 'single_quote': True},
	'proto': {'line_slash': True, 'nl_significant': False, 'single_quote': True},
	'scala': {'block_nested': True, 'line_slash': True, 'single_quote': False, 'triple_quote': True},
	'scss': {'css_url': True, 'line_slash': True, 'nl_significant': False, 'single_quote': True},
	'swift': {'block_nested': True, 'line_slash': True, 'single_quote': False, 'triple_quote': True},
	'typescript': {'line_slash': True, 'regex_slash': True, 'shebang_code': True, 'single_quote': True, 'template_tick': True},
}
_DIRECT_LEXERS = {
	'batch': lex_batch,
	'cmake': lex_cmake,
	'dockerfile': lex_dockerfile,
	'fsharp': lex_fsharp,
	'hcl': lex_hcl,
	'justfile': lex_indent_hash,
	'lua': lex_lua,
	'makefile': lex_indent_hash,
	'php': lex_php,
	'python': lex_python,
	'rust': lex_rust,
	'sass': lex_sass,
	'sed': lex_sed,
	'sfc': lex_sfc,
	'sql': lex_sql,
	'tcl': lex_tcl,
	'vb': lex_vbscript,
	'vbscript': lex_vbscript,
	'zig': lex_zig,
}
_HASH_CONFIGS: dict[str, dict] = {
	'awk': {'regex_slash': True, 'single_quote': False},
	'graphql': {'single_quote': False, 'triple_quote': True},
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
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`agent_tools.tdd.diff_executability._classify_existing_git_path()`
# @used-by :func:`agent_tools.tdd.diff_executability._classify_last_commit_path()`
# @used-by :func:`agent_tools.tdd.diff_executability._read_current_git_text()`
# @used-by :func:`agent_tools.tdd.diff_executability._resolve_range_recipes()`
# @used-by :func:`agent_tools.tdd.diff_executability.classify_git_path()`
# @used-by :func:`agent_tools.tdd.mechanical._is_last_commit_mechanical_exempt()`
# @used-by :func:`agent_tools.tdd.mechanical.is_git_file_mechanical_exempt()`
def _git_read_text(repo: Path, args: list[str]) -> str | None:
	return df_git_read_text(repo, *args) if (repo / '.git').exists() else None
# @used-by :func:`detect_comment_language()`
def _lang_from_shebang(first_line: str) -> str:
	low = first_line.lower()
	return next((lang for key, lang in _SHEBANG_MAP if key in low), 'shell')
# @used-by :func:`detect_comment_language()`
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
# @used-by :func:`classify_comment_or_whitespace_diff()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_all_software_code_suffixes_and_basenames_have_lexers()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_comment_only_diffs_accepted_for_all_20_languages()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def detect_comment_language(path: str | Path, *, content: str | None=None) -> str | None:
	p = Path(str(path))
	# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
	# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
	name_low = p.name.lower()
	suffix = df_path_suffix(p)
	if suffix in _EXTENSION_LANG:
		r: str | None = _EXTENSION_LANG[suffix]
	elif name_low in _BASENAME_LANG:
		r = _BASENAME_LANG[name_low]
	elif (not suffix) and (name_low in _GIT_HOOK_SCRIPT_NAMES or _has_shebang(p, content=content)):
		r = _lang_from_shebang(_read_first_line(p, content))
	else:
		r = None
	return r
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`agent_tools.tdd.diff_executability._classify_modified_entry()`
# @used-by :func:`agent_tools.tdd.diff_executability.classify_text_diff()`
# @used-by :func:`is_comment_only_diff()`
# @used-by :func:`is_whitespace_only_diff()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_comment_or_whitespace_diff(path: str | Path, old_text: str | None, new_text: str | None) -> str | None:
	r: str | None = None
	if None is not old_text and None is not new_text:
		lang = detect_comment_language(path, content=old_text)
		if None is not lang:
			if old_text == new_text:
				r = 'unchanged'
			else:
				old_lex, new_lex = (lex_language(lang, old_text), lex_language(lang, new_text))
				if None is not old_lex and None is not new_lex and old_lex[0] == new_lex[0]:
					r = 'comment_only' if old_lex[1] != new_lex[1] else 'whitespace_only'
	return r
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`agent_tools.issue_comment_gate._check_diff_issue_lines()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_all_software_code_suffixes_and_basenames_have_lexers()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_comment_only_diffs_accepted_for_all_20_languages()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_non_comment_and_edge_cases_fail_closed()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_comment_only_diff(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
	return classify_comment_or_whitespace_diff(path, old_text, new_text) in ('comment_only', 'unchanged', 'whitespace_only')
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_whitespace_only_and_indentation_sensitive_fail_closed()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_whitespace_only_diff(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
	return 'whitespace_only' == classify_comment_or_whitespace_diff(path, old_text, new_text)
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`classify_comment_or_whitespace_diff()`
def lex_language(lang: str, source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	direct = _DIRECT_LEXERS.get(lang)
	if None is not direct:
		r = direct(source)
	elif lang in _C_LIKE_CONFIGS:
		r = lex_c_like(source, _C_LIKE_CONFIGS[lang])
	elif lang in _HASH_CONFIGS:
		r = lex_hash_script(source, _HASH_CONFIGS[lang])
	else:
		r = None
	return r
