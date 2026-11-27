# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.runtime import instance_entry, platform_homes, platform_settings, settings, using
from agent_tools.storage import create_bytes
import argparse
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Publisher import Publisher
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.LabelError import LabelError
from Df.Harness.Project.Registry import Registry
from Df.Harness.Upwork.ConfigurationChecker import ConfigurationChecker
from Df.Harness.Upwork.DoctorAuditor import DoctorAuditor
from Df.Harness.Upwork.InstancesReporter import InstancesReporter
from Df.Harness.Upwork.JobExtractor import JobExtractor
from Df.Harness.Upwork.ProjectConfigurator import ProjectConfigurator
from Df.Harness.Upwork.ProjectInitializer import ProjectInitializer
import os
from pathlib import Path
import sqlite3
import sys
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CliRunner:
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :meth:`CliRunner.main()`
	def __init__(self, args, *, doctor_fn=None, configure_fn=None, check_cfg_fn=None, init_fn=None, extract_fn=None, instances_fn=None, register_fn=None, platform_settings_fn=None, incoming_fn=None, commit_capture_fn=None, drain_incoming_fn=None) -> None:
		self.__args = args
		self.__doctor_fn = (lambda: DoctorAuditor().audit()) if None is doctor_fn else doctor_fn
		self.__configure_fn = (lambda p: ProjectConfigurator(p).configure()) if None is configure_fn else configure_fn
		self.__check_cfg_fn = (lambda p: ConfigurationChecker(p).check()) if None is check_cfg_fn else check_cfg_fn
		self.__init_fn, self.__extract_fn, self.__instances_fn, self.__register_fn = (init_fn, extract_fn, instances_fn, register_fn)
		self.__platform_settings_fn = platform_settings if None is platform_settings_fn else platform_settings_fn
		self.__incoming_fn, self.__commit_capture_fn, self.__drain_incoming_fn = (incoming_fn, commit_capture_fn, drain_incoming_fn)
	# @used-by :meth:`CliRunner.main()`
	@classmethod
	def __build_parser(cls, cfg: dict, daily_root: Path | None, description) -> argparse.ArgumentParser:
		from agent_tools.cli_common import add_arg_specs
		from agent_tools.cli_registry import add_registered_parsers
		from agent_tools.operations import add_parsers
		platforms_map = cfg['platforms']
		all_profiles = tuple(dict.fromkeys((h for p_name in platforms_map for h in platform_homes(p_name, config=cfg, include_disabled=True))))
		codex_profiles = tuple(platform_homes('codex', config=cfg, include_disabled=True)) if 'codex' in platforms_map else ()
		d_root = Path(cfg['workspace_root']).resolve() / cfg['daily_root'] if None is daily_root else daily_root
		parser = argparse.ArgumentParser(description=description)
		sub = parser.add_subparsers(dest='command', required=True)
		for cmd_name, (help_text, specs) in cls.__subcommand_specs(d_root, all_profiles, platforms_map).items():
			add_arg_specs(sub.add_parser(cmd_name, help=help_text), specs)
		add_registered_parsers(sub)
		add_parsers(sub)
		for child in sub.choices.values():
			add_arg_specs(child, (('--platform', {'choices': tuple(platforms_map)}), ('--codex-profile', {'choices': codex_profiles}), ('--instance', {'help': 'Optional target instance ID from runtime.json'})))
		return parser
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __cmd_init(self) -> dict:
		from agent_tools.cli_common import read_input_json
		from agent_tools.path_registry import store_path
		from Df.Harness.Project.Intake.CaptureCommitter import CaptureCommitter
		a = self.__args
		data = self.__load_init_capture(read_input_json, a.from_json)
		site_h = read_input_json(a.site_hypothesis, encoding='utf-8') if a.site_hypothesis else None
		kw = {'date_str': a.date, 'daily_root': a.daily_root, 'extracted_data': data, 'site_hypothesis': site_h, 'register_native': False if a.no_register else None, 'launcher_root': a.launcher_root if getattr(a, 'launcher_root', None) else Path.cwd(), 'conversation_id': getattr(a, 'conversation', None), 'topic': getattr(a, 'topic', None)}
		r = ProjectInitializer(a.url, a.domain, **kw).initialize() if None is self.__init_fn else self.__init_fn(a.url, a.domain, **kw)
		incoming = store_path('incoming_dir') if None is self.__incoming_fn else self.__incoming_fn()
		capture = Path(os.path.abspath(a.from_json)).parent
		if 'source.json' == a.from_json.name and capture.parent == Path(os.path.abspath(incoming)):
			r['intake'] = CaptureCommitter(capture, incoming_root=incoming, daily_root=a.daily_root, apply=True).commit() if None is self.__commit_capture_fn else self.__commit_capture_fn(capture, incoming_root=incoming, daily_root=a.daily_root, apply=True)
		return r
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __cmd_inspect(self) -> dict:
		from Df.Harness.Project.OnceFileWriter import OnceFileWriter
		a = self.__args
		if a.output.exists():
			raise FileExistsError('Capture exists; reuse it with init --from-json')
		a.output.parent.mkdir(parents=True, exist_ok=True)
		port = a.cdp_port or self.__platform_settings_fn().get('browser', {}).get('cdp_port', 9222)
		kw = {'cdp_port': port, 'tab_id': a.tab_id, 'session_id': getattr(a, 'session_id', None), 'attachments_dir': a.output.parent / 'attachments'}
		captured = JobExtractor(a.url, **kw).extract() if None is self.__extract_fn else self.__extract_fn(a.url, **kw)
		create_bytes(a.output, OnceFileWriter.json_bytes(captured))
		return {'capture': str(a.output), 'job_id': captured['job_id'], 'coverage': captured['coverage']}
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __cmd_journal_upgrade(self) -> dict:
		from agent_tools.journal import ensure_project_journal_upgraded, upgrade_journal
		from agent_tools.path_registry import project_paths, resolve_project_root
		a = self.__args
		proj_root = resolve_project_root(a.project)
		if getattr(a, 'journal', None):
			j_target = a.journal if a.journal.is_absolute() else (proj_root / a.journal)
			r = upgrade_journal(j_target, project_root=proj_root, dry_run=bool(getattr(a, 'dry_run', False)))
		elif getattr(a, 'dry_run', False):
			pp_u = project_paths(proj_root, exact_root=True)
			r = upgrade_journal(pp_u.journal_dir if pp_u.journal_glob else pp_u.journal_root_dir, project_root=pp_u.root, dry_run=True)
		else:
			r = ensure_project_journal_upgraded(proj_root)
		return r
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __cmd_register(self) -> dict:
		a = self.__args
		if not a.project.is_dir():
			raise FileNotFoundError(a.project)
		if a.target:
			r = Registry(a.project, a.domain).register(platform=a.target, single=True) if None is self.__register_fn else self.__register_fn(a.project, a.domain, platform=a.target)
		else:
			r = Registry(a.project, a.domain).register(single=False)
		return r
	# @used-by :meth:`CliRunner.__execute()`
	def __cmd_validate_analysis(self, dump_json, analysis_root) -> int:
		from agent_tools.cli_common import read_input_json
		a = self.__args
		value = read_input_json(a.input)
		issues = Validator(value).issues()
		if a.evidence and isinstance(value, dict):
			issues.extend(EvidenceAuditor(analysis_root(a.input), value).issues())
		for issue in issues:
			if not issue.get('file'):
				issue['file'] = str(a.input.resolve())
		result: dict = {'valid': not issues, 'issues': issues, 'evidence_checked': a.evidence, 'semantic_truth_verified': False}
		return self.__emit_validation_result(a, value, result, dump_json)
	# @used-by :meth:`CliRunner.__execute()`
	def __dispatch_builtin(self) -> dict:
		a = self.__args
		handlers = {'doctor': self.__doctor_fn, 'paths': self.__run_paths, 'journal-upgrade': self.__cmd_journal_upgrade, 'instances': self.__run_instances, 'build-native': self.__run_build_native, 'policy-instructions': self.__run_policy_instructions, 'install-global': self.__run_install_global, 'configure': lambda: self.__check_cfg_fn(a.project) if a.check else {'configuration': str(self.__configure_fn(a.project))}, 'register': self.__cmd_register, 'inspect': self.__cmd_inspect, 'browser-anchor': self.__run_browser_anchor, 'init': self.__cmd_init, 'intake-drain': self.__run_intake_drain, 'cleanup': self.__run_cleanup, 'cleanup-report': self.__run_cleanup_report}
		if a.command not in handlers:
			raise ValueError(f'Unknown command: {a.command}')
		return handlers[a.command]()
	# @used-by :meth:`CliRunner.__cmd_validate_analysis()`
	@staticmethod
	def __emit_validation_result(a, value, result: dict, dump_json) -> int:
		if result['issues']:
			if 'json' != a.format:
				print('\n'.join((f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" for x in result['issues'])))
			else:
				dump_json(result)
			r = 1
		else:
			if a.render:
				result['publication'] = Publisher(a.input, a.render).publish()
			if a.render and 'conflict' == result['publication']['status']:
				dump_json(result)
				r = 2
			else:
				result['claims'] = sum((len(value[key]) for key in ('identity', 'concerns', 'misconceptions', 'causes', 'methods')))
				dump_json(result)
				r = 0
		return r
	# @used-by :meth:`CliRunner.run()`
	def __execute(self, dump_json, result_exit_code, commands, analysis_root, execute_fn) -> int:
		from agent_tools.cli_registry import dispatch_registered
		a = self.__args
		reg_hit, reg_rc = dispatch_registered(a, dump_json, result_exit_code)
		if reg_hit:
			r = reg_rc
		elif a.command in commands:
			result = execute_fn(a)
			dump_json(result)
			r = result_exit_code(result, extra_failures=(False is result.get('content_available_for_all'), bool(result.get('error')), bool(result.get('extraction_error')), True is result.get('browser_check_required'), 'conflict' == (result.get('publication') or {}).get('status')))
		elif 'validate-analysis' == a.command:
			r = self.__cmd_validate_analysis(dump_json, analysis_root)
		else:
			result = self.__dispatch_builtin()
			dump_json(result)
			r = result_exit_code(result, extra_failures=(False is (result.get('registration') or {}).get('complete'), 'retained' == (result.get('intake') or {}).get('status')))
		return r
	# @used-by :meth:`CliRunner.__cmd_init()`
	@staticmethod
	def __load_init_capture(read_input_json, from_json: Path) -> dict:
		data = read_input_json(from_json)
		if not isinstance(data, dict):
			raise ValueError('Capture must be a JSON object')
		for asset in data.get('saved_attachments') or []:
			if not Path(asset['path']).resolve().is_relative_to(from_json.parent.resolve()):
				raise ValueError('Attachment must belong to the capture directory')
		return data
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_browser_anchor(self) -> dict:
		from agent_tools.text_browser import browser_anchor_status
		return browser_anchor_status(session_id=self.__args.session_id, init_sentinel_tab=self.__args.init_sentinel_tab)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_build_native(self) -> dict:
		from agent_tools.configuration import build_native
		return build_native(self.__args.root, check=self.__args.check)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_cleanup(self) -> dict:
		from agent_tools.cleanup import cleanup_projects
		return cleanup_projects(apply=self.__args.apply, daily_root=self.__args.daily_root)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_cleanup_report(self) -> dict:
		from agent_tools.cleanup_audit import run_cleanup_report_cli
		return run_cleanup_report_cli(self.__args)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_install_global(self) -> dict:
		from agent_tools.native_profiles import install_native_profiles
		return install_native_profiles(self.__args.target_profile, check=self.__args.check)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_instances(self) -> dict:
		a = self.__args
		kw = {'platform': a.platform, 'instance': getattr(a, 'instance', None), 'conversation': getattr(a, 'conversation', None), 'include_disabled': not getattr(a, 'only_enabled', False), 'check_exists': not getattr(a, 'no_exists_check', False)}
		return InstancesReporter(**kw).report() if None is self.__instances_fn else self.__instances_fn(**kw)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_intake_drain(self) -> dict:
		from agent_tools.path_registry import store_path
		from Df.Harness.Project.Intake.CaptureCommitter import CaptureCommitter
		incoming = store_path('incoming_dir') if None is self.__incoming_fn else self.__incoming_fn()
		return CaptureCommitter.drain_incoming(self.__args.capture, incoming_root=incoming, daily_root=self.__args.daily_root, apply=self.__args.apply) if None is self.__drain_incoming_fn else self.__drain_incoming_fn(self.__args.capture, incoming_root=incoming, daily_root=self.__args.daily_root, apply=self.__args.apply)
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_paths(self) -> dict:
		from agent_tools.path_registry import paths_report
		a = self.__args
		return paths_report(getattr(a, 'project', None), expand=getattr(a, 'expand', None), check=bool(getattr(a, 'check', False)))
	# @used-by :meth:`CliRunner.__dispatch_builtin()`
	def __run_policy_instructions(self) -> dict:
		from agent_tools.configuration import global_codex_instructions
		return global_codex_instructions()
	# @used-by :meth:`CliRunner.__build_parser()`
	@staticmethod
	def __subcommand_specs(daily_root: Path, all_profiles: tuple[str, ...], platforms_map: dict) -> dict:
		return {
			'inspect': ('Capture the selected tab once, including attachments', (('url', {}), ('--output', {'required': True, 'type': Path}), ('--tab-id', {}), ('--session-id', {'help': 'Authorized runtime text.browser.sessions entry (default: primary session)'}), ('--cdp-port', {'type': int}))),
			'browser-anchor': ('Verify primary Chrome profile M-2A/M-2B isolation or initialize M-2B sentinel on an explicit Default tab', (('--session-id', {}), ('--init-sentinel-tab', {'help': 'Explicit Default profile tab_id on which to set the isolated https://harness-profile.invalid sentinel cookie'}))),
			'init': ('Initialize from an existing capture without browser requests', (('url', {}), ('--from-json', {'required': True, 'type': Path}), ('--domain', {'help': 'Verified target domain hostname without scheme or www.'}), ('--topic', {'help': 'Provisional human-readable topic title when no domain is yet verified'}), ('--date', {}), ('--site-hypothesis', {'type': Path, 'help': 'Four-part identity hypothesis with evidence and expert probability'}), ('--daily-root', {'type': Path, 'default': daily_root}), ('--no-register', {'action': 'store_true'}), ('--launcher-root', {'type': Path, 'help': 'Optional launcher workspace root whose open /upwork-init turn should be handed off to the created daily project (default: current working directory)'}), ('--conversation', {'help': 'Optional native conversation UUID to narrow launcher turn handoff'}))),
			'intake-drain': ('Verify and commit managed staging evidence; dry-run unless --apply', (('capture', {'nargs': '?', 'type': Path, 'help': 'One immediate capture directory; default: all managed incoming'}), ('--daily-root', {'type': Path, 'default': daily_root}), ('--apply', {'action': 'store_true', 'help': 'Drain only after durable evidence and receipt verification'}))),
			'cleanup': ('Remove empty native Upwork projects older than 72 hours; keep the entire daily archive', (('--apply', {'action': 'store_true', 'help': 'Apply cleanup; default is a read-only preview'}), ('--daily-root', {'type': Path, 'default': daily_root}))),
			'cleanup-report': ('Save the cleanup report with a Harness JSON metadata header and optional sidecar manifest link', (('--answer', {'default': '-', 'help': 'Legacy answer body path or - for stdin'}), ('--answer-file', {'type': Path, 'help': 'UTF-8 scratch file containing the cleanup report body (preferred per FILE-5)'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete verified scratch input file after read-back confirmation'}), ('--manifest', {'type': Path, 'help': 'Optional sidecar JSON manifest path produced by cleanup --apply'}), ('--project', {'type': Path, 'help': 'Optional project root for metadata and scratch path validation'}))),
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
	# @used-by :func:`agent_tools.upwork_project.main()`
	@classmethod
	def main(cls, argv=None, *, settings_fn=None, daily_root: Path | None=None, run_fn=None, description=None) -> int:
		cfg = (settings if None is settings_fn else settings_fn)()
		args = cls.__build_parser(cfg, daily_root, description).parse_args(argv)
		eff_platform = instance_entry(args.instance, include_disabled=True)['platform'] if None is args.platform and getattr(args, 'instance', None) and 'instances' != args.command else args.platform
		with using(eff_platform, args.codex_profile, getattr(args, 'instance', None)):
			r = cls(args).run() if None is run_fn else run_fn(args)
		return r
	# @used-by :func:`agent_tools.upwork_project.run()`
	def run(self) -> int:
		from agent_tools.cli_common import dump_json, operation_error_payload, result_exit_code
		from agent_tools.operations import COMMANDS, analysis_root, execute
		a = self.__args
		try:
			r = self.__execute(dump_json, result_exit_code, COMMANDS, analysis_root, execute)
		except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as exc:
			if a.command in COMMANDS or 'json' == getattr(a, 'format', None):
				dump_json(operation_error_payload(exc))
			else:
				print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
			r = 2 if isinstance(exc, LabelError) else 1
		return r
