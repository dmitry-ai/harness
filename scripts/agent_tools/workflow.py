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
	def _kb_targets(self):
		r = []
		for target in (self.pp.manual_kb_dir / 'Project.md', self.pp.kb_dir / 'Project.md', self.pp.kb_dir / 'Projects.md'):
			label = self.pp.rel_to_root(target)
			r.append((label, target, target.read_text(encoding='utf-8') if target.is_file() else ''))
		return tuple(r)
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
	def __init__(self, root):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
	def _apply_add(self, state, ident, entry):
		if ident in state['questions']:
			raise ValueError('Question already exists; use its saved inputs/results')
		# 2026-11-04
		# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
		# https://github.com/dmitry-ai/harness/issues/44
		state['questions'][ident] = {**entry, 'time': now()}
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
	def _apply_handoff(self, state, ident, previous_owner, new_owner, reason):
		q = state['questions'][ident]
		if q['owner'] != previous_owner or 'running' != q['status']:
			raise ValueError('Task owner/status changed; refresh native progress before handoff')
		q.update(owner=new_owner, handoff_reason=reason)
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
	def claim(self, ident, owner):
		if not isinstance(owner, str) or not owner.strip():
			raise ValueError('Owner must be an observed session/subagent ID')
		return update(self.root, {'action': 'claim_question', 'question_id': ident, 'owner': owner}, lambda state: self._apply_claim(state, ident, owner))
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
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
	def current(self, state):
		engine = WorkflowStateEngine(self.root)
		return all((q['status'] in ('complete', 'gap') and engine.receipt_current({'inputs': q['inputs'], 'outputs': q['results']}) and (not self.contract_issues(q)) for q in state['questions'].values()))
	def finish(self, ident, owner, outputs, gap=None, *, results=None):
		return update(self.root, {'action': 'finish_question', 'question_id': ident}, lambda state: self._apply_finish(state, ident, owner, outputs, gap, results))
	def handoff(self, ident, previous_owner, new_owner, reason):
		if not all((isinstance(s, str) and s.strip() for s in (previous_owner, new_owner, reason))):
			raise ValueError('Explicit previous owner, new owner and observed stopping reason required')
		return update(self.root, {'action': 'handoff', 'question_id': ident, 'reason': reason}, lambda state: self._apply_handoff(state, ident, previous_owner, new_owner, reason))
	def record_search(self, ident, owner, query, useful=False, method_change=None):
		if not isinstance(query, str) or not query.strip():
			raise ValueError('Search query required')
		return update(self.root, {'action': 'search', 'question_id': ident}, lambda state: self._apply_search(state, ident, owner, query, useful, method_change))
# 2026-11-14
# "Decompose workflow.py and knowledge.py into WorkflowStateEngine, ResearchQuestionRegistry, and ProjectHealthAuditor with shared attachment inventory":
# https://github.com/dmitry-ai/harness/issues/74
class WorkflowStateEngine:
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
	def _apply_answer(self, locked_state, initial_state, approval, auth_kw, ids, turn, steps, directory, resp_sha):
		from .review import authorize
		if locked_state != initial_state:
			authorize(self.root, locked_state, package_path=approval['package'], **auth_kw)
		for request in locked_state['requests']:
			if request['id'] in ids:
				request['response_prepared'] = {'turn': turn, 'steps': steps, 'journal': str(directory), 'sha256': resp_sha, 'review_approval': approval}
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
	def _apply_unadopt(self, state, conversation_id, req_ids):
		state['requests'] = [x for x in state.get('requests', []) if not ((conversation_id and x.get('native_conversation_id') == conversation_id) or (req_ids and x.get('id') in req_ids))]
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
	def evidence_hashes(self):
		if None is self._evidence_cache:
			self._evidence_cache = hashes(self.root, evidence_paths(self.root))
		return self._evidence_cache
	def invalidate_caches(self):
		self._evidence_cache = None
		self._kb_cache = None
		self._reg_cache = None
	def kb_hashes(self):
		if None is self._kb_cache:
			self._kb_cache = hashes(self.root, kb_paths(self.root))
		return self._kb_cache
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
	def state_path(self):
		return self.pp.workflow_json
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
	def unadopt_requests(self, conversation_id=None, request_ids=None):
		req_ids = set(request_ids or [])
		if not conversation_id and (not req_ids):
			raise ValueError('Provide --conversation or at least one --request-id to unadopt')
		return update(self.root, {'action': 'unadopt_requests', 'conversation_id': conversation_id, 'request_ids': sorted(req_ids)}, lambda state: self._apply_unadopt(state, conversation_id, req_ids))
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
def now():
	return datetime.now(timezone.utc).isoformat(timespec='seconds')
def file_hash(path):
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(root, paths):
	r = {}
	resolved = Path(root).resolve()
	for path in paths:
		target = inside(resolved, path)
		if not target.is_file():
			raise FileNotFoundError(f'Missing stage artifact: {path}')
		r[target.relative_to(resolved).as_posix()] = file_hash(target)
	return r
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
def question_contract_issues(root, question):
	return ResearchQuestionRegistry(root).contract_issues(question)
def questions_current(root, state):
	return ResearchQuestionRegistry(root).current(state)
def state_path(root):
	return WorkflowStateEngine(root).state_path()
def load(root):
	return WorkflowStateEngine(root).load()
def receipt_current(root, receipt):
	return WorkflowStateEngine(root).receipt_current(receipt)
# 2026-10-25
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
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
def registration_status(root):
	return WorkflowStateEngine(root).registration_status()
def stage_statuses(root, state):
	return WorkflowStateEngine(root).stage_statuses(state)
def status(root, *, state=None, statuses=None):
	return WorkflowStateEngine(root).status(state=state, statuses=statuses)
def publish_progress(root, state, *, statuses=None):
	return WorkflowStateEngine(root).publish_progress(state, statuses=statuses)
def update(root, event, change):
	return WorkflowStateEngine(root).update(event, change)
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def resume(root, reason, request=None):
	return WorkflowStateEngine(root).resume(reason, request=request)
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-03
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
def adopt_requests(root, conversation_id, *, allow_finalized=False, backend=None, platform=None):
	return WorkflowStateEngine(root).adopt_requests(conversation_id, allow_finalized=allow_finalized, backend=backend, platform=platform)
# 2026-11-03
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
def unadopt_requests(root, conversation_id=None, request_ids=None):
	return WorkflowStateEngine(root).unadopt_requests(conversation_id=conversation_id, request_ids=request_ids)
# 2026-10-19
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def doc4_sentence_issues(text):
	from .hook_runtime import scan_doc4_sentence_issues
	return scan_doc4_sentence_issues(text, mode='workflow')
def record_current_answer(root, response, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None):
	return WorkflowStateEngine(root).record_current_answer(response, journal_directory=journal_directory, request_ids=request_ids, preauthorized=preauthorized, recorded_steps=recorded_steps, turn_token=turn_token)
def add_question(root, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
	return ResearchQuestionRegistry(root).add(ident, question, impact, done_when, inputs, outputs, requirements=requirements)
def claim_question(root, ident, owner):
	return ResearchQuestionRegistry(root).claim(ident, owner)
def handoff(root, ident, previous_owner, new_owner, reason):
	return ResearchQuestionRegistry(root).handoff(ident, previous_owner, new_owner, reason)
def record_search(root, ident, owner, query, useful=False, method_change=None):
	return ResearchQuestionRegistry(root).record_search(ident, owner, query, useful=useful, method_change=method_change)
def finish_question(root, ident, owner, outputs, gap=None, *, results=None):
	return ResearchQuestionRegistry(root).finish(ident, owner, outputs, gap=gap, results=results)
def kb_issues(root):
	return ProjectHealthAuditor(root).kb_issues()
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
def attachment_issues(root):
	return ProjectHealthAuditor(root).attachment_issues()
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
def check_project(root, *, prevalidated_analysis=None):
	return ProjectHealthAuditor(root).check_project(prevalidated_analysis=prevalidated_analysis)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def record_review(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .review import record
	return record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role, native_evidence=native_evidence, risk=risk)
def prepare_review(root, parent_id, spec=None, response=None):
	from .review import prepare
	return prepare(root, parent_id, spec, response)
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def review_input(root, package):
	from .review import input_receipt
	return input_receipt(root, package)
def record_review_disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	from .review import disposition
	return disposition(root, review_id, finding_id, status, basis, evidence, parent_id)
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def complete_stage(root, stage, inputs, outputs, *, note=None):
	return WorkflowStateEngine(root).complete_stage(stage, inputs, outputs, note=note)
