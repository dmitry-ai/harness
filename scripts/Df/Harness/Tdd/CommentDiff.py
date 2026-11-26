# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Core.lib.git import df_git_read_text
from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
from Df.Harness.Tdd.ExtCommentLexer import ExtCommentLexer
from Df.Harness.Tdd.MarkupCommentLexer import MarkupCommentLexer
from Df.Harness.Tdd.ScriptCommentLexer import ScriptCommentLexer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.comment_diff`
class CommentDiff:
	BASENAME_LANG: dict[str, str] = {
		'cmakelists.txt': 'cmake',
		'dockerfile': 'dockerfile',
		'gemfile': 'ruby',
		'justfile': 'justfile',
		'makefile': 'makefile',
		'rakefile': 'ruby',
		'vagrantfile': 'ruby',
	}
	COMMENT_LEXER_LANGUAGES: tuple[str, ...] = (
		'awk', 'batch', 'c', 'cmake', 'cpp', 'csharp', 'css', 'dockerfile', 'fsharp', 'go', 'graphql', 'groovy',
		'hcl', 'java', 'javascript', 'justfile', 'kotlin', 'less', 'lua', 'makefile', 'objc', 'perl', 'php',
		'powershell', 'proto', 'python', 'ruby', 'rust', 'sass', 'scala', 'scss', 'sed', 'sfc', 'shell', 'sql',
		'swift', 'tcl', 'typescript', 'vb', 'vbscript', 'zig',
	)
	EXTENSION_LANG: dict[str, str] = {
		'.astro': 'sfc', '.awk': 'awk', '.bash': 'shell', '.bat': 'batch', '.c': 'c', '.cc': 'cpp',
		'.cjs': 'javascript', '.cmd': 'batch', '.cpp': 'cpp', '.cs': 'csharp', '.css': 'css', '.cxx': 'cpp',
		'.dockerfile': 'dockerfile', '.fish': 'shell', '.fs': 'fsharp', '.go': 'go', '.gql': 'graphql',
		'.graphql': 'graphql', '.groovy': 'groovy', '.h': 'c', '.hcl': 'hcl', '.hpp': 'cpp', '.hxx': 'cpp',
		'.java': 'java', '.js': 'javascript', '.jsx': 'javascript', '.kt': 'kotlin', '.kts': 'kotlin',
		'.less': 'less', '.lua': 'lua', '.m': 'objc', '.mjs': 'javascript', '.mm': 'objc', '.php': 'php',
		'.phtml': 'php', '.pl': 'perl', '.pm': 'perl', '.proto': 'proto', '.ps1': 'powershell',
		'.psd1': 'powershell', '.psm1': 'powershell', '.py': 'python', '.pyi': 'python', '.pyx': 'python',
		'.rb': 'ruby', '.rs': 'rust', '.sass': 'sass', '.scala': 'scala', '.scss': 'scss', '.sed': 'sed',
		'.sh': 'shell', '.sql': 'sql', '.svelte': 'sfc', '.swift': 'swift', '.tcl': 'tcl', '.tf': 'hcl',
		'.tfvars': 'hcl', '.ts': 'typescript', '.tsx': 'typescript', '.vb': 'vb', '.vbs': 'vbscript',
		'.vue': 'sfc', '.zig': 'zig', '.zsh': 'shell',
	}
	__C_LIKE_CONFIGS: dict[str, dict] = {
		'c': {'line_slash': True, 'single_quote': True},
		'cpp': {'line_slash': True, 'raw_cpp': True, 'single_quote': True},
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
	__DIRECT_LEXERS = {
		'batch': ScriptCommentLexer.lex_batch,
		'cmake': ExtCommentLexer.lex_cmake,
		'dockerfile': MarkupCommentLexer.lex_dockerfile,
		'fsharp': ExtCommentLexer.lex_fsharp,
		'hcl': ExtCommentLexer.lex_hcl,
		'justfile': MarkupCommentLexer.lex_indent_hash,
		'lua': ExtCommentLexer.lex_lua,
		'makefile': MarkupCommentLexer.lex_indent_hash,
		'php': CLikeCommentLexer.lex_php,
		'python': CLikeCommentLexer.lex_python,
		'rust': ExtCommentLexer.lex_rust,
		'sass': ExtCommentLexer.lex_sass,
		'sed': MarkupCommentLexer.lex_sed,
		'sfc': MarkupCommentLexer.lex_sfc,
		'sql': ScriptCommentLexer.lex_sql,
		'tcl': MarkupCommentLexer.lex_tcl,
		'vb': ScriptCommentLexer.lex_vbscript,
		'vbscript': ScriptCommentLexer.lex_vbscript,
		'zig': ExtCommentLexer.lex_zig,
	}
	__HASH_CONFIGS: dict[str, dict] = {
		'awk': {'regex_slash': True, 'single_quote': False},
		'graphql': {'single_quote': False, 'triple_quote': True},
		'perl': {'backtick_str': True, 'perl_pod': True, 'regex_slash': True, 'single_quote': True, 'sq_bs': True},
		'powershell': {'ps_block': True, 'ps_here': True, 'single_quote': True},
		'ruby': {'backtick_str': True, 'regex_slash': True, 'ruby_block': True, 'single_quote': True, 'sq_bs': True},
		'shell': {'backtick_str': True, 'sh_hash': True, 'sh_heredoc': True, 'single_quote': True, 'sq_bs': False},
	}
	__SHEBANG_MAP = (
		('python', 'python'),
		('ruby', 'ruby'),
		('perl', 'perl'),
		('awk', 'awk'),
		('node', 'javascript'),
		('pwsh', 'powershell'),
		('php', 'php'),
	)
	# @used-by :func:`agent_tools.tdd.comment_diff.classify_comment_or_whitespace_diff()`
	# @used-by :meth:`CommentDiff.is_comment_only()`
	# @used-by :meth:`CommentDiff.is_whitespace_only()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_modified_entry()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_text_diff()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def __init__(self, path: str | Path, old_text: str | None, new_text: str | None) -> None:
		self.__path = path
		self.__old_text = old_text
		self.__new_text = new_text
	# @used-by :func:`agent_tools.tdd.comment_diff.classify_comment_or_whitespace_diff()`
	# @used-by :meth:`CommentDiff.is_comment_only()`
	# @used-by :meth:`CommentDiff.is_whitespace_only()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_modified_entry()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_text_diff()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def classify(self) -> str | None:
		r: str | None = None
		if None is not self.__old_text and None is not self.__new_text:
			lang = CommentDiff.detect_language(self.__path, content=self.__old_text)
			if None is not lang:
				if self.__old_text == self.__new_text:
					r = 'unchanged'
				else:
					old_lex, new_lex = (CommentDiff.lex_language(lang, self.__old_text), CommentDiff.lex_language(lang, self.__new_text))
					if None is not old_lex and None is not new_lex and old_lex[0] == new_lex[0]:
						r = 'comment_only' if old_lex[1] != new_lex[1] else 'whitespace_only'
		return r
	# @used-by :meth:`CommentDiff.detect_language()`
	@staticmethod
	def __lang_from_shebang(first_line: str) -> str:
		low = first_line.lower()
		return next((lang for key, lang in CommentDiff.__SHEBANG_MAP if key in low), 'shell')
	# @used-by :meth:`CommentDiff.detect_language()`
	@staticmethod
	def __read_first_line(path: Path, content: str | None) -> str:
		if isinstance(content, str):
			r = content.splitlines()[0] if content else ''
		else:
			try:
				with path.open('r', encoding='utf-8', errors='replace') as fh:
					r = fh.readline()
			except OSError:
				r = ''
		return r
	# @used-by :func:`agent_tools.tdd.comment_diff.detect_comment_language()`
	# @used-by :meth:`CommentDiff.classify()`
	@staticmethod
	def detect_language(path: str | Path, *, content: str | None=None) -> str | None:
		p = Path(str(path))
		name_low = p.name.lower()
		suffix = df_path_suffix(p)
		if suffix in CommentDiff.EXTENSION_LANG:
			r: str | None = CommentDiff.EXTENSION_LANG[suffix]
		elif name_low in CommentDiff.BASENAME_LANG:
			r = CommentDiff.BASENAME_LANG[name_low]
		elif (not suffix) and (name_low in CodeClassifier.GIT_HOOK_SCRIPT_NAMES or CodeClassifier.has_shebang(p, content=content)):
			r = CommentDiff.__lang_from_shebang(CommentDiff.__read_first_line(p, content))
		else:
			r = None
		return r
	# @used-by :func:`agent_tools.tdd.comment_diff._git_read_text()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_existing_git_path()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_last_commit_path()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__read_current_git_text()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__resolve_range_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_git_path()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__is_last_commit_exempt()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.is_git_file_exempt()`
	@staticmethod
	def git_read_text(repo: Path, args: list[str]) -> str | None:
		return df_git_read_text(repo, *args) if (repo / '.git').exists() else None
	# @used-by :func:`agent_tools.tdd.comment_diff.is_comment_only_diff()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_diff_issue_lines()`
	@staticmethod
	def is_comment_only(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
		return CommentDiff(path, old_text, new_text).classify() in ('comment_only', 'unchanged', 'whitespace_only')
	# @used-by :func:`agent_tools.tdd.comment_diff.is_whitespace_only_diff()`
	@staticmethod
	def is_whitespace_only(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
		return 'whitespace_only' == CommentDiff(path, old_text, new_text).classify()
	# @used-by :func:`agent_tools.tdd.comment_diff.lex_language()`
	# @used-by :meth:`CommentDiff.classify()`
	@staticmethod
	def lex_language(lang: str, source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		direct = CommentDiff.__DIRECT_LEXERS.get(lang)
		if None is not direct:
			r = direct(source)
		elif lang in CommentDiff.__C_LIKE_CONFIGS:
			r = CLikeCommentLexer(source, CommentDiff.__C_LIKE_CONFIGS[lang]).lex()
		elif lang in CommentDiff.__HASH_CONFIGS:
			r = ScriptCommentLexer.lex_hash_script(source, CommentDiff.__HASH_CONFIGS[lang])
		else:
			r = None
		return r
