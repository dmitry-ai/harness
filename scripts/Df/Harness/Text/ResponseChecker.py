# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import difflib
from pathlib import Path
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.ProseLinter import ProseLinter
from Df.Harness.lib.text_core import KEPT, REMOVAL, REPLACED, dfh_detect_language, dfh_load_lexicon, dfh_normalized, dfh_scan
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ResponseChecker:
	# @used-by :func:`agent_tools.text_core.check_response()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__dispatch()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__check_gate_response()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_diagnostics_scanner_and_response_checker()`
	def __init__(self, path: Path, text: str | None=None, against=(), lexicon=None, journal: Path | None=None) -> None:
		self.__path = path
		self.__text = text
		self.__against = against
		self.__lexicon = lexicon
		self.__journal = journal
	# @used-by :meth:`ResponseChecker.check()`
	def __check_against(self, text: str, findings: list[Finding]) -> None:
		for target in self.__against:
			target_path = Path(target)
			target_lines = target_path.read_bytes().decode('utf-8').splitlines()
			for no, raw in enumerate(text.splitlines(), 1):
				for sentence in re.split('(?<=[.!?])\\s+', raw):
					self.__check_removal_sentence(no, sentence, target_path, target_lines, findings)
	# @used-by :meth:`ResponseChecker.check()`
	def __check_duplicates(self, text: str, findings: list[Finding]) -> None:
		from agent_tools.journal import is_bucket_dir_name, iter_side_step_files, journal_pair_dirs
		from agent_tools.metadata import strip_leading_metadata_header
		parent = self.__path.parent
		folder = journal_pair_dirs(Path(self.__journal))[1] if self.__journal else (parent if parent.name in ('res', '\u227a') else (parent.parent if is_bucket_dir_name(parent.name) and parent.parent.name in ('res', '\u227a') else None))
		if None is not folder and folder.is_dir():
			mine = dfh_normalized(text)
			for _, other in iter_side_step_files(folder):
				if other.resolve() == self.__path.resolve() or (self.__path.stem.isdigit() and other.stem.isdigit() and (int(other.stem) > int(self.__path.stem))):
					continue
				theirs = dfh_normalized(strip_leading_metadata_header(other.read_bytes().decode('utf-8', errors='replace')))
				ratio = self.__similarity(mine, theirs)
				if 0.9 <= ratio:
					findings.append(Finding('warning', 'RESP-DUP', 1, f'{ratio:.0%} similar to {other.name}: compare the current request and operation receipts; similarity alone does not establish whether it was executed'))
	# @used-by :meth:`ResponseChecker.__check_against()`
	def __check_removal_sentence(self, no: int, sentence: str, target: Path, target_lines: list[str], findings: list[Finding]) -> None:
		removal, replaced = (REMOVAL.search(sentence), REPLACED.search(sentence))
		if removal or replaced:
			stop = replaced.start() if replaced and (not removal) else len(sentence)
			kept = KEPT.search(sentence)
			stop = min(stop, kept.start()) if kept else stop
			self.__check_removal_tokens(no, sentence, sentence[:stop], target, target_lines, findings)
	# @used-by :meth:`ResponseChecker.__check_removal_sentence()`
	@staticmethod
	def __check_removal_tokens(no: int, sentence: str, prefix: str, target: Path, target_lines: list[str], findings: list[Finding]) -> None:
		for token in re.findall('`([^`]+)`', prefix):
			cleaned = token.replace('...', '').replace('…', '').strip()
			if 3 > len(cleaned) or cleaned.startswith('§'):
				continue
			needle = re.compile('(?<![\\w-])' + re.escape(cleaned) + '(?!\\w)', re.I)
			hits = [i for i, l in enumerate(target_lines, 1) if needle.search(l)]
			if hits:
				line_list = ', '.join(map(str, hits[:8])) + (' …' if 8 < len(hits) else '')
				findings.append(Finding('warning', 'RESP-CLAIM', no, f'claimed removed/replaced, but `{cleaned}` remains in {target.name} at lines {line_list}', sentence[:100]))
	# @used-by :meth:`ResponseChecker.__check_duplicates()`
	@staticmethod
	def __similarity(mine: str, theirs: str) -> float:
		if not theirs or not mine or min(len(mine), len(theirs)) < 0.8 * max(len(mine), len(theirs)):
			r = 0.0
		elif theirs == mine:
			r = 1.0
		else:
			matcher = difflib.SequenceMatcher(None, mine.split(' '), theirs.split(' '))
			r = matcher.ratio() if 0.9 <= matcher.quick_ratio() else 0.0
		return r
	# @used-by :func:`agent_tools.text_core.check_response()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__dispatch()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__check_gate_response()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_diagnostics_scanner_and_response_checker()`
	def check(self) -> list[Finding]:
		from agent_tools.metadata import strip_leading_metadata_header
		text = strip_leading_metadata_header(self.__path.read_bytes().decode('utf-8') if None is self.__text else self.__text)
		findings: list[Finding] = []
		ProseLinter(dfh_scan(text), 'response', dfh_detect_language(text), findings, dfh_load_lexicon() if None is self.__lexicon else self.__lexicon, []).check()
		self.__check_duplicates(text, findings)
		self.__check_against(text, findings)
		return sorted(findings, key=lambda f: (f.line, f.rule))
