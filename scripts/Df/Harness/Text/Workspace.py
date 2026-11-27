# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import re
import uuid
from Df.Harness.Text.ResponseChecker import ResponseChecker
from Df.Harness.Text.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Text.SourceCheckValidator import SourceCheckValidator
from Df.Harness.Text.WorkspaceCheckRunner import WorkspaceCheckRunner
from Df.Harness.Text.WorkspaceScopeChecker import WorkspaceScopeChecker
from Df.Harness.lib.research import dfh_inside, dfh_json_data
from Df.Harness.lib.text_claims import dfh_text_digest
from Df.Harness.lib.text_review import dfh_text_review_seam
from Df.Harness.lib.text_sections import TEXT_KINDS
from Df.Harness.lib.text_workflow import APPLIED_CHECK_KEYS, dfh_has_linked_ancestor, dfh_hash_or_none, dfh_immutable_text, dfh_read_json_sig, dfh_target_bytes
from agent_tools.storage import create_bytes, locked, read_addressed_json, replace_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Workspace:
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_find_registered_text()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_gate_paths()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_gate_requests()`
	# @used-by :func:`agent_tools.text_workflow._applied_integrity()`
	# @used-by :func:`agent_tools.text_workflow._claim_snapshot()`
	# @used-by :func:`agent_tools.text_workflow._document()`
	# @used-by :func:`agent_tools.text_workflow._index()`
	# @used-by :func:`agent_tools.text_workflow._reconciled_integrity()`
	# @used-by :func:`agent_tools.text_workflow._save_index()`
	# @used-by :func:`agent_tools.text_workflow._verify_applied_successor()`
	# @used-by :func:`agent_tools.text_workflow.apply()`
	# @used-by :func:`agent_tools.text_workflow.begin()`
	# @used-by :func:`agent_tools.text_workflow.check()`
	# @used-by :func:`agent_tools.text_workflow.gate()`
	# @used-by :func:`agent_tools.text_workflow.integrity_snapshot()`
	# @used-by :func:`agent_tools.text_workflow.operation()`
	# @used-by :func:`agent_tools.text_workflow.operation_meta()`
	# @used-by :func:`agent_tools.text_workflow.read_check()`
	# @used-by :func:`agent_tools.text_workflow.refresh_check()`
	# @used-by :func:`agent_tools.text_workflow.verify_integrity()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
	# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def __init__(self, root, *, strict: bool=False) -> None:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		raw_p = Path(root)
		canon = canonicalize_root_dir(raw_p)
		resolved = canon.resolve(strict=strict) if canon != raw_p.resolve(strict=False) else raw_p.resolve(strict=strict)
		self.pp = project_paths(resolved, exact_root=True)
		self.root = self.pp.root
		self.folder = self.pp.data_dir / 'texts'
	# @used-by :meth:`Workspace.gate()`
	def __check_gate_response(self, response: str, selected: set, state: dict, issues: list[str]) -> None:
		against = [dfh_inside(self.root, p) for p in selected if p in state['targets'] and dfh_inside(self.root, p).is_file()]
		findings = ResponseChecker(self.pp.data_dir / 'answer-candidate.md', text=response, against=against).check()
		issues.extend((f.format() for f in findings if 'error' == f.severity or 'RESP-CLAIM' == f.rule))
	# @used-by :meth:`Workspace.__validate_target_and_protected()`
	def __collect_protected(self, spec: dict, target: Path, current: bytes | None) -> dict:
		protected: dict = {}
		for name in spec.get('protected', []):
			file = dfh_inside(self.root, name)
			if file == target:
				raise ValueError('A protected document cannot be the writable target')
			protected[file.relative_to(self.root).as_posix()] = dfh_hash_or_none(dfh_target_bytes(file))
		prev_draft = target.with_name('draft.prev.md')
		if None is not current and 'draft.md' == target.name and ('edit' == spec['mode']) and (prev_draft.relative_to(self.root).as_posix() in protected) and (dfh_target_bytes(prev_draft) != current):
			raise ValueError('Draft snapshot would overwrite protected draft.prev.md; all protected bytes preserved')
		return protected
	# @used-by :meth:`Workspace.begin()`
	def __ensure_workspace_identity(self) -> None:
		if not self.pp.project_json.exists() and (not self.pp.text_project_json.exists()):
			from agent_tools.platforms.request_binding import text_project_id
			dfh_immutable_text(self.pp.text_project_json, dfh_json_data({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(self.root), 'id': text_project_id(self.root)}))
	# @used-by :meth:`Workspace.__gate_target()`
	def __gate_applied_receipt(self, name: str, target: Path, saved: dict, *, publication: bool) -> list[str]:
		r = [item['message'] for item in SourceCheckValidator(self.root, target.read_bytes().decode('utf-8'), saved.get('source_checks', [])).validate()['issues']]
		for path, expected in saved['inputs'].items():
			if not dfh_inside(self.root, path).is_file() or dfh_text_digest(dfh_inside(self.root, path).read_bytes()) != expected:
				r.append('Text evidence/registry changed; recheck dependent text: ' + name)
		if publication and 'semantic' != saved['coverage']:
			r.append('Mechanical edit does not assert semantic publication readiness: ' + name)
		if saved.get('approval'):
			auth_fn = dfh_text_review_seam('authorize', lambda rt, ck, **kw: ReviewAuthorizer(rt, ck, **kw).authorize())
			try:
				auth_fn(self.root, saved['check'], applied=True)
			except (OSError, ValueError) as exc:
				r.append(name + ': ' + str(exc))
		return r
	# @used-by :meth:`Workspace.gate()`
	def __gate_target(self, name: str, entry: dict, *, publication: bool=False) -> list[str]:
		r: list[str] = []
		target = self.document(name)
		if dfh_hash_or_none(dfh_target_bytes(target)) != entry['sha256']:
			r.append('Text target changed without a current apply receipt: ' + name)
		elif not entry.get('receipt'):
			if publication:
				r.append('Text target has only a baseline, not publication approval: ' + name)
		else:
			saved = None
			try:
				_, saved = read_addressed_json(dfh_inside(self.root, entry['receipt']), suffix='-applied.json', error_msg='Applied receipt changed: ' + name)
			except (OSError, ValueError):
				r.append('Applied receipt changed: ' + name)
			if None is not saved:
				if saved.get('candidate_sha256') != entry['sha256']:
					r.append('Applied receipt changed: ' + name)
				else:
					r.extend(self.__gate_applied_receipt(name, target, saved, publication=publication))
		return r
	# @used-by :meth:`Workspace.apply()`
	def __persist_applied(self, op: dict, checked: dict, reference: str, approval, previous: dict, state: dict, payload_sha: str) -> dict:
		receipt = {**{k: checked[k] for k in APPLIED_CHECK_KEYS}, 'schema_version': 1, 'check': reference, 'approval': approval, 'status': 'applied', 'previous': previous}
		raw = dfh_json_data(receipt)
		rel_receipt = dfh_immutable_text(self.folder / 'operations' / op['id'] / (dfh_text_digest(raw) + '-applied.json'), raw).relative_to(self.root).as_posix()
		state['targets'][op['target']] = {'sha256': payload_sha, 'kind': op['kind'], 'receipt': rel_receipt}
		self.save_index(state)
		return {**receipt, 'receipt': rel_receipt, 'sha256': payload_sha}
	# @used-by :meth:`Workspace.begin()`
	def __reconcile_if_changed(self, spec: dict, record: dict, current: bytes | None, previous: dict | None, op_folder: Path, state: dict) -> None:
		if previous and previous.get('sha256') != record['base_sha256']:
			if 'reconcile_sha256' not in spec or spec['reconcile_sha256'] != record['base_sha256']:
				raise ValueError('Registered output changed outside the workflow; read and explicitly reconcile its current SHA256 first')
			baseline = dfh_immutable_text(op_folder / 'base.bin', current or b'')
			reconciliation = {'schema_version': 1, 'kind': 'baseline_reconciliation', 'root': str(self.root), 'target': record['target'], 'document_kind': spec['kind'], 'operation': record['id'], 'previous': deepcopy(previous), 'baseline': {'file': baseline.relative_to(self.root).as_posix(), 'sha256': record['base_sha256']}}
			raw = dfh_json_data(reconciliation)
			file = dfh_immutable_text(op_folder / (dfh_text_digest(raw) + '-reconciled.json'), raw)
			record['reconciliation'] = file.relative_to(self.root).as_posix()
			state['targets'][record['target']] = {'sha256': record['base_sha256'], 'kind': spec['kind'], 'receipt': None, 'reconciliation': record['reconciliation']}
	# @used-by :meth:`Workspace.begin()`
	@staticmethod
	def __snapshot_draft_if_needed(target: Path, current: bytes | None, mode: str, ident: str) -> None:
		if None is not current and 'draft.md' == target.name and ('edit' == mode):
			from agent_tools.snapshot import snapshot_draft
			snapshot_draft(target, 'text-' + ident)
	# @used-by :meth:`Workspace.begin()`
	def __validate_begin_spec(self, spec: dict) -> tuple[Path, bytes | None, dict]:
		if not isinstance(spec, dict) or spec.get('kind') not in TEXT_KINDS:
			raise ValueError('Explicit text kind article/proposal/letter is required')
		if spec.get('mode') not in ('edit', 'propose', 'inspect') or spec.get('changes') not in ('prose', 'links', 'renumber'):
			raise ValueError('Declare result mode and allowed change kind')
		if not isinstance(spec.get('goal'), str) or not spec['goal'].strip():
			raise ValueError('The current task goal is required')
		if not isinstance(spec.get('requests'), list) or not spec['requests'] or any((not isinstance(x, str) or not x.strip() for x in spec['requests'])):
			raise ValueError('Preserve the exact current requests in the operation')
		allowed = spec.get('allow_sections', [])
		if not isinstance(allowed, list) or any((not isinstance(x, str) or not x for x in allowed)):
			raise ValueError('allow_sections is a list of exact section IDs or explicit inclusive ranges')
		return self.__validate_target_and_protected(spec)
	# @used-by :meth:`Workspace.__validate_begin_spec()`
	def __validate_target_and_protected(self, spec: dict) -> tuple[Path, bytes | None, dict]:
		requested = self.root / spec.get('target', '')
		if dfh_has_linked_ancestor(self.root, requested):
			raise ValueError('Text target indirections need an explicit resolved ordinary file')
		target = dfh_inside(self.root, spec.get('target', ''))
		if target == self.root or target.is_relative_to(self.root / '\ua616') or target.is_relative_to(self.pp.agent_dir):
			raise ValueError('Choose an explicit user document outside agent service storage')
		if dfh_has_linked_ancestor(self.root, target):
			raise ValueError('Text target indirections need an explicit resolved ordinary file')
		current = dfh_target_bytes(target)
		if None is current and 'inspect' == spec['mode']:
			raise ValueError('Inspect requires an existing document')
		return (target, current, self.__collect_protected(spec, target, current))
	# @used-by :meth:`Workspace.apply()`
	@staticmethod
	def __write_applied_target(target: Path, payload: bytes, base_exists: bool) -> None:
		if base_exists:
			replace_bytes(target, payload)
		else:
			target.parent.mkdir(parents=True, exist_ok=True)
			create_bytes(target, payload)
		if target.read_bytes() != payload:
			raise OSError('Applied text read-back differs')
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_repo_tag_retro()`
	# @used-by :func:`agent_tools.text_workflow.apply()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def apply(self, reference: str) -> dict:
		with locked(self.folder / 'writer.lock'):
			checked, candidate, op = self.refresh_check_with_operation(reference)
			if 'edit' != op['mode']:
				raise ValueError('This operation only proposes/inspects; it cannot write the user target')
			auth_fn = dfh_text_review_seam('authorize', lambda rt, ck, **kw: ReviewAuthorizer(rt, ck, **kw).authorize())
			approval = auth_fn(self.root, reference) if 'semantic' == checked['coverage'] else None
			target = self.document(op['target'])
			if dfh_hash_or_none(dfh_target_bytes(target)) != op['base_sha256']:
				raise ValueError('Concurrent user edit preserved; reconcile a new operation')
			state = self.index()
			previous = deepcopy(state['targets'].get(op['target']))
			if None is previous or previous.get('sha256') != op['base_sha256']:
				raise ValueError('The applied revision requires its exact registered predecessor')
			payload = candidate.encode('utf-8')
			self.__write_applied_target(target, payload, op['base_exists'])
			r = self.__persist_applied(op, checked, reference, approval, previous, state, dfh_text_digest(payload))
		return r
	# @used-by :func:`agent_tools.text_workflow.begin()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	def begin(self, spec: dict) -> dict:
		target, current, protected = self.__validate_begin_spec(spec)
		ident = uuid.uuid4().hex
		r = {**deepcopy(spec), 'schema_version': 1, 'id': ident, 'root': str(self.root), 'target': target.relative_to(self.root).as_posix(), 'base_sha256': dfh_hash_or_none(current), 'base_exists': None is not current, 'protected_versions': protected, 'reconciliation': None}
		with locked(self.folder / 'writer.lock'):
			state = self.index()
			op_folder = self.folder / 'operations' / ident
			self.__reconcile_if_changed(spec, r, current, state['targets'].get(r['target']), op_folder, state)
			dfh_immutable_text(op_folder / 'base.bin', current or b'')
			dfh_immutable_text(op_folder / 'operation.json', dfh_json_data(r))
			self.__snapshot_draft_if_needed(target, current, spec['mode'], ident)
			if dfh_target_bytes(target) != current:
				raise ValueError('Target changed during capture; snapshot retained, external edit preserved')
			state['operations'].append(ident)
			state['protected'] = sorted(set(state.get('protected', [])) | set(protected))
			state['targets'].setdefault(r['target'], {'sha256': r['base_sha256'], 'kind': spec['kind'], 'receipt': None})
			self.save_index(state)
			self.__ensure_workspace_identity()
		return r
	# @used-by :func:`agent_tools.text_workflow.check()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`Workspace.refresh_check_with_operation()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def check(self, ident: str, candidate: str, manifest=None, *, run_replay: bool=False, replay_record=None, warning_dispositions=None, applied: bool=False, _return_op: bool=False):
		return WorkspaceCheckRunner(self, ident, candidate, manifest, run_replay=run_replay, replay_record=replay_record, warning_dispositions=warning_dispositions, applied=applied, return_op=_return_op).run()
	# @used-by :func:`agent_tools.text_workflow._document()`
	# @used-by :meth:`Workspace.__gate_target()`
	# @used-by :meth:`Workspace.apply()`
	def document(self, name: str) -> Path:
		requested = self.root / name
		if dfh_has_linked_ancestor(self.root, requested, require_exists=False):
			raise ValueError('Text target indirection changed; protected bytes preserved')
		return dfh_inside(self.root, name)
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_gate_paths()`
	# @used-by :func:`agent_tools.text_workflow.gate()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`Workspace.gate_requests_for_root()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def gate(self, *, targets=None, response=None, publication: bool=False, capture: bool=False) -> dict:
		state, issues = (self.index(), [])
		selected = set(targets) if None is not targets else set(state['targets'])
		for name, entry in state['targets'].items():
			if name in selected:
				issues.extend(self.__gate_target(name, entry, publication=publication))
		if None is not response and state['targets']:
			self.__check_gate_response(response, selected, state, issues)
		if issues:
			raise ValueError('\n'.join(issues))
		r: dict = {'valid': True, 'targets_checked': sorted(selected & set(state['targets'])), 'publication': publication}
		if capture:
			from Df.Harness.Text.IntegrityVerifier import IntegrityVerifier
			r['integrity'] = IntegrityVerifier(self, index_state=state).snapshot({name: state['targets'][name] for name in r['targets_checked']})
		return r
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_gate_requests()`
	def gate_requests_for_root(self, requests, response, *, capture: bool=False):
		state, selected = (self.index(), set())
		req_set = set(requests)
		for ident in state['operations']:
			op = self.operation_meta(ident)
			if set(op['requests']) & req_set:
				selected.add(op['target'])
		return self.gate(targets=selected, response=response, capture=capture) if selected else None
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_extract_managed_block()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_replace_managed_block()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._strip_owned_role_block()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_profile_agents()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_find_registered_text()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_gate_paths()`
	# @used-by :func:`agent_tools.git_ignore.merge_managed_git_ignore()`
	# @used-by :func:`agent_tools.text_workflow._index()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__extract_body()`
	# @used-by :meth:`Df.Harness.Git.CommitArgsParser.CommitArgsParser.__parse_flag_bundle()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__merge_block()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.__finalize_ag_info()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.extract_codex_info()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__replace_existing()`
	# @used-by :meth:`Df.Harness.Text.CodeBlockLinter.CodeBlockLinter.__check_output()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceScopeChecker.WorkspaceScopeChecker.__permitted_sections()`
	# @used-by :meth:`Df.Harness.Upwork.LoomVideoExtractor.LoomVideoExtractor.__parse_vtt_block()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Workspace.apply()`
	# @used-by :meth:`Workspace.begin()`
	# @used-by :meth:`Workspace.gate()`
	# @used-by :meth:`Workspace.gate_requests_for_root()`
	# @used-by :meth:`test_agent_tools.ContextTests.test_sources_and_fences_preserved_in_configured_order()`
	# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_arch_audit_gate_priority_manifest_and_lazy_export()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
	# @used-by :meth:`test_gate_registry.GateRegistryTests.test_builtin_pre_tool_gates_discovered_in_strict_priority_order()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_and_red_flags_have_stable_order_and_preserve_manual_edits()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_both_risks_precede_technical_analysis_and_are_duplicated_in_card()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_mixed_anchor_style_follows_keys_when_renumbering()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
	def index(self) -> dict:
		file = self.folder / 'index.json'
		r = dfh_read_json_sig(file) if file.exists() else {'schema_version': 1, 'targets': {}, 'operations': []}
		if 1 != r.get('schema_version') or not isinstance(r.get('targets'), dict):
			raise ValueError('Invalid client-text index; preserve it for recovery')
		return r
	# @used-by :func:`agent_tools.text_workflow.operation()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
	# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
	# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
	def operation(self, ident: str) -> tuple[dict, bytes]:
		result = self.operation_meta(ident)
		base = (self.folder / 'operations' / ident / 'base.bin').read_bytes()
		if (dfh_text_digest(base) if result['base_exists'] else None) != result['base_sha256']:
			raise ValueError('Captured baseline bytes changed')
		return (result, base)
	# @used-by :func:`agent_tools.text_workflow.operation_meta()`
	# @used-by :meth:`Workspace.gate_requests_for_root()`
	# @used-by :meth:`Workspace.operation()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def operation_meta(self, ident: str) -> dict:
		from agent_tools.path_registry import same_project_root
		if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
			raise ValueError('Use the exact operation ID returned by text-begin')
		r = dfh_read_json_sig(self.folder / 'operations' / ident / 'operation.json')
		if not same_project_root(r.get('root'), self.root) or r.get('id') != ident:
			raise ValueError('Text operation belongs to another workspace')
		return r
	# @used-by :func:`agent_tools.text_workflow.read_check()`
	# @used-by :meth:`Workspace.refresh_check_with_operation()`
	def read_check(self, reference: str) -> tuple[dict, str]:
		from agent_tools.path_registry import same_project_root
		_, data = read_addressed_json(dfh_inside(self.root, reference), suffix='-check.json', error_msg='Invalid/changed text check receipt')
		if not same_project_root(data.get('root'), self.root):
			raise ValueError('Invalid/changed text check receipt')
		candidate = dfh_inside(self.root, data['candidate']).read_bytes()
		if dfh_text_digest(candidate) != data['candidate_sha256']:
			raise ValueError('Candidate bytes changed after checking')
		return (data, candidate.decode('utf-8'))
	# @used-by :func:`agent_tools.text_workflow.refresh_check()`
	# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
	# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
	def refresh_check(self, reference: str, *, applied: bool=False) -> tuple[dict, str]:
		current, candidate, _ = self.refresh_check_with_operation(reference, applied=applied)
		return (current, candidate)
	# @used-by :meth:`Workspace.apply()`
	# @used-by :meth:`Workspace.refresh_check()`
	def refresh_check_with_operation(self, reference: str, *, applied: bool=False) -> tuple[dict, str, dict]:
		saved, candidate = self.read_check(reference)
		current, op = self.check(saved['operation'], candidate, saved['manifest'], replay_record=saved['replay_record'], warning_dispositions=saved['warning_dispositions'], applied=applied, _return_op=True)
		if not current['valid'] or current['inputs'] != saved['inputs'] or current['claim_versions'] != saved['claim_versions']:
			raise ValueError('Text check is stale or failed: ' + json.dumps(current['issues'], ensure_ascii=False))
		return (current, candidate, op)
	# @used-by :func:`agent_tools.text_workflow._save_index()`
	# @used-by :meth:`Workspace.__persist_applied()`
	# @used-by :meth:`Workspace.begin()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	def save_index(self, value: dict) -> None:
		replace_bytes(self.folder / 'index.json', dfh_json_data(value))
	# @used-by :func:`agent_tools.text_workflow.scope_issues()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	@staticmethod
	def scope_issues(op: dict, base, candidate: str) -> list[dict]:
		return WorkspaceScopeChecker(op, base, candidate).check()
