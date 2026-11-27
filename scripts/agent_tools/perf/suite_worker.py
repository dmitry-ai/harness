# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.SuiteWorker import SuiteWorker
from Df.Harness.Perf.TimedResult import TimedResult
# 2026-11-24
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
_TimedResult = TimedResult
# @used-by :mod:`agent_tools.perf.suite_worker`
def main(argv: list[str] | None=None) -> int:
	return SuiteWorker.main(argv)
# @used-by unused
def run_module_profile(mod_path: Path, top_dir: Path, *, cprofile_top: int=0) -> dict[str, Any]:
	return SuiteWorker(mod_path, top_dir, cprofile_top=cprofile_top).run()
if '__main__' == __name__:
	raise SystemExit(main())
