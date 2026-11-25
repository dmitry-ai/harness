# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
# https://github.com/dmitry-ai/harness/issues/230
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import sys
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
from agent_tools import completion, links, workflow as flow
from agent_tools.analysis import publish_owned, render_analysis
from agent_tools.metrics import native_review_proof
from agent_tools.response_grounding import ResponseEvidenceAuditor
from test_analysis_workflow import NativeReviewTests, ProjectCase
class ChatReplyLinkIssuesM5Tests(ProjectCase):
	def test_chat_reply_link_issues_allows_unencoded_file_uri_and_rejects_encoded(self) -> None:
		ev = self.put_project('\ua616/KB/Evidence/HTTP/abc/response.bin', b'ok')
		good_uri = f'file:///{ev.resolve().as_posix()}'
		good_md = f'Verified capture: [response.bin](<{good_uri}>).  \n'
		self.assertEqual([], links.chat_reply_link_issues(good_md))
		self.assertNotEqual([], links.readable_link_issues(good_md))
		bad_uri = good_uri.replace(' ', '%20')
		bad_md = f'Encoded link: [response.bin]({bad_uri}) and [doc](https://example.com/%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80).  \n'
		bad_errs = links.chat_reply_link_issues(bad_md)
		self.assertTrue(any('LINK-5:' in e for e in bad_errs), bad_errs)
	def test_completion_and_grounding_match_chat_reply_link_policy(self) -> None:
		ev = self.put_project('\ua616/KB/Evidence/note.txt', 'hello')
		good_uri = f'file:///{ev.resolve().as_posix()}'
		good_md = f'Evidence: [note.txt](<{good_uri}>).  \n'
		self.assertEqual([], completion._response_link_issues(self.project, good_md))
		auditor = ResponseEvidenceAuditor(self.project, good_md, [])
		self.assertEqual([], [e for e in auditor.errors if e.startswith('LINK-5:')])
		bad_md = f'Bad: [note.txt]({good_uri.replace(" ", "%20")}).  \n'
		self.assertTrue(any('LINK-5:' in e for e in completion._response_link_issues(self.project, bad_md)))
		bad_auditor = ResponseEvidenceAuditor(self.project, bad_md, [])
		self.assertTrue(any('LINK-5:' in e for e in bad_auditor.errors))
	def test_finalize_stage_accepts_unencoded_file_uri_chat_links(self) -> None:
		value = self.valid_review_analysis()
		publish_owned(self.project / '\ua616/KB/Analysis.md', render_analysis(value))
		ev = self.put_project('\ua616/KB/Evidence/HTTP/b1a7/response.bin', b'payload')
		flow.resume(self.project, 'quota', 'Continue analysis.')
		self.put_project('\ua616/KB/Evidence/init-check.json', '{}')
		self.put_project('\ua616/KB/Evidence/research-report.json', '{}')
		flow.complete_stage(self.project, 'identity_init', ['\ua616/project.json'], ['\ua616/KB/Evidence/init-check.json'])
		flow.complete_stage(self.project, 'research', ['\ua616/project.json'], ['\ua616/KB/Evidence/research-report.json'])
		flow.complete_stage(self.project, 'analysis', ['\ua616/project.json'], ['\ua616/KB/Analysis.json', '\ua616/KB/Analysis.md'])
		reply = f'Client task verified via [response.bin](<file:///{ev.resolve().as_posix()}>).  \n'
		package = self.review_package(str(uuid.uuid4()), response=reply)
		home, _backend, parent, child = NativeReviewTests.native_fixture(self, package)
		with patch.object(Path, 'home', return_value=home):
			native = native_review_proof(self.project, parent, child)
			report = self.review_report(package)
			self.put_project('\ua616/KB/Evidence/Reviews/report.json', json.dumps(report))
			flow.record_review(self.project, '\ua616/KB/Evidence/Reviews/report.json', parent_id=parent, reviewer_id=child, native_evidence=native['proof'])
			flow.complete_stage(self.project, 'review', ['\ua616/KB/Analysis.json'], ['\ua616/KB/Evidence/Reviews/report.json'])
			flow.complete_stage(self.project, 'kb_review', flow.kb_paths(self.project), ['\ua616/KB/Analysis.md'], note='Reviewed KB consistency')
			flow.record_current_answer(self.project, reply)
			flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['\ua66e/\u227a/1\u201320/1.md'])
			self.assertEqual('complete', flow.status(self.project)['stages']['finalize'])
if '__main__' == __name__:
	unittest.main()
