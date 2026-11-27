# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.snapshot_canary_ops import CANARY_PROBE, NO_WINDOW, dfh_run_large_transcript_latency_canary
import subprocess
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class CanaryProbe:
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_validate_staged_release()`
	# @used-by :func:`agent_tools.snapshot_canary.run_pre_tool_use_canary()`
	def __init__(self, staging: Path, *, max_seconds: float=2.0, max_subprocesses: int=5, committed_files: int=20, large_canary_fn: Any=None) -> None:
		self.__staging = Path(staging).resolve()
		self.__max_seconds = max_seconds
		self.__max_subprocesses = max_subprocesses
		self.__committed_files = committed_files
		self.__large_canary_fn = large_canary_fn
	# @used-by :meth:`CanaryProbe.run()`
	def __run_pre_tool_probe(self) -> tuple[bool, str]:
		proc = subprocess.run([sys.executable, '-I', '-c', CANARY_PROBE, str(self.__staging), str(self.__max_seconds), str(self.__max_subprocesses), str(self.__committed_files)], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45, check=False, creationflags=NO_WINDOW)
		return (0 == proc.returncode, (proc.stderr or proc.stdout or '').strip())
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_validate_staged_release()`
	# @used-by :func:`agent_tools.snapshot_canary.run_pre_tool_use_canary()`
	def run(self) -> tuple[bool, str]:
		ok, detail = self.__run_pre_tool_probe()
		if not ok:
			r = (False, detail)
		else:
			fn = self.__large_canary_fn or dfh_run_large_transcript_latency_canary
			r = fn(self.__staging)
		return r
