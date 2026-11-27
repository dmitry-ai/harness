# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.runtime_context import dfh_platform_settings
import json
import subprocess
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`agent_tools.platforms.codex.shared_control()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init_stores()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProjectRegistrar.ProjectRegistrar.run()`
def dfh_shared_control(request: dict, *, platform_settings_fn=None, run_fn=None) -> dict:
	ps_fn = platform_settings_fn if None is not platform_settings_fn else (lambda name: dfh_platform_settings(name, settings_fn=lambda: SettingsLoader().run()))
	exec_run = run_fn if None is not run_fn else subprocess.run
	config = ps_fn('codex')
	script = 'import {controlWithHelper as control} from ' + json.dumps(Path(config['ui_manage']).as_uri()) + ";let input='';for await(const part of process.stdin)input+=part;console.log(JSON.stringify(await control(JSON.parse(input))));"
	try:
		result = exec_run([config['node'], '--input-type=module', '-e', script], input=json.dumps(request), text=True, capture_output=True, timeout=55, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	except subprocess.TimeoutExpired as exc:
		raise RuntimeError('Shared-Projects timed out; the request may have been accepted. Repeat the same idempotent command to recover.') from exc
	if result.returncode:
		raise RuntimeError('Shared-Projects request failed: ' + (result.stderr.strip() or result.stdout.strip()))
	return json.loads(result.stdout)
