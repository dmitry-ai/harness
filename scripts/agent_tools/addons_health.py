# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from .runtime import extract_platform_instances, platform_active, platform_key_for_adapter, settings
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
def _is_pid_alive(pid) -> bool:
	if not isinstance(pid, int) or isinstance(pid, bool) or 0 >= pid:
		return False
	if 'nt' == os.name:
		import ctypes
		kernel32 = ctypes.windll.kernel32
		handle = kernel32.OpenProcess(0x1000, False, int(pid))
		if not handle:
			return 5 == kernel32.GetLastError()
		try:
			code = ctypes.c_ulong()
			ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
			return bool(ok and 259 == code.value)
		finally:
			kernel32.CloseHandle(handle)
	try:
		os.kill(pid, 0)
		return True
	except OSError:
		return False
def _is_lockfile_held(user_data_dir: Path) -> bool:
	lockfile = Path(user_data_dir) / 'lockfile'
	if not lockfile.is_file():
		return False
	try:
		with open(lockfile, 'r+b') as fh:
			if 'nt' == os.name:
				import msvcrt
				try:
					msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
					msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
				except OSError:
					return True
			return False
	except OSError:
		return True
def _active_antigravity_instances(ag_cfg: dict) -> list[str]:
	active = []
	for inst_id, inst in extract_platform_instances(ag_cfg, platform='antigravity', include_disabled=False).items():
		udd_raw = inst.get('user_data_dir') or (inst.get('system_paths') or {}).get('user_data_dir')
		if not udd_raw:
			continue
		udd = Path(udd_raw)
		rt_file = udd / 'main-runtime.json'
		pid_alive = False
		if rt_file.is_file():
			try:
				rec = json.loads(rt_file.read_text(encoding='utf-8'))
				pid_alive = _is_pid_alive(rec.get('pid'))
			except (OSError, ValueError):
				pid_alive = False
		if pid_alive or _is_lockfile_held(udd):
			active.append(inst_id)
	return active
def _read_runtime_state(state_path: Path | None) -> tuple[dict | None, bool]:
	if None is state_path or not state_path.is_file():
		return (None, False)
	try:
		data = json.loads(state_path.read_text(encoding='utf-8-sig'))
	except (OSError, ValueError):
		return (None, False)
	if not isinstance(data, dict):
		return (None, False)
	pid_ok = _is_pid_alive(data.get('pid'))
	fresh = False
	updated = data.get('updated')
	if isinstance(updated, str) and updated.strip():
		try:
			dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
			fresh = abs((datetime.now(timezone.utc) - dt).total_seconds()) < 30.0
		except ValueError:
			fresh = False
	alive = pid_ok and 'stopped' != data.get('state') and fresh
	return (data, alive)
def _run_node_cli(node_bin: str, script_path: Path, args: list[str] = (), *, timeout: int = 10) -> tuple[int, dict | str | None]:
	try:
		proc = subprocess.run([node_bin, str(script_path), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=_NO_WINDOW)
	except (OSError, subprocess.SubprocessError) as exc:
		return (1, str(exc))
	out = (proc.stdout or '').strip()
	err = (proc.stderr or '').strip()
	parsed = None
	if out:
		try:
			parsed = json.loads(out)
		except ValueError:
			parsed = out
	return (proc.returncode, parsed if None is not parsed else (err or None))
def check_antigravity_addons(config=None, *, heal: bool = False, timeout: int = 10, run_cli=None) -> dict:
	cfg_all = config
	if None is cfg_all:
		try:
			cfg_all = settings()
		except Exception:
			cfg_all = {}
	ag_key = platform_key_for_adapter('antigravity', cfg_all) if isinstance(cfg_all, dict) else None
	ag_cfg = ((cfg_all or {}).get('platforms') or {}).get(ag_key) if ag_key else None
	addons_cfg = ag_cfg.get('addons') if isinstance(ag_cfg, dict) else None
	if not isinstance(addons_cfg, dict):
		return {'configured': False, 'valid': True, 'status': 'not_configured'}
	if not platform_active(ag_key, config=cfg_all):
		return {'configured': True, 'valid': True, 'status': 'disabled'}
	upgrade_raw = str(addons_cfg.get('upgrade_cli') or '').strip()
	health_raw = str(addons_cfg.get('health_cli') or '').strip()
	state_raw = str(addons_cfg.get('runtime_state_json') or '').strip()
	node_bin = str(addons_cfg.get('node') or 'node').strip() or 'node'
	upgrade_cli = Path(os.path.expanduser(upgrade_raw)) if upgrade_raw else None
	health_cli = Path(os.path.expanduser(health_raw)) if health_raw else None
	state_path = Path(os.path.expanduser(state_raw)) if state_raw else None
	if None is upgrade_cli or None is health_cli or (not upgrade_cli.is_file()) or (not health_cli.is_file()):
		return {'configured': False, 'valid': True, 'status': 'not_configured'}
	runner = run_cli or (lambda script, args: _run_node_cli(node_bin, script, args, timeout=timeout))
	active_profiles = _active_antigravity_instances(ag_cfg)
	state_data, companion_alive = _read_runtime_state(state_path)
	code, health = runner(health_cli, [])
	healed = False
	heal_output = None
	needs_heal = bool(heal and ((not companion_alive) or (active_profiles and 0 != code) or (isinstance(state_data, dict) and 'error' == state_data.get('state'))))
	if needs_heal:
		h_code, heal_output = runner(upgrade_cli, [])
		healed = 0 == h_code
		state_data, companion_alive = _read_runtime_state(state_path)
		code, health = runner(health_cli, [])
	health_state = health.get('state') if isinstance(health, dict) else None
	prof_by_id = {p.get('id'): p for p in ((state_data or {}).get('profiles') or []) if isinstance(p, dict) and p.get('id')} if isinstance(state_data, dict) else {}
	tray_idle = bool(
		2 == code
		and 'unavailable' == health_state
		and companion_alive
		and isinstance(state_data, dict)
		and 'error' != state_data.get('state')
		and active_profiles
		and all(('available' == (prof_by_id.get(pid) or {}).get('state') and 0 == (prof_by_id.get(pid) or {}).get('windows') for pid in active_profiles))
	)
	if 0 == code and 'ready' == health_state:
		status = 'ready'
		valid = True
	elif 'waiting-for-sign-in' == health_state:
		status = 'waiting-for-sign-in'
		valid = True
	elif tray_idle or (not active_profiles and 'unavailable' == health_state and companion_alive and (not isinstance(state_data, dict) or 'error' != state_data.get('state'))):
		status = 'idle'
		valid = True
	else:
		status = 'error'
		valid = False
	r = {
		'configured': True,
		'valid': valid,
		'status': status,
		'companion_alive': companion_alive,
		'companion_pid': state_data.get('pid') if isinstance(state_data, dict) else None,
		'companion_state': state_data.get('state') if isinstance(state_data, dict) else None,
		'active_profiles': active_profiles,
		'healed': healed,
		'health_exit_code': code,
		'health': health,
	}
	if None is not heal_output:
		r['heal_output'] = heal_output
	return r
