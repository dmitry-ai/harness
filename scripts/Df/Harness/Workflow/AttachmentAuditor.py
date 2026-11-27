# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
import json
import re
_IMG_CONFIRM_RE = '(?i)confirm|contradict|\\u043f\\u043e\\u0434\\u0442\\u0432\\u0435\\u0440\\u0436\\u0434\\u0435\\u043d\\u0438|\\u043f\\u0440\\u043e\\u0442\\u0438\\u0432\\u043e\\u0440\\u0435\\u0447\\u0438'
_IMG_SCORE_RE = '(?i)(?:score|\\u043e\\u0446\\u0435\\u043d\\u043a\\u0430).*\\d+\\s*%'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AttachmentAuditor:
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.attachment_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_attachment_auditor_branches()`
	def __init__(self, root) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
	# @used-by :meth:`AttachmentAuditor.issues()`
	def __check_attachment(self, att: dict, inv: dict, targets: tuple, doc_markdowns: list, out: list[dict]) -> None:
		from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
		fname, sha, ev_path = (att['filename'], att['sha256'], att['evidence_path'])
		payload = ev_path.read_bytes()
		if not inv['source_by_sha'].get(sha):
			out.append(Diagnostics().problem('attachment.source_missing', f'source/{fname}', f'Attached file {fname} must be saved in the root source/ folder (§2.1); run sync-attachments', file=ev_path))
		kind = AttachmentExtractor.classify(fname, payload)
		markers = (f'Description in `{fname}`', f'\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0432 `{fname}`')
		if 'document' == kind:
			doc_markdowns.append(AttachmentExtractor.extract_markdown(ev_path, payload))
			for label, target_file, target_text in targets:
				if not any((hm in target_text for hm in markers)):
					out.append(Diagnostics().problem('attachment.kb_missing', label, f'Attached document {fname} is missing from {label} (§2.2); run sync-attachments', file=target_file))
		elif 'image' == kind:
			self.__check_image(fname, markers, targets, out)
	# @used-by :meth:`AttachmentAuditor.__check_attachment()`
	@staticmethod
	def __check_image(fname: str, markers: tuple[str, str], targets: tuple, out: list[dict]) -> None:
		for label, target_file, target_text in targets:
			matched = next((hm for hm in markers if hm in target_text), None)
			if not matched:
				out.append(Diagnostics().problem('attachment.image_missing', label, f'Attached image {fname} must be transcribed and analyzed in {label} (§2.4)', file=target_file))
			else:
				sec_match = re.search(f'(?ms){re.escape(matched)}.*?(?:~~~+|```+)markdown\\n(.*?)\\n(?:~~~+|```+)', target_text)
				sec_body = (sec_match.group(1) if sec_match else '').strip()
				if not sec_body or '«' not in sec_body or (not re.search(_IMG_CONFIRM_RE, sec_body)) or (not re.search(_IMG_SCORE_RE, sec_body)):
					out.append(Diagnostics().problem('attachment.image_incomplete', label, f'Attached image {fname} in {label} requires verbatim «...» text transcription, exhaustive UI description, and confirmation/contradiction analysis with % score (§2.4)', file=target_file))
	# @used-by :meth:`AttachmentAuditor.issues()`
	@staticmethod
	def __check_videos(snap: dict, doc_markdowns: list, inv: dict, targets: tuple, out: list[dict]) -> None:
		from Df.Harness.Upwork.VideoDetector import VideoDetector
		for video in VideoDetector.detect(snap.get('description') or '', doc_markdowns, [{'filename': a['filename'], 'sha256': a['sha256']} for a in inv['attachments']]):
			heading = video['heading']
			for label, target_file, target_text in targets:
				if heading not in target_text:
					out.append(Diagnostics().problem('attachment.video_missing', label, f'Client video ({heading}) must be transcribed in {label} (§2.3)', file=target_file))
				elif '# Full Audio Transcript:' not in target_text and '# \u041f\u043e\u043b\u043d\u0430\u044f \u0440\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0430 \u0430\u0443\u0434\u0438\u043e\u0437\u0430\u043f\u0438\u0441\u0438:' not in target_text or not re.search('\\[\\d{2}:\\d{2}\\]', target_text):
					out.append(Diagnostics().problem('attachment.video_incomplete', label, f'Client video ({heading}) in {label} requires # Video:, # Key Spoken Commentary Points..., and # Full Audio Transcript: with [MM:SS] timestamps (§2.3)', file=target_file))
	# @used-by :meth:`AttachmentAuditor.issues()`
	def __kb_targets(self) -> tuple:
		r = []
		for target in (self.__pp.manual_kb_dir / 'Project.md', self.__pp.kb_dir / 'Project.md', self.__pp.kb_dir / 'Projects.md'):
			r.append((self.__pp.rel_to_root(target), target, target.read_text(encoding='utf-8') if target.is_file() else ''))
		return tuple(r)
	# @used-by :meth:`AttachmentAuditor.issues()`
	def __load_snapshot(self):
		pj_file = self.__pp.project_json
		r = None
		if pj_file.is_file():
			try:
				pj = json.loads(pj_file.read_text(encoding='utf-8'))
				snap_path = self.__root / pj.get('snapshot', '')
				r = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.is_file() else {}
			except Exception:
				r = None
		return r
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.attachment_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_attachment_auditor_branches()`
	def issues(self) -> list[dict]:
		from agent_tools.knowledge import AttachmentInventory
		r: list[dict] = []
		snap = self.__load_snapshot()
		if None is not snap:
			inv = AttachmentInventory(self.__root).scan(snap.get('asset_evidence'))
			for f, sha in inv['missing_evidence']:
				r.append(Diagnostics().problem('attachment.evidence_missing', f'source/{f.name}', f'Attached file in source/{f.name} is not synced to \ua616/KB/Evidence/Attachments/{sha}/{f.name}; run sync-attachments', file=f))
			targets = self.__kb_targets()
			doc_markdowns: list = []
			for att in inv['attachments']:
				self.__check_attachment(att, inv, targets, doc_markdowns, r)
			self.__check_videos(snap, doc_markdowns, inv, targets, r)
		return r
