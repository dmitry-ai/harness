# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ResponseEvidenceAuditor class into response_grounding.py from response_source_and_kb_issues and helpers in completion.py":
# https://github.com/dmitry-ai/harness/issues/56
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce local_source_grounding_issues across touched client deliverables, require post-compaction re-read of evicted tool outputs, and close A.A review bypass":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate turn scratch answer files, decouple turn/journal locks, allow pre-delivery re-preparation, and add preemptive step/compaction budget gate":
# https://github.com/dmitry-ai/harness/issues/49
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce typed source provenance tiers (Tier 0/1/2), entity Tier 0 auto-discovery, and post-CHECKPOINT re-read gates":
# https://github.com/dmitry-ai/harness/issues/45
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
# https://github.com/dmitry-ai/harness/issues/30
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from . import journal
from .issue_lifecycle import code_and_issue_lifecycle_status as _code_and_issue_lifecycle_status, evidence_issue_files as _evidence_issue_files, evidence_issue_state as _evidence_issue_state, origin_repo_slug as _origin_repo_slug
from .platforms import adapter
from .response_grounding import ResponseEvidenceAuditor, response_source_and_kb_issues
from .runtime import PRIMARY, platform_name, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
COMMANDS = ('turn-begin', 'answer-prepare', 'recover-checkpoint', 'recover-turn-violation', 'journal-sync', 'journal-watch', 'journal-unwatch', 'reconcile-unprepared-delivery')
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'), 'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'), 'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}
RULE_REQUIREMENTS = {'FILE-3': 'Before publication, the primary agent saves the exact request and complete final response via answer-prepare.', 'EXEC-5': 'Run read-only Git checks with `--no-optional-locks` to avoid updating the index as a side effect.', 'DOC-2': 'Frame any unknown or unproven explanation as a hypothesis with arguments for/against and an expert score in %.'}
class AnswerPreparationRunner:
	def __init__(self, root, response, result, native, turn):
		self.root = root
		self.response = response
		self.sha = _hash(response.encode('utf-8'))
		self.result = result
		self.native = native
		self.turn = turn
		self.path, self.value = _state(root, native, turn)
		self.allow_reprepare = False
		self.workflow_path = root / '\ua616/data/workflow.json'
		self.wf_state = None
		self.wf_identifiers = set()
		self.wf_covered = set()
		self.is_finalized = False
		self.has_substantive_hm = False
		self.admission_check = None
	def _audit_workflow_scope(self):
		if self.workflow_path.exists():
			from .workflow import load
			self.wf_state = load(self.root)
			self.wf_identifiers = {req['id'] for req in self.turn['requests']}
			self.wf_covered = {req['id'] for req in self.wf_state['requests']} & self.wf_identifiers
			self.is_finalized = 'complete' == self.wf_state.get('stages', {}).get('finalize', {}).get('status')
			kb_scan = _factual_kb_note_issues(self.root, self.turn)
			if kb_scan['issues']:
				self._fail_gate('factual_kb_note', 'KB-2 / DOC-1 violation in factual research note: ' + '; '.join(kb_scan['issues']))
			has_kb_or_issue_mutation = kb_scan['has_normative'] or bool(self.turn.get('issue_actions')) or bool(self.value.get('github_issues'))
			touches_client_deliverable = any((any((seg in str(tf).replace('\\', '/').lower() for seg in ('/letters/', '/result/', '/defects/'))) and '/\ua616/' not in str(tf).replace('\\', '/').lower() for tf in (self.turn.get('touched_files') or [])))
			has_hm_tags = bool(re.search('\\b(?:H|M)-(?:[A-Za-z0-9]+-)*\\d+\\b', self.response))
			if self.is_finalized:
				self.has_substantive_hm = kb_scan['has_analysis'] or (has_hm_tags and 0 == self.value['delegation_check'].get('aa_subagent_step_count', 0))
			else:
				self.has_substantive_hm = has_hm_tags or has_kb_or_issue_mutation or touches_client_deliverable
			if self.wf_covered and self.wf_covered != self.wf_identifiers:
				raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
			if not self.wf_covered and (self.root / '\ua616/project.json').is_file() and (not any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', req.get('text', '')) for req in self.turn['requests']))) and (not self.is_finalized or self.has_substantive_hm):
				self._fail_gate('workflow_adoption', 'REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project')
	def _authorize_and_sync_workflow(self):
		if None is not self.wf_state and self.wf_covered:
			if self.is_finalized and (not self.has_substantive_hm):
				from .workflow import update
				def change(s):
					for req in s.get('requests', []):
						if req['id'] in self.wf_identifiers and (not req.get('response_prepared') or self.allow_reprepare):
							req['response_prepared'] = {'sha256': self.sha, 'prepared_at': _now()}
				update(self.root, {'action': 'post_finalize_answer', 'request_ids': sorted(self.wf_identifiers)}, change)
			else:
				from .review import authorize
				try:
					authorize(self.root, self.wf_state, response=self.response, request_ids=self.wf_identifiers)
				except (OSError, ValueError) as exc:
					self._fail_gate('review_authorize', str(exc), cause=exc)
				pending = {req['id'] for req in self.wf_state['requests'] if not req.get('response_prepared') and (req.get('native_conversation_id') in (None, self.native['conversation_id']) or req['id'] in self.wf_identifiers)}
				if pending:
					if pending != self.wf_identifiers:
						raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
					from .workflow import record_current_answer
					record_current_answer(self.root, self.response, journal_directory=self.value['journal'], request_ids=self.wf_identifiers)
				elif any((req['response_prepared']['sha256'] != self.sha for req in self.wf_state['requests'] if req['id'] in self.wf_identifiers)):
					if not self.allow_reprepare:
						raise ValueError('Tracked analysis requests already have different prepared response bytes')
					from .workflow import update
					def update_reprepared(s):
						for req in s.get('requests', []):
							if req['id'] in self.wf_identifiers:
								req['response_prepared'] = {'sha256': self.sha, 'prepared_at': _now()}
					update(self.root, {'action': 'reprepare_before_delivery', 'request_ids': sorted(self.wf_identifiers)}, update_reprepared)
	def _check_evicted_citations(self):
		if self.value['compaction_check'].get('occurred') and self.value['compaction_check'].get('evicted_unreread_files'):
			turn_key = self.result['turn_key']
			scratch_ans = self.root / f'\ua616/data/scratch/answer-{turn_key}.md'
			post_cp_w_low = {str(w).replace('\\', '/').lower() for w in (self.value['compaction_check'].get('post_checkpoint_written_files') or [])}
			pre_cp_authored = False
			if scratch_ans.is_file() and scratch_ans.resolve().as_posix().lower() not in post_cp_w_low:
				try:
					pre_cp_authored = scratch_ans.read_text(encoding='utf-8') == self.response
				except OSError:
					pre_cp_authored = False
			if not pre_cp_authored:
				from .source_grounding import extract_block_links, markdown_parser
				ev_map = {p.replace('\\', '/').lower(): p for p in self.value['compaction_check']['evicted_unreread_files']}
				unreread_cited = []
				for blk in markdown_parser().parse(self.response):
					if 'inline' == blk.type:
						lpaths, _ = extract_block_links(blk, self.root, None)
						for rp in lpaths:
							rlow = rp.as_posix().lower()
							if rlow in ev_map and (rlow.endswith('/kb/source.md') or '/source/' in rlow or '/res/' in rlow or '/kb/' in rlow) and (ev_map[rlow] not in unreread_cited):
								unreread_cited.append(ev_map[rlow])
				for ev_low, ev_orig in ev_map.items():
					m_res = re.search('/res/(\\d+\\.md)$', ev_low)
					if m_res and re.search(f'\\bres/{re.escape(m_res.group(1))}\\b', self.response, re.I) and (ev_orig not in unreread_cited):
						unreread_cited.append(ev_orig)
				if unreread_cited:
					detail = 'COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(unreread_cited)
					self._fail_gate('evicted_citations', detail, extra={'cited_files': unreread_cited})
	def _check_source_grounding(self):
		source_issues = response_source_and_kb_issues(self.root, self.response, self.turn['requests'], touched_files=self.turn.get('touched_files'))
		self.value['source_kb_check'] = {'verified': not source_issues, 'issues': source_issues}
		if source_issues:
			self._fail_gate('source_grounding', '; '.join(source_issues))
	def _check_turn_hygiene(self):
		if not self.value['exec5_check']['verified']:
			commands = [cmd for item in self.value['exec5_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('exec5', 'EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['http_fetch_check']['verified']:
			commands = [cmd for item in self.value['http_fetch_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('http_fetch', 'KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection; use collect/collect-http or run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['compaction_check']['verified']:
			unreread_src = self.value['compaction_check'].get('unreread_analysis_sources') or []
			if unreread_src:
				detail = 'COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread_src)
			else:
				detail = 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare'
			self._fail_gate('compaction', detail)
		self._check_evicted_citations()
		if not self.value['delegation_check']['verified']:
			dc = self.value['delegation_check']
			detail = f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={dc['tool_step_count']}, max_streak={dc.get('max_unpersisted_step_streak', 0)} > {dc['max_unpersisted_steps']}, or unpersisted_source_reads={dc.get('max_unpersisted_source_reads', 0)} >= {dc.get('max_allowed_unpersisted_source_reads', 10)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence"
			self._fail_gate('delegation', detail)
		self.value['code_lifecycle_check'] = _code_and_issue_lifecycle_status(self.root, self.turn, self.value, response=self.response)
		if not self.value['code_lifecycle_check']['verified']:
			self._fail_gate('code_lifecycle', 'EXEC-5 violation in active turn (code/issue lifecycle incomplete): ' + '; '.join(self.value['code_lifecycle_check']['violations']))
		lang_issues = _intermediate_or_language_issues(self.turn['requests'], self.response)
		self.value['language_and_stub_check'] = {'verified': not lang_issues, 'issues': lang_issues}
		if lang_issues:
			self._fail_gate('language_and_stub', '; '.join(lang_issues))
		if self.value['prepared'] and self.value['prepared']['response_sha256'] != self.sha:
			if None is not self.value.get('delivery') or 'delivered' == self.value.get('status') or self.turn.get('completed'):
				raise ValueError('Prepared response bytes are immutable after delivery; preserve the earlier version and reconcile before a corrective turn')
			self.allow_reprepare = True
		if 'conflict' == self.value['status']:
			raise ValueError('Resolve the native delivery conflict without overwriting journal history')
		aa_part_errs = self.value['delegation_check'].get('aa_partial_read_violations') or []
		if aa_part_errs:
			self._fail_gate('aa_partial_read', 'REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(aa_part_errs))
	def _fail_gate(self, gate_id, detail, *, admission_failed=False, status=None, extra=None, cause=None):
		if admission_failed:
			self.value['admission_failure'] = {'detail': detail, 'checked_at': _now()}
		if None is not status:
			self.value['status'] = status
		rc = {'verified': False, 'gate_id': gate_id, 'checked_at': _now(), 'detail': detail}
		if extra:
			rc.update(extra)
		self.value['readiness_check'] = rc
		_persist(self.path, self.value)
		if None is cause:
			raise ValueError(detail)
		else:
			raise cause
	def _record_journal_entry(self):
		try:
			self.value['prepared'], self.admission_check = _record(self.root, self.native, self.turn, self.response, self.value['journal'], existing=None if self.allow_reprepare else _recorded(self.value), allow_reprepare=self.allow_reprepare)
		except (OSError, ValueError) as exc:
			self._fail_gate('journal_admission', str(exc), admission_failed=True, cause=exc)
		self.value.pop('admission_failure', None)
	def _verify_delivered_fast_path(self):
		if 'delivered' != self.value['status']:
			r = None
		else:
			recorded = _recorded(self.value)
			if not recorded or recorded['response_sha256'] != self.sha:
				raise ValueError('Delivered response bytes are immutable; preserve the completed turn')
			if not self.turn.get('completed') or self.value['delivery'].get('native_response_sha256') != _hash(self.turn['response'].encode('utf-8')):
				raise ValueError('The saved native delivery requires foreground reconciliation before preparation')
			recorded, admission_check = _record(self.root, self.native, self.turn, self.response, self.value['journal'], existing=recorded, purpose='observation')
			r = {**self.result, **recorded, 'ready': True, 'status': 'delivered', 'delivery_verified': True, 'preparation_verified': self.value['delivery'].get('preparation_verified', False), 'admission_verification': admission_check}
		return r
	def run(self):
		delivered = self._verify_delivered_fast_path()
		if None is not delivered:
			r = delivered
		else:
			self._check_turn_hygiene()
			self._audit_workflow_scope()
			self._check_source_grounding()
			recorded_early = not self.workflow_path.exists() or self.is_finalized
			if recorded_early:
				self._record_journal_entry()
			self._authorize_and_sync_workflow()
			if not recorded_early:
				self._record_journal_entry()
			try:
				_unchanged(self.root, self.native, self.turn)
			except (OSError, ValueError, sqlite3.Error) as exc:
				self._fail_gate('turn_unchanged', str(exc), status='preparation_unverified', cause=exc)
			self.value['status'] = 'prepared'
			if not self.value.get('readiness_check', {}).get('verified'):
				self.value['readiness_check'] = {'verified': True, 'checked_at': _now()}
			_persist(self.path, self.value)
			r = {**self.result, **self.value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False, 'admission_verification': self.admission_check}
		return r
def _now():
	return datetime.now(timezone.utc).isoformat()
def _hash(value):
	return hashlib.sha256(value).hexdigest()
def _json(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _read(path):
	value = json.loads(path.read_bytes().decode('utf-8'))
	if not isinstance(value, dict):
		raise ValueError('Completion metadata must be a JSON object: ' + str(path))
	r = value
	return r
def _folder(root):
	return data_dir_for(root) / 'turns'
def _turn_lock(root, key):
	return _folder(root) / f'turn-{key}.lock'
def _journal_lock(root):
	return _folder(root) / 'journal.lock'
def _directory(root, selected=None):
	return journal.resolve_journal_dir(root, selected)
def _key(native, turn):
	identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
	r = _hash(_json(identity))[:40]
	return r
def _native(root, conversation=None, *, platform=None, backend=None):
	platform = platform_name(platform)
	conversation = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == platform else None)
	if not conversation:
		raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
	r = adapter(platform).native_answers(Path(root).resolve(), conversation, backend=backend)
	return r
def _policy():
	return {ident: {'source': relative, 'anchor': anchor, 'sha256': _hash((PRIMARY / relative).read_bytes()), 'requirement': RULE_REQUIREMENTS[ident]} for ident, (relative, anchor) in RULES.items()}
def _violation_recovery(root, key):
	if None is root or not key:
		return {}
	path = _folder(root) / f'{key}-violation-recovery.json'
	if not path.is_file():
		return {}
	try:
		return _read(path)
	except (OSError, ValueError):
		return {}
def _exec5_status(turn, root=None, key=None):
	violations = list(turn.get('exec5_violations') or [])
	rec = _violation_recovery(root, key) if violations else {}
	covered = set(rec.get('covered_exec5_steps') or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
def _factual_kb_note_issues(root, turn):
	from .knowledge import validate_kb_factual_note
	r = {'has_normative': False, 'has_analysis': False, 'issues': []}
	for tf in turn.get('touched_files') or []:
		tf_norm = str(tf).replace('\\', '/').lower()
		if ('/\ua616/kb/' in tf_norm or tf_norm.endswith('/kb/analysis.md') or tf_norm.endswith('/kb/analysis.json')) and '/\ua616/kb/evidence/' not in tf_norm:
			basename = Path(tf).name.lower()
			if basename in ('analysis.md', 'analysis.json'):
				r['has_analysis'] = True
				r['has_normative'] = True
			elif basename in ('project.md', 'projects.md'):
				r['has_normative'] = True
			else:
				fpath = Path(tf) if Path(tf).is_absolute() else (root / Path(tf))
				if fpath.is_file():
					try:
						note_text = fpath.read_text(encoding='utf-8', errors='replace')
						r['issues'].extend(validate_kb_factual_note(fpath, note_text))
					except OSError:
						pass
	return r
def _gate_resolved(root, turn, value):
	rc = value.get('readiness_check') or {}
	gid = str(rc.get('gate_id') or '')
	rc_detail = str(rc.get('detail') or '')
	root_p = Path(root).resolve()
	if 'exec5' == gid or ('' == gid and rc_detail.startswith('EXEC-5 violation in active turn (git read')):
		specific = bool(value.get('exec5_check', {}).get('verified'))
	elif 'http_fetch' == gid or ('' == gid and rc_detail.startswith('KB-3 / EXEC-1 violation')):
		specific = bool(value.get('http_fetch_check', {}).get('verified'))
	elif 'compaction' == gid or ('' == gid and rc_detail.startswith('COMPACT-1 / KB-3 violation') and 'cited in response' not in rc_detail):
		specific = bool(value.get('compaction_check', {}).get('verified'))
	elif 'evicted_citations' == gid or ('' == gid and rc_detail.startswith('COMPACT-1 / KB-3 violation') and 'cited in response' in rc_detail):
		cited = set(rc.get('cited_files') or ())
		evicted = set(value.get('compaction_check', {}).get('evicted_unreread_files') or ())
		specific = bool(value.get('compaction_check', {}).get('verified')) and (not (cited & evicted if cited else evicted))
	elif 'delegation' == gid or ('' == gid and rc_detail.startswith('REVIEW-1 / KB-3 violation')):
		specific = bool(value.get('delegation_check', {}).get('verified'))
	elif 'code_lifecycle' == gid or ('' == gid and rc_detail.startswith('EXEC-5 violation in active turn (code/issue')):
		specific = bool(value.get('code_lifecycle_check', {}).get('verified'))
	elif 'language_and_stub' == gid or ('' == gid and rc_detail.startswith(('TEXT-1:', 'FILE-3 / REVIEW-1:'))):
		specific = bool(value.get('language_and_stub_check', {}).get('verified'))
	elif 'aa_partial_read' == gid or ('' == gid and rc_detail.startswith('REVIEW-3 / REVIEW-4: Independent A.A reviewer')):
		specific = not bool(value.get('delegation_check', {}).get('aa_partial_read_violations'))
	elif 'factual_kb_note' == gid or ('' == gid and rc_detail.startswith('KB-2 / DOC-1 violation')):
		specific = not bool(_factual_kb_note_issues(root_p, turn)['issues'])
	elif 'workflow_adoption' == gid or ('' == gid and rc_detail.startswith('REVIEW-3 / REVIEW-4: Adopt current requests')):
		specific = _workflow_gate_resolved(root_p, turn, 'workflow_adoption')
	elif 'review_authorize' == gid:
		specific = _workflow_gate_resolved(root_p, turn, 'review_authorize')
	elif 'source_grounding' == gid or ('' == gid and rc_detail.startswith(('VERIFY-1', 'LINK-', 'KB-1 / KB-3:', 'DOC-1 / VERIFY-'))):
		specific = bool(value.get('source_kb_check', {}).get('verified'))
	else:
		specific = False
	r = bool(specific and all((value.get(k, {}).get('verified', True) for k in ('exec5_check', 'http_fetch_check', 'compaction_check', 'delegation_check', 'code_lifecycle_check', 'language_and_stub_check', 'source_kb_check'))))
	return r
def _http_fetch_status(turn, root=None, key=None):
	violations = list(turn.get('http_fetch_violations') or [])
	rec = _violation_recovery(root, key) if violations else {}
	covered = set(rec.get('covered_http_fetch_steps') or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
def _compaction_status(root, key, turn):
	comp = dict(turn.get('compaction') or {})
	occurred = bool(comp.get('occurred'))
	last_cp = comp.get('last_checkpoint_step')
	pre_steps = list(comp.get('pre_checkpoint_tool_steps') or [])
	post_rec = list(comp.get('post_checkpoint_recovery_steps') or [])
	pre_reads = list(comp.get('pre_checkpoint_read_files') or [])
	post_reads = list(comp.get('post_checkpoint_read_files') or [])
	post_writes = list(comp.get('post_checkpoint_written_files') or [])
	evicted_unreread = list(comp.get('evicted_unreread_files') or [])
	evicted_lower = {p.replace('\\', '/').lower(): p for p in evicted_unreread}
	unreread_analysis_sources = []
	writes_client_deliverable = False
	for w in post_writes:
		wnorm = w.replace('\\', '/')
		wlow = wnorm.lower()
		if wlow.endswith('/kb/analysis.md'):
			sib = (Path(wnorm).parent / 'source.md').as_posix()
			if sib.lower() in evicted_lower and evicted_lower[sib.lower()] not in unreread_analysis_sources:
				unreread_analysis_sources.append(evicted_lower[sib.lower()])
		elif any((seg in wlow for seg in ('/letters/', '/result/', '/defects/'))) and '/\ua616/' not in wlow and '/\ua66e/' not in wlow:
			writes_client_deliverable = True
	if writes_client_deliverable:
		for ev_l, ev_orig in evicted_lower.items():
			if ('/.system_generated/steps/' in ev_l or ev_l.endswith('/kb/source.md') or '/source/' in ev_l or '/\ua616/kb/evidence/' in ev_l) and ev_orig not in unreread_analysis_sources:
				unreread_analysis_sources.append(ev_orig)
	recovered_in_trace = bool(comp.get('recovered_in_trace', True))
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	recovered_via_receipt = False
	if receipt_path.is_file():
		try:
			rec_data = _read(receipt_path)
			cov = rec_data.get('covered_checkpoint_step')
			if None is last_cp or (isinstance(cov, int) and cov >= last_cp):
				recovered_via_receipt = True
		except (OSError, ValueError):
			pass
	verified = bool((not occurred or not pre_steps or recovered_in_trace or recovered_via_receipt) and (not unreread_analysis_sources))
	r = {'verified': verified, 'occurred': occurred, 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_steps, 'post_checkpoint_recovery_steps': post_rec, 'recovered_in_trace': recovered_in_trace, 'recovered_via_receipt': recovered_via_receipt, 'pre_checkpoint_read_files': pre_reads, 'post_checkpoint_read_files': post_reads, 'post_checkpoint_written_files': post_writes, 'evicted_unreread_files': evicted_unreread, 'unreread_analysis_sources': unreread_analysis_sources}
	return r
DEL_MAX_UNPERSISTED_STEPS = 40
DEL_MAX_UNPERSISTED_SOURCE_READS = 10
DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS = 60
DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS = 3
def _delegation_status(root, turn):
	del_info = dict(turn.get('delegation') or {})
	tool_steps = int(del_info.get('tool_step_count') or 0)
	sub_steps = int(del_info.get('subagent_step_count') or 0)
	aa_steps = int(del_info.get('aa_subagent_step_count') if 'aa_subagent_step_count' in del_info else sub_steps)
	af_steps = int(del_info.get('af_subagent_step_count') or 0)
	kb_steps = int(del_info.get('kb_persistence_step_count') or 0)
	cur_streak = int(del_info.get('unpersisted_step_streak') if 'unpersisted_step_streak' in del_info else tool_steps if 0 == sub_steps and 0 == kb_steps else 0)
	max_streak = int(del_info.get('max_unpersisted_step_streak') if 'max_unpersisted_step_streak' in del_info else cur_streak)
	max_src_reads = int(del_info.get('max_unpersisted_source_reads') or 0)
	issue_actions_count = len(turn.get('issue_actions') or [])
	aa_part_errs = list(del_info.get('aa_partial_read_violations') or [])
	is_upwork_project = (Path(root).resolve() / '\ua616/project.json').is_file()
	unpersisted_bulk = bool(is_upwork_project and ((tool_steps > DEL_MAX_UNPERSISTED_STEPS and 0 == sub_steps and 0 == kb_steps) or cur_streak > DEL_MAX_UNPERSISTED_STEPS or (max_src_reads >= DEL_MAX_UNPERSISTED_SOURCE_READS and 0 == sub_steps) or (tool_steps > DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS and 0 == sub_steps) or (issue_actions_count > DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS and 0 == sub_steps)))
	r = {'verified': not unpersisted_bulk, 'tool_step_count': tool_steps, 'subagent_step_count': sub_steps, 'aa_subagent_step_count': aa_steps, 'aa_partial_read_violations': aa_part_errs, 'af_subagent_step_count': af_steps, 'kb_persistence_step_count': kb_steps, 'issue_actions_count': issue_actions_count, 'max_unpersisted_steps': DEL_MAX_UNPERSISTED_STEPS, 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads, 'max_allowed_unpersisted_source_reads': DEL_MAX_UNPERSISTED_SOURCE_READS}
	return r
BUDGET_MAX_CHECKPOINTS = 2
BUDGET_MAX_TOOL_STEPS = 120
BUDGET_WINDOW_5H_MAX_STEPS = 400
def _budget_status(root, turn):
	comp = dict(turn.get('compaction') or {})
	del_info = dict(turn.get('delegation') or {})
	cp_count = len(comp.get('checkpoint_steps') or [])
	tool_steps = int(del_info.get('tool_step_count') or 0)
	now_ts = datetime.now(timezone.utc).timestamp()
	window_5h_steps = tool_steps
	turns_dir = _folder(root)
	cur_tid = turn.get('turn_id')
	if turns_dir.is_dir():
		for tf in turns_dir.glob('*.json'):
			if '-' in tf.stem:
				continue
			try:
				if now_ts - tf.stat().st_mtime <= 18000:
					td = _read(tf)
					if td.get('native_turn_id') != cur_tid:
						window_5h_steps += int((td.get('delegation_check') or {}).get('tool_step_count') or 0)
			except (OSError, ValueError):
				pass
	touched = [str(x).replace('\\', '/').lower() for x in (turn.get('touched_files') or [])]
	continuation_saved = any((x.endswith('/data/continuation.md') or x.endswith('\ua616/data/continuation.md') for x in touched))
	kb_saved = any(('/\ua616/kb/' in x or x.endswith('/kb/analysis.md') or x.endswith('/kb/analysis.json') for x in touched))
	exceeded = bool(cp_count >= BUDGET_MAX_CHECKPOINTS or tool_steps >= BUDGET_MAX_TOOL_STEPS or window_5h_steps >= BUDGET_WINDOW_5H_MAX_STEPS)
	r = {'verified': True, 'checkpoint_count': cp_count, 'max_checkpoints': BUDGET_MAX_CHECKPOINTS, 'tool_step_count': tool_steps, 'max_tool_steps': BUDGET_MAX_TOOL_STEPS, 'window_5h_tool_steps': window_5h_steps, 'max_window_5h_tool_steps': BUDGET_WINDOW_5H_MAX_STEPS, 'graceful_checkpoint_required': exceeded, 'continuation_saved': continuation_saved, 'kb_saved': kb_saved}
	return r
def _instruction_snapshot(root, native, *, stage):
	from .configuration import _project_rule_paths
	root = Path(root).resolve()
	sources = {path: 'canonical' for path in sorted((PRIMARY / 'rules').glob('*.md'))}
	sources.update({PRIMARY / 'runtime.json': 'runtime', PRIMARY / 'platforms' / (native['platform'] + '.md'): 'adapter'})
	errors = []
	manifest = root / '.agents/rules.json'
	if manifest.exists():
		sources[manifest] = 'project-registration'
	try:
		sources.update({path: 'project-rule' for path in _project_rule_paths(root, PRIMARY)})
	except (OSError, ValueError) as exc:
		errors.append(str(exc))
	if 'codex' == native['platform']:
		workspace = Path(settings()['workspace_root']).resolve()
		folders = [root]
		if root.is_relative_to(workspace):
			folders += [parent for parent in root.parents if parent == workspace or parent.is_relative_to(workspace)]
		folders.append(Path(native['native_backend']))
		for folder in folders:
			for name in ('AGENTS.md', 'AGENTS.override.md'):
				path = folder / name
				if path.is_file():
					sources[path] = 'native-guidance-candidate'
	files = []
	for path, kind in sorted(sources.items(), key=lambda item: str(item[0])):
		try:
			files.append({'path': str(path.resolve()), 'kind': kind, 'sha256': _hash(path.read_bytes())})
		except OSError as exc:
			errors.append(str(exc))
	r = {'captured_at': _now(), 'capture_stage': stage, 'sources': files, 'errors': errors, 'selection_verified': False, 'delivery_to_model_verified': False}
	return r
def _new(root, native, turn, *, recovered=False, journal_directory=None):
	key = _key(native, turn)
	lifecycle = {'verified': True, 'touched_repos': {}, 'issues': [], 'violations': []} if recovered else _code_and_issue_lifecycle_status(root, turn)
	r = {'schema_version': 1, 'key': key, 'project_root': str(Path(root).resolve()), 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'], 'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary', 'journal_required': True, 'journal': str(_directory(root, journal_directory)), 'applicable_rules': _policy(), 'git_optional_locks_env': os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0'), 'exec5_check': _exec5_status(turn, root, key), 'http_fetch_check': _http_fetch_status(turn, root, key), 'compaction_check': _compaction_status(root, key, turn), 'delegation_check': _delegation_status(root, turn), 'budget_check': _budget_status(root, turn), 'code_lifecycle_check': lifecycle, 'instruction_snapshot': _instruction_snapshot(root, native, stage='recovery' if recovered else 'turn-begin'), 'format_independent': True, 'rule_comprehension_verified': False, 'required_completion': ['answer-prepare', 'native-delivery-check'], 'status': 'open', 'prepared': None, 'delivery': None, 'recovered_after_delivery': recovered, 'created_at': _now()}
	return r
def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
	key = _key(native, turn)
	path = _folder(root) / (key + '.json')
	value = _read(path) if path.exists() else _new(root, native, turn, recovered=recovered, journal_directory=journal_directory)
	active_validation = not recovered and not (turn.get('completed') and value.get('status') in ('delivered', 'conflict'))
	if 'instruction_snapshot' not in value and active_validation:
		value['instruction_snapshot'] = _instruction_snapshot(root, native, stage='existing-state-upgrade')
	if 'applicable_rules' not in value:
		value['applicable_rules'] = _policy()
	if 'git_optional_locks_env' not in value:
		value['git_optional_locks_env'] = os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
	for name, check in (('exec5_check', lambda: _exec5_status(turn, root, key)), ('http_fetch_check', lambda: _http_fetch_status(turn, root, key)), ('compaction_check', lambda: _compaction_status(root, key, turn)), ('delegation_check', lambda: _delegation_status(root, turn)), ('budget_check', lambda: _budget_status(root, turn))):
		if active_validation or name not in value:
			value[name] = check()
	if active_validation:
		value['code_lifecycle_check'] = _code_and_issue_lifecycle_status(root, turn, value)
	elif 'code_lifecycle_check' not in value:
		value['code_lifecycle_check'] = {'verified': True, 'touched_repos': {}, 'issues': [], 'violations': []}
	if value.get('readiness_check', {}).get('verified') is False and (not value.get('admission_failure')):
		if _gate_resolved(root, turn, value):
			value.pop('readiness_check', None)
	saved_directory = _directory(root, value['journal'])
	if strict_journal and None is not journal_directory and (saved_directory != _directory(root, journal_directory)):
		raise ValueError('The native turn already has a different journal; preserve its original binding')
	value['journal'] = str(saved_directory)
	for name, expected in [('project_root', str(Path(root).resolve())), ('platform', native['platform']), ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']), ('native_turn_id', turn['turn_id'])]:
		if value.get(name) != expected:
			raise ValueError('Completion state has a different native owner; preserved')
	old, current = (value['requests'], turn['requests'])
	if current[:len(old)] != old:
		raise ValueError('Native requests changed before the saved boundary; preserved')
	if not (value.get('prepared') and current != old):
		value['requests'] = current
		r = (path, value)
	else:
		if not allow_extended:
			raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
		value['uncovered_requests'] = current[len(old):]
		r = (path, value)
	return r
def _persist(path, value):
	if path.exists() and _read(path) == value:
		return
	value['updated_at'] = _now()
	replace_bytes(path, _json(value))
def _active(native):
	if not native['primary']:
		r = None
	else:
		turn = next((turn for turn in native['turns'] if turn['turn_id'] == native['active_turn_id']), None)
		if None is turn or not turn['owned'] or turn['aborted']:
			raise ValueError('No active native user turn belonging entirely to this project')
		r = turn
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def begin(root, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		r = {'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
	else:
		with locked(_turn_lock(root, _key(native, turn))):
			path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
			_persist(path, value)
		result = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), 'role': 'primary', 'journal_required': True, 'status': value['status'], 'native_requests_sha256': _hash(_json(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': value['compaction_check'], 'delegation_check': value['delegation_check'], 'budget_check': value['budget_check'], 'code_lifecycle_check': value['code_lifecycle_check'], 'rule_comprehension_verified': False, 'required_completion': value['required_completion']}
		result['execution_mode'] = 'foreground-only'
		if any((t.get('owned') and t.get('completed') and (not t.get('aborted')) and (t.get('start_step', 0) <= turn['start_step']) for t in native.get('turns', []))):
			try:
				result['native_reconciliation'] = sync(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'], journal_directory=value['journal'], _preloaded_native=native)
				current = next((item for item in result['native_reconciliation']['turns'] if item['turn_key'] == value['key']), None)
				if current:
					result['status'] = current['status']
			except (OSError, ValueError, sqlite3.Error) as exc:
				result['native_reconciliation'] = {'valid': False, 'error': str(exc)}
		r = result
	return r
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def recover_checkpoint(root, conversation=None, *, platform=None, backend=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	comp = dict(turn.get('compaction') or {})
	raw_records = list(comp.get('pre_checkpoint_records') or [])
	rec_dir = _folder(root) / f'{key}-recovery'
	rec_dir.mkdir(parents=True, exist_ok=True)
	stdout_records = []
	compact_mode = len(raw_records) > 5
	for rec in raw_records:
		st = rec.get('step')
		outs = list(rec.get('outputs') or [])
		step_file = rec_dir / f'step-{st}.txt'
		if outs:
			replace_bytes(step_file, ('\n--- OUTPUT ---\n'.join(outs) + '\n').encode('utf-8'))
		rel_step = step_file.relative_to(root).as_posix() if step_file.is_relative_to(root) else str(step_file)
		if compact_mode:
			stdout_records.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step if outs else None, 'output_preview': [o[:200] for o in outs[:2]]})
		else:
			stdout_records.append({**rec, 'output_file': rel_step if outs else None})
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	receipt = {'turn_key': key, 'recovered_at': _now(), 'compact_mode': compact_mode, 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'pre_checkpoint_tool_steps': list(comp.get('pre_checkpoint_tool_steps') or []), 'pre_checkpoint_read_files': list(comp.get('pre_checkpoint_read_files') or []), 'post_checkpoint_read_files': list(comp.get('post_checkpoint_read_files') or []), 'evicted_unreread_files': list(comp.get('evicted_unreread_files') or []), 'recovery_dir': rec_dir.relative_to(root).as_posix() if rec_dir.is_relative_to(root) else str(rec_dir), 'pre_checkpoint_records': raw_records}
	with locked(_turn_lock(root, key)):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		value.pop('admission_failure', None)
		_persist(path, value)
	r = {**receipt, 'pre_checkpoint_records': stdout_records, 'recovery_file': receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path), 'compaction_check': value['compaction_check']}
	return r
def recover_turn_violation(root, conversation=None, *, reason=None, platform=None, backend=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	exec5_v = list(turn.get('exec5_violations') or [])
	http_v = list(turn.get('http_fetch_violations') or [])
	receipt_path = _folder(root) / f'{key}-violation-recovery.json'
	receipt = {'turn_key': key, 'recovered_at': _now(), 'reason': (reason or 'Retrospective turn violation acknowledged for journal completion').strip(), 'covered_exec5_steps': [item.get('step') for item in exec5_v if None is not item.get('step')], 'covered_http_fetch_steps': [item.get('step') for item in http_v if None is not item.get('step')], 'exec5_violations': exec5_v, 'http_fetch_violations': http_v}
	with locked(_turn_lock(root, key)):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		_persist(path, value)
	r = {**receipt, 'recovery_file': receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path), 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check']}
	return r
def _norm_journal_text(text: str) -> str:
	return _strip_local_file_scheme((text or '').replace('\r\n', '\n'))
def _find_orphan_or_overwritten_steps(directory: Path, requests: list[str], response: str, native_ids: list[str]):
	n = len(requests or [])
	req_dir, res_dir = (directory / 'req', directory / 'res')
	if 0 == n or (not req_dir.is_dir()) or (not res_dir.is_dir()):
		return (None, None, None)
	norm_reqs = [_norm_journal_text(r) for r in requests]
	norm_resp = _norm_journal_text(response)
	groups_dir = journal.state_dir(directory) / 'answer-groups'
	claimed_by_step = {}
	if groups_dir.is_dir():
		for g_file in groups_dir.glob('*.json'):
			try:
				g_val = _read(g_file)
				for st in g_val.get('steps') or []:
					if type(st) is int:
						claimed_by_step[st] = g_val
			except (OSError, ValueError):
				continue
	pair_ids = sorted({int(p.stem) for p in req_dir.glob('*.md') if p.stem.isascii() and p.stem.isdigit() and (res_dir / p.name).is_file()})
	pair_set = set(pair_ids)
	overwritten_conflict = None
	for start in pair_ids:
		cand_steps = list(range(start, start + n))
		if not all((st in pair_set for st in cand_steps)):
			continue
		try:
			disk_reqs = [(req_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
			disk_resps = [(res_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
		except (OSError, UnicodeDecodeError):
			continue
		if len(set(disk_resps)) != 1:
			continue
		if [_norm_journal_text(x) for x in disk_reqs] != norm_reqs or _norm_journal_text(disk_resps[0]) != norm_resp:
			continue
		if all((st not in claimed_by_step and (not (journal.state_dir(directory) / f'{st}.json').exists()) for st in cand_steps)):
			return (cand_steps, disk_reqs, disk_resps[0])
		for st in cand_steps:
			owner = claimed_by_step.get(st)
			if owner and owner.get('request_ids') != native_ids:
				o_steps = owner.get('steps') or []
				o_reqs = owner.get('requests') or []
				o_sha = owner.get('response_sha256')
				matches_owner = o_steps == cand_steps and len(o_reqs) == len(cand_steps) and all((d_req == o_req for d_req, o_req in zip(disk_reqs, o_reqs))) and (_hash(disk_resps[0].encode('utf-8')) == o_sha)
				if not matches_owner and None is overwritten_conflict:
					overwritten_conflict = (cand_steps, owner.get('turn'))
	if None is not overwritten_conflict:
		c_steps, o_turn = overwritten_conflict
		raise ValueError(f'Journal step(s) {c_steps} match this native turn but are claimed by another answer group ({o_turn}); preserve the conflict')
	return (None, None, None)
def _group(root, native, turn, response, directory, *, allow_reprepare=False):
	key = 'native-' + _key(native, turn)
	legacy = turn['turn_id']
	groups = journal.state_dir(directory) / 'answer-groups'
	native_ids = [r['id'] for r in turn['requests']]
	norm_turn_reqs = [_norm_journal_text(r['text']) for r in turn['requests']]
	norm_turn_resp = _norm_journal_text(response)
	matches = []
	for file in groups.glob('*.json'):
		old = _read(file)
		if old.get('request_ids') == native_ids:
			old_reqs = old.get('requests') or []
			reqs_ok = old_reqs == [r['text'] for r in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
			resp_ok = old.get('response_sha256') == _hash(response.encode('utf-8'))
			if not resp_ok and old.get('steps'):
				res_p = directory / 'res' / f"{old['steps'][0]}.md"
				if res_p.is_file():
					try:
						disk_r = res_p.read_bytes().decode('utf-8')
						resp_ok = _hash(disk_r.encode('utf-8')) == old.get('response_sha256') and _norm_journal_text(disk_r) == norm_turn_resp
					except (OSError, UnicodeDecodeError):
						pass
			if not reqs_ok or (not resp_ok and not allow_reprepare):
				raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
			matches.append(old)
	if len(matches) > 1:
		raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
	if matches:
		return (matches[0]['turn'], native_ids)
	if re.fullmatch('[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
		old = _read(groups / (legacy + '.json'))
		old_reqs = old.get('requests') or []
		reqs_ok = old_reqs == [r['text'] for r in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
		if not reqs_ok or (old.get('response_sha256') != _hash(response.encode('utf-8')) and not allow_reprepare):
			raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
		return (legacy, old.get('request_ids'))
	return (key, native_ids)
def _recorded(value):
	return next((receipt for receipt in (value.get('prepared'), value.get('journal_record'), value.get('delivery')) if isinstance(receipt, dict) and 'journal_steps' in receipt), None)
def _intermediate_or_language_issues(requests, response: str) -> list[str]:
	from .source_grounding import verify_target_locale
	r = []
	if re.search('(?i)(?:^|\\n)\\s*waiting\\s+for\\s+(?:the\\s+)?(?:remaining\\s+)?(?:\\d+\\s+)?(?:subagents?|background\\s+tasks?|tasks?|commands?)\\b[^\\n]{0,120}\\bto\\s+(?:complete|finish)\\b', response or ''):
		r.append('FILE-3 / REVIEW-1: Response is an intermediate subagent/task waiting status stub rather than a complete final response')
	req_raw = '\n'.join((req.get('text', '') if isinstance(req, dict) else str(req) for req in requests or []))
	for err in verify_target_locale(response or '', target_locale='und', container_text=req_raw, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20):
		r.append(err['message'])
	return r
def _record(root, native, turn, response, directory, *, existing=None, purpose='publication', allow_reprepare=False):
	if purpose not in ('publication', 'observation'):
		raise ValueError('Choose publication admission or historical observation')
	directory = _directory(root, directory)
	from . import admission
	token, request_ids = _group(root, native, turn, response, directory, allow_reprepare=allow_reprepare)
	group_file = journal.state_dir(directory) / 'answer-groups' / (token + '.json')
	already_complete = group_file.exists() and 'complete' == _read(group_file).get('status')
	if not already_complete or allow_reprepare:
		lang_issues = _intermediate_or_language_issues(turn['requests'], response)
		if lang_issues:
			raise ValueError('; '.join(lang_issues))
	if existing:
		if not already_complete:
			raise ValueError('Recorded answer-group receipt is missing or incomplete; preserve journal history')
		if _read(group_file).get('steps') != existing['journal_steps']:
			raise ValueError('Recorded answer-group steps changed; preserve journal history')
	effective_requests = [r['text'] for r in turn['requests']]
	effective_response = response
	adopt_steps = None
	adopted_existing = False
	reprepared_before_delivery = False
	if already_complete:
		g_data = _read(group_file)
		g_reqs = g_data.get('requests') or []
		if [_norm_journal_text(x) for x in g_reqs] == [_norm_journal_text(x) for x in effective_requests]:
			effective_requests = list(g_reqs)
		if g_data.get('steps') and _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256'):
			res_p = directory / 'res' / f"{g_data['steps'][0]}.md"
			if res_p.is_file():
				try:
					disk_r = res_p.read_bytes().decode('utf-8')
					if _hash(disk_r.encode('utf-8')) == g_data.get('response_sha256') and _norm_journal_text(disk_r) == _norm_journal_text(effective_response):
						effective_response = disk_r
				except (OSError, UnicodeDecodeError):
					pass
			if _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256') and allow_reprepare:
				reprepared_before_delivery = True
	elif None is existing:
		adopt_steps, disk_reqs, disk_resp = _find_orphan_or_overwritten_steps(directory, effective_requests, effective_response, request_ids)
		if None is not adopt_steps:
			effective_requests = disk_reqs
			effective_response = disk_resp
			adopted_existing = True
	identity = admission.binding(directory, effective_requests, effective_response, token, request_ids)
	if already_complete and not reprepared_before_delivery:
		if purpose == 'publication':
			from .text_workflow import gate_requests
			gate_requests([root, directory], effective_requests, effective_response)
		steps = journal.verify_answer(directory, effective_requests, effective_response, token, request_ids)
		proof = _read(group_file).get('admission')
		if existing and existing.get('admission') != proof:
			raise ValueError('Recorded admission differs from the original answer group; preserve history')
		verification = admission.verify(proof, identity) if proof else {'status': 'legacy_proof_gap', 'scope': 'journal_and_native_identity_only'}
	else:
		capability = admission.capture([root, directory], effective_requests, effective_response, identity)
		steps = journal.record_answer(directory, effective_requests, effective_response, token, request_ids, adopt_steps=adopt_steps, admission=capability, allow_reprepare=reprepared_before_delivery)
		proof = capability.reference
		verification = {'status': 'verified', 'scope': 'original_publication_admission' if purpose == 'observation' else 'current_publication_readiness'}
	for step, request in zip(steps, effective_requests):
		if (directory / 'req' / f'{step}.md').read_bytes() != request.encode('utf-8'):
			raise ValueError('Recorded request read-back differs from native text')
		if (directory / 'res' / f'{step}.md').read_bytes() != effective_response.encode('utf-8'):
			raise ValueError('Recorded response read-back differs from prepared text')
	recorded = {'journal_steps': steps, 'response_sha256': _hash(effective_response.encode('utf-8')), 'response_file': str(directory / 'res' / f'{steps[0]}.md'), 'group_file': str(group_file)}
	if existing:
		if any((existing.get(name) != expected for name, expected in recorded.items())):
			raise ValueError('Recorded answer receipt differs from its verified journal identity; preserve history')
		if existing.get('group_sha256') and existing['group_sha256'] != _hash(group_file.read_bytes()):
			raise ValueError('Recorded answer-group bytes changed; preserve history')
		return dict(existing), verification
	res_receipt = {**recorded, 'group_sha256': _hash(group_file.read_bytes()), 'recorded_at': _now(), 'reused_complete_journal_group': bool((already_complete and not reprepared_before_delivery) or adopted_existing), 'admission': proof}
	if reprepared_before_delivery:
		res_receipt['reprepared_before_delivery'] = True
	return res_receipt, verification
def _unchanged(root, native, turn):
	latest = _native(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'])
	current = _active(latest)
	if None is current or _key(latest, current) != _key(native, turn) or current['requests'] != turn['requests']:
		raise ValueError('The active native turn or requests changed during preparation; readiness was not granted')
def _workflow_gate_resolved(root_p, turn, kind):
	wf_file = root_p / '\ua616/data/workflow.json'
	if not wf_file.is_file():
		r = True
	elif 'workflow_adoption' == kind:
		from .workflow import load
		r = {req['id'] for req in turn.get('requests') or []}.issubset({req['id'] for req in load(root_p).get('requests') or []})
	else:
		from .review import approval_current
		from .workflow import load
		r = bool(approval_current(root_p, load(root_p)))
	return r
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None):
	if not isinstance(response, str) or not response.strip():
		raise ValueError('An exact nonempty UTF-8 final response is required')
	from .causal_checks import unsupported_probability_claims
	issues = unsupported_probability_claims(response)
	if issues:
		raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
	result = begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory)
	if not result['journal_required']:
		raise ValueError('A child executor cannot prepare the primary user journal')
	root_p = Path(root).resolve()
	with locked(_turn_lock(root_p, result['turn_key'])):
		native = _native(root_p, conversation, platform=platform, backend=backend)
		turn = _active(native)
		if None is turn or _key(native, turn) != result['turn_key'] or _hash(_json(turn['requests'])) != result['native_requests_sha256']:
			raise ValueError('The active native turn changed during preparation; no answer was recorded')
		r = AnswerPreparationRunner(root_p, response, result, native, turn).run()
	return r
def _conflict(root, path, value, native, turn, response, detail, *, retryable=False):
	payload = response.encode('utf-8')
	evidence = write_immutable_bytes(_folder(root) / 'conflicts' / (value['key'] + '-' + _hash(payload) + '.txt'), payload, diff_error='Immutable native conflict evidence changed')
	if _recorded(value):
		value['journal_record'] = _recorded(value)
	prior_verified = value.get('delivery') if (value.get('delivery') or {}).get('verified') else value.get('prior_verified_delivery')
	if prior_verified:
		value['prior_verified_delivery'] = deepcopy(prior_verified)
	value['status'] = 'conflict'
	value['delivery'] = {'verified': False, 'native_response_sha256': _hash(payload), 'source_file': native['source_file'], 'final_step': turn['final_step'], 'native_requests': turn['requests'], 'conflict_evidence': evidence.relative_to(root).as_posix(), 'detail': detail, 'retryable': retryable}
	_persist(path, value)
	r = {'turn_key': value['key'], 'status': 'conflict', 'detail': detail, 'evidence': evidence.relative_to(root).as_posix(), 'retryable': retryable}
	return r
def _strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None, adopt_conflict=False, _preloaded_native=None):
	if type(from_step) is not int or from_step < 0:
		raise ValueError('Native from-step must be a nonnegative integer')
	root = Path(root).resolve()
	native = _preloaded_native if None is not _preloaded_native else _native(root, conversation, platform=platform, backend=backend)
	if not native['primary']:
		raise ValueError('A child executor has no primary user journal to synchronize')
	if not any((turn['owned'] for turn in native['turns'])):
		raise ValueError('Native conversation has no user turns owned by this project')
	eligible = [turn for turn in native['turns'] if turn['owned'] and turn['completed'] and (not turn['aborted']) and (turn['start_step'] >= from_step)]
	if not eligible:
		return {'valid': True, 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': [], 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
	results = []
	with locked(_journal_lock(root)):
		for turn in eligible:
			with locked(_turn_lock(root, _key(native, turn))):
				path, value = _state(root, native, turn, recovered=True, allow_extended=True, journal_directory=journal_directory)
				response = turn['response']
				sha = _hash(response.encode('utf-8'))
				if value.get('uncovered_requests') and not adopt_conflict:
					results.append(_conflict(root, path, value, native, turn, response, 'Prepared answer does not cover newly received native requests'))
					continue
				if not _recorded(value) and (value.get('admission_failure') or value.get('readiness_check', {}).get('verified') is False) and not adopt_conflict:
					results.append(_conflict(root, path, value, native, turn, response, 'A prior preparation/admission gate failed; recovery cannot grant publication approval'))
					continue
				try:
					effective_response = response
					if value['prepared'] and value['prepared']['response_sha256'] != sha:
						prep_file = Path(value['prepared'].get('response_file') or '')
						prep_text = prep_file.read_bytes().decode('utf-8') if prep_file.is_file() else ''
						if prep_text and _norm_journal_text(prep_text) == _norm_journal_text(response):
							effective_response = prep_text
						elif not adopt_conflict:
							results.append(_conflict(root, path, value, native, turn, response, 'Prepared and delivered response bytes differ'))
							continue
					elif not value['prepared']:
						j_dir = _directory(root, value['journal'])
						req_ids = [r['id'] for r in turn['requests']]
						for g_file in (journal.state_dir(j_dir) / 'answer-groups').glob('*.json'):
							g_val = _read(g_file)
							if g_val.get('request_ids') == req_ids and g_val.get('steps'):
								res_path = j_dir / 'res' / f"{g_val['steps'][0]}.md"
								res_text = res_path.read_bytes().decode('utf-8') if res_path.is_file() else ''
								if res_text and _norm_journal_text(res_text) == _norm_journal_text(response):
									effective_response = res_text
								break
					recorded, admission_check = _record(root, native, turn, effective_response, value['journal'], existing=_recorded(value), purpose='observation')
				except (OSError, ValueError) as exc:
					results.append(_conflict(root, path, value, native, turn, response, str(exc), retryable=isinstance(exc, OSError) and (not isinstance(exc, FileNotFoundError))))
					continue
				if admission_check['status'] == 'legacy_proof_gap' and value['status'] in ('delivered', 'conflict'):
					results.append({'turn_key': value['key'], 'status': value['status'], 'delivery_verified': bool(value.get('delivery', {}).get('verified')), 'journal_steps': recorded['journal_steps'], 'completion_provenance': value.get('delivery', {}).get('completion_provenance'), 'preparation_verified': value.get('delivery', {}).get('preparation_verified', False), 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check})
					continue
				if adopt_conflict:
					value.pop('admission_failure', None)
					if (value.get('delivery') or {}).get('conflict_evidence'):
						conflict_file = root / value['delivery']['conflict_evidence']
						if conflict_file.is_file():
							try:
								conflict_file.unlink()
							except OSError:
								pass
				if not _recorded(value):
					value['recovered_after_delivery'] = not bool(value['prepared']) and (not recorded['reused_complete_journal_group'])
				if adopt_conflict:
					value['recovered_after_delivery'] = True
				provenance = 'prepared' if value['prepared'] and not adopt_conflict else 'recovered_native' if value['recovered_after_delivery'] else 'existing_journal'
				preparation_verified = bool(value['prepared']) and value.get('readiness_check', {}).get('verified', True) and not adopt_conflict
				value['journal_record'] = recorded
				delivery = {**recorded, 'verified': True, 'source_file': native['source_file'], 'final_step': turn['final_step'], 'completion_step': turn['completion_step'], 'native_response_sha256': sha, 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'exec5_check': value['exec5_check']}
				previous_delivery = value.get('delivery') or {}
				prior_verified = value.get('prior_verified_delivery') or {}
				if 'delivered' == value['status'] and all((previous_delivery.get(name) == expected for name, expected in delivery.items())):
					delivery = previous_delivery
				elif prior_verified and all((prior_verified.get(name) == expected for name, expected in delivery.items() if name != 'verified_at')):
					delivery = prior_verified
				else:
					delivery['verified_at'] = _now()
				value.pop('prior_verified_delivery', None)
				value['delivery'] = delivery
				value['status'] = 'delivered'
				if adopt_conflict:
					value['readiness_check'] = {'verified': True, 'checked_at': _now(), 'detail': 'Adopted into journal via --adopt-conflict'}
				_persist(path, value)
				results.append({'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True, 'journal_steps': recorded['journal_steps'], 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check})
	return {'valid': not any(('conflict' == r['status'] for r in results)), 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': results, 'retryable': any((r.get('retryable') for r in results)), 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def reconcile_unprepared_delivery(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
	return sync(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=True)
def add_parser_arguments(parser, command):
	if 'journal-watch' == command:
		parser.add_argument('--action', choices=('start', 'status', 'stop', 'once', 'run'), default='status')
		parser.add_argument('--state-dir', type=Path)
		parser.add_argument('--interval', type=float, default=5)
		parser.add_argument('--token', help='Internal watcher ownership token')
		parser.add_argument('--dry-run', action='store_true')
		return
	parser.add_argument('project', type=Path)
	parser.add_argument('--conversation', help='Actual current native conversation UUID; Codex can use CODEX_THREAD_ID')
	if 'recover-turn-violation' == command:
		parser.add_argument('--reason', help='Audit note for retrospective turn violation recovery')
	if command not in ('journal-unwatch', 'recover-checkpoint', 'recover-turn-violation'):
		parser.add_argument('--journal', type=Path, help='User-selected journal; otherwise preserve the turn binding or use ꙮ/1 - Analysis')
	if command in ('turn-begin', 'answer-prepare'):
		parser.add_argument('--no-watch', action='store_true', help='Compatibility option; all completion operations are foreground-only')
	if 'answer-prepare' == command:
		parser.add_argument('--response-file', type=Path, required=True, help='Exact UTF-8 final response, or - for stdin')
		parser.add_argument('--consume-input', action='store_true')
		parser.add_argument('--expected-sha256', help='Optional expected SHA-256 hex digest of response file')
	if command in ('journal-sync', 'reconcile-unprepared-delivery'):
		parser.add_argument('--from-step', type=int, default=0)
	if 'journal-sync' == command:
		parser.add_argument('--adopt-conflict', action='store_true', help='Adopt turns that experienced preparation or admission failures into the journal as recovered deliveries')
def execute(args):
	if 'turn-begin' == args.command:
		r = begin(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal)
	elif 'recover-checkpoint' == args.command:
		r = recover_checkpoint(args.project, args.conversation)
	elif 'recover-turn-violation' == args.command:
		r = recover_turn_violation(args.project, args.conversation, reason=args.reason)
	elif 'answer-prepare' == args.command:
		from .operations import _operation_input, _consumed
		payload = _operation_input(args, args.response_file)
		result = prepare(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal)
		r = _consumed(args, args.response_file, payload, result)
	elif 'reconcile-unprepared-delivery' == args.command:
		r = reconcile_unprepared_delivery(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal)
	elif 'journal-sync' == args.command:
		r = sync(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal, adopt_conflict=getattr(args, 'adopt_conflict', False))
	elif 'journal-unwatch' == args.command:
		from .journal_watch import unregister
		native = _native(args.project, args.conversation)
		if not native['primary'] or not any((turn['owned'] for turn in native['turns'])):
			raise ValueError('Only the owned primary conversation can remove its watcher binding')
		r = unregister(args.project, native)
	elif 'journal-watch' != args.command:
		raise ValueError('Unknown completion operation')
	else:
		from . import journal_watch
		if 'run' == args.action:
			r = journal_watch.run(state_dir=args.state_dir, token=args.token, interval=args.interval)
		elif 'once' == args.action:
			r = journal_watch.once(state_dir=args.state_dir, dry_run=args.dry_run)
		else:
			r = getattr(journal_watch, args.action)(state_dir=args.state_dir)
	return r
