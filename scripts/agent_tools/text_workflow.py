# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
import difflib
import json
from pathlib import Path
import re
import uuid
from .research import inside, json_data
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
from .storage import create_bytes, data_dir_for, locked, read_addressed_json, replace_bytes, write_immutable_bytes
from .text_claims import digest, validate_map
# 2026-11-14
# "Generalize keyed section numbering (@key), section-reference validation, and profile dispatch across article.py, proposal.py, text_workflow.py, text_claims.py, and text_cli.py":
# https://github.com/dmitry-ai/harness/issues/70
from .text_sections import TEXT_KINDS as KINDS, lint_document as _lint, mechanical_projection as _mechanical_projection, scope_blocks as _scope_blocks
_APPLIED_CHECK_KEYS = ('operation', 'target', 'kind', 'base_sha256', 'candidate_sha256', 'coverage', 'inputs', 'claim_versions', 'candidate', 'manifest', 'source_checks')
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-14
# "Decompose text_workflow.py into ClientTextWorkspace and TextIntegrityVerifier classes":
# https://github.com/dmitry-ai/harness/issues/78
class ClientTextWorkspace:
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	# 2026-11-22
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	# @used-by :func:`_applied_integrity()`
	# @used-by :func:`_claim_snapshot()`
	# @used-by :func:`_document()`
	# @used-by :func:`_index()`
	# @used-by :func:`_reconciled_integrity()`
	# @used-by :func:`_save_index()`
	# @used-by :func:`_verify_applied_successor()`
	# @used-by :func:`apply()`
	# @used-by :func:`begin()`
	# @used-by :func:`check()`
	# @used-by :func:`gate()`
	# @used-by :func:`gate_paths()`
	# @used-by :func:`gate_requests()`
	# @used-by :func:`integrity_snapshot()`
	# @used-by :func:`operation()`
	# @used-by :func:`operation_meta()`
	# @used-by :func:`read_check()`
	# @used-by :func:`refresh_check()`
	# @used-by :func:`verify_integrity()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def __init__(self, root, *, strict=False):
		from .path_registry import canonicalize_root_dir, project_paths
		raw_p = Path(root)
		canon = canonicalize_root_dir(raw_p)
		resolved = canon.resolve(strict=strict) if canon != raw_p.resolve(strict=False) else raw_p.resolve(strict=strict)
		self.pp = project_paths(resolved, exact_root=True)
		self.root = self.pp.root
		self.folder = self.pp.data_dir / 'texts'
	# @used-by :meth:`ClientTextWorkspace.check()`
	def _check_replay(self, ident, op, candidate, candidate_sha, changed, manifest, *, run_replay=False, replay_record=None):
		from .text_core import replay
		issues = []
		replay_data = []
		if changed:
			if not run_replay and (not replay_record):
				issues.append({'code': 'text.replay_missing', 'message': 'New/changed commands require an explicit replay of exactly these blocks', 'lines': changed})
			elif not run_replay:
				_, stored = read_addressed_json(inside(self.root, replay_record), suffix='-replay.json', error_msg='Replay receipt does not cover the exact changed command blocks')
				if stored.get('operation') != ident or stored.get('candidate_sha256') != candidate_sha or (stored.get('lines') != changed):
					raise ValueError('Replay receipt does not cover the exact changed command blocks')
				replay_data = stored['results']
			else:
				replay_data = replay(candidate, only=changed, contracts=(manifest or {}).get('commands'), shell=op.get('shell'))
				payload = json_data({'schema_version': 1, 'operation': ident, 'candidate_sha256': candidate_sha, 'lines': changed, 'results': replay_data})
				replay_path = _immutable(self.folder / 'operations' / ident / (digest(payload) + '-replay.json'), payload)
				replay_record = replay_path.relative_to(self.root).as_posix()
			if replay_data and (len(replay_data) != len(changed) or any(('match' != item.get('status') for item in replay_data))):
				issues.append({'code': 'text.replay', 'message': 'Changed command coverage or execution failed', 'results': replay_data})
		return (replay_record, issues)
	# @used-by :meth:`ClientTextWorkspace.gate()`
	def _gate_target(self, name, entry, *, publication=False):
		r = []
		target = self.document(name)
		if _hash_or_none(_target_bytes(target)) != entry['sha256']:
			r.append('Text target changed without a current apply receipt: ' + name)
		elif not entry.get('receipt'):
			if publication:
				r.append('Text target has only a baseline, not publication approval: ' + name)
		else:
			saved = None
			try:
				_, saved = read_addressed_json(inside(self.root, entry['receipt']), suffix='-applied.json', error_msg='Applied receipt changed: ' + name)
			except (OSError, ValueError):
				r.append('Applied receipt changed: ' + name)
			if None is not saved:
				if saved.get('candidate_sha256') != entry['sha256']:
					r.append('Applied receipt changed: ' + name)
				else:
					# 2026-10-23
					# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
					# https://github.com/dmitry-ai/harness/issues/16
					from .text_sources import validate_source_checks
					sources = validate_source_checks(self.root, target.read_bytes().decode('utf-8'), saved.get('source_checks', []))
					r.extend((item['message'] for item in sources['issues']))
					for path, expected in saved['inputs'].items():
						if not inside(self.root, path).is_file() or digest(inside(self.root, path).read_bytes()) != expected:
							r.append('Text evidence/registry changed; recheck dependent text: ' + name)
					if publication and 'semantic' != saved['coverage']:
						r.append('Mechanical edit does not assert semantic publication readiness: ' + name)
					if saved.get('approval'):
						from .text_review import authorize
						try:
							authorize(self.root, saved['check'], applied=True)
						except (OSError, ValueError) as exc:
							r.append(name + ': ' + str(exc))
		return r
	# @used-by :meth:`ClientTextWorkspace.begin()`
	def _validate_begin_spec(self, spec):
		if not isinstance(spec, dict) or spec.get('kind') not in KINDS:
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
		requested = self.root / spec.get('target', '')
		if _has_linked_ancestor(self.root, requested):
			raise ValueError('Text target indirections need an explicit resolved ordinary file')
		target = inside(self.root, spec.get('target', ''))
		if target == self.root or target.is_relative_to(self.root / '\ua616') or target.is_relative_to(self.pp.agent_dir):
			raise ValueError('Choose an explicit user document outside agent service storage')
		if _has_linked_ancestor(self.root, target):
			raise ValueError('Text target indirections need an explicit resolved ordinary file')
		current = _target_bytes(target)
		if None is current and 'inspect' == spec['mode']:
			raise ValueError('Inspect requires an existing document')
		protected = {}
		for name in spec.get('protected', []):
			file = inside(self.root, name)
			if file == target:
				raise ValueError('A protected document cannot be the writable target')
			protected[file.relative_to(self.root).as_posix()] = _hash_or_none(_target_bytes(file))
		prev_draft = target.with_name('draft.prev.md')
		if None is not current and 'draft.md' == target.name and ('edit' == spec['mode']) and (prev_draft.relative_to(self.root).as_posix() in protected) and (_target_bytes(prev_draft) != current):
			raise ValueError('Draft snapshot would overwrite protected draft.prev.md; all protected bytes preserved')
		return (target, current, protected)
	# @used-by :func:`agent_tools.cli_registry._exec_repo_tag_retro()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :func:`apply()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def apply(self, reference):
		with locked(self.folder / 'writer.lock'):
			checked, candidate, op = self.refresh_check_with_operation(reference)
			if 'edit' != op['mode']:
				raise ValueError('This operation only proposes/inspects; it cannot write the user target')
			approval = None
			if 'semantic' == checked['coverage']:
				from .text_review import authorize
				approval = authorize(self.root, reference)
			target = self.document(op['target'])
			if _hash_or_none(_target_bytes(target)) != op['base_sha256']:
				raise ValueError('Concurrent user edit preserved; reconcile a new operation')
			state = self.index()
			previous = deepcopy(state['targets'].get(op['target']))
			if None is previous or previous.get('sha256') != op['base_sha256']:
				raise ValueError('The applied revision requires its exact registered predecessor')
			payload = candidate.encode('utf-8')
			payload_sha = digest(payload)
			if op['base_exists']:
				replace_bytes(target, payload)
			else:
				target.parent.mkdir(parents=True, exist_ok=True)
				create_bytes(target, payload)
			if target.read_bytes() != payload:
				raise OSError('Applied text read-back differs')
			receipt = {k: checked[k] for k in _APPLIED_CHECK_KEYS}
			receipt.update(schema_version=1, check=reference, approval=approval, status='applied', previous=previous)
			raw = json_data(receipt)
			path = _immutable(self.folder / 'operations' / op['id'] / (digest(raw) + '-applied.json'), raw)
			rel_receipt = path.relative_to(self.root).as_posix()
			state['targets'][op['target']] = {'sha256': payload_sha, 'kind': op['kind'], 'receipt': rel_receipt}
			self.save_index(state)
		return {**receipt, 'receipt': rel_receipt, 'sha256': payload_sha}
	# @used-by :func:`begin()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	def begin(self, spec):
		target, current, protected = self._validate_begin_spec(spec)
		ident = uuid.uuid4().hex
		r = {**deepcopy(spec), 'schema_version': 1, 'id': ident, 'root': str(self.root), 'target': target.relative_to(self.root).as_posix(), 'base_sha256': _hash_or_none(current), 'base_exists': None is not current, 'protected_versions': protected, 'reconciliation': None}
		with locked(self.folder / 'writer.lock'):
			state = self.index()
			previous = state['targets'].get(r['target'])
			op_folder = self.folder / 'operations' / ident
			if previous and previous.get('sha256') != r['base_sha256']:
				# 2026-11-03
				# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
				# https://github.com/dmitry-ai/harness/issues/41
				if 'reconcile_sha256' not in spec or spec['reconcile_sha256'] != r['base_sha256']:
					raise ValueError('Registered output changed outside the workflow; read and explicitly reconcile its current SHA256 first')
				baseline = _immutable(op_folder / 'base.bin', current or b'')
				reconciliation = {'schema_version': 1, 'kind': 'baseline_reconciliation', 'root': str(self.root), 'target': r['target'], 'document_kind': spec['kind'], 'operation': ident, 'previous': deepcopy(previous), 'baseline': {'file': baseline.relative_to(self.root).as_posix(), 'sha256': r['base_sha256']}}
				raw = json_data(reconciliation)
				file = _immutable(op_folder / (digest(raw) + '-reconciled.json'), raw)
				r['reconciliation'] = file.relative_to(self.root).as_posix()
				state['targets'][r['target']] = {'sha256': r['base_sha256'], 'kind': spec['kind'], 'receipt': None, 'reconciliation': r['reconciliation']}
			_immutable(op_folder / 'base.bin', current or b'')
			_immutable(op_folder / 'operation.json', json_data(r))
			if None is not current and 'draft.md' == target.name and ('edit' == spec['mode']):
				from .snapshot import snapshot_draft
				snapshot_draft(target, 'text-' + ident)
			if _target_bytes(target) != current:
				raise ValueError('Target changed during capture; snapshot retained, external edit preserved')
			state['operations'].append(ident)
			state['protected'] = sorted(set(state.get('protected', [])) | set(protected))
			state['targets'].setdefault(r['target'], {'sha256': r['base_sha256'], 'kind': spec['kind'], 'receipt': None})
			self.save_index(state)
			identity = self.pp.text_project_json
			if not self.pp.project_json.exists() and (not identity.exists()):
				from .platforms.request_binding import text_project_id
				_immutable(identity, json_data({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(self.root), 'id': text_project_id(self.root)}))
		return r
	# @used-by :func:`check()`
	# @used-by :meth:`ClientTextWorkspace.refresh_check_with_operation()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def check(self, ident, candidate, manifest=None, *, run_replay=False, replay_record=None, warning_dispositions=None, applied=False, _return_op=False):
		from .text_core import changed_command_lines
		op, base = self.operation(ident)
		if not isinstance(candidate, str):
			raise ValueError('Candidate must be exact UTF-8 text')
		base_text = base.decode('utf-8')
		candidate_bytes = candidate.encode('utf-8')
		candidate_sha = digest(candidate_bytes)
		target = self.document(op['target'])
		scoped = self.scope_issues(op, base_text, candidate)
		issues = list(scoped)
		expected_target = candidate_sha if applied else op['base_sha256']
		if _hash_or_none(_target_bytes(target)) != expected_target:
			issues.append({'code': 'text.conflict', 'message': 'User target changed after capture; reconcile without overwriting it'})
		for name, sha in op['protected_versions'].items():
			if _hash_or_none(_target_bytes(inside(self.root, name))) != sha:
				issues.append({'code': 'text.protected', 'message': 'Protected file changed: ' + name})
		findings = _lint(candidate, op['kind'], target, op.get('profile'))
		issues += [{'code': f.rule, 'message': f.message, 'line': f.line} for f in findings if 'error' == f.severity]
		warning_dispositions = warning_dispositions or {}
		for finding in findings:
			basis = warning_dispositions.get(f'{finding.rule}:{finding.line}')
			if 'warning' == finding.severity and (not isinstance(basis, str) or not basis.strip()):
				issues.append({'code': 'text.warning', 'message': 'Resolve or substantively explain warning: ' + finding.format()})
		mechanical = op['changes'] in ('links', 'renumber') and (not scoped)
		mapped = {'valid': True, 'issues': [], 'inputs': {}, 'claims': [], 'claim_versions': {}}
		if not mechanical and 'inspect' != op['mode']:
			mapped = validate_map(self.root, candidate, op['kind'], manifest)
			issues.extend(mapped['issues'])
		# 2026-10-23
		# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
		# https://github.com/dmitry-ai/harness/issues/16
		from .text_sources import validate_source_checks
		sources = validate_source_checks(self.root, candidate, (manifest or {}).get('source_checks', []))
		issues.extend(sources['issues'])
		changed = changed_command_lines(candidate, base_text)
		replay_record, replay_issues = self._check_replay(ident, op, candidate, candidate_sha, changed, manifest, run_replay=run_replay, replay_record=replay_record)
		issues.extend(replay_issues)
		result = {'schema_version': 1, 'operation': ident, 'root': str(self.root), 'target': op['target'], 'kind': op['kind'], 'base_sha256': op['base_sha256'], 'candidate_sha256': candidate_sha, 'valid': not issues, 'issues': issues, 'coverage': 'mechanical' if mechanical else 'semantic', 'inputs': {**mapped['inputs'], **sources['inputs']}, 'claims': mapped['claims'], 'claim_versions': mapped['claim_versions'], 'source_checks': sources['checks'], 'manifest': manifest, 'replay_record': replay_record, 'warning_dispositions': warning_dispositions, 'diff': ''.join(difflib.unified_diff(base_text.splitlines(True), candidate.splitlines(True), fromfile='before/' + op['target'], tofile='after/' + op['target']))}
		if result['claim_versions']:
			from .text_claims import registry_path, subset
			registry = registry_path(self.root, (manifest or {}).get('registry'))
			result['claim_snapshot'] = subset(_read(registry), result['claim_versions'])
		op_folder = self.folder / 'operations' / ident
		source = _immutable(op_folder / (candidate_sha + '.md'), candidate_bytes)
		result['candidate'] = source.relative_to(self.root).as_posix()
		payload = json_data(result)
		receipt = _immutable(op_folder / (digest(payload) + '-check.json'), payload)
		out = {**result, 'check': receipt.relative_to(self.root).as_posix()}
		return (out, op) if _return_op else out
	# @used-by :func:`_document()`
	# @used-by :meth:`ClientTextWorkspace._gate_target()`
	# @used-by :meth:`ClientTextWorkspace.apply()`
	# @used-by :meth:`ClientTextWorkspace.check()`
	def document(self, name):
		requested = self.root / name
		if _has_linked_ancestor(self.root, requested, require_exists=False):
			raise ValueError('Text target indirection changed; protected bytes preserved')
		return inside(self.root, name)
	# @used-by :func:`gate()`
	# @used-by :func:`gate_paths()`
	# @used-by :meth:`ClientTextWorkspace.gate_requests_for_root()`
	def gate(self, *, targets=None, response=None, publication=False, capture=False):
		state, issues = (self.index(), [])
		selected = set(targets) if None is not targets else set(state['targets'])
		for name, entry in state['targets'].items():
			if name in selected:
				issues.extend(self._gate_target(name, entry, publication=publication))
		if None is not response and state['targets']:
			from .text_core import check_response
			findings = check_response(self.pp.data_dir / 'answer-candidate.md', text=response, against=[inside(self.root, p) for p in selected if p in state['targets'] and inside(self.root, p).is_file()])
			issues.extend((f.format() for f in findings if 'error' == f.severity or 'RESP-CLAIM' == f.rule))
		if issues:
			raise ValueError('\n'.join(issues))
		r = {'valid': True, 'targets_checked': sorted(selected & set(state['targets'])), 'publication': publication}
		if capture:
			r['integrity'] = TextIntegrityVerifier(self, index_state=state).snapshot({name: state['targets'][name] for name in r['targets_checked']})
		return r
	# @used-by :func:`gate_requests()`
	def gate_requests_for_root(self, requests, response, *, capture=False):
		state, selected = (self.index(), set())
		req_set = set(requests)
		for ident in state['operations']:
			op = self.operation_meta(ident)
			if set(op['requests']) & req_set:
				selected.add(op['target'])
		return self.gate(targets=selected, response=response, capture=capture) if selected else None
	# @used-by :func:`_index()`
	# @used-by :func:`agent_tools.configuration.extract_managed_block()`
	# @used-by :func:`agent_tools.configuration.replace_managed_block()`
	# @used-by :func:`agent_tools.git_ignore._merge_managed_block()`
	# @used-by :func:`agent_tools.grounding_helpers.build_active_corpus_cached()`
	# @used-by :func:`agent_tools.meta.transcripts._extract_codex_transcript_info()`
	# @used-by :func:`agent_tools.meta.transcripts._finalize_ag_info()`
	# @used-by :func:`agent_tools.native_profiles._profile_agents()`
	# @used-by :func:`agent_tools.native_profiles._role_config()`
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.text_core.check_code()`
	# @used-by :func:`agent_tools.upwork_data.parse_webvtt_phrases()`
	# @used-by :func:`gate_paths()`
	# @used-by :meth:`ClientTextWorkspace.apply()`
	# @used-by :meth:`ClientTextWorkspace.begin()`
	# @used-by :meth:`ClientTextWorkspace.gate()`
	# @used-by :meth:`ClientTextWorkspace.gate_requests_for_root()`
	# @used-by :meth:`ClientTextWorkspace.scope_issues()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.unconditional_calls()`
	# @used-by :meth:`agent_tools.shell_audit.ShellCommandInspector._parse_commit_flag_bundle()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`test_agent_tools.ContextTests.test_sources_and_fences_preserved_in_configured_order()`
	# @used-by :meth:`test_gate_registry.GateRegistryTests.test_builtin_pre_tool_gates_discovered_in_strict_priority_order()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_and_red_flags_have_stable_order_and_preserve_manual_edits()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_both_risks_precede_technical_analysis_and_are_duplicated_in_card()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_mixed_anchor_style_follows_keys_when_renumbering()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
	def index(self):
		file = self.folder / 'index.json'
		r = _read(file) if file.exists() else {'schema_version': 1, 'targets': {}, 'operations': []}
		if 1 != r.get('schema_version') or not isinstance(r.get('targets'), dict):
			raise ValueError('Invalid client-text index; preserve it for recovery')
		return r
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :func:`operation()`
	# @used-by :meth:`ClientTextWorkspace.check()`
	def operation(self, ident):
		result = self.operation_meta(ident)
		base = (self.folder / 'operations' / ident / 'base.bin').read_bytes()
		if (digest(base) if result['base_exists'] else None) != result['base_sha256']:
			raise ValueError('Captured baseline bytes changed')
		return (result, base)
	# 2026-11-22
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	# @used-by :func:`operation_meta()`
	# @used-by :meth:`ClientTextWorkspace.gate_requests_for_root()`
	# @used-by :meth:`ClientTextWorkspace.operation()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def operation_meta(self, ident):
		from .path_registry import same_project_root
		if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
			raise ValueError('Use the exact operation ID returned by text-begin')
		r = _read(self.folder / 'operations' / ident / 'operation.json')
		if not same_project_root(r.get('root'), self.root) or r.get('id') != ident:
			raise ValueError('Text operation belongs to another workspace')
		return r
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	# 2026-11-22
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	# @used-by :func:`read_check()`
	# @used-by :meth:`ClientTextWorkspace.refresh_check_with_operation()`
	def read_check(self, reference):
		from .path_registry import same_project_root
		_, data = read_addressed_json(inside(self.root, reference), suffix='-check.json', error_msg='Invalid/changed text check receipt')
		if not same_project_root(data.get('root'), self.root):
			raise ValueError('Invalid/changed text check receipt')
		candidate = inside(self.root, data['candidate']).read_bytes()
		if digest(candidate) != data['candidate_sha256']:
			raise ValueError('Candidate bytes changed after checking')
		return (data, candidate.decode('utf-8'))
	# @used-by :func:`refresh_check()`
	def refresh_check(self, reference, *, applied=False):
		current, candidate, _ = self.refresh_check_with_operation(reference, applied=applied)
		return (current, candidate)
	# @used-by :meth:`ClientTextWorkspace.apply()`
	# @used-by :meth:`ClientTextWorkspace.refresh_check()`
	def refresh_check_with_operation(self, reference, *, applied=False):
		saved, candidate = self.read_check(reference)
		current, op = self.check(saved['operation'], candidate, saved['manifest'], replay_record=saved['replay_record'], warning_dispositions=saved['warning_dispositions'], applied=applied, _return_op=True)
		if not current['valid'] or current['inputs'] != saved['inputs'] or current['claim_versions'] != saved['claim_versions']:
			raise ValueError('Text check is stale or failed: ' + json.dumps(current['issues'], ensure_ascii=False))
		return (current, candidate, op)
	# @used-by :func:`_save_index()`
	# @used-by :meth:`ClientTextWorkspace.apply()`
	# @used-by :meth:`ClientTextWorkspace.begin()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	def save_index(self, value):
		replace_bytes(self.folder / 'index.json', json_data(value))
	# @used-by :func:`scope_issues()`
	# @used-by :meth:`ClientTextWorkspace.check()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	@staticmethod
	def scope_issues(op, base, candidate):
		r = []
		base_text = base.decode('utf-8') if isinstance(base, (bytes, bytearray)) else base
		if 'inspect' == op['mode'] and candidate != base_text:
			r.append({'code': 'text.inspect_write', 'message': 'Inspect cannot change the document'})
		if op['changes'] in ('links', 'renumber') and _mechanical_projection(base_text, op['kind'], op['changes']) != _mechanical_projection(candidate, op['kind'], op['changes']):
			r.append({'code': 'text.scope', 'message': 'Candidate changes content outside the declared mechanical operation'})
		allowed = op.get('allow_sections', [])
		if allowed:
			before = _scope_blocks(base_text, op['kind'])
			after = {b['section']: b['text'] for b in _scope_blocks(candidate, op['kind'])}
			names = [b['section'] for b in before]
			permit = set()
			for name in allowed:
				if name in names:
					permit.update((key for key in names if key == name or key.startswith(name + '.')))
				elif 1 != name.count('-'):
					r.append({'code': 'text.allow', 'message': 'Unknown allowed section: ' + name})
				else:
					first, last = name.split('-')
					if first not in names or last not in names or names.index(first) > names.index(last):
						r.append({'code': 'text.allow', 'message': 'Invalid allowed section range: ' + name})
					else:
						chosen = names[names.index(first):names.index(last) + 1]
						permit.update((key for key in names if any((key == node or key.startswith(node + '.') for node in chosen))))
			for block in before:
				if block['section'] not in permit and after.get(block['section']) != block['text']:
					r.append({'code': 'text.outside_scope', 'message': 'Changed or removed section outside scope: ' + block['section']})
			for name in set(after) - set(names):
				if name not in permit and (not any((name.startswith(parent + '.') for parent in permit))):
					r.append({'code': 'text.outside_scope', 'message': 'Added section outside scope: ' + name})
		return r
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
# 2026-11-14
# "Decompose text_workflow.py into ClientTextWorkspace and TextIntegrityVerifier classes":
# https://github.com/dmitry-ai/harness/issues/78
class TextIntegrityVerifier:
	# @used-by :func:`_applied_integrity()`
	# @used-by :func:`_claim_snapshot()`
	# @used-by :func:`_reconciled_integrity()`
	# @used-by :func:`_verify_applied_successor()`
	# @used-by :func:`integrity_snapshot()`
	# @used-by :func:`verify_integrity()`
	# @used-by :meth:`ClientTextWorkspace.gate()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def __init__(self, workspace: ClientTextWorkspace, *, index_state=None):
		self.ws = workspace
		self.index_state = index_state
	# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
	def _add_artifact(self, files, reference, expected=None):
		actual = digest(inside(self.ws.root, reference).read_bytes())
		if None is not expected and actual != expected:
			raise ValueError('Admitted text artifact changed: ' + reference)
		if reference in files and files[reference] != actual:
			raise ValueError('Conflicting admitted text artifact versions')
		files[reference] = actual
	# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_locked()`
	# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
	def _state(self):
		if None is self.index_state:
			self.index_state = self.ws.index()
		return self.index_state
	# @used-by :func:`_applied_integrity()`
	# @used-by :meth:`TextIntegrityVerifier.snapshot()`
	# @used-by :meth:`TextIntegrityVerifier.verify()`
	def applied_integrity(self, name, entry, *, require_live_proof=True):
		if self._state()['targets'].get(name) != entry or _hash_or_none(_target_bytes(self.ws.document(name))) != entry['sha256']:
			raise ValueError('Registered text target changed without its applied version: ' + name)
		files, claims, reviews = ({}, [], [])
		if entry.get('reconciliation') and (not entry.get('receipt')):
			for reference, expected in self.reconciled_integrity(name, entry)['files'].items():
				self._add_artifact(files, reference, expected)
		elif entry.get('receipt'):
			_, saved = read_addressed_json(inside(self.ws.root, entry['receipt']), suffix='-applied.json', error_msg='Applied text receipt changed: ' + name)
			if 'applied' != saved.get('status') or saved.get('target') != name or saved.get('candidate_sha256') != entry['sha256']:
				raise ValueError('Applied text receipt changed: ' + name)
			checked, candidate = self.ws.read_check(saved['check'])
			if True is not checked.get('valid') or any((saved.get(key) != checked.get(key) for key in _APPLIED_CHECK_KEYS)):
				raise ValueError('Applied text no longer matches its admitted check')
			op, _ = self.ws.operation(saved['operation'])
			if op['target'] != name or op['base_sha256'] != saved['base_sha256']:
				raise ValueError('Applied text operation identity changed')
			claim = self.claim_snapshot(checked)
			versioned = {claim['registry']} if claim else set()
			if claim:
				claims.append(claim)
			for reference, expected in saved['inputs'].items():
				if reference not in versioned:
					self._add_artifact(files, reference, expected)
			op_dir = self.ws.folder / 'operations' / op['id']
			for reference in (entry['receipt'], saved['check'], checked['candidate'], (op_dir / 'operation.json').relative_to(self.ws.root).as_posix(), (op_dir / 'base.bin').relative_to(self.ws.root).as_posix()):
				self._add_artifact(files, reference)
			from .text_sources import source_integrity
			for reference in saved.get('source_checks', []):
				for source, expected in source_integrity(self.ws.root, candidate, reference)['inputs'].items():
					self._add_artifact(files, source, expected)
			if saved.get('approval'):
				from .text_review import approval_integrity
				approval = approval_integrity(self.ws.root, saved['approval'], versioned_inputs=versioned, require_live_proof=require_live_proof)
				reviews = approval['reviews']
				for reference, expected in approval['files'].items():
					self._add_artifact(files, reference, expected)
		return {'target': name, 'entry': deepcopy(entry), 'files': files, 'claims': claims, 'reviews': reviews}
	# @used-by :func:`_claim_snapshot()`
	# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
	def claim_snapshot(self, checked):
		from .claims import all_claims, claim_digest
		from .text_claims import registry_path, subset
		r = None
		versions = checked.get('claim_versions', {})
		if versions:
			registry = registry_path(self.ws.root, (checked.get('manifest') or {}).get('registry'))
			reference = registry.relative_to(self.ws.root).as_posix()
			snapshot = checked.get('claim_snapshot')
			if None is snapshot:
				candidates = [registry]
				if reference in checked['inputs']:
					candidates.append(self.ws.pp.data_dir / 'text-claim-history' / (checked['inputs'][reference] + '.json'))
				for path in candidates:
					try:
						candidate = subset(_read(path), versions)
						if {claim['id']: claim_digest(claim) for claim in all_claims(candidate)} == versions:
							snapshot = candidate
							break
					except (OSError, ValueError, KeyError, TypeError):
						continue
			if not isinstance(snapshot, dict) or {claim['id']: claim_digest(claim) for claim in all_claims(snapshot)} != versions:
				raise ValueError('Original admitted claim revisions are missing or changed')
			r = {'registry': reference, 'versions': versions, 'snapshot': snapshot}
		return r
	# @used-by :func:`_reconciled_integrity()`
	# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
	# @used-by :meth:`TextIntegrityVerifier.verify_applied_successor()`
	def reconciled_integrity(self, name, entry):
		from .path_registry import same_project_root
		reference = entry.get('reconciliation')
		if not reference or entry.get('receipt'):
			raise ValueError('Explicit text baseline reconciliation is missing: ' + name)
		raw, saved = read_addressed_json(inside(self.ws.root, reference), suffix='-reconciled.json', error_msg='Explicit text baseline reconciliation identity changed: ' + name)
		if 1 != saved.get('schema_version') or 'baseline_reconciliation' != saved.get('kind') or (not same_project_root(saved.get('root'), self.ws.root)) or saved.get('target') != name or saved.get('document_kind') != entry.get('kind') or (not isinstance(saved.get('previous'), dict)) or saved.get('baseline', {}).get('sha256') != entry.get('sha256'):
			raise ValueError('Explicit text baseline reconciliation identity changed: ' + name)
		op, base = self.ws.operation(saved['operation'])
		op_dir = self.ws.folder / 'operations' / op['id']
		if op.get('reconciliation') != reference or op['target'] != name or op['kind'] != entry['kind'] or op['base_sha256'] != entry['sha256'] or 'reconcile_sha256' not in op or op['reconcile_sha256'] != entry['sha256'] or saved['baseline']['file'] != (op_dir / 'base.bin').relative_to(self.ws.root).as_posix():
			raise ValueError('Explicit text reconciliation no longer matches the captured baseline operation: ' + name)
		op_json_rel = (op_dir / 'operation.json').relative_to(self.ws.root).as_posix()
		files = {reference: digest(raw), saved['baseline']['file']: digest(base), op_json_rel: digest((op_dir / 'operation.json').read_bytes())}
		return {'previous': saved['previous'], 'files': files}
	# @used-by :func:`integrity_snapshot()`
	# @used-by :meth:`ClientTextWorkspace.gate()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def snapshot(self, entries):
		return {'schema_version': 1, 'root': str(self.ws.root), 'targets': [self.applied_integrity(name, entry) for name, entry in sorted(entries.items())]}
	# @used-by :func:`verify_integrity()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def verify(self, graph):
		from .claims import all_claims, claim_digest
		with locked(self.ws.folder / 'writer.lock'):
			self.index_state = self.ws.index()
			for target in graph['targets']:
				for reference, expected in target['files'].items():
					if digest(inside(self.ws.root, reference).read_bytes()) != expected:
						raise ValueError('Historical admitted artifact changed: ' + reference)
				for claim in target['claims']:
					if {item['id']: claim_digest(item) for item in all_claims(claim['snapshot'])} != claim['versions']:
						raise ValueError('Historical admitted claim snapshot changed')
				if target.get('reviews'):
					from .text_review import _state
					reviews = {entry['id']: entry for entry in _state(self.ws.root)['reviews']}
					if any((reviews.get(entry['id']) != entry for entry in target['reviews'])):
						raise ValueError('Historical admitted publication review changed or is missing')
				name = target['target']
				current = self.index_state['targets'].get(name)
				if None is current:
					raise ValueError('Historical text target registration is missing: ' + name)
				if current == target['entry']:
					if _hash_or_none(_target_bytes(self.ws.document(name))) != target['entry']['sha256']:
						raise ValueError('Historical text target changed without an applied revision: ' + name)
				else:
					if not current.get('receipt') and (not current.get('reconciliation')):
						raise ValueError('Later text version has no applied receipt: ' + name)
					self.verify_applied_successor(name, current, target['entry'])
					self.applied_integrity(name, current, require_live_proof=False)
		return {'valid': True, 'scope': 'original_admitted_artifacts'}
	# @used-by :func:`_verify_applied_successor()`
	# @used-by :meth:`TextIntegrityVerifier.verify()`
	def verify_applied_successor(self, name, current, original):
		entry, visited = (current, set())
		while entry != original:
			reference = entry.get('receipt') or entry.get('reconciliation')
			if not reference or reference in visited:
				raise ValueError('Current text is not a proven applied successor of the admitted version: ' + name)
			visited.add(reference)
			if not entry.get('receipt'):
				entry = self.reconciled_integrity(name, entry)['previous']
			else:
				_, saved = read_addressed_json(inside(self.ws.root, reference), suffix='-applied.json', error_msg='Applied text successor identity changed: ' + name)
				if 'applied' != saved.get('status') or saved.get('target') != name or saved.get('candidate_sha256') != entry.get('sha256') or saved.get('kind') != entry.get('kind'):
					raise ValueError('Applied text successor identity changed: ' + name)
				previous = saved.get('previous')
				if not isinstance(previous, dict) or previous.get('sha256') != saved.get('base_sha256'):
					raise ValueError('Applied text successor has no exact predecessor: ' + name)
				entry = previous
		return {'valid': True, 'scope': 'exact_applied_successor_lineage'}
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`_find_registered()`
# @used-by :func:`_roots()`
# @used-by :func:`agent_tools.text_review._state()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_sources.probe_links()`
# @used-by :func:`agent_tools.text_sources.save_source_check()`
def _folder(root):
	from .path_registry import project_paths
	return project_paths(root, exact_root=True).data_dir / 'texts'
# @used-by :meth:`ClientTextWorkspace.check()`
# @used-by :meth:`ClientTextWorkspace.index()`
# @used-by :meth:`ClientTextWorkspace.operation_meta()`
# @used-by :meth:`TextIntegrityVerifier.claim_snapshot()`
def _read(path):
	return json.loads(Path(path).read_text(encoding='utf-8-sig'))
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# @used-by :func:`write_candidate_output()`
# @used-by :meth:`ClientTextWorkspace._check_replay()`
# @used-by :meth:`ClientTextWorkspace.apply()`
# @used-by :meth:`ClientTextWorkspace.begin()`
# @used-by :meth:`ClientTextWorkspace.check()`
def _immutable(path, payload):
	return write_immutable_bytes(path, payload, diff_error='Immutable text artifact differs: ' + str(path))
# @used-by :func:`_find_registered()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
def _index(root):
	return ClientTextWorkspace(root).index()
# @used-by unused
def _save_index(root, value):
	ClientTextWorkspace(root).save_index(value)
# @used-by :func:`write_candidate_output()`
# @used-by :meth:`ClientTextWorkspace._gate_target()`
# @used-by :meth:`ClientTextWorkspace._validate_begin_spec()`
# @used-by :meth:`ClientTextWorkspace.apply()`
# @used-by :meth:`ClientTextWorkspace.begin()`
# @used-by :meth:`ClientTextWorkspace.check()`
# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
# @used-by :meth:`TextIntegrityVerifier.verify()`
def _target_bytes(path):
	if path.exists() and (not path.is_file()):
		raise ValueError('Text target must be a file')
	return path.read_bytes() if path.exists() else None
# @used-by unused
def _document(root, name):
	return ClientTextWorkspace(root).document(name)
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# @used-by :meth:`ClientTextWorkspace._validate_begin_spec()`
# @used-by :meth:`ClientTextWorkspace.document()`
def _has_linked_ancestor(root, target, *, require_exists=True):
	return any((p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (target, *target.parents) if (not require_exists or p.exists()) and p.is_relative_to(root)))
# @used-by :func:`write_candidate_output()`
# @used-by :meth:`ClientTextWorkspace._gate_target()`
# @used-by :meth:`ClientTextWorkspace._validate_begin_spec()`
# @used-by :meth:`ClientTextWorkspace.apply()`
# @used-by :meth:`ClientTextWorkspace.begin()`
# @used-by :meth:`ClientTextWorkspace.check()`
# @used-by :meth:`TextIntegrityVerifier.applied_integrity()`
# @used-by :meth:`TextIntegrityVerifier.verify()`
def _hash_or_none(value):
	return digest(value) if None is not value else None
# @used-by :func:`write_candidate_output()`
def _find_registered(target):
	target = Path(target).resolve()
	r = None
	for root in target.parents:
		file = _folder(root) / 'index.json'
		if file.is_file():
			state = _index(root)
			name = target.relative_to(root).as_posix()
			if name in state['targets'] or name in state.get('protected', []):
				r = root
				break
	return r
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_formatter_cannot_overwrite_a_document_protected_by_the_operation()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_registered_target_cannot_be_overwritten_via_formatter()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_unregistered_candidate_output_requires_cas_and_keeps_history()`
def write_candidate_output(path, payload, *, expected_sha256=None):
	path = Path(path).resolve()
	if None is not _find_registered(path):
		raise ValueError('Registered text target: use text-check/text-apply; formatter output is only a candidate')
	folder = data_dir_for(path)
	with locked(folder / 'text-candidates.lock'):
		previous = _target_bytes(path)
		if _hash_or_none(previous) != expected_sha256:
			raise ValueError('Existing output needs its current --expected-sha256; external version preserved')
		if None is not previous:
			_immutable(folder / 'text-output-history' / (digest(previous) + '.bin'), previous)
		if _target_bytes(path) != previous:
			raise ValueError('Output changed during candidate preparation')
		path.parent.mkdir(parents=True, exist_ok=True)
		if None is previous:
			create_bytes(path, payload)
		else:
			replace_bytes(path, payload)
	return {'path': str(path), 'sha256': digest(payload), 'kind': 'candidate', 'publication_approved': False}
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.reconcile_manual_baseline()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.start()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_external_journal_cannot_bypass_the_current_client_document_gate()`
def begin(root, spec):
	return ClientTextWorkspace(root, strict=True).begin(spec)
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_review.read_package()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
def operation(root, ident):
	return ClientTextWorkspace(root).operation(ident)
# @used-by unused
def operation_meta(root, ident):
	return ClientTextWorkspace(root).operation_meta(ident)
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_links_only_allows_url_presentation_but_preserves_crlf_and_anchor_words()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_renumber_scope_accepts_external_spacing_without_rebinding_its_number()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_section_scope_covers_group_headers_and_protects_part_title()`
# @used-by :meth:`test_text_workflow.TextMechanicalScopeTests.scope()`
# @used-by :meth:`test_text_workflow.TextMechanicalScopeTests.test_inspect_never_allows_even_one_word_change()`
def scope_issues(op, base, candidate):
	return ClientTextWorkspace.scope_issues(op, base, candidate)
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.checked()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_missing_map_is_an_invalid_result_instead_of_a_crash()`
# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_map_change_does_not_inherit_an_old_check_approval()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_manual_change_after_check_preserves_the_users_new_bytes()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
def check(root, ident, candidate, manifest=None, *, run_replay=False, replay_record=None, warning_dispositions=None, applied=False):
	return ClientTextWorkspace(root).check(ident, candidate, manifest, run_replay=run_replay, replay_record=replay_record, warning_dispositions=warning_dispositions, applied=applied)
# @used-by unused
def read_check(root, reference):
	return ClientTextWorkspace(root).read_check(reference)
# @used-by :func:`agent_tools.text_review.authorize()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_review.read_package()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
def refresh_check(root, reference, *, applied=False):
	return ClientTextWorkspace(root).refresh_check(reference, applied=applied)
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.fixture()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_map_change_does_not_inherit_an_old_check_approval()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_significant_subject_needs_two_distinct_reviewers()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_manual_change_after_check_preserves_the_users_new_bytes()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
def apply(root, reference):
	return ClientTextWorkspace(root).apply(reference)
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_direct_write_bypass_never_acquires_a_valid_receipt()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
def gate(root, *, targets=None, response=None, publication=False, capture=False):
	return ClientTextWorkspace(root).gate(targets=targets, response=response, publication=publication, capture=capture)
# @used-by unused
def _claim_snapshot(root, checked):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).claim_snapshot(checked)
# @used-by unused
def _applied_integrity(root, name, entry, *, require_live_proof=True):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).applied_integrity(name, entry, require_live_proof=require_live_proof)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def integrity_snapshot(root, entries):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).snapshot(entries)
# @used-by unused
def _reconciled_integrity(root, name, entry):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).reconciled_integrity(name, entry)
# @used-by unused
def _verify_applied_successor(root, name, current, original):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).verify_applied_successor(name, current, original)
# @used-by :func:`agent_tools.admission.verify()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def verify_integrity(graph):
	if not isinstance(graph, dict) or 1 != graph.get('schema_version') or not isinstance(graph.get('root'), str) or not Path(graph['root']).is_absolute() or not isinstance(graph.get('targets'), list):
		raise ValueError('Invalid historical text integrity graph')
	return TextIntegrityVerifier(ClientTextWorkspace(graph['root'])).verify(graph)
# 2026-11-22
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# @used-by :func:`gate_paths()`
# @used-by :func:`gate_requests()`
def _roots(paths):
	from .path_registry import canonicalize_root_dir
	roots = set()
	for value in paths:
		path = canonicalize_root_dir(value)
		for root in (path, *path.parents):
			if (_folder(root) / 'index.json').is_file():
				roots.add(root)
	return sorted(roots)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.check_commit()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
def gate_paths(paths, *, response=None):
	selected = {Path(path).resolve() for path in paths}
	r = []
	for root in _roots(selected):
		ws = ClientTextWorkspace(root)
		r.append(ws.gate(response=response, targets=[name for name in ws.index()['targets'] if (root / name).resolve() in selected]))
	return r
# @used-by :func:`agent_tools.admission.capture()`
# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
def gate_requests(paths, requests, response, *, capture=False):
	r = []
	for root in _roots(paths):
		res = ClientTextWorkspace(root).gate_requests_for_root(requests, response, capture=capture)
		if None is not res:
			r.append(res)
	return r
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
def record_answer(root, journal, requests, response, turn):
	from .journal import record_answer as save
	steps = save(Path(journal), requests, response, turn, admission_roots=[root, journal])
	return {'journal_steps': steps, 'response_sha256': digest(response.encode()), 'delivery_verified': False}
