# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.state import df_is_windows
from Df.Harness.TestRunner.ProcessTree import ProcessTree
import subprocess
# 2026-11-24
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
_NO_WINDOW = ProcessTree.NO_WINDOW
POPEN_TREE_KWARGS: dict = ProcessTree.POPEN_TREE_KWARGS
# @used-by unused
def kill_process_tree(proc: subprocess.Popen, *, wait_timeout: float=5.0) -> None:
	ProcessTree(proc, wait_timeout=wait_timeout).kill()
