# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
# https://github.com/dmitry-ai/harness/issues/160
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
# https://github.com/dmitry-ai/harness/issues/116
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Initialize new Upwork projects in the V2 filesystem layout":
# https://github.com/dmitry-ai/harness/issues/110
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
# https://github.com/dmitry-ai/harness/issues/109
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove automatic Context.md generation from project initialization and finalize stage":
# https://github.com/dmitry-ai/harness/issues/104
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove Antigravity addons runtime health probing from Harness":
# https://github.com/dmitry-ai/harness/issues/93
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import re
import sqlite3
import sys
from .configuration import DISCOVERY_KINDS, configure_codex_project, is_linked_path, load_discovery_manifest, project_discovery_entries
from .knowledge import create_once, json_bytes, populate_agent_kb, render_analysis, validate_analysis
from .storage import create_bytes, locked, replace_bytes
from .upwork_data import canonical_job_url, normalize_job_id, format_kb_project_md
from .upwork_extract import attachment_path, extract_upwork_job
from .runtime import HARNESS_META, PRIMARY as PRIMARY_AGENTS_DIR, all_instances, extract_platform_instances, find_conversation_instance, instance_entry, platform_active, platform_homes, platform_instances, platform_name, platform_settings, request_day, role_settings, settings, using
from .platforms.antigravity import ANTIGRAVITY_FOLDERS_JSON, ANTIGRAVITY_PROJECTS_DIR, register as register_antigravity_default, register_antigravity_project
WORKSPACE_ROOT = Path(settings()['workspace_root']).resolve()
DAILY_PROPOSALS_ROOT = WORKSPACE_ROOT / settings()['daily_root']
def default_context_config(root: Path | None=None):
	out_rel = 'ꙮ/0/Context.md'
	overview_rel = '.md'
	manual_kb_glob = 'KB/**/*.md'
	agent_kb_glob = 'ꘖ/KB/**/*.md'
	ev_excl = '\ua616/KB/Evidence/**'
	journal_rel = 'ꙮ'
	proposals_rel = 'result'
	letters_my = 'Letters/my'
	letters_client = 'Letters/client'
	if None is not root:
		from .path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		if pp.context_output.is_relative_to(pp.root):
			out_rel = pp.context_output.relative_to(pp.root).as_posix()
		ov_p = pp.path('overview_md', pp.root / '.md')
		overview_rel = pp.rel_to_root(ov_p)
		manual_kb_glob = f'{pp.rel_to_root(pp.manual_kb_dir)}/**/*.md'
		agent_kb_glob = f'{pp.rel_to_root(pp.kb_dir)}/**/*.md'
		ev_excl = f'{pp.rel_to_root(pp.evidence_dir)}/**'
		journal_rel = pp.rel_to_root(pp.journal_dir)
		prop_p = pp.path('proposals_dir', pp.root / 'result')
		proposals_rel = pp.rel_to_root(prop_p)
		let_p = pp.path('letters_dir', pp.root / 'Letters')
		let_rel = pp.rel_to_root(let_p)
		if 2 <= pp.fs_version:
			letters_my = let_rel
			cli_let_p = pp.path('client_letters_dir', pp.root / '\u2c0f/\u227a/\U0001f582/\ua19c')
			letters_client = pp.rel_to_root(cli_let_p)
		else:
			letters_my = f'{let_rel}/my'
			letters_client = f'{let_rel}/client'
	return {'version': 1, 'output': out_rel, 'sections': [{'title': 'Project', 'files': [overview_rel]}, {'title': 'Manual KB', 'globs': [manual_kb_glob], 'optional': True}, {'title': 'Agent KB', 'globs': [agent_kb_glob], 'exclude': [ev_excl], 'optional': True}, {'title': 'Analysis', 'journals': [journal_rel], 'optional': True}, {'title': 'Proposals', 'globs': [f'{proposals_rel}/**/final/*.md', f'{proposals_rel}/**/final.md'], 'drafts': [proposals_rel], 'optional': True}, {'title': 'Correspondence', 'optional': True, 'letters': [{'root': letters_my, 'author': 'Consultant', 'languages': ['EN', 'RU']}, {'root': letters_client, 'author': 'Client', 'languages': ['EN', 'RU']}]}]}
def validate_label(value):
	if not value or len(value) > 120 or value != value.strip().rstrip('.') or re.search('[\\\\/:\\x00-\\x1f<>"|?*]', value):
		raise ValueError('Project name must be a Windows-safe domain or short topic, without a URL scheme')
	r = value
	return r
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def configure_project(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, job_url=None, domain_or_topic=None, *, platform=None):
	from .journal import ensure_project_journal_upgraded
	from .path_registry import project_paths, relocated_harness_code_dirs
	root, primary = (Path(project_root).resolve(), Path(primary_agents_dir).resolve())
	ensure_project_journal_upgraded(root)
	pp = project_paths(root, exact_root=True)
	agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary else (root / '.agents')
	if is_linked_path(agents):
		raise ValueError('Configuration must be project-local; existing linked directory is preserved')
	agents.mkdir(parents=True, exist_ok=True)
	rules = agents / 'rules'
	if is_linked_path(rules):
		raise ValueError('Local rules directory is linked; preserved without conversion')
	rules.mkdir(exist_ok=True)
	relocated_codes = relocated_harness_code_dirs(primary=primary)
	for kind in DISCOVERY_KINDS:
		expected = project_discovery_entries(primary, kind, require_dir=True)
		relocated_shared = {(rc / kind).as_posix() for rc in relocated_codes}
		path = agents / f'{kind}.json'
		if not path.exists():
			create_once(path, json_bytes({'entries': expected}).decode('utf-8'))
		else:
			existing = load_discovery_manifest(path, missing_ok=False, entries_error=f'Native manifest needs an entries list; preserved: {path}')
			cur_entries = [e for e in existing.get('entries', []) if not (isinstance(e, dict) and set(e) == {'path'} and isinstance(e.get('path'), str) and Path(e['path']).as_posix() in relocated_shared)]
			missing = [entry for entry in expected if entry not in cur_entries]
			if cur_entries != existing.get('entries', []) or missing:
				existing['entries'] = [*cur_entries, *missing]
				replace_bytes(path, json_bytes(existing))
	context_path = pp.context_config if pp.agents_config_dir.resolve() != primary else (agents / 'context.json')
	use_project_ctx = pp.has_overlay or 2 <= pp.fs_version
	context_config = default_context_config(root if use_project_ctx else None)
	if not context_path.exists():
		create_once(context_path, json_bytes(context_config).decode('utf-8'))
	else:
		v_no_drafts = deepcopy(context_config)
		next((section for section in v_no_drafts['sections'] if 'Proposals' == section['title'])).pop('drafts')
		v_no_excl = deepcopy(context_config)
		next((section for section in v_no_excl['sections'] if 'Agent KB' == section['title'])).pop('exclude')
		v_neither = deepcopy(v_no_drafts)
		next((section for section in v_neither['sections'] if 'Agent KB' == section['title'])).pop('exclude')
		if json.loads(context_path.read_text(encoding='utf-8-sig')) in (v_no_drafts, v_no_excl, v_neither):
			previous = context_path.read_bytes()
			history = pp.data_dir / 'config-history' / (hashlib.sha256(previous).hexdigest() + '-context.json')
			history.parent.mkdir(parents=True, exist_ok=True)
			if not history.exists():
				create_bytes(history, previous)
			replace_bytes(context_path, json_bytes(context_config))
	create_once(rules / '90-project.md', '\n'.join(['---', 'trigger: always_on', 'description: "Project parameters"', '---', '', '# Project', f"Job post: {job_url or 'not specified'}.  ", f'Folder name: `{domain_or_topic or root.name}`; domain ownership is not proven by this.  ', 'Paths and boundaries: shared rules KB-1 and FILE-4.  ', '']))
	cfg = settings(primary / 'runtime.json') if primary != Path(PRIMARY_AGENTS_DIR).resolve() and (primary / 'runtime.json').is_file() else settings()
	if 'codex' in (cfg.get('platforms') or {}):
		configure_codex_project(root, primary, job_url, domain_or_topic)
	return agents
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def check_configuration(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR):
	from .path_registry import project_paths, relocated_harness_code_dirs
	root, primary = (Path(project_root).resolve(), Path(primary_agents_dir).resolve())
	pp = project_paths(root, exact_root=True)
	agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary else (root / '.agents')
	cfg = settings(primary / 'runtime.json') if primary != Path(PRIMARY_AGENTS_DIR).resolve() and (primary / 'runtime.json').is_file() else settings()
	result = configure_codex_project(root, primary, check=True) if 'codex' in (cfg.get('platforms') or {}) else {'valid': True, 'issues': [], 'written': []}
	relocated_codes = relocated_harness_code_dirs(primary=primary)
	for kind in DISCOVERY_KINDS:
		path = agents / f'{kind}.json'
		try:
			entries = load_discovery_manifest(path, entries_error='Native manifest needs an entries list').get('entries', [])
		except (ValueError, OSError) as exc:
			result['valid'] = False
			result['issues'].append({'file': str(path), 'message': str(exc)})
			continue
		shared_equivs = {expected_entry['path'] for expected_entry in project_discovery_entries(primary, kind) if expected_entry['path'] != 'rules'} | {(rc / kind).as_posix() for rc in relocated_codes if (rc / kind).is_dir()}
		entry_paths = {Path(e['path']).as_posix() if Path(e['path']).is_absolute() else e['path'] for e in entries if isinstance(e, dict) and isinstance(e.get('path'), str)}
		missing_shared = not bool(entry_paths & shared_equivs)
		missing_local_rules = 'rules' == kind and 'rules' not in entry_paths
		if missing_shared or missing_local_rules:
			result['valid'] = False
			result['issues'].append({'file': str(path), 'message': 'Antigravity common/local discovery entry is missing; run configure'})
	return result
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
GLOBAL_KINDS = DISCOVERY_KINDS
UNDECLARED_ANTIGRAVITY_HOME = 'current-undeclared'
HOOK_RUNNER_HEADER = '# Generated by Harness; do not edit.\n# https://github.com/dmitry-ai/harness/issues/103\n'
def harness_hook_runner_source(primary=PRIMARY_AGENTS_DIR) -> str:
	fb_lit = json.dumps(Path(primary).resolve().as_posix(), ensure_ascii=True)
	return (
		HOOK_RUNNER_HEADER
		+ 'import json\nfrom pathlib import Path\nimport runpy\nimport sys\n'
		+ f'FALLBACK_PRIMARY = {fb_lit}\n'
		+ "V2_RELS = ('\\u2c0f/\\u227b/\\u2655/\\u26ef', 'Artifacts/\\u227b/Deliverables/\\u26ef', 'code')\n"
		+ 'def _expand_variants(cand: Path) -> list[Path]:\n'
		+ '\tout = [cand]\n'
		+ "\tif cand.parts[-4:] in (('\\u2c0f', '\\u227b', '\\u2655', '\\u26ef'), ('Artifacts', '\\u227b', 'Deliverables', '\\u26ef')):\n"
		+ '\t\tbase = cand.parents[3]\n'
		+ '\t\tout.extend((base / rel for rel in V2_RELS))\n'
		+ "\telif 'code' == cand.name:\n"
		+ '\t\tbase = cand.parent\n'
		+ '\t\tout.extend((base / rel for rel in V2_RELS))\n'
		+ '\treturn out\n'
		+ 'def _discover_primaries() -> list[Path]:\n'
		+ '\tcfg_dir = Path(__file__).resolve().parent\n'
		+ '\tcands: list[Path] = []\n'
		+ "\trules_manifest = cfg_dir / 'rules.json'\n"
		+ '\tif rules_manifest.is_file():\n'
		+ '\t\ttry:\n'
		+ "\t\t\tdata = json.loads(rules_manifest.read_text(encoding='utf-8-sig'))\n"
		+ '\t\t\tif isinstance(data, dict):\n'
		+ "\t\t\t\tfor item in data.get('inherits') or []:\n"
		+ "\t\t\t\t\traw_p = item.get('path') if isinstance(item, dict) else None\n"
		+ '\t\t\t\t\tif isinstance(raw_p, str) and raw_p.strip():\n'
		+ '\t\t\t\t\t\tinh = (cfg_dir / raw_p).resolve() if not Path(raw_p).is_absolute() else Path(raw_p).resolve()\n'
		+ "\t\t\t\t\t\tif 3 <= len(inh.parts) and ('platforms', 'antigravity') == inh.parts[-3:-1]:\n"
		+ '\t\t\t\t\t\t\tcands.extend(_expand_variants(inh.parents[2]))\n'
		+ '\t\t\t\t\t\tif inh.is_file():\n'
		+ "\t\t\t\t\t\t\tsub = json.loads(inh.read_text(encoding='utf-8-sig'))\n"
		+ "\t\t\t\t\t\t\tfor ent in (sub.get('entries') or []) if isinstance(sub, dict) else []:\n"
		+ "\t\t\t\t\t\t\t\tep = ent.get('path') if isinstance(ent, dict) else None\n"
		+ '\t\t\t\t\t\t\t\tif isinstance(ep, str) and ep.strip():\n'
		+ '\t\t\t\t\t\t\t\t\trp = (inh.parent / ep).resolve() if not Path(ep).is_absolute() else Path(ep).resolve()\n'
		+ '\t\t\t\t\t\t\t\t\tcands.extend(_expand_variants(rp.parent))\n'
		+ "\t\t\t\tfor ent in data.get('entries') or []:\n"
		+ "\t\t\t\t\tep = ent.get('path') if isinstance(ent, dict) else None\n"
		+ '\t\t\t\t\tif isinstance(ep, str) and ep.strip():\n'
		+ '\t\t\t\t\t\trp = (cfg_dir / ep).resolve() if not Path(ep).is_absolute() else Path(ep).resolve()\n'
		+ '\t\t\t\t\t\tcands.extend(_expand_variants(rp.parent))\n'
		+ '\t\texcept (OSError, ValueError):\n'
		+ '\t\t\tpass\n'
		+ '\tcands.extend(_expand_variants(Path(FALLBACK_PRIMARY)))\n'
		+ '\tseen: set[str] = set()\n'
		+ '\tout: list[Path] = []\n'
		+ '\tfor c in cands:\n'
		+ '\t\tk = str(c).lower()\n'
		+ '\t\tif k not in seen:\n'
		+ '\t\t\tseen.add(k)\n'
		+ '\t\t\tout.append(c)\n'
		+ '\treturn out\n'
		+ 'def main() -> None:\n'
		+ '\tif 2 > len(sys.argv):\n'
		+ '\t\traise SystemExit(2)\n'
		+ '\tscript_name = Path(sys.argv[1]).name\n'
		+ '\tfor prim in _discover_primaries():\n'
		+ "\t\tscript_path = prim / 'scripts' / script_name\n"
		+ '\t\tif script_path.is_file():\n'
		+ '\t\t\tscripts_dir = str(script_path.parent.resolve())\n'
		+ '\t\t\tif scripts_dir not in sys.path:\n'
		+ '\t\t\t\tsys.path.insert(0, scripts_dir)\n'
		+ '\t\t\tsys.argv = [str(script_path), *sys.argv[2:]]\n'
		+ "\t\t\trunpy.run_path(str(script_path), run_name='__main__')\n"
		+ '\t\t\treturn\n'
		+ "\tsys.stderr.write(f'Harness hook script not found: {script_name}\\n')\n"
		+ '\traise SystemExit(2)\n'
		+ "if '__main__' == __name__:\n"
		+ '\tmain()\n'
	)
def legacy_direct_global_hooks(primary=PRIMARY_AGENTS_DIR):
	primary = Path(primary)
	return {
		'doc4-anti-slop-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file', 'hooks': [{'type': 'command', 'command': f"python {(primary / 'scripts/check_markdown_slop.py').as_posix()}", 'timeout': 10}]}]},
		'rules-and-server-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file|run_command|read_file|mcp_.*|invoke_subagent', 'hooks': [{'type': 'command', 'command': f"python {(primary / 'scripts/check_rules_and_server_gate.py').as_posix()}", 'timeout': 10}]}]},
		'final-turn-gate': {'Stop': [{'type': 'command', 'command': f"python {(primary / 'scripts/check_stop_gate.py').as_posix()}", 'timeout': 15}]},
	}
def legacy_runner_global_hooks(primary=PRIMARY_AGENTS_DIR):
	return {
		'doc4-anti-slop-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file', 'hooks': [{'type': 'command', 'command': 'python harness_hook_runner.py check_markdown_slop.py', 'timeout': 10}]}]},
		'rules-and-server-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file|run_command|read_file|mcp_.*|invoke_subagent', 'hooks': [{'type': 'command', 'command': 'python harness_hook_runner.py check_rules_and_server_gate.py', 'timeout': 10}]}]},
		'final-turn-gate': {'Stop': [{'type': 'command', 'command': 'python harness_hook_runner.py check_stop_gate.py', 'timeout': 15}]},
	}
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
# https://github.com/dmitry-ai/harness/issues/33
def canonical_global_hooks(primary=PRIMARY_AGENTS_DIR, *, config_dir: str | Path | None=None):
	r = {
		'doc4-anti-slop-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file', 'hooks': [{'type': 'command', 'command': 'python harness_hook_runner.py check_markdown_slop.py', 'timeout': 10}]}]},
		'rules-and-server-gate': {'PreToolUse': [{'matcher': 'write_file|edit_file|run_command|read_file|mcp_.*|invoke_subagent|schedule', 'hooks': [{'type': 'command', 'command': 'python harness_hook_runner.py check_rules_and_server_gate.py', 'timeout': 10}]}]},
		'final-turn-gate': {
			'PreInvocation': [{'type': 'command', 'command': 'python harness_hook_runner.py check_pre_invocation.py', 'timeout': 15}],
			'Stop': [{'type': 'command', 'command': 'python harness_hook_runner.py check_stop_gate.py', 'timeout': 15}],
		},
	}
	return r
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
# https://github.com/dmitry-ai/harness/issues/33
def antigravity_global_config_dirs():
	from .path_registry import default_platform_paths
	config = settings()
	if not platform_active('antigravity', config=config):
		return {}
	ag_cfg = config.get('platforms', {}).get('antigravity') or {}
	all_insts = extract_platform_instances(ag_cfg, platform='antigravity', include_disabled=True)
	r = {name: Path(inst['system_paths']['config_dir']) for name, inst in all_insts.items() if inst['enabled'] and 'config_dir' in inst['system_paths']}
	current = Path(default_platform_paths('antigravity')['config_dir'])
	declared_paths = [Path(inst['system_paths']['config_dir']).resolve() for inst in all_insts.values() if 'config_dir' in inst['system_paths']]
	if all((current.resolve() != path for path in declared_paths)):
		r[UNDECLARED_ANTIGRAVITY_HOME] = current
	return r
def _has_entry(entries, target):
	r = isinstance(entries, list) and any((isinstance(e, dict) and isinstance(e.get('path'), str) and Path(e['path']).resolve() == Path(target).resolve() for e in entries))
	return r
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
# https://github.com/dmitry-ai/harness/issues/33
def _install_profile_customizations(config, primary=PRIMARY_AGENTS_DIR):
	from .native_profiles import install_native_profiles
	result = install_native_profiles(['explicit'], primary=primary, config_dirs={'explicit': Path(config)}, codex_homes={})
	return result['profiles']['explicit'] | {'valid': result['valid'], 'issues': result['issues']}
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
# https://github.com/dmitry-ai/harness/issues/33
def check_global_customizations(config_dirs=None, primary=PRIMARY_AGENTS_DIR):
	from .native_profiles import install_native_profiles
	targets = antigravity_global_config_dirs() if config_dirs is None else config_dirs
	result = install_native_profiles(list(targets), primary=primary, check=True, config_dirs=targets, codex_homes={})
	if UNDECLARED_ANTIGRAVITY_HOME in result['profiles']:
		profile = result['profiles'][UNDECLARED_ANTIGRAVITY_HOME]
		issue = {'file': profile['config'], 'message': 'Current Antigravity home is not declared in runtime.json platforms.antigravity.instances'}
		profile['issues'].insert(0, issue)
		profile['valid'] = False
		result['issues'].append(issue)
		result['valid'] = False
	return result
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
# https://github.com/dmitry-ai/harness/issues/33
def install_global_customizations(config_dir=None, primary=PRIMARY_AGENTS_DIR):
	from .native_profiles import install_native_profiles
	targets = {'explicit': Path(config_dir)} if config_dir is not None else antigravity_global_config_dirs()
	result = install_native_profiles(list(targets), primary=primary, config_dirs=targets, codex_homes={})
	result['check'] = check_global_customizations(targets, primary)
	result['valid'] = result['valid'] and result['check']['valid']
	return result
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
def resolve_or_create_project_dir(job_id, domain_or_topic, date_str=None, daily_root=DAILY_PROPOSALS_ROOT):
	from .path_registry import store_path
	job_id, label, day = (normalize_job_id(job_id), validate_label(domain_or_topic), request_day(date_str))
	daily = Path(daily_root).resolve()
	state = store_path('upwork_projects_dir') if daily == DAILY_PROPOSALS_ROOT and (not (daily / '\ua616/data/projects.json').exists()) else daily / '\ua616/data'
	r = None
	with locked(state / 'projects.lock'):
		index_file = state / 'projects.json'
		index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
		if job_id in index:
			cand = (daily / str(index[job_id])).resolve()
			if cand.is_relative_to(daily):
				from .path_registry import _path_key, load_registry
				reg = load_registry()
				ck = _path_key(cand)
				if not cand.is_dir() and ck in reg.relocations:
					reloc = Path(reg.relocations[ck]).resolve()
					if reloc.is_dir():
						r = reloc
				elif cand.is_dir():
					r = cand
			if None is r:
				raise ValueError('Project registry points to a missing or external directory')
		else:
			parent = daily / f'{day.year:04d}' / f'{day.month:02d}' / f'{day.day:02d}'
			parent.mkdir(parents=True, exist_ok=True)
			numbers = []
			for child in parent.iterdir():
				match = re.match('^(\\d+) - ', child.name)
				if child.is_dir() and match:
					numbers.append(int(match[1]))
					state_path = child / '\ua616/project.json'
					matched_state = False
					if state_path.is_file():
						try:
							matched_state = json.loads(state_path.read_text(encoding='utf-8')).get('job_id') == job_id
						except Exception:
							matched_state = False
					if matched_state or any((ov.is_file() and any((u in ov.read_text(encoding='utf-8') for u in (canonical_job_url(job_id), f'https://www.upwork.com/jobs/{job_id}'))) for ov in (child / 'readme.md', child / '.md'))):
						index[job_id] = child.relative_to(daily).as_posix()
						replace_bytes(index_file, json_bytes(index))
						r = child
						break
			if None is r:
				target = parent / f'{max(numbers, default=0) + 1} - {label}'
				target.mkdir(exist_ok=False)
				index[job_id] = target.relative_to(daily).as_posix()
				replace_bytes(index_file, json_bytes(index))
				r = target
	return r
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
def initialize_upwork_project(url_or_id, domain_or_topic=None, date_str=None, daily_root=DAILY_PROPOSALS_ROOT, primary_agents_dir=PRIMARY_AGENTS_DIR, extracted_data=None, register_antigravity=None, antigravity_projects_dir=None, antigravity_folders_json=None, site_hypothesis=None, platform=None, register_native=None, all_platforms=None, launcher_root=None, conversation_id=None):
	platform = platform_name(platform)
	job_id, day = (normalize_job_id(url_or_id), request_day(date_str))
	if None is extracted_data:
		raise ValueError('Capture once with inspect; initialize from that capture')
	data = extracted_data
	if not isinstance(data, dict):
		raise ValueError('Capture must be a JSON object')
	if data.get('job_id') != job_id or not data.get('title') or (not data.get('description')):
		raise ValueError('A capture with matching job ID, title and full description is required')
	label = domain_or_topic or ' '.join(re.findall('[\\w-]+', data['title'])[:5])
	from .path_registry import project_paths
	root = resolve_or_create_project_dir(job_id, label, day.isoformat(), daily_root)
	(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
	with locked(root / '\ua616/data/init.lock'):
		state_file = root / '\ua616/project.json'
		existing_state = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else None
		state = existing_state if None is not existing_state else {'job_id': job_id, 'initialized': False, 'created_by': 'upwork-init', 'created_at': datetime.now(timezone.utc).isoformat()}
		if state['job_id'] != job_id:
			raise ValueError('Project identity mismatch')
		is_legacy_v1 = (isinstance(existing_state, dict) and 1 == existing_state.get('fs_version')) or ((root / 'KB/Project.md').is_file() and not (root / '\U0001f56e').is_dir() and not (root / '\u2c0f').is_dir())
		if not is_legacy_v1:
			for v2_dir in (root / '\U0001f56e', root / '\u2c0f/\u227b', root / '\u2c0f/\u227a'):
				v2_dir.mkdir(parents=True, exist_ok=True)
			state['fs_version'] = 2
			state.setdefault('journal_version', 3)
		else:
			state.setdefault('fs_version', 1)
		replace_bytes(state_file, json_bytes(state))
		configure_project(root, primary_agents_dir, canonical_job_url(job_id), root.name.split(' - ', 1)[-1], platform=platform)
		pp = project_paths(root, exact_root=True)
		state_file = pp.project_json
		from .journal import journal_pair_dirs
		req_dir, res_dir = journal_pair_dirs(pp.journal_dir)
		for folder in (pp.manual_kb_dir, pp.kb_dir, req_dir, res_dir):
			folder.mkdir(parents=True, exist_ok=True)
		from .knowledge import sync_source_folder_attachments, build_project_extra_sources
		assets = sync_source_folder_attachments(root, data.get('saved_attachments') or [])
		extra_sources = build_project_extra_sources(root, data, assets)
		overview_md = pp.path('overview_md', root / '.md')
		if not state['initialized']:
			create_once(overview_md, f"# {data['title']}\n\n{canonical_job_url(job_id)}\n")
			create_once(pp.manual_kb_dir / 'Project.md', format_kb_project_md({**data, 'extra_sources': extra_sources, **({'site_hypothesis': site_hypothesis} if site_hypothesis else {})}))
		source_data = {**data, 'asset_evidence': [{'file': a['file'], 'sha256': a['sha256']} for a in assets], 'extra_sources': extra_sources}
		snapshot = populate_agent_kb(root, source_data)
		if not state['initialized']:
			from .knowledge import sync_initial_website
			website = sync_initial_website(root, snapshot, site_hypothesis)
			if 'conflict' == website['status']:
				raise ValueError('Initial website card conflicts with a manual block; preserve and reconcile it')
		state.update(initialized=True, snapshot=str(snapshot.relative_to(root)))
		state.setdefault('request_date', day.isoformat())
		replace_bytes(state_file, json_bytes(state))
	should_register = register_native if None is not register_native else register_antigravity
	if None is should_register:
		plat_caps = platform_settings(platform).get('capabilities')
		should_register = Path(daily_root).resolve() == DAILY_PROPOSALS_ROOT.resolve() and (None is plat_caps or 'upwork_registration' in plat_caps)
	initial_day = state['request_date']
	info = None
	if should_register:
		from .registration import register_projects
		both = all_platforms if None is not all_platforms else Path(daily_root).resolve() == DAILY_PROPOSALS_ROOT.resolve()
		registrars = {'antigravity': lambda project, label, day: register_antigravity_default(project, label, day, projects_dir=antigravity_projects_dir, folders_json_path=antigravity_folders_json)}
		info = register_projects(root, root.name.split(' - ', 1)[1], initial_day, platform=platform, targets=None if both else [platform], registrars=registrars)
	handoffs: list[dict] = []
	if None is not launcher_root:
		try:
			from .completion import handoff_launcher_turn
			handoffs = handoff_launcher_turn(launcher_root, root, job_id, conversation_id=conversation_id)
		except (OSError, ValueError):
			handoffs = []
	r = {'project_dir': str(root), 'job_id': job_id, 'domain_or_topic': label, 'context_path': None, 'snapshot': str(snapshot), 'registration': info, 'platform': platform, 'registrations': info['registrations'] if info else {}, 'antigravity': info['registrations'].get('antigravity') if info else None, 'analysis_status': 'pending; initialization is not a completed analysis'}
	if handoffs:
		r['launcher_handoff'] = handoffs
	return r
def register_project(project, label=None, day=None, *, platform=None):
	from .registration import register_project as register_one
	r = register_one(project, label, day, platform=platform)
	return r
def save_registration(root, platform, result):
	from .registration import save_registration as save
	r = save(root, platform, result)
	return r
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove Antigravity addons runtime health probing from Harness":
# https://github.com/dmitry-ai/harness/issues/93
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Audit and integrate official Antigravity hooks and slash-commands capabilities into platform adapters":
# https://github.com/dmitry-ai/harness/issues/25
def doctor(primary=PRIMARY_AGENTS_DIR):
	primary = Path(primary)
	files = sorted((primary / 'rules').glob('*.md'))
	sizes = {p.name: p.stat().st_size for p in files}
	if not files or any((size >= 24000 for size in sizes.values())):
		raise ValueError('Rules are missing or exceed the 24,000-byte per-file limit')
	if any((not re.search('^trigger: always_on\\s*$', p.read_text(encoding='utf-8'), re.M) for p in files)):
		raise ValueError('Every shared rule must remain always_on')
	from .operations import COMMANDS
	version_files = sorted((p for p in primary.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json') and ('__pycache__' not in p.parts)))
	tool_version = hashlib.sha256(b''.join((p.relative_to(primary).as_posix().encode() + hashlib.sha256(p.read_bytes()).digest() for p in version_files))).hexdigest()
	cfg_file = primary / 'runtime.json'
	doc_config = settings(cfg_file) if cfg_file.is_file() else ({} if primary.resolve() != PRIMARY_AGENTS_DIR.resolve() else settings())
	active_platform = platform_name(config=doc_config) if doc_config else platform_name()
	plat_cfg = deepcopy(doc_config['platforms'][active_platform]) if doc_config else platform_settings(active_platform)
	roles_cfg = plat_cfg.get('roles') or {}
	env_inventory = all_instances(config=doc_config if doc_config else None, check_exists=True)
	r = {
		'tool_version': tool_version,
		'rules': len(files),
		'rule_bytes': sum(sizes.values()),
		'per_file_bytes': sizes,
		'skills': sorted((p.parent.name for p in (primary / 'skills').glob('*/SKILL.md'))),
		'resolved_role_defaults': {role: role_settings(active_platform, role) for role in ('AA', 'AF') if role in roles_cfg},
		'subagent_policy': plat_cfg.get('subagents', {'selection': 'configured_roles'}),
		'surface': plat_cfg.get('surface'),
		'delegation': plat_cfg.get('delegation'),
		'actual_session_models_verified': False,
		'environments': env_inventory['environments'],
		'enabled_environments': env_inventory['enabled_environments'],
		'instances': env_inventory['instances'],
		'available_handoff_targets': env_inventory['available_handoff_targets'],
		'paths': {'rules': [str(p.resolve()) for p in files], 'reference': str((primary / 'scripts/README-agent-tools.md').resolve()), 'analysis_contract': str((primary / 'scripts/agent_tools/analysis.py').resolve()), 'workflow_reference': str((primary / 'skills/upwork-init/references/workflow.md').resolve()), 'examples': str((primary / 'skills/upwork-init/references').resolve()), 'example_files': [str(p.resolve()) for p in sorted((primary / 'skills/upwork-init/references').glob('*.json'))]},
		'workflow_commands': list(COMMANDS),
		'internal_knowledge': 'ꘖ/KB',
		'context_purpose': 'complete external export for Gemini DeepThink or another external agent',
	}
	# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
	# "Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)":
	# https://github.com/dmitry-ai/harness/issues/33
	r['global_customizations'] = check_global_customizations(primary=primary)
	from .path_registry import load_registry, paths_report
	reg_file = primary / 'paths.json'
	reg = load_registry(reg_file if reg_file.is_file() else None, primary=primary)
	p_rep = paths_report(check=True, registry=reg)
	r['paths_registry'] = {'file': p_rep['registry_file'], 'valid': p_rep['valid'], 'overlays': len(p_rep['discovered_overlays']), 'issues': p_rep['issues']}
	r['valid'] = r['global_customizations']['valid'] and p_rep['valid']
	return r
def instances_report(*, platform=None, instance=None, conversation=None, include_disabled=True, check_exists=True):
	config = settings()
	if conversation:
		matches = find_conversation_instance(conversation, platform=platform, config=config, include_disabled=include_disabled)
		if instance:
			matches = [m for m in matches if m['id'] == instance]
		return {'conversation_id': conversation, 'matches': matches, 'found': bool(matches), 'available_handoff_targets': all_instances(config=config, include_disabled=False)['available_handoff_targets']}
	if instance:
		entry = instance_entry(instance, platform=platform, config=config, include_disabled=include_disabled)
		inv = all_instances(config=config, platform=entry['platform'], include_disabled=include_disabled, check_exists=check_exists)
		record = inv['environments'][entry['platform']]['instances'][entry['id']]
		return {'instance': record, 'available_handoff_targets': all_instances(config=config, include_disabled=False)['available_handoff_targets']}
	return all_instances(config=config, platform=platform, include_disabled=include_disabled, check_exists=check_exists)
def main(argv=None):
	from .cli_common import add_arg_specs
	from .cli_registry import add_registered_parsers
	from .operations import add_parsers
	parser = argparse.ArgumentParser(description=__doc__)
	sub = parser.add_subparsers(dest='command', required=True)
	cfg = settings()
	platforms_map = cfg['platforms']
	all_profiles = tuple(dict.fromkeys((h for p_name in platforms_map for h in platform_homes(p_name, config=cfg, include_disabled=True))))
	codex_profiles = tuple(platform_homes('codex', config=cfg, include_disabled=True)) if 'codex' in platforms_map else ()
	subcommands = {
		'inspect': ('Capture the selected tab once, including attachments', (('url', {}), ('--output', {'required': True, 'type': Path}), ('--tab-id', {}), ('--session-id', {'help': 'Authorized runtime text.browser.sessions entry (default: primary session)'}), ('--cdp-port', {'type': int}))),
		'browser-anchor': ('Verify primary Chrome profile M-2A/M-2B isolation or initialize M-2B sentinel on an explicit Default tab', (('--session-id', {}), ('--init-sentinel-tab', {'help': 'Explicit Default profile tab_id on which to set the isolated https://harness-profile.invalid sentinel cookie'}))),
		'init': ('Initialize from an existing capture without browser requests', (('url', {}), ('--from-json', {'required': True, 'type': Path}), ('--domain', {}), ('--date', {}), ('--site-hypothesis', {'type': Path, 'help': 'Four-part identity hypothesis with evidence and expert probability'}), ('--daily-root', {'type': Path, 'default': DAILY_PROPOSALS_ROOT}), ('--no-register', {'action': 'store_true'}), ('--launcher-root', {'type': Path, 'help': 'Optional launcher workspace root whose open /upwork-init turn should be handed off to the created daily project (default: current working directory)'}), ('--conversation', {'help': 'Optional native conversation UUID to narrow launcher turn handoff'}))),
		'intake-drain': ('Verify and commit managed staging evidence; dry-run unless --apply', (('capture', {'nargs': '?', 'type': Path, 'help': 'One immediate capture directory; default: all managed incoming'}), ('--daily-root', {'type': Path, 'default': DAILY_PROPOSALS_ROOT}), ('--apply', {'action': 'store_true', 'help': 'Drain only after durable evidence and receipt verification'}))),
		'cleanup': ('Remove empty native Upwork projects older than 72 hours; keep the entire daily archive', (('--apply', {'action': 'store_true', 'help': 'Apply cleanup; default is a read-only preview'}), ('--daily-root', {'type': Path, 'default': DAILY_PROPOSALS_ROOT}))),
		'cleanup-report': ('Save the exact cleanup answer with an Istanbul timestamp in AI/log/cleanup', (('--answer', {'default': '-', 'help': 'Answer body as a UTF-8 file, or - for stdin'}),)),
		'configure': ('Create missing native manifests; preserve existing configuration', (('project', {'type': Path}), ('--check', {'action': 'store_true', 'help': 'Check the project Codex projection without writing'}))),
		'register': ('Ensure the same project and folder in configured active platforms', (('project', {'type': Path}), ('--domain', {}), ('--target', {'choices': tuple(platforms_map), 'help': 'Repair one platform only; default: active targets'}))),
		'validate-analysis': ('Check all five analysis stages and their evidence graph', (('input', {'type': Path}), ('--render', {'type': Path}), ('--format', {'choices': ('text', 'json'), 'default': 'text'}), ('--evidence', {'action': 'store_true', 'help': 'Verify saved sources and quotes without network requests'}))),
		'doctor': ('Check discovery inputs, always_on rules, size and model settings', ()),
		'paths': ('Inspect global path registry R, project overlay R+, and template variable expansion', (('project', {'nargs': '?', 'type': Path, 'help': 'Optional project root or child path'}), ('--expand', {'help': 'Optional path template string to expand'}), ('--check', {'action': 'store_true', 'help': 'Validate registry R and discovered project overlays R+'}))),
		'journal-upgrade': ('Upgrade project journal structure to versioned 20-entry range buckets', (('project', {'type': Path}), ('--journal', {'type': Path, 'help': 'Optional explicit journal directory'}), ('--dry-run', {'action': 'store_true', 'help': 'Preview planned file moves without modifying disk'}))),
		'instances': ('Inspect configured environments, instances, enabled status, and system paths for handoff/audit', (('--conversation', {'help': 'Locate the instance owning this conversation UUID'}), ('--only-enabled', {'action': 'store_true', 'help': 'Show only enabled instances'}), ('--no-exists-check', {'action': 'store_true', 'help': 'Skip checking whether each system path currently exists on disk'}))),
		'install-global': ('Connect selected Antigravity/Codex profiles to shared native Harness sources', (('--target-profile', {'action': 'append', 'choices': all_profiles, 'help': 'Profile to configure; repeat for a pilot, default: enabled profiles'}), ('--check', {'action': 'store_true', 'help': 'Verify shared sources, inherited manifests, directory links and role paths without writing'}))),
		'build-native': ('Generate/check native projections from canonical policy and runtime', (('--root', {'type': Path}), ('--check', {'action': 'store_true'}))),
		'policy-instructions': ('Read only the current profile global developer_instructions key', ()),
	}
	for cmd_name, (help_text, specs) in subcommands.items():
		add_arg_specs(sub.add_parser(cmd_name, help=help_text), specs)
	add_registered_parsers(sub)
	add_parsers(sub)
	for child in sub.choices.values():
		add_arg_specs(child, (('--platform', {'choices': tuple(platforms_map)}), ('--codex-profile', {'choices': codex_profiles}), ('--instance', {'help': 'Optional target instance ID from runtime.json'})))
	args = parser.parse_args(argv)
	effective_platform = args.platform
	if None is effective_platform and getattr(args, 'instance', None) and 'instances' != args.command:
		effective_platform = instance_entry(args.instance, include_disabled=True)['platform']
	with using(effective_platform, args.codex_profile, getattr(args, 'instance', None)):
		r = run(args)
	return r
def run(args):
	from .cli_common import dump_json, operation_error_payload, read_input_json, read_input_text, result_exit_code
	from .operations import COMMANDS, analysis_root, execute
	try:
		from .cli_registry import dispatch_registered
		reg_hit, reg_rc = dispatch_registered(args, dump_json, result_exit_code)
		if reg_hit:
			r = reg_rc
		elif args.command in COMMANDS:
			result = execute(args)
			dump_json(result)
			r = result_exit_code(result, extra_failures=(False is result.get('content_available_for_all'), bool(result.get('error')), bool(result.get('extraction_error')), True is result.get('browser_check_required'), 'conflict' == (result.get('publication') or {}).get('status')))
		elif 'validate-analysis' == args.command:
			value = read_input_json(args.input)
			from .analysis import analysis_issues, publish_analysis
			issues = analysis_issues(value)
			if args.evidence and isinstance(value, dict):
				from .evidence import evidence_issues
				issues.extend(evidence_issues(analysis_root(args.input), value))
			for issue in issues:
				if not issue.get('file'):
					issue['file'] = str(args.input.resolve())
			result = {'valid': not issues, 'issues': issues, 'evidence_checked': args.evidence, 'semantic_truth_verified': False}
			if issues:
				if 'json' != args.format:
					print('\n'.join((f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" for x in issues)))
				else:
					dump_json(result)
				r = 1
			else:
				if args.render:
					result['publication'] = publish_analysis(args.input, args.render)
				if args.render and 'conflict' == result['publication']['status']:
					dump_json(result)
					r = 2
				else:
					result['claims'] = sum((len(value[key]) for key in ('identity', 'concerns', 'misconceptions', 'causes', 'methods')))
					dump_json(result)
					r = 0
		else:
			if 'doctor' == args.command:
				result = doctor()
			elif 'paths' == args.command:
				from .path_registry import paths_report
				result = paths_report(getattr(args, 'project', None), expand=getattr(args, 'expand', None), check=bool(getattr(args, 'check', False)))
			elif 'journal-upgrade' == args.command:
				from .journal import ensure_project_journal_upgraded, upgrade_journal
				from .path_registry import project_paths, resolve_project_root
				proj_root = resolve_project_root(args.project)
				if getattr(args, 'journal', None):
					j_target = args.journal if args.journal.is_absolute() else (proj_root / args.journal)
					result = upgrade_journal(j_target, project_root=proj_root, dry_run=bool(getattr(args, 'dry_run', False)))
				elif getattr(args, 'dry_run', False):
					pp_u = project_paths(proj_root, exact_root=True)
					result = upgrade_journal(pp_u.journal_dir if pp_u.journal_glob else pp_u.journal_root_dir, project_root=pp_u.root, dry_run=True)
				else:
					result = ensure_project_journal_upgraded(proj_root)
			elif 'instances' == args.command:
				result = instances_report(platform=args.platform, instance=getattr(args, 'instance', None), conversation=getattr(args, 'conversation', None), include_disabled=not getattr(args, 'only_enabled', False), check_exists=not getattr(args, 'no_exists_check', False))
			elif 'build-native' == args.command:
				from .configuration import build_native
				result = build_native(args.root, check=args.check)
			elif 'policy-instructions' == args.command:
				from .configuration import global_codex_instructions
				result = global_codex_instructions()
			elif 'install-global' == args.command:
				from .native_profiles import install_native_profiles
				result = install_native_profiles(args.target_profile, check=args.check)
			elif 'configure' == args.command:
				result = check_configuration(args.project) if args.check else {'configuration': str(configure_project(args.project))}
			elif 'register' == args.command:
				if not args.project.is_dir():
					raise FileNotFoundError(args.project)
				from .registration import register_projects
				result = register_project(args.project, args.domain, platform=args.target) if args.target else register_projects(args.project, args.domain)
			elif 'inspect' == args.command:
				if args.output.exists():
					raise FileExistsError('Capture exists; reuse it with init --from-json')
				args.output.parent.mkdir(parents=True, exist_ok=True)
				captured = extract_upwork_job(args.url, cdp_port=args.cdp_port or platform_settings().get('browser', {}).get('cdp_port', 9222), tab_id=args.tab_id, session_id=getattr(args, 'session_id', None), attachments_dir=args.output.parent / 'attachments')
				create_bytes(args.output, json_bytes(captured))
				result = {'capture': str(args.output), 'job_id': captured['job_id'], 'coverage': captured['coverage']}
			elif 'browser-anchor' == args.command:
				from .text_browser import browser_anchor_status
				result = browser_anchor_status(session_id=args.session_id, init_sentinel_tab=args.init_sentinel_tab)
			elif 'init' == args.command:
				data = read_input_json(args.from_json)
				if not isinstance(data, dict):
					raise ValueError('Capture must be a JSON object')
				for asset in data.get('saved_attachments') or []:
					if not Path(asset['path']).resolve().is_relative_to(args.from_json.parent.resolve()):
						raise ValueError('Attachment must belong to the capture directory')
				result = initialize_upwork_project(args.url, args.domain, date_str=args.date, daily_root=args.daily_root, extracted_data=data, site_hypothesis=read_input_json(args.site_hypothesis, encoding='utf-8') if args.site_hypothesis else None, register_native=False if args.no_register else None, launcher_root=args.launcher_root if getattr(args, 'launcher_root', None) else Path.cwd(), conversation_id=getattr(args, 'conversation', None))
				from .intake import INCOMING, commit_capture
				capture = Path(os.path.abspath(args.from_json)).parent
				if 'source.json' == args.from_json.name and capture.parent == Path(os.path.abspath(INCOMING)):
					result['intake'] = commit_capture(capture, incoming_root=INCOMING, daily_root=args.daily_root, apply=True)
			elif 'intake-drain' == args.command:
				from .intake import INCOMING, drain_incoming
				result = drain_incoming(args.capture, incoming_root=INCOMING, daily_root=args.daily_root, apply=args.apply)
			elif 'cleanup' == args.command:
				from .cleanup import cleanup_projects
				result = cleanup_projects(apply=args.apply, daily_root=args.daily_root)
			elif 'cleanup-report' != args.command:
				raise ValueError(f'Unknown command: {args.command}')
			else:
				from .cleanup import record_cleanup_answer
				result = record_cleanup_answer(read_input_text(args.answer, encoding='utf-8'))
			dump_json(result)
			r = result_exit_code(result, extra_failures=(False is (result.get('registration') or {}).get('complete'), 'retained' == (result.get('intake') or {}).get('status')))
	except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as exc:
		if args.command in COMMANDS or 'json' == getattr(args, 'format', None):
			dump_json(operation_error_payload(exc))
		else:
			print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
		r = 1
	return r
if '__main__' == __name__:
	raise SystemExit(main())
