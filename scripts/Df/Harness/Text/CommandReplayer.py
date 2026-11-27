# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import os
from pathlib import Path
import subprocess
from Df.Harness.lib.text_core import dfh_command_blocks, dfh_default_shell, dfh_output_lines
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CommandReplayer:
	# @used-by :func:`agent_tools.text_core.replay()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__dispatch()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def __init__(self, text: str, *, shell=None, timeout: float=60, only=None, expected_exit=None, contracts=None) -> None:
		self.__text = text
		self.__shell = shell
		self.__timeout = timeout
		self.__only = only
		self.__expected_exit = expected_exit
		self.__contracts = contracts or {}
	# @used-by :meth:`CommandReplayer.__run_block()`
	def __execute(self, shell: str, command: str, record: dict, expected: list[str], contract: dict, wanted_exit: int) -> dict:
		try:
			env = os.environ.copy()
			if Path(shell).is_absolute():
				env['PATH'] = str(Path(shell).parent) + os.pathsep + env.get('PATH', '')
			done = subprocess.run([shell, '-e', '-o', 'pipefail', '-c', command], capture_output=True, timeout=self.__timeout, encoding='utf-8', errors='replace', env=env)
			actual = dfh_output_lines(done.stdout)
			status = 'exit-mismatch' if done.returncode != wanted_exit else 'match' if expected == actual else 'mismatch'
			if 'match' == status and 'stderr' in contract and (contract['stderr'] != done.stderr):
				status = 'mismatch'
			r = {**record, 'status': status, 'expected': expected, 'actual': actual, 'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr}
		except (OSError, subprocess.TimeoutExpired) as exc:
			r = {**record, 'status': 'error', 'error': str(exc)}
		return r
	# @used-by :meth:`CommandReplayer.replay()`
	def __run_block(self, block: dict, shell: str) -> dict:
		first = block['line']
		contract = self.__contracts.get(first, self.__contracts.get(str(first), {}))
		wanted_exit = contract.get('exit', 0)
		if None is not self.__expected_exit:
			wanted_exit = self.__expected_exit.get(first, self.__expected_exit.get(str(first), wanted_exit)) if isinstance(self.__expected_exit, dict) else self.__expected_exit
		if not isinstance(wanted_exit, int) or isinstance(wanted_exit, bool):
			raise ValueError(f'expected exit for line {first} must be an integer')
		record = {'line': first, 'end': block['end'], 'command_sha256': block['command_sha256'], 'shell': str(shell), 'expected_exit': wanted_exit, 'presentation': block['presentation']}
		if not block['closed']:
			r = {**record, 'status': 'error', 'error': 'unclosed command fence'}
		elif not block['presentation'] and 'stdout' not in contract:
			r = {**record, 'status': 'no-quoted-output'}
		else:
			expected = dfh_output_lines(contract['stdout']) if 'stdout' in contract else dfh_output_lines('\n'.join(block['expected']))
			r = self.__execute(shell, block['command'], record, expected, contract, wanted_exit)
		return r
	# @used-by :func:`agent_tools.text_core.replay()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__dispatch()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def replay(self) -> list[dict]:
		results, covered = ([], set())
		shell = self.__shell or dfh_default_shell()
		selected = set(self.__only) if None is not self.__only else None
		for block in dfh_command_blocks(self.__text):
			wanted = {line for line in selected or () if block['line'] <= line <= block['end']}
			if None is not selected and (not wanted):
				continue
			covered.update(wanted)
			results.append(self.__run_block(block, shell))
		for line in sorted((selected or set()) - covered):
			results.append({'line': line, 'status': 'uncovered', 'error': 'selected line is not in a Bash block or its quoted output'})
		return results
