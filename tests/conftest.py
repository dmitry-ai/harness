# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections.abc import MutableMapping
from pathlib import Path
import os
import sys
TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / 'scripts'
# 2026-11-24
# "Enable parallel pytest-xdist full-suite execution and outcome parsing":
# https://github.com/dmitry-ai/harness/issues/178
# @used-by :mod:`conftest`
def configure_test_environment(*, sys_path: list[str] | None=None, env: MutableMapping[str, str] | None=None) -> None:
	target_path = sys.path if None is sys_path else sys_path
	for entry in (str(TESTS_DIR), str(SCRIPTS_DIR)):
		if entry not in target_path:
			target_path.insert(0, entry)
	target_env = os.environ if None is env else env
	target_env.setdefault('GIT_OPTIONAL_LOCKS', '0')
	target_env.setdefault('HARNESS_TEST_NO_FSYNC', '1')
configure_test_environment()
