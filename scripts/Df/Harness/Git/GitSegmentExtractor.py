# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.ShellSegmenter import ShellSegmenter
import re
_GIT_SEG_RE = re.compile(r'^\s*(?:&\s*)?(?:["\']?[A-Za-z]:[\\/][^"\'\s]*[\\/])?git(?:\.exe)?(?:\s+|$)(?P<rest>.*)$')
_HERE_RE = re.compile(r'@\'[\s\S]*?\'@|@"[\s\S]*?"@')
_PY_INLINE_RE = re.compile(r'(\bpython(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\s+)(?:"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\')')
_RAW_TOK_RE = re.compile(r'"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|\S+')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GitSegmentExtractor:
	# @used-by :func:`agent_tools.shell_audit._iter_shell_git_segments()`
	# @used-by :meth:`Df.Harness.Git.GitReadAudit.GitReadAudit.__scan_shell_candidates()`
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.detect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, candidate: str) -> None:
		self.__candidate = candidate
	# @used-by :meth:`GitSegmentExtractor.extract()`
	@staticmethod
	def __unquote(token: str) -> str:
		if not (2 <= len(token) and token[0] == token[-1] and token[0] in ('"', "'")):
			r = token
		else:
			r = token[1:-1].replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
		return r
	# @used-by :func:`agent_tools.shell_audit._iter_shell_git_segments()`
	# @used-by :meth:`Df.Harness.Git.GitReadAudit.GitReadAudit.__scan_shell_candidates()`
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.detect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def extract(self) -> list[tuple[str, list[str]]]:
		cleaned = _PY_INLINE_RE.sub('\\1""', _HERE_RE.sub('""', self.__candidate))
		r: list[tuple[str, list[str]]] = []
		for segment in ShellSegmenter(cleaned).split():
			m = _GIT_SEG_RE.match(segment)
			if None is not m:
				r.append((segment, [self.__unquote(tok) for tok in _RAW_TOK_RE.findall(m.group('rest'))]))
		return r
