# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import uuid
from .analysis import analysis_issues, publish_owned, SECTIONS
from .diagnostics import problem
from .evidence import evidence_issues
from .research import inside, json_data
from .storage import locked, replace_bytes
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
STAGES = ('capture', 'identity_init', 'research', 'analysis', 'review', 'kb_review', 'finalize')
# 2026-11-14
# "Decompose workflow.py and knowledge.py into WorkflowStateEngine, ResearchQuestionRegistry, and ProjectHealthAuditor with shared attachment inventory":
# https://github.com/dmitry-ai/harness/issues/74
class ProjectHealthAuditor:
	# @used-by :func:`attachment_issues()`
	# @used-by :func:`check_project()`
	# @used-by :func:`kb_issues()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def __init__(self, root):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	# @used-by :meth:`ProjectHealthAuditor.check_project()`
	def _analysis_card_issues(self, path, prevalidated=None):
		r = []
		analysis_rel = self.pp.rel_to_root(path)
		overview_file = self.pp.path('overview_md', self.root / '.md')
		overview_rel = self.pp.rel_to_root(overview_file)
		if not path.is_file():
			r.append(problem('analysis.missing', analysis_rel, 'Analysis draft is not saved'))
		else:
			try:
				from .evidence_loader import load_analysis_card_validation
				value, contract_issues, ev_issues = load_analysis_card_validation(self.root, path, prevalidated, analysis_issues_fn=analysis_issues, evidence_issues_fn=evidence_issues)
				r.extend(contract_issues)
				r.extend(ev_issues)
				if isinstance(value, dict):
					# 2026-10-18
					# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
					# https://github.com/dmitry-ai/harness/issues/10
					if value.get('schema_version') in (2, 3) and (not contract_issues):
						# 2026-10-17
						# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
						# https://github.com/dmitry-ai/harness/issues/7
						# 2026-10-19
						# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
						# https://github.com/dmitry-ai/harness/issues/12
						# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
						from .project_drift import analysis_card_sync_issues
						r.extend(analysis_card_sync_issues(self.pp, value))
			except (OSError, ValueError, TypeError) as exc:
				r.append(problem('analysis.input', str(path), str(exc)))
		return r
	# @used-by :meth:`ProjectHealthAuditor.attachment_issues()`
	def _kb_targets(self):
		r = []
		for target in (self.pp.manual_kb_dir / 'Project.md', self.pp.kb_dir / 'Project.md', self.pp.kb_dir / 'Projects.md'):
			label = self.pp.rel_to_root(target)
			r.append((label, target, target.read_text(encoding='utf-8') if target.is_file() else ''))
		return tuple(r)
	# @used-by :meth:`ProjectHealthAuditor.attachment_issues()`
	def _load_snapshot(self):
		pj_file = self.pp.project_json
		r = None
		if pj_file.is_file():
			try:
				pj = json.loads(pj_file.read_text(encoding='utf-8'))
				snap_path = self.root / pj.get('snapshot', '')
				r = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.is_file() else {}
			except Exception:
				r = None
		return r
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	# @used-by :func:`attachment_issues()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def attachment_issues(self):
		from .knowledge import AttachmentInventory
		from .upwork_data import classify_attachment, detect_client_videos, extract_attachment_markdown
		r = []
		snap = self._load_snapshot()
		if None is not snap:
			inv = AttachmentInventory(self.root).scan(snap.get('asset_evidence'))
			for f, sha in inv['missing_evidence']:
				r.append(problem('attachment.evidence_missing', f'source/{f.name}', f'Attached file in source/{f.name} is not synced to ꘖ/KB/Evidence/Attachments/{sha}/{f.name}; run sync-attachments', file=f))
			targets = self._kb_targets()
			doc_markdowns = []
			for att in inv['attachments']:
				fname, sha, ev_path = (att['filename'], att['sha256'], att['evidence_path'])
				payload = ev_path.read_bytes()
				if not inv['source_by_sha'].get(sha):
					r.append(problem('attachment.source_missing', f'source/{fname}', f'Attached file {fname} must be saved in the root source/ folder (§2.1); run sync-attachments', file=ev_path))
				kind = classify_attachment(fname, payload)
				heading_markers = (f'Description in `{fname}`', f'\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0432 `{fname}`')
				if 'document' == kind:
					doc_markdowns.append(extract_attachment_markdown(ev_path, payload))
					for label, target_file, target_text in targets:
						if not any((hm in target_text for hm in heading_markers)):
							r.append(problem('attachment.kb_missing', label, f'Attached document {fname} is missing from {label} (§2.2); run sync-attachments', file=target_file))
				elif 'image' == kind:
					for label, target_file, target_text in targets:
						matched_hm = next((hm for hm in heading_markers if hm in target_text), None)
						if not matched_hm:
							r.append(problem('attachment.image_missing', label, f'Attached image {fname} must be transcribed and analyzed in {label} (§2.4)', file=target_file))
						else:
							sec_match = re.search(f'(?ms){re.escape(matched_hm)}.*?(?:~~~+|```+)markdown\\n(.*?)\\n(?:~~~+|```+)', target_text)
							sec_body = (sec_match.group(1) if sec_match else '').strip()
							if not sec_body or '«' not in sec_body or (not re.search('(?i)confirm|contradict|\\u043f\\u043e\\u0434\\u0442\\u0432\\u0435\\u0440\\u0436\\u0434\\u0435\\u043d\\u0438|\\u043f\\u0440\\u043e\\u0442\\u0438\\u0432\\u043e\\u0440\\u0435\\u0447\\u0438', sec_body)) or (not re.search('(?i)(?:score|\\u043e\\u0446\\u0435\\u043d\\u043a\\u0430).*\\d+\\s*%', sec_body)):
								r.append(problem('attachment.image_incomplete', label, f'Attached image {fname} in {label} requires verbatim «...» text transcription, exhaustive UI description, and confirmation/contradiction analysis with % score (§2.4)', file=target_file))
			for v in detect_client_videos(snap.get('description') or '', doc_markdowns, [{'filename': a['filename'], 'sha256': a['sha256']} for a in inv['attachments']]):
				v_heading = v['heading']
				for label, target_file, target_text in targets:
					if v_heading not in target_text:
						r.append(problem('attachment.video_missing', label, f'Client video ({v_heading}) must be transcribed in {label} (§2.3)', file=target_file))
					elif '# Full Audio Transcript:' not in target_text and '# \u041f\u043e\u043b\u043d\u0430\u044f \u0440\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0430 \u0430\u0443\u0434\u0438\u043e\u0437\u0430\u043f\u0438\u0441\u0438:' not in target_text or not re.search('\\[\\d{2}:\\d{2}\\]', target_text):
						r.append(problem('attachment.video_incomplete', label, f'Client video ({v_heading}) in {label} requires # Video:, # Key Spoken Commentary Points..., and # Full Audio Transcript: with [MM:SS] timestamps (§2.3)', file=target_file))
		return r
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	# @used-by :func:`check_project()`
	def check_project(self, *, prevalidated_analysis=None):
		from .runtime import PRIMARY
		issues = kb_issues(self.root) + attachment_issues(self.root)
		# 2026-10-19
		# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
		# https://github.com/dmitry-ai/harness/issues/12
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		scan_folders = [self.pp.data_dir]
		if self.pp.agents_config_dir.resolve() != Path(PRIMARY).resolve():
			scan_folders.append(self.pp.agents_config_dir)
		elif (self.root / '.agents').is_dir():
			scan_folders.append(self.root / '.agents')
		for folder in scan_folders:
			if folder.is_dir():
				for script in sorted(folder.rglob('*')):
					if script.is_file() and script.suffix.lower() in ('.py', '.ps1', '.sh', '.bat', '.cmd'):
						issues.append(problem('project.one_off_script', self.pp.rel_to_root(script), 'Executable one-off scripts are prohibited in project directories (FILE-5/EXEC-1); use shared upwork_project.py commands', file=script))
		# 2026-10-17
		# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
		# https://github.com/dmitry-ai/harness/issues/9
		from .links import readable_link_issues
		# 2026-11-21
		# "Initialize new Upwork projects in the V2 filesystem layout":
		# https://github.com/dmitry-ai/harness/issues/110
		deliverable_dirs = list(dict.fromkeys((d.resolve() for d in (self.pp.path('proposals_dir', self.root / 'result'), self.pp.path('letters_dir', self.root / 'Letters'), self.pp.path('articles_dir', self.root / '\u2c0f/\u227b/\u2655/\U0001f582/Articles'), self.root / 'result') if d.is_dir())))
		overview_file = self.pp.path('overview_md', self.root / '.md')
		proposal_docs = list({p.resolve(): p for d in deliverable_dirs for p in sorted(d.rglob('*'))}.values())
		for document in [overview_file, *proposal_docs]:
			if document.is_file() and 'draft.prev.md' != document.name and ('.md' == document.name or document.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm')):
				for error in readable_link_issues(document.read_text(encoding='utf-8')):
					issues.append(problem('document.link_style', self.pp.rel_to_root(document), error, file=document))
		path = self.pp.kb_dir / 'Analysis.json'
		issues.extend(self._analysis_card_issues(path, prevalidated=prevalidated_analysis))
		# 2026-11-26 "Harden follow-up launcher handoff and journal reservation integrity": https://github.com/dmitry-ai/harness/issues/269
		from .journal_integrity import finalize_project_check
		return finalize_project_check(self.pp, issues, path)
	# @used-by :func:`kb_issues()`
	def kb_issues(self):
		from .links import validate_file
		r = []
		for relative in kb_paths(self.root):
			file = inside(self.root, relative)
			if '.md' != file.suffix.lower() and '.md' != file.name:
				continue
			# 2026-10-17
			# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
			# https://github.com/dmitry-ai/harness/issues/9
			for error in validate_file(file, local_anchors=True, readable_links=True):
				r.append(problem('kb.link', relative, error, file=file))
			text = file.read_text(encoding='utf-8')
			if re.search('(?im)^\\s*\\|.*\\|\\s*$\\n\\s*\\|?\\s*:?-{3,}', text) or re.search('(?i)<a\\s+[^>]*(?:name|id)\\s*=', text):
				r.append(problem('kb.format', relative, 'Markdown tables or HTML anchors conflict with DOC-4/LINK-4', file=file))
			# 2026-10-19
			# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
			# https://github.com/dmitry-ai/harness/issues/12
			if 'Analysis.md' != file.name:
				for doc4_err in doc4_sentence_issues(text):
					r.append(problem('kb.doc4_sentence', relative, doc4_err, file=file))
		return r
# 2026-11-14
# "Decompose workflow.py and knowledge.py into WorkflowStateEngine, ResearchQuestionRegistry, and ProjectHealthAuditor with shared attachment inventory":
# https://github.com/dmitry-ai/harness/issues/74
class ResearchQuestionRegistry:
	# @used-by :func:`add_question()`
	# @used-by :func:`claim_question()`
	# @used-by :func:`finish_question()`
	# @used-by :func:`handoff()`
	# @used-by :func:`question_contract_issues()`
	# @used-by :func:`questions_current()`
	# @used-by :func:`record_search()`
	# @used-by :meth:`WorkflowStateEngine.stage_statuses()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def __init__(self, root):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
	# @used-by :meth:`ResearchQuestionRegistry.add()`
	def _apply_add(self, state, ident, entry):
		if ident in state['questions']:
			raise ValueError('Question already exists; use its saved inputs/results')
		# 2026-11-04
		# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
		# https://github.com/dmitry-ai/harness/issues/44
		state['questions'][ident] = {**entry, 'time': now()}
	# @used-by :meth:`ResearchQuestionRegistry.claim()`
	def _apply_claim(self, state, ident, owner):
		q = state['questions'][ident]
		if q['status'] in ('complete', 'gap'):
			raise ValueError('Use the existing result; reopening requires a new documented question')
		if q['owner'] and q['owner'] != owner:
			raise ValueError('Question already has an owner; inspect native subagent status before explicit handoff')
		for other in state['questions'].values():
			if other['id'] != ident and other['owner'] and ('running' == other['status']) and (set(other['allowed_outputs']) & set(q['allowed_outputs'])):
				raise ValueError('Another active question owns the same output file')
		q.update(owner=owner, status='running')
	# @used-by :meth:`ResearchQuestionRegistry.finish()`
	def _apply_finish(self, state, ident, owner, outputs, gap, results):
		q = state['questions'][ident]
		if q['owner'] != owner or 'running' != q['status']:
			raise ValueError('Only the current task owner may finish the question')
		if not all((inside(self.root, p).relative_to(self.root).as_posix() in q['allowed_outputs'] for p in outputs)):
			raise ValueError('Result was not among declared outputs')
		if hashes(self.root, list(q['inputs'])) != q['inputs']:
			raise ValueError('Question inputs changed; review the result against the new inputs')
		if not outputs or (None is not gap and (not gap.strip())):
			raise ValueError('A saved result/report and explicit gap explanation are required')
		# 2026-10-18
		# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
		# https://github.com/dmitry-ai/harness/issues/10
		issues = self.contract_issues({**q, 'gap': gap, 'requirement_results': results})
		if issues:
			raise ValueError('\n'.join(issues))
		q.update(status='gap' if gap else 'complete', results=hashes(self.root, outputs), gap=gap, requirement_results=results)
	# @used-by :meth:`ResearchQuestionRegistry.handoff()`
	def _apply_handoff(self, state, ident, previous_owner, new_owner, reason):
		q = state['questions'][ident]
		if q['owner'] != previous_owner or 'running' != q['status']:
			raise ValueError('Task owner/status changed; refresh native progress before handoff')
		q.update(owner=new_owner, handoff_reason=reason)
	# @used-by :meth:`ResearchQuestionRegistry.record_search()`
	def _apply_search(self, state, ident, owner, query, useful, method_change):
		q = state['questions'][ident]
		if q['owner'] != owner or 'running' != q['status']:
			raise ValueError('Only current task owner can record searches')
		recent = []
		for attempt in reversed(q['searches']):
			recent.append(attempt)
			if attempt.get('method_change') or 3 == len(recent):
				break
		if 3 == len(recent) and all((not x['useful'] for x in recent)) and (not method_change):
			raise ValueError('Three unsuccessful searches: return a gap or document a different method before continuing')
		q['searches'].append({'query': ' '.join(query.casefold().split()), 'useful': bool(useful), 'method_change': method_change, 'time': now()})
	# @used-by :func:`Df.Core.lib.lang.other.df_no_rec()`
	# @used-by :func:`add_question()`
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :func:`agent_tools.claims.collect_claim_closure()`
	# @used-by :func:`agent_tools.claims.evaluate_safe_arithmetic()`
	# @used-by :func:`agent_tools.claims.extract_verified_inline_calc_numbers()`
	# @used-by :func:`agent_tools.claims.source_numeric_tokens()`
	# @used-by :func:`agent_tools.cleanup._collect_folder_ancestors()`
	# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._journal_pair_activity()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._launcher_turn_dirs()`
	# @used-by :func:`agent_tools.code_size_gate._code_lines_and_semicolons()`
	# @used-by :func:`agent_tools.completion._build_compaction_file_index()`
	# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
	# @used-by :func:`agent_tools.completion.similar_project_exempt()`
	# @used-by :func:`agent_tools.configuration._root_options()`
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :func:`agent_tools.context.discover_letters()`
	# @used-by :func:`agent_tools.contract_invariants.audit_readable_link_call_sites()`
	# @used-by :func:`agent_tools.evidence_loader._add_anchor()`
	# @used-by :func:`agent_tools.experiments.requirement_issues()`
	# @used-by :func:`agent_tools.failfast_gate._active_turn_run_command_tasks()`
	# @used-by :func:`agent_tools.gates.answer_checks.run_answer_gates()`
	# @used-by :func:`agent_tools.gates.bulk_source_read._update_streak()`
	# @used-by :func:`agent_tools.gates.worktree_isolation._count_active_open_turns()`
	# @used-by :func:`agent_tools.git_gate._ancestor_process_names()`
	# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
	# @used-by :func:`agent_tools.grounding_domains.extract_ticket_metadata()`
	# @used-by :func:`agent_tools.grounding_domains.fact_tuple_contradictions()`
	# @used-by :func:`agent_tools.intake._inventory()`
	# @used-by :func:`agent_tools.intake._validate_new()`
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :func:`agent_tools.issue_comment_gate._diff_changes()`
	# @used-by :func:`agent_tools.issue_comment_gate._scan_record_code()`
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_issue_first_events()`
	# @used-by :func:`agent_tools.issues.parity._evaluate_similar_peer_item()`
	# @used-by :func:`agent_tools.issues.parity._find_peer_issue_resolution()`
	# @used-by :func:`agent_tools.issues.parity._peer_code_repo_candidates()`
	# @used-by :func:`agent_tools.issues.parity.similar_project_repo_slugs()`
	# @used-by :func:`agent_tools.issues.repo_locator._first_matching_repo()`
	# @used-by :func:`agent_tools.issues.service_helpers._collect_recorded_repos_from_turn()`
	# @used-by :func:`agent_tools.issues.turn_scope.has_competing_open_turns()`
	# @used-by :func:`agent_tools.journal.reserve_turn_steps()`
	# @used-by :func:`agent_tools.journal_integrity._eligible_active_turn_keys()`
	# @used-by :func:`agent_tools.journal_integrity.collect_handed_off_conversations()`
	# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
	# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
	# @used-by :func:`agent_tools.links.parse_markdown_headings()`
	# @used-by :func:`agent_tools.meta.identity._push_project_dir()`
	# @used-by :func:`agent_tools.metrics.summarize()`
	# @used-by :func:`agent_tools.native_profiles._retire_shared_roles()`
	# @used-by :func:`agent_tools.native_profiles._role_config()`
	# @used-by :func:`agent_tools.native_profiles._shared_plan()`
	# @used-by :func:`agent_tools.parallel_runner._run_single_module()`
	# @used-by :func:`agent_tools.path_registry._candidate_discovery_roots()`
	# @used-by :func:`agent_tools.path_registry._is_registered_single_project()`
	# @used-by :func:`agent_tools.path_registry._validate_similar_project_groups()`
	# @used-by :func:`agent_tools.path_registry.evaluate_similar_project_touches()`
	# @used-by :func:`agent_tools.path_registry.paths_report()`
	# @used-by :func:`agent_tools.platforms.codex.summarize()`
	# @used-by :func:`agent_tools.platforms.trace_common.collect_subagent_bfs()`
	# @used-by :func:`agent_tools.platforms.trace_common.summarize_turn_activity()`
	# @used-by :func:`agent_tools.project_rename_verify._verify_journal_regression()`
	# @used-by :func:`agent_tools.python_integrity._collect_defined_globals()`
	# @used-by :func:`agent_tools.python_integrity._collect_undefined_globals()`
	# @used-by :func:`agent_tools.red_flags.red_flag_issues()`
	# @used-by :func:`agent_tools.repo_link_gate.hydrate_local_repo_urls()`
	# @used-by :func:`agent_tools.repo_tag_gate._parse_ls_remote_tags()`
	# @used-by :func:`agent_tools.repo_tags._build_retro_entry()`
	# @used-by :func:`agent_tools.research._extract_sitemap()`
	# @used-by :func:`agent_tools.research._grep_section_windows()`
	# @used-by :func:`agent_tools.research._summarize_observation_bundle()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_markdown()`
	# @used-by :func:`agent_tools.runtime_cache._collect_one_session()`
	# @used-by :func:`agent_tools.runtime_cache._compute_browser_perimeter()`
	# @used-by :func:`agent_tools.runtime_snapshot._rotate_releases()`
	# @used-by :func:`agent_tools.scatter_banner._collect_candidate_recommendations()`
	# @used-by :func:`agent_tools.schema_help._check_one_assertion()`
	# @used-by :func:`agent_tools.stop_subagent_check._apply_call()`
	# @used-by :func:`agent_tools.stop_subagent_check._process_manage_subagents()`
	# @used-by :func:`agent_tools.subprocess_hygiene_gate._collect_subprocess_bindings()`
	# @used-by :func:`agent_tools.suite_runner._run_module_worker()`
	# @used-by :func:`agent_tools.tdd.commands.shell_test_delete_targets()`
	# @used-by :func:`agent_tools.tdd.commands.shell_write_targets()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._collect_hit_lines()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._prod_match_tokens()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._touched_git_repos()`
	# @used-by :func:`agent_tools.tdd.enforcement._diff_added_lines()`
	# @used-by :func:`agent_tools.tdd.substantive._collect_read_wrapper_params()`
	# @used-by :func:`agent_tools.text_browser._verify_context_anchor()`
	# @used-by :func:`agent_tools.text_claims.primary_numbers()`
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :func:`agent_tools.text_review._source_reviews()`
	# @used-by :func:`agent_tools.text_review.approval_integrity()`
	# @used-by :func:`agent_tools.text_sources.validate_source_checks()`
	# @used-by :func:`agent_tools.text_workflow._roots()`
	# @used-by :func:`agent_tools.upwork_data.collect_unique_public_past_jobs()`
	# @used-by :func:`agent_tools.upwork_data.detect_client_videos()`
	# @used-by :func:`agent_tools.upwork_data.extract_client_names()`
	# @used-by :func:`agent_tools.worktree_guard.find_worktree_lock_holders()`
	# @used-by :func:`agent_tools.xref.java_graph._link_java_method()`
	# @used-by :func:`agent_tools.xref.java_model._consume_modifiers()`
	# @used-by :func:`agent_tools.xref.java_model.discover_java_files()`
	# @used-by :func:`agent_tools.xref.js_graph.find_js_overridden_method()`
	# @used-by :func:`agent_tools.xref.js_model._add_def()`
	# @used-by :func:`agent_tools.xref.js_model._collect_js_rels()`
	# @used-by :func:`agent_tools.xref.js_model._parse_class_body()`
	# @used-by :func:`agent_tools.xref.js_model._parse_top_class()`
	# @used-by :func:`agent_tools.xref.python_model._collect_file_ast()`
	# @used-by :func:`agent_tools.xref.python_model._record_top_assign()`
	# @used-by :func:`agent_tools.xref.python_model._walk_body()`
	# @used-by :func:`agent_tools.xref.python_model._walk_class()`
	# @used-by :func:`agent_tools.xref.python_model.discover_python_files()`
	# @used-by :func:`agent_tools.xref.python_overrides._check_repo_ancestors()`
	# @used-by :func:`agent_tools.xref_gate._staged_overrides()`
	# @used-by :func:`split_project_rules.split_rules()`
	# @used-by :meth:`ResearchQuestionRegistry.contract_issues()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_dependencies_and_caps()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_structure()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_cycles()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._load_direct_evidence()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.capabilities()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._committed_parent_numbers()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
	# @used-by :meth:`agent_tools.knowledge.AttachmentInventory._register_bytes()`
	# @used-by :meth:`agent_tools.knowledge.AttachmentInventory.scan()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.__init__()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.similar_projects()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._visit_subagent_rows()`
	# @used-by :meth:`agent_tools.research.HTMLData.result()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._evaluate_claim_risk()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier.classify()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approved_claim_digests()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_claim_reviews()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_findings()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._load_ledger_tuples()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._candidate_files()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.gate_requests_for_root()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify_applied_successor()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._detect_bold_fonts()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_cache_distinguishes_network_country_language_and_session_state()`
	# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_comment_only_diffs_accepted_for_all_20_languages()`
	def add(self, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
		if not re.fullmatch('[A-Z][A-Z0-9-]*', ident) or not all((isinstance(x, str) and x.strip() for x in (question, impact, done_when))):
			raise ValueError('Question needs a stable ID, question, impact and completion criterion')
		if not inputs:
			raise ValueError('Declare at least the saved capture or relevant KB module as question input')
		# 2026-10-18
		# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
		# https://github.com/dmitry-ai/harness/issues/10
		from .experiments import requirement_issues
		issues = requirement_issues(requirements)
		if issues:
			raise ValueError('\n'.join(issues))
		input_hashes = hashes(self.root, inputs)
		permitted = [inside(self.root, path).relative_to(self.root).as_posix() for path in outputs]
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		ag_prefix = self.pp.rel_to_root(self.pp.agent_dir).rstrip('/') + '/'
		wf_prefix = self.pp.rel_to_root(self.pp.workflow_json).rsplit('.json', 1)[0]
		if not permitted or any((not (p.startswith('ꘖ/') or p.startswith(ag_prefix)) or p.startswith('ꘖ/data/workflow') or p.startswith(wf_prefix) for p in permitted)):
			raise ValueError('Declare exact project-owned outputs under ꘖ; not workflow state')
		entry = {'id': ident, 'question': question, 'impact': impact, 'done_when': done_when, 'inputs': input_hashes, 'allowed_outputs': permitted, 'status': 'pending', 'owner': None, 'searches': [], 'results': {}, 'requirements': requirements, 'requirement_results': []}
		return update(self.root, {'action': 'question', 'question_id': ident}, lambda state: self._apply_add(state, ident, entry))
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :func:`claim_question()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def claim(self, ident, owner):
		if not isinstance(owner, str) or not owner.strip():
			raise ValueError('Owner must be an observed session/subagent ID')
		return update(self.root, {'action': 'claim_question', 'question_id': ident, 'owner': owner}, lambda state: self._apply_claim(state, ident, owner))
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	# @used-by :func:`question_contract_issues()`
	# @used-by :meth:`ResearchQuestionRegistry._apply_finish()`
	# @used-by :meth:`ResearchQuestionRegistry.current()`
	def contract_issues(self, question):
		from .experiments import requirement_issues, result_issues
		requirements = question.get('requirements')
		r = requirement_issues(requirements)
		results = question.get('requirement_results', [])
		if not isinstance(results, list):
			r.append('Structured requirement_results list is required')
		else:
			expected = {req['id']: req for req in requirements if isinstance(req, dict) and isinstance(req.get('id'), str)} if isinstance(requirements, list) else {}
			seen = set()
			for result in results:
				ident = result.get('requirement_id') if isinstance(result, dict) else None
				if ident not in expected or ident in seen:
					r.append('Each declared requirement must have one structured result')
					continue
				seen.add(ident)
				r.extend(result_issues(self.root, expected[ident], result))
			if seen != set(expected):
				r.append('Research requirement results are incomplete')
			if any((item.get('status') in ('unverified', 'unavailable') for item in results if isinstance(item, dict))) and (not question.get('gap')):
				r.append('Unavailable/unverified requirements require an explicit question gap')
		return r
	# @used-by :func:`questions_current()`
	# @used-by :meth:`WorkflowStateEngine.stage_statuses()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def current(self, state):
		engine = WorkflowStateEngine(self.root)
		return all((q['status'] in ('complete', 'gap') and engine.receipt_current({'inputs': q['inputs'], 'outputs': q['results']}) and (not self.contract_issues(q)) for q in state['questions'].values()))
	# @used-by :func:`finish_question()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def finish(self, ident, owner, outputs, gap=None, *, results=None):
		return update(self.root, {'action': 'finish_question', 'question_id': ident}, lambda state: self._apply_finish(state, ident, owner, outputs, gap, results))
	# @used-by :func:`handoff()`
	def handoff(self, ident, previous_owner, new_owner, reason):
		if not all((isinstance(s, str) and s.strip() for s in (previous_owner, new_owner, reason))):
			raise ValueError('Explicit previous owner, new owner and observed stopping reason required')
		return update(self.root, {'action': 'handoff', 'question_id': ident, 'reason': reason}, lambda state: self._apply_handoff(state, ident, previous_owner, new_owner, reason))
	# @used-by :func:`record_search()`
	def record_search(self, ident, owner, query, useful=False, method_change=None):
		if not isinstance(query, str) or not query.strip():
			raise ValueError('Search query required')
		return update(self.root, {'action': 'search', 'question_id': ident}, lambda state: self._apply_search(state, ident, owner, query, useful, method_change))
# 2026-11-14
# "Decompose workflow.py and knowledge.py into WorkflowStateEngine, ResearchQuestionRegistry, and ProjectHealthAuditor with shared attachment inventory":
# https://github.com/dmitry-ai/harness/issues/74
class WorkflowStateEngine:
	# @used-by :func:`adopt_requests()`
	# @used-by :func:`complete_stage()`
	# @used-by :func:`load()`
	# @used-by :func:`publish_progress()`
	# @used-by :func:`receipt_current()`
	# @used-by :func:`record_current_answer()`
	# @used-by :func:`registration_status()`
	# @used-by :func:`resume()`
	# @used-by :func:`stage_statuses()`
	# @used-by :func:`state_path()`
	# @used-by :func:`status()`
	# @used-by :func:`unadopt_requests()`
	# @used-by :func:`update()`
	# @used-by :meth:`ResearchQuestionRegistry.current()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
	def __init__(self, root):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
		self._evidence_cache = None
		self._kb_cache = None
		self._reg_cache = None
	# @used-by :meth:`WorkflowStateEngine.adopt_requests()`
	def _apply_adopt(self, state, requests, saved_answers):
		recorded = {x['id']: x for x in state['requests'] if x.get('native_conversation_id')}
		# 2026-10-15
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		incoming = {x['id'] for x in requests}
		exact_texts = {x['text'] for x in requests}
		state['requests'] = [x for x in state['requests'] if x['id'] not in incoming and (x.get('native_conversation_id') or x['text'] not in exact_texts)]
		for request in requests:
			prepared = saved_answers.get(request['id']) or recorded.get(request['id'], {}).get('response_prepared')
			state['requests'].append({**request, **({'response_prepared': prepared} if prepared else {})})
	# 2026-11-14
	# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
	# https://github.com/dmitry-ai/harness/issues/60
	# @used-by :meth:`WorkflowStateEngine.record_current_answer()`
	def _apply_answer(self, locked_state, initial_state, approval, auth_kw, ids, turn, steps, directory, resp_sha):
		from .review import authorize
		if locked_state != initial_state:
			authorize(self.root, locked_state, package_path=approval['package'], **auth_kw)
		for request in locked_state['requests']:
			if request['id'] in ids:
				request['response_prepared'] = {'turn': turn, 'steps': steps, 'journal': str(directory), 'sha256': resp_sha, 'review_approval': approval}
	# @used-by :meth:`WorkflowStateEngine.complete_stage()`
	def _apply_complete_stage(self, state, stage, in_hashes, out_hashes, outputs, note):
		self.invalidate_caches()
		statuses = self.stage_statuses(state)
		preceding = STAGES[:STAGES.index(stage)]
		if any(('complete' != statuses[s] for s in preceding)):
			raise ValueError('Complete/check preceding stages before marking this stage complete')
		# 2026-10-15
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		if 'identity_init' == stage and (not self.registration_status()['complete']):
			raise ValueError('Complete native project/folder registration in the current platform/profile first')
		if 'research' == stage and (not questions_current(self.root, state)):
			raise ValueError('A research question is open or its inputs/results changed')
		# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
		from .project_drift import require_stage_project_valid
		if 'analysis' == stage:
			from .analysis import require_current_contract
			analysis_json = self.pp.kb_dir / 'Analysis.json'
			require_current_contract(json.loads(analysis_json.read_text(encoding='utf-8-sig')))
			# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
			require_stage_project_valid(self.root, check_project, 'Resolve project/evidence diagnostics before completing analysis')
			if self.pp.rel_to_root(analysis_json) not in out_hashes:
				raise ValueError('Analysis.json must be a declared stage output')
		if 'kb_review' == stage and (not note):
			raise ValueError('Record the result of the semantic KB consistency review')
		approval = None
		if stage in ('review', 'kb_review'):
			from .review import authorize
			approval = authorize(self.root, state)
			# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
			require_stage_project_valid(self.root, check_project, 'Current KB/evidence checks failed')
		elif 'finalize' == stage:
			# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
			require_stage_project_valid(self.root, check_project, 'Current KB/evidence checks failed')
			approval = self._finalize_stage(state, out_hashes, outputs)
		state['stages'][stage] = {'status': 'complete', 'time': now(), 'inputs': in_hashes, 'outputs': out_hashes, 'note': note}
		# 2026-10-15
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		if 'finalize' == stage:
			state['stages'][stage]['request_ids'] = [request['id'] for request in state['requests']]
		if 'research' == stage:
			from copy import deepcopy
			state['stages'][stage]['research_questions'] = deepcopy(state['questions'])
		if stage in ('review', 'kb_review', 'finalize'):
			self.invalidate_caches()
			state['stages'][stage]['review_approval'] = approval
			state['stages'][stage]['kb_inputs'] = self.kb_hashes()
			state['stages'][stage]['evidence_inputs'] = self.evidence_hashes()
		for dependent in STAGES[STAGES.index(stage) + 1:]:
			if dependent in state['stages']:
				state['stages'][dependent].update(status='stale', invalidated_by=stage)
	# @used-by :meth:`WorkflowStateEngine.resume()`
	def _apply_resume(self, state, request):
		from .upwork_data import normalize_job_id
		state['legacy'] = False
		if None is not request:
			state['requests'].append({'id': uuid.uuid4().hex, 'time': now(), 'text': request})
		pj = json.loads(self.pp.project_json.read_text(encoding='utf-8'))
		source = inside(self.root, pj['snapshot'])
		data = json.loads(source.read_text(encoding='utf-8'))
		if normalize_job_id(data.get('job_id')) != pj['job_id'] or not data.get('title') or (not data.get('description')):
			raise ValueError('Existing capture does not match this project')
		if re.fullmatch('[a-f0-9]{64}', source.stem) and file_hash(source) != source.stem:
			raise ValueError('Immutable capture hash differs')
		state['stages']['capture'] = {'status': 'complete', 'time': now(), 'inputs': {}, 'outputs': hashes(self.root, [pj['snapshot']]), 'method': 'verified saved capture'}
	# 2026-11-03
	# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
	# https://github.com/dmitry-ai/harness/issues/43
	# @used-by :meth:`WorkflowStateEngine.unadopt_requests()`
	def _apply_unadopt(self, state, conversation_id, req_ids):
		state['requests'] = [x for x in state.get('requests', []) if not ((conversation_id and x.get('native_conversation_id') == conversation_id) or (req_ids and x.get('id') in req_ids))]
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	def _finalize_stage(self, state, out_hashes, outputs):
		# 2026-11-26 "Harden follow-up launcher handoff and journal reservation integrity": https://github.com/dmitry-ai/harness/issues/269
		from .journal import journal_pair_dirs, resolve_journal_dir, step_file
		from .journal_integrity import validate_finalize_journal
		# 2026-11-25
		# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
		# https://github.com/dmitry-ai/harness/issues/230
		from .links import chat_reply_link_issues
		# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
		from .project_drift import require_no_domain_drift_for_finalize
		from .review import authorize
		# 2026-10-20
		# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
		# https://github.com/dmitry-ai/harness/issues/13
		from .text_workflow import gate_paths
		# 2026-10-19
		# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
		# https://github.com/dmitry-ai/harness/issues/12
		# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
		require_no_domain_drift_for_finalize(self.root)
		gate_paths([self.root / name for name in outputs])
		# 2026-10-23
		# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
		# https://github.com/dmitry-ai/harness/issues/16
		prepared = state['requests'][-1].get('response_prepared', {}) if state['requests'] else {}
		# 2026-11-13
		# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
		# https://github.com/dmitry-ai/harness/issues/57
		journal = resolve_journal_dir(self.root, prepared.get('journal'))
		# 2026-11-20
		# "Remove automatic Context.md generation from project initialization and finalize stage":
		# https://github.com/dmitry-ai/harness/issues/104
		# 2026-11-26 "Harden follow-up launcher handoff and journal reservation integrity": https://github.com/dmitry-ai/harness/issues/269
		ids = validate_finalize_journal(self.root, journal, state)
		# 2026-11-20
		# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
		# https://github.com/dmitry-ai/harness/issues/101
		req_dir, res_dir = journal_pair_dirs(journal)
		latest = max(ids)
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		reply = step_file(res_dir, latest, directory=journal)
		# 2026-11-23
		# "Prepend JSON metadata headers to new journal responses":
		# https://github.com/dmitry-ai/harness/issues/151
		from .metadata import strip_leading_metadata_header
		reply_body = strip_leading_metadata_header(reply.read_bytes().decode('utf-8'))
		link_issues = chat_reply_link_issues(reply_body)
		if link_issues:
			raise ValueError('\n'.join(link_issues))
		if reply.relative_to(self.root).as_posix() not in out_hashes:
			raise ValueError('Declare the actual final reply file as a finalize output')
		if state['requests'] and step_file(req_dir, latest, directory=journal).read_bytes().decode('utf-8') != state['requests'][-1]['text']:
			raise ValueError('Latest journal request differs from the recorded current continuation request')
		r = authorize(self.root, state, response=reply_body)
		if any((not request.get('response_prepared') for request in state['requests'])) or not state['requests'] or state['requests'][-1]['response_prepared'].get('sha256') != r['response_sha256']:
			raise ValueError('Record the exact approved answer for current requests before finalizing')
		return r
	# @used-by :func:`adopt_requests()`
	def adopt_requests(self, conversation_id, *, allow_finalized=False, backend=None, platform=None):
		from .journal import answer_groups, ensure_project_journal_upgraded, journal_pair_dirs, resolve_journal_dir, step_file
		from .metadata import strip_leading_metadata_header
		from .metrics import native_requests
		from .path_registry import project_paths
		state = self.load()
		# 2026-11-03
		# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
		# https://github.com/dmitry-ai/harness/issues/43
		if 'complete' == state.get('stages', {}).get('finalize', {}).get('status') and (not allow_finalized):
			raise ValueError('Initial analysis finalize stage is already complete. Post-finalize questions do not require adopt-requests unless explicitly reopening analysis with --allow-finalized')
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		ensure_project_journal_upgraded(self.root)
		self.pp = project_paths(self.root, exact_root=True)
		requests = native_requests(self.root, conversation_id, backend=backend, platform=platform)
		# 2026-11-13
		# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
		# https://github.com/dmitry-ai/harness/issues/57
		jdir = resolve_journal_dir(self.root)
		_, res_dir_a = journal_pair_dirs(jdir)
		saved_answers = {}
		# 2026-10-30
		# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
		# https://github.com/dmitry-ai/harness/issues/21
		for group in answer_groups(jdir, request_ids={x['id'] for x in requests}):
			# 2026-11-23
			# "Prepend JSON metadata headers to new journal responses":
			# https://github.com/dmitry-ai/harness/issues/151
			body_sha = group['response_sha256']
			if group.get('steps'):
				rp = step_file(res_dir_a, group['steps'][0], directory=jdir)
				if rp.is_file():
					try:
						body_sha = hashlib.sha256(strip_leading_metadata_header(rp.read_bytes().decode('utf-8')).encode('utf-8')).hexdigest()
					except (OSError, UnicodeDecodeError):
						pass
			for ident in group.get('request_ids') or []:
				saved_answers[ident] = {'turn': group['turn'], 'steps': group['steps'], 'sha256': body_sha}
		return update(self.root, {'action': 'adopt_requests', 'conversation_id': conversation_id}, lambda current: self._apply_adopt(current, requests, saved_answers))
	# 2026-10-21
	# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
	# https://github.com/dmitry-ai/harness/issues/14
	# @used-by :func:`complete_stage()`
	def complete_stage(self, stage, inputs, outputs, *, note=None):
		if stage not in STAGES or not inputs or (not outputs):
			raise ValueError('Known stage and explicit nonempty input/output artifacts required')
		# 2026-10-25
		# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
		# https://github.com/dmitry-ai/harness/issues/17
		if stage in ('identity_init', 'finalize'):
			reg = self.registration_status()
			if reg['required'] and (not reg['all_registered']):
				from .registration import register_projects
				register_projects(self.root, platform=reg['platform'], targets=[reg['platform'], *reg['pending_targets']])
				self._reg_cache = None
		in_hashes, out_hashes = (hashes(self.root, inputs), hashes(self.root, outputs))
		forbidden = {'ꘖ/data/workflow.json', 'ꘖ/data/rendered.json', 'ꘖ/KB/Progress.md', self.pp.rel_to_root(self.pp.workflow_json), self.pp.rel_to_root(self.pp.rendered_json), self.pp.rel_to_root(self.pp.kb_dir / 'Progress.md')}
		if set((*in_hashes, *out_hashes)) & forbidden:
			raise ValueError('Generated workflow/navigation state cannot serve as its own stage proof')
		return update(self.root, {'action': 'complete_stage', 'stage': stage}, lambda state: self._apply_complete_stage(state, stage, in_hashes, out_hashes, outputs, note))
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.receipt_current()`
	def evidence_hashes(self):
		if None is self._evidence_cache:
			self._evidence_cache = hashes(self.root, evidence_paths(self.root))
		return self._evidence_cache
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	def invalidate_caches(self):
		self._evidence_cache = None
		self._kb_cache = None
		self._reg_cache = None
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.receipt_current()`
	# @used-by :meth:`WorkflowStateEngine.status()`
	def kb_hashes(self):
		if None is self._kb_cache:
			self._kb_cache = hashes(self.root, kb_paths(self.root))
		return self._kb_cache
	# @used-by :func:`load()`
	# @used-by :meth:`WorkflowStateEngine.adopt_requests()`
	# @used-by :meth:`WorkflowStateEngine.record_current_answer()`
	# @used-by :meth:`WorkflowStateEngine.status()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def load(self):
		pj = self.pp.project_json
		if not pj.is_file():
			raise ValueError('Provide the existing project root from this chat; no project is selected or initialized implicitly')
		project = json.loads(pj.read_text(encoding='utf-8'))
		path = self.state_path()
		if not path.exists():
			r = {'schema_version': 1, 'project_root': str(self.root), 'job_id': project['job_id'], 'stages': {}, 'questions': {}, 'reviews': [], 'events': [], 'requests': [], 'legacy': True}
		else:
			# 2026-11-21
			# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
			# https://github.com/dmitry-ai/harness/issues/113
			from .path_registry import same_project_root
			state = json.loads(path.read_text(encoding='utf-8'))
			if 1 != state.get('schema_version') or (not same_project_root(state.get('project_root'), self.root)) or state.get('job_id') != project['job_id']:
				raise ValueError('Workflow identity/version mismatch; preserve the file for explicit migration')
			r = state
		return r
	# 2026-10-31
	# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
	# https://github.com/dmitry-ai/harness/issues/26
	# @used-by :func:`publish_progress()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	def publish_progress(self, state, *, statuses=None):
		# 2026-10-17
		# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
		# https://github.com/dmitry-ai/harness/issues/9
		from .links import markdown_link
		resolved_statuses = self.stage_statuses(state) if None is statuses else statuses
		lines = ['# Analysis Progress', '', 'Service navigation for the agent KB; statuses do not prove the truth of conclusions.', f"Job: {state['job_id']}.", '', '## Stages']
		lines += [f'- {stage}: {resolved_statuses[stage]}.' for stage in STAGES if 'finalize' != stage]
		lines += ['Verify completion and external export receipt with the status command.', '']
		# 2026-10-16
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		if self.pp.continuation_md.is_file():
			cont_rel = Path(os.path.relpath(self.pp.continuation_md, self.pp.kb_dir)).as_posix()
			lines += [f"Current post-analysis instruction: {markdown_link('continuation state', cont_rel)}.", '']
		lines += ['', '## Questions']
		for question in state['questions'].values():
			lines += [f"- {question['id']}: {question['question']}", f"  Status: {question['status']}; owner: {question.get('owner') or 'unassigned'}.", f"  Completion criterion: {question['done_when']}."]
			if question.get('gap'):
				lines.append('  Gap: ' + question['gap'])
			for ref in question.get('results', {}):
				target = inside(self.root, ref)
				relative = Path(os.path.relpath(target, self.pp.kb_dir)).as_posix()
				lines.append('  ' + markdown_link('Saved result', relative))
		lines += ['', '## Topical Modules']
		lines += ['- ' + markdown_link(p.name, p.name) for p in sorted(self.pp.kb_dir.glob('*.md')) if 'Progress.md' != p.name]
		lines += ['', 'Before new research, check the overview and topical KB modules.', 'Corrections propagate to linked claims and documents; anything unverified is marked explicitly.', 'Context.md is intended for handoff to an external agent, not for internal work.', '']
		# 2026-10-17
		# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
		# https://github.com/dmitry-ai/harness/issues/7
		return publish_owned(self.pp.kb_dir / 'Progress.md', '\n'.join(lines), source=self.state_path(), history=False)
	# 2026-11-21
	# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
	# https://github.com/dmitry-ai/harness/issues/109
	# @used-by :meth:`WorkflowStateEngine.receipt_current()`
	def _resolve_receipt_artifact(self, path: str) -> Path:
		target = inside(self.root, path)
		if not target.is_file():
			from .journal import resolve_migrated_step_file
			cand = resolve_migrated_step_file(target)
			if cand.is_file() and cand.is_relative_to(self.root):
				return cand
			# 2026-11-21
			# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
			# https://github.com/dmitry-ai/harness/issues/113
			v2_cand = {'\ua66e/0/Context.md': self.pp.context_output, 'KB/Project.md': self.pp.manual_kb_dir / 'Project.md', '.md': self.pp.path('readme_file', self.root / 'readme.md')}.get(Path(path).as_posix())
			if None is not v2_cand and v2_cand.is_file() and v2_cand.is_relative_to(self.root):
				return v2_cand
		return target
	# @used-by :func:`receipt_current()`
	# @used-by :meth:`ResearchQuestionRegistry.current()`
	# @used-by :meth:`WorkflowStateEngine.stage_statuses()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
	def receipt_current(self, receipt):
		return all(((t := self._resolve_receipt_artifact(path)).is_file() and file_hash(t) == digest for group in ('inputs', 'outputs') for path, digest in receipt.get(group, {}).items())) and ('kb_inputs' not in receipt or receipt['kb_inputs'] == self.kb_hashes()) and ('evidence_inputs' not in receipt or receipt['evidence_inputs'] == self.evidence_hashes())
	# 2026-10-23
	# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
	# https://github.com/dmitry-ai/harness/issues/16
	# 2026-10-30
	# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
	# https://github.com/dmitry-ai/harness/issues/21
	# 2026-11-14
	# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
	# https://github.com/dmitry-ai/harness/issues/60
	# @used-by :func:`record_current_answer()`
	def record_current_answer(self, response, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None):
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		from .journal import ensure_project_journal_upgraded, record_answer, resolve_journal_dir
		# 2026-11-25
		# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
		# https://github.com/dmitry-ai/harness/issues/230
		from .links import chat_reply_link_issues
		from .path_registry import project_paths
		from .review import authorize
		ensure_project_journal_upgraded(self.root, selected=journal_directory)
		self.pp = project_paths(self.root, exact_root=True)
		issues = chat_reply_link_issues(response)
		if issues:
			raise ValueError('\n'.join(issues))
		# 2026-10-19
		# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
		# https://github.com/dmitry-ai/harness/issues/12
		analysis_path = self.pp.kb_dir / 'Analysis.json'
		if analysis_path.is_file():
			try:
				analysis_val = json.loads(analysis_path.read_text(encoding='utf-8-sig'))
			except Exception:
				analysis_val = None
			if isinstance(analysis_val, dict) and [] == analysis_val.get('red_flags') and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', response):
				raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
		state = self.load()
		filter_ids = set(request_ids) if None is not request_ids else None
		auth_kw = {'response': response, **({'request_ids': filter_ids} if None is not filter_ids else {})}
		# 2026-10-18
		# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
		# https://github.com/dmitry-ai/harness/issues/10
		approval = authorize(self.root, state, **auth_kw) if None is preauthorized else preauthorized
		unanswered = [x for x in state['requests'] if not x.get('response_prepared') and (None is filter_ids or x['id'] in filter_ids)]
		if not unanswered:
			raise ValueError('No unrecorded current requests; import exact native inputs or save the current request first')
		# 2026-11-13
		# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
		# https://github.com/dmitry-ai/harness/issues/57
		directory = resolve_journal_dir(self.root, journal_directory)
		if None is not recorded_steps:
			turn = turn_token or unanswered[-1]['id']
			steps = list(recorded_steps)
		else:
			turn = turn_token or unanswered[-1]['id']
			# 2026-10-15
			# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
			# https://github.com/dmitry-ai/harness/issues/6
			if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn):
				turn = 'native-' + hashlib.sha256(turn.encode('utf-8')).hexdigest()
			steps = record_answer(directory, [x['text'] for x in unanswered], response, turn, [x['id'] for x in unanswered], admission_roots=[self.root, directory])
		ids = {x['id'] for x in unanswered}
		resp_sha = hashlib.sha256(response.encode()).hexdigest()
		result = update(self.root, {'action': 'reply_prepared', 'turn': turn, 'steps': steps}, lambda locked_state: self._apply_answer(locked_state, state, approval, auth_kw, ids, turn, steps, directory, resp_sha))
		return {**result, 'journal_steps': steps, 'delivery_verified': False}
	# 2026-10-15
	# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
	# https://github.com/dmitry-ai/harness/issues/6
	# 2026-10-25
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	# @used-by :func:`registration_status()`
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.stage_statuses()`
	# @used-by :meth:`WorkflowStateEngine.status()`
	def registration_status(self):
		if None is self._reg_cache:
			from .runtime import platform_active, platform_name, settings
			config, platform = (settings(), platform_name())
			path = self.pp.registrations_json
			required = path.exists() or self.root.is_relative_to(Path(config['workspace_root']) / config['daily_root'])
			data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
			receipt = data.get(platform) if isinstance(data, dict) else None
			# 2026-11-18
			# "Externalize agent environments and per-instance system paths into runtime.json":
			# https://github.com/dmitry-ai/harness/issues/86
			raw_targets = list(dict.fromkeys((config.get('registration') or {}).get('targets') or [platform]))
			targets = [target for target in raw_targets if platform_active(target, config=config) or target == platform]
			if platform not in targets:
				targets.insert(0, platform)
			targets_status = {}
			for target in targets:
				item = data.get(target) if isinstance(data, dict) else None
				done = not required or _target_complete(target, item)
				targets_status[target] = {'complete': done, 'status': (item.get('status') if isinstance(item, dict) else None) or ('registered' if done else 'pending'), 'attempts': item.get('attempts', 0) if isinstance(item, dict) else 0}
			pending_targets = [target for target, info in targets_status.items() if not info['complete']]
			self._reg_cache = {'platform': platform, 'required': required, 'complete': targets_status[platform]['complete'], 'all_registered': not pending_targets, 'targets': targets_status, 'pending_targets': pending_targets, 'receipt': receipt}
		return self._reg_cache
	# @used-by :func:`resume()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def resume(self, reason, request=None):
		if not isinstance(reason, str) or not reason.strip():
			raise ValueError('Record why the current analysis is being continued')
		if None is not request and (not isinstance(request, str) or not request.strip()):
			raise ValueError('Continuation request must preserve exact nonempty user text')
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		from .journal import ensure_project_journal_upgraded
		from .path_registry import project_paths
		ensure_project_journal_upgraded(self.root)
		self.pp = project_paths(self.root, exact_root=True)
		return update(self.root, {'action': 'resume', 'reason': reason}, lambda state: self._apply_resume(state, request))
	# @used-by :func:`stage_statuses()`
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`WorkflowStateEngine.publish_progress()`
	# @used-by :meth:`WorkflowStateEngine.status()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	def stage_statuses(self, state):
		r, dependency_ok = ({}, True)
		for stage in STAGES:
			receipt = state['stages'].get(stage)
			current = bool(receipt and 'complete' == receipt.get('status') and self.receipt_current(receipt))
			# 2026-10-15
			# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
			# https://github.com/dmitry-ai/harness/issues/6
			if 'identity_init' == stage:
				current = current and self.registration_status()['complete']
			if 'research' == stage and receipt:
				current = current and ResearchQuestionRegistry(self.root).current(state) and (receipt.get('research_questions') == state['questions'])
			# 2026-10-18
			# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
			# https://github.com/dmitry-ai/harness/issues/10
			if stage in ('review', 'kb_review', 'finalize') and current:
				from .review import approval_current
				current = approval_current(self.root, state, receipt.get('review_approval'))
			if 'finalize' == stage:
				covered = receipt.get('request_ids') if receipt else None
				current = current and (covered == [request['id'] for request in state['requests']] if None is not covered else all((request.get('response_prepared') for request in state['requests'])))
			r[stage] = 'complete' if current and dependency_ok else 'stale' if receipt else 'pending'
			dependency_ok = dependency_ok and current
		return r
	# @used-by :func:`state_path()`
	# @used-by :meth:`WorkflowStateEngine.load()`
	# @used-by :meth:`WorkflowStateEngine.publish_progress()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	def state_path(self):
		return self.pp.workflow_json
	# @used-by :func:`agent_tools.cli_domains._op_review_disposition()`
	# @used-by :func:`agent_tools.links.check_network()`
	# @used-by :func:`agent_tools.links.fetch_page()`
	# @used-by :func:`agent_tools.research.fetch()`
	# @used-by :func:`status()`
	# @used-by :meth:`WorkflowStateEngine.update()`
	def status(self, *, state=None, statuses=None):
		resolved_state = self.load() if None is state else state
		resolved_statuses = self.stage_statuses(resolved_state) if None is statuses else statuses
		existing = {name: (self.pp.kb_dir / name).is_file() for name in ('Analysis.json', 'Analysis.md', 'Progress.md')}
		# 2026-10-16
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		# 2026-11-21
		# "Initialize new Upwork projects in the V2 filesystem layout":
		# https://github.com/dmitry-ai/harness/issues/110
		prop_dirs = list(dict.fromkeys((d.resolve() for d in (self.pp.path('proposals_dir', self.root / 'result'), self.root / 'result') if d.is_dir() and d.resolve().is_relative_to(self.root))))
		prop_files = list({p.resolve(): p for d in prop_dirs for p in sorted(d.rglob('*.md'))}.values())
		proposals = [{'path': inside(self.root, path).relative_to(self.root).as_posix(), 'sha256': file_hash(inside(self.root, path))} for path in prop_files if path.is_file() and path.name in ('draft.md', 'final.md', 'draft.prev.md')]
		checkpoint = self.pp.continuation_md
		return {'project': str(self.root), 'job_id': resolved_state['job_id'], 'legacy': resolved_state['legacy'], 'stages': resolved_statuses, 'scope': 'initial_analysis', 'proposal_artifacts': proposals, 'continuation': {'file': self.pp.rel_to_root(checkpoint), 'exists': checkpoint.is_file()}, 'next_stage': next((s for s in STAGES if 'complete' != resolved_statuses[s]), None), 'agent_kb': str(self.pp.kb_dir), 'existing_drafts': existing, 'kb_hashes': self.kb_hashes(), 'questions': list(resolved_state['questions'].values()), 'registration': self.registration_status(), 'detail': 'Stages track saved analysis. Every new analytical reply requires current request/answer-bound approval. Continue the same filesystem project in either UI using agent KB, journal and actual proposal files; Context.md is an external export.'}
	# 2026-11-03
	# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
	# https://github.com/dmitry-ai/harness/issues/43
	# @used-by :func:`unadopt_requests()`
	def unadopt_requests(self, conversation_id=None, request_ids=None):
		req_ids = set(request_ids or [])
		if not conversation_id and (not req_ids):
			raise ValueError('Provide --conversation or at least one --request-id to unadopt')
		return update(self.root, {'action': 'unadopt_requests', 'conversation_id': conversation_id, 'request_ids': sorted(req_ids)}, lambda state: self._apply_unadopt(state, conversation_id, req_ids))
	# @used-by :func:`Df.Core.lib.array.other.unshift_assoc.dfa_unshift_assoc()`
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :func:`agent_tools.article.render()`
	# @used-by :func:`agent_tools.claims.extract_verified_inline_calc_numbers()`
	# @used-by :func:`agent_tools.claims.grounded_numbers_for_claim()`
	# @used-by :func:`agent_tools.claims.source_numeric_tokens()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.count_project_conversations()`
	# @used-by :func:`agent_tools.code_size_gate._add_override_decorator_lines()`
	# @used-by :func:`agent_tools.code_size_gate._collect_excluded_lines()`
	# @used-by :func:`agent_tools.code_size_gate._function_metrics()`
	# @used-by :func:`agent_tools.code_style_gate._scan_tokens()`
	# @used-by :func:`agent_tools.completion._instruction_snapshot()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :func:`agent_tools.evidence_loader._extract_bundle_html()`
	# @used-by :func:`agent_tools.grounding_domains._check_mem_tuples()`
	# @used-by :func:`agent_tools.grounding_helpers._assemble_corpus()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :func:`agent_tools.issues.workspace._update_turn_issue_entry()`
	# @used-by :func:`agent_tools.journal.get_existing_step_ids()`
	# @used-by :func:`agent_tools.journal.reserved_step_ids()`
	# @used-by :func:`agent_tools.journal_integrity._eligible_active_turn_keys()`
	# @used-by :func:`agent_tools.journal_integrity._group_steps_for_cid()`
	# @used-by :func:`agent_tools.journal_integrity.collect_conversation_journal_steps()`
	# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
	# @used-by :func:`agent_tools.landing_lease._enqueue_owner()`
	# @used-by :func:`agent_tools.landing_lease._try_acquire_once()`
	# @used-by :func:`agent_tools.native_profiles._execute()`
	# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
	# @used-by :func:`agent_tools.path_registry.clear_registry_cache()`
	# @used-by :func:`agent_tools.path_registry.derive_platform_system_paths()`
	# @used-by :func:`agent_tools.platforms.antigravity._apply_requested_config()`
	# @used-by :func:`agent_tools.platforms.antigravity._query_step_model_ids()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_executor_metadata()`
	# @used-by :func:`agent_tools.platforms.codex.native_executor_metadata()`
	# @used-by :func:`agent_tools.platforms.trace_common.summarize_turn_activity()`
	# @used-by :func:`agent_tools.project_labels.update_state_label()`
	# @used-by :func:`agent_tools.proposal.render()`
	# @used-by :func:`agent_tools.python_integrity._collect_defined_globals()`
	# @used-by :func:`agent_tools.registration._attempt()`
	# @used-by :func:`agent_tools.registration.save_registration()`
	# @used-by :func:`agent_tools.research._summarize_observation_bundle()`
	# @used-by :func:`agent_tools.research.collect_browser()`
	# @used-by :func:`agent_tools.research.collect_http()`
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :func:`agent_tools.runtime.extract_platform_instances()`
	# @used-by :func:`agent_tools.shadow_replay_command.stage_command_shadow_copies()`
	# @used-by :func:`agent_tools.shell_audit.extract_comment_issue_urls()`
	# @used-by :func:`agent_tools.stop_subagent_check._collect_invoke_outputs()`
	# @used-by :func:`agent_tools.stop_subagent_check._process_row_message()`
	# @used-by :func:`agent_tools.stop_subagent_check._record_invoke()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._changed_py_files()`
	# @used-by :func:`agent_tools.tdd.events._track_bg_command_outputs()`
	# @used-by :func:`agent_tools.tdd.exemption._verify_single_file_issue_urls()`
	# @used-by :func:`agent_tools.tdd.substantive._collect_repo_anchor_vars()`
	# @used-by :func:`agent_tools.text_browser._verify_context_anchor()`
	# @used-by :func:`agent_tools.text_browser.preflight()`
	# @used-by :func:`agent_tools.text_claims.primary_numbers()`
	# @used-by :func:`agent_tools.text_claims.validate_map()`
	# @used-by :func:`agent_tools.text_core.replay()`
	# @used-by :func:`agent_tools.text_review._source_reviews()`
	# @used-by :func:`agent_tools.text_sources.save_source_check()`
	# @used-by :func:`agent_tools.text_sources.validate_source_checks()`
	# @used-by :func:`agent_tools.worktree_flow._enrich_worktree_entry()`
	# @used-by :func:`agent_tools.worktree_flow._push_and_finish_land()`
	# @used-by :func:`agent_tools.xref.java_graph._scan_plugin_xml_classes()`
	# @used-by :func:`agent_tools.xref.java_sync._expected_java_used_by()`
	# @used-by :func:`agent_tools.xref.js_sync._expected_js_used_by()`
	# @used-by :func:`agent_tools.xref.python_sync._expected_used_by_lines()`
	# @used-by :func:`test_evidence_contract.v3_analysis()`
	# @used-by :func:`test_issue_close_acceptance._run_close_cli()`
	# @used-by :func:`test_stop_emergency_capture_and_foreign_sync._reserve_foreign()`
	# @used-by :func:`test_text_browser.dom_fixture()`
	# @used-by :func:`update()`
	# @used-by :meth:`ResearchQuestionRegistry._apply_claim()`
	# @used-by :meth:`ResearchQuestionRegistry._apply_finish()`
	# @used-by :meth:`ResearchQuestionRegistry._apply_handoff()`
	# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_structure()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._inherited()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._load_direct_evidence()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._inspect_candidate()`
	# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._fail_gate()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._collector_artifact()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._ingest_artifacts_and_trace()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.capabilities()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.evaluate_assertions()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate._extract_added_diff_urls()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_latest_commits()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.extract_unlinked_m_subtasks()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._build_mutation_success_payload()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._build_issue_record()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.__init__()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._record_tool_calls()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._evaluate_claim_risk()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approved_claim_digests()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._populate_source_metadata()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.scope_issues()`
	# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_anchored_quote_from_another_section_is_rejected()`
	# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_existing_heading_or_ancestor_anchor_is_required()`
	# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
	# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
	# @used-by :meth:`test_cleanup.CleanupTests.control()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_new_chat_restores_a_partially_held_codex_project()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests._make_project()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_claim_graph_validator_memoizes_diamond_dag_and_dns_cache()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.price_analysis()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.signed_price_analysis()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_critical_severity_needs_impact_evidence()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e5_and_e6_html_sitemap_and_site_summary_diagnostics()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_explicit_text_locator_does_not_cover_another_part_of_page()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_full_real_intake_receipt_binds_source_to_snapshot_and_rejects_relabelled_note()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_misconception_hypothesis_requires_alternatives_and_discriminating_check()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_own_prya_kb_note_in_evidence_is_not_a_primary_observation()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_referenced_primary_cannot_be_replaced_with_an_own_kb_quote()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unavailable_result_is_valid_with_explicit_gap()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
	# @used-by :meth:`test_experiments.ExperimentTests.browser_requirement()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_actual_exec_wrapper_with_nested_shell_plan_receipt_is_supported()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_amended_expectation_requires_new_observation_and_retains_original()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_context_or_session_difference_is_rejected_even_for_same_tab_ids()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_egress_must_be_measured_in_the_actual_action_browser_context()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_missing_native_identity_cannot_be_repaired_by_declared_session()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_native_before_and_action_in_different_browser_tabs_are_rejected()`
	# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_and_consume_input_with_readback_verification()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unrelated_review_entry_does_not_reapprove_or_invalidate_history()`
	# @used-by :meth:`test_issue_first_github_cli.IssueFirstGitHubCliTests.test_create_parent_issue_blocked_on_dirty_tree_while_open_parent_child_create_allowed()`
	# @used-by :meth:`test_onboarding.EvidenceTests.test_missing_counterevidence_probability_or_documentation_anchor_is_rejected()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_portability.CodexEvidenceTests.test_parent_can_select_another_model_and_effort_with_native_proof()`
	# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
	# @used-by :meth:`test_readable_links.ReadableProjectTests.test_analysis_sources_are_readable_while_quotes_keep_their_exact_bytes()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_unknown_duplicate_and_unsupported_basis_cannot_be_published()`
	# @used-by :meth:`test_registration_portability.RegistrationProfileTests.setUp()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_audit_target_must_equal_the_analysis_claim_and_irrelevant_test_is_unsupported()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_causal_property_forces_significant_even_when_labeled_descriptive_routine()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_e8_causes_misconceptions_and_methods_cannot_be_downgraded_or_omitted_in_routine_review()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_empty_manifest_package_cannot_pass_record_review()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_routine_package_cannot_bypass_computed_risk()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_official_distributor_is_not_established_by_contains_lunos_proxy()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_per_claim_audit_is_required_and_qualified_gap_can_pass()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_restatement_is_routine_only_after_two_approved_exact_versions_and_no_new_evidence()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_review_package_rejects_ungrounded_numbers_in_response_excerpt_and_reviewer_report()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_task_flags_cannot_omit_typed_work_or_silently_default()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m1_heading_band_wrapper_child_sentinel_and_github_user_content_anchors()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m3_passive_cloudflare_jsd_script_is_admitted_while_real_interstitial_is_blocked()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_old_current_sources_expire_but_explicit_historical_editions_are_distinct()`
	# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_ag2_conversation_id_without_session_id_enforces_stop_gate()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_dynamic_antigravity_port_read_each_time_without_launch()`
	# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.dependent_registry()`
	# @used-by :meth:`test_text_workflow.TextWorkspaceCase.start()`
	def update(self, event, change):
		with locked(self.pp.data_dir / 'workflow.lock'):
			state = self.load()
			# 2026-11-21
			# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
			# https://github.com/dmitry-ai/harness/issues/113
			state['project_root'] = str(self.root)
			change(state)
			state['events'].append({'id': uuid.uuid4().hex, 'time': now(), **event})
			replace_bytes(self.state_path(), json_data(state))
			self.invalidate_caches()
			statuses = self.stage_statuses(state)
			progress = self.publish_progress(state, statuses=statuses)
			snap = self.status(state=state, statuses=statuses)
		return {'workflow': str(self.state_path()), 'progress': progress, **snap}
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.record()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :meth:`ResearchQuestionRegistry._apply_add()`
# @used-by :meth:`ResearchQuestionRegistry._apply_search()`
# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
# @used-by :meth:`WorkflowStateEngine._apply_resume()`
# @used-by :meth:`WorkflowStateEngine.update()`
def now():
	return datetime.now(timezone.utc).isoformat(timespec='seconds')
# @used-by :func:`agent_tools.review.input_receipt()`
# @used-by :func:`hashes()`
# @used-by :meth:`WorkflowStateEngine._apply_resume()`
# @used-by :meth:`WorkflowStateEngine.receipt_current()`
# @used-by :meth:`WorkflowStateEngine.status()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
def file_hash(path):
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :func:`agent_tools.review.record()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :meth:`ResearchQuestionRegistry._apply_finish()`
# @used-by :meth:`ResearchQuestionRegistry.add()`
# @used-by :meth:`WorkflowStateEngine._apply_resume()`
# @used-by :meth:`WorkflowStateEngine.complete_stage()`
# @used-by :meth:`WorkflowStateEngine.evidence_hashes()`
# @used-by :meth:`WorkflowStateEngine.kb_hashes()`
# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approved_claim_digests()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
def hashes(root, paths):
	r = {}
	resolved = Path(root).resolve()
	for path in paths:
		target = inside(resolved, path)
		if not target.is_file():
			raise FileNotFoundError(f'Missing stage artifact: {path}')
		r[target.relative_to(resolved).as_posix()] = file_hash(target)
	return r
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :meth:`ProjectHealthAuditor.kb_issues()`
# @used-by :meth:`WorkflowStateEngine.kb_hashes()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
def kb_paths(root):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	kb = pp.kb_dir
	ev = pp.evidence_dir
	if not kb.is_dir():
		return []
	return [p.relative_to(pp.root).as_posix() for p in sorted(kb.rglob('*')) if p.is_file() and (p.suffix.lower() in ('.md', '.json') or '.md' == p.name) and ('Progress.md' != p.name) and (not p.is_relative_to(ev))]
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :meth:`WorkflowStateEngine.evidence_hashes()`
# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approved_claim_digests()`
def evidence_paths(root):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	resolved = pp.root
	evidence = pp.evidence_dir
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	dirs = [d for d in (evidence, pp.manual_kb_dir, pp.source_dir) if d.is_dir() and d.resolve().is_relative_to(resolved)]
	return sorted({p.relative_to(resolved).as_posix() for directory in dirs for p in directory.rglob('*') if p.is_file() and (not p.is_relative_to(evidence / 'Reviews'))})
# @used-by unused
def question_contract_issues(root, question):
	return ResearchQuestionRegistry(root).contract_issues(question)
# @used-by :func:`agent_tools.review.authorize()`
# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap()`
def questions_current(root, state):
	return ResearchQuestionRegistry(root).current(state)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
def state_path(root):
	return WorkflowStateEngine(root).state_path()
# @used-by :func:`agent_tools.blocked_report._standard_workflow_errors()`
# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
# @used-by :func:`agent_tools.completion._workflow_gate_resolved()`
# @used-by :func:`agent_tools.metrics.project_metrics()`
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :func:`agent_tools.review.record()`
# @used-by :func:`agent_tools.shadow_replay._run_finalize_stage()`
# @used-by :func:`agent_tools.shadow_replay._run_review_stage()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._audit_workflow_scope()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_resume_uses_existing_capture_and_agent_kb_without_reading_context()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_render_analysis_promote_domain_preserves_finalized_invariants()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_self_review_uses_codex_parent_evidence_without_requiring_antigravity()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_progress_is_replaced_without_archiving_derived_navigation()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.authorize()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_legacy_review_and_analysis_cannot_authorize_new_answer()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_needs_changes_and_open_findings_persist_and_parent_disposition_cannot_approve()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_original_report_proof_is_immutable_when_input_filename_is_reused()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_parent_cannot_replace_authored_needs_changes_with_an_approved_json()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_relabeling_same_answer_cannot_hide_an_independent_rejection()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_routine_fact_approves_and_exact_answer_is_recorded()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_significant_self_finding_requires_two_independent_authored_followups()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_classifier_has_significant_flags_and_post_finalize_synthetic_claims()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_tracked_prepare_preserves_finalizer_receipt_without_duplicate_pair()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
def load(root):
	return WorkflowStateEngine(root).load()
# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.entry_proof_current()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_review_package_pins_primary_evidence_and_unquoted_new_contradiction()`
def receipt_current(root, receipt):
	return WorkflowStateEngine(root).receipt_current(receipt)
# 2026-10-25
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# @used-by :meth:`WorkflowStateEngine.registration_status()`
def _target_complete(target, item):
	from .runtime import profile_name, registration_profile_name
	if not isinstance(item, dict):
		r = False
	elif not isinstance(item.get('profiles'), dict):
		r = bool(item.get('complete', item.get('project_id') and item.get('folder_id')))
	else:
		# 2026-11-18
		# "Externalize agent environments and per-instance system paths into runtime.json":
		# https://github.com/dmitry-ai/harness/issues/86
		if 'codex' == target and 'CODEX_HOME' in os.environ:
			prof = profile_name()
		else:
			prof = item.get('profile')
			if not prof and 'codex' == target:
				try:
					prof = registration_profile_name()
				except ValueError:
					prof = None
		r = bool(prof and item['profiles'].get(prof, {}).get('ready'))
	return r
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_workflow_registration_status_exposes_all_targets_and_pending_targets()`
def registration_status(root):
	return WorkflowStateEngine(root).registration_status()
# @used-by :func:`agent_tools.metrics.project_metrics()`
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_render_analysis_promote_domain_preserves_finalized_invariants()`
def stage_statuses(root, state):
	return WorkflowStateEngine(root).stage_statuses(state)
# @used-by :func:`agent_tools.cli_domains._op_status()`
# @used-by :func:`record_review_disposition()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_file_presence_does_not_complete_analysis_or_review()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_legacy_review_and_analysis_cannot_authorize_new_answer()`
def status(root, *, state=None, statuses=None):
	return WorkflowStateEngine(root).status(state=state, statuses=statuses)
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_progress_is_replaced_without_archiving_derived_navigation()`
def publish_progress(root, state, *, statuses=None):
	return WorkflowStateEngine(root).publish_progress(state, statuses=statuses)
# @used-by :func:`agent_tools.blocked_report.sync_authorized_workflow_requests()`
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.record()`
# @used-by :meth:`ResearchQuestionRegistry.add()`
# @used-by :meth:`ResearchQuestionRegistry.claim()`
# @used-by :meth:`ResearchQuestionRegistry.finish()`
# @used-by :meth:`ResearchQuestionRegistry.handoff()`
# @used-by :meth:`ResearchQuestionRegistry.record_search()`
# @used-by :meth:`WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`WorkflowStateEngine.complete_stage()`
# @used-by :meth:`WorkflowStateEngine.record_current_answer()`
# @used-by :meth:`WorkflowStateEngine.resume()`
# @used-by :meth:`WorkflowStateEngine.unadopt_requests()`
# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._authorize_and_sync_workflow()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
def update(root, event, change):
	return WorkflowStateEngine(root).update(event, change)
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.cli_domains._op_resume()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_file_presence_does_not_complete_analysis_or_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_resume_uses_existing_capture_and_agent_kb_without_reading_context()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.setUp()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.setUp()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.setUp()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.setUp()`
def resume(root, reason, request=None):
	return WorkflowStateEngine(root).resume(reason, request=request)
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-03
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
# @used-by :func:`agent_tools.cli_domains._op_adopt_requests()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.setUp()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_and_unadopt_requests_lifecycle()`
def adopt_requests(root, conversation_id, *, allow_finalized=False, backend=None, platform=None):
	return WorkflowStateEngine(root).adopt_requests(conversation_id, allow_finalized=allow_finalized, backend=backend, platform=platform)
# 2026-11-03
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
# @used-by :func:`agent_tools.cli_domains._op_unadopt_requests()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_and_unadopt_requests_lifecycle()`
def unadopt_requests(root, conversation_id=None, request_ids=None):
	return WorkflowStateEngine(root).unadopt_requests(conversation_id=conversation_id, request_ids=request_ids)
# 2026-10-19
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :meth:`ProjectHealthAuditor.kb_issues()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_doc4_scanner_supports_hook_and_workflow_modes()`
def doc4_sentence_issues(text):
	from .hook_runtime import scan_doc4_sentence_issues
	return scan_doc4_sentence_issues(text, mode='workflow')
# @used-by :func:`agent_tools.blocked_report.sync_authorized_workflow_requests()`
# @used-by :func:`agent_tools.cli_domains._op_record_answer()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_record_answer_blocks_encoded_authored_links_before_any_journal_mutation()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_routine_fact_approves_and_exact_answer_is_recorded()`
def record_current_answer(root, response, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None):
	return WorkflowStateEngine(root).record_current_answer(response, journal_directory=journal_directory, request_ids=request_ids, preauthorized=preauthorized, recorded_steps=recorded_steps, turn_token=turn_token)
# @used-by :func:`agent_tools.cli_domains._op_question_add()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
def add_question(root, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
	return ResearchQuestionRegistry(root).add(ident, question, impact, done_when, inputs, outputs, requirements=requirements)
# @used-by :func:`agent_tools.cli_domains._op_question_claim()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
def claim_question(root, ident, owner):
	return ResearchQuestionRegistry(root).claim(ident, owner)
# @used-by :func:`agent_tools.cli_domains._op_question_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
def handoff(root, ident, previous_owner, new_owner, reason):
	return ResearchQuestionRegistry(root).handoff(ident, previous_owner, new_owner, reason)
# @used-by :func:`agent_tools.cli_domains._op_question_search()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
def record_search(root, ident, owner, query, useful=False, method_change=None):
	return ResearchQuestionRegistry(root).record_search(ident, owner, query, useful=useful, method_change=method_change)
# @used-by :func:`agent_tools.cli_domains._op_question_finish()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
def finish_question(root, ident, owner, outputs, gap=None, *, results=None):
	return ResearchQuestionRegistry(root).finish(ident, owner, outputs, gap=gap, results=results)
# @used-by :meth:`ProjectHealthAuditor.check_project()`
def kb_issues(root):
	return ProjectHealthAuditor(root).kb_issues()
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# @used-by :meth:`ProjectHealthAuditor.check_project()`
# @used-by :meth:`test_onboarding.AttachmentTests.test_docx_and_text_attachments_saved_in_source_and_both_kbs()`
def attachment_issues(root):
	return ProjectHealthAuditor(root).attachment_issues()
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
# @used-by :func:`agent_tools.cli_domains._op_check_project()`
# @used-by :func:`agent_tools.review.authorize()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`WorkflowStateEngine._apply_complete_stage()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_html_links_json_summary_non_destructive_collect_and_scratch_cleanliness()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_new_analysis_cannot_finish_with_an_unpublished_website_card()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_project_check_covers_agent_kb_and_client_markdown_text_and_html()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_review_package_pins_primary_evidence_and_unquoted_new_contradiction()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_e12_check_project_flags_unsynced_client_identity_in_kb_project_md()`
def check_project(root, *, prevalidated_analysis=None):
	return ProjectHealthAuditor(root).check_project(prevalidated_analysis=prevalidated_analysis)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`agent_tools.cli_domains._op_record_review()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._authorize_routine_reply()`
# @used-by :func:`test_contract_invariants._authorize_routine()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests._native_record()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_self_review_uses_codex_parent_evidence_without_requiring_antigravity()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.native_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.self_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_audit_must_explain_falsifiability_and_compare_raw_criteria()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_empty_manifest_package_cannot_pass_record_review()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_official_distributor_is_not_established_by_contains_lunos_proxy()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_original_report_proof_is_immutable_when_input_filename_is_reused()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_per_claim_audit_is_required_and_qualified_gap_can_pass()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
def record_review(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .review import record
	return record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role, native_evidence=native_evidence, risk=risk)
# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._authorize_routine_reply()`
# @used-by :func:`test_contract_invariants._authorize_routine()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_missing_risk_basis_or_manifest_is_rejected()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_relabeling_same_answer_cannot_hide_an_independent_rejection()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_task_flags_cannot_omit_typed_work_or_silently_default()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_report_validator_covers_falsifier_and_text_checks()`
def prepare_review(root, parent_id, spec=None, response=None):
	from .review import prepare
	return prepare(root, parent_id, spec, response)
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`agent_tools.cli_domains._op_review_input()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.setUp()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
# @used-by :meth:`test_portability.CodexEvidenceTests.set_review_input()`
def review_input(root, package):
	from .review import input_receipt
	return input_receipt(root, package)
# @used-by :func:`agent_tools.cli_domains._op_review_disposition()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_needs_changes_and_open_findings_persist_and_parent_disposition_cannot_approve()`
def record_review_disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	from .review import disposition
	return disposition(root, review_id, finding_id, status, basis, evidence, parent_id)
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.cli_domains._op_stage()`
# @used-by :func:`agent_tools.shadow_replay._execute_finalize_reply()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
def complete_stage(root, stage, inputs, outputs, *, note=None):
	return WorkflowStateEngine(root).complete_stage(stage, inputs, outputs, note=note)
