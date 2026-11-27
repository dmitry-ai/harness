# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`unittest`
class DfHarnessS11Wave2CTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_git_subsystem_single_class_modules_exist_and_delegate(self) -> None:
		from Df.Harness.Git.CommitVerifier import CommitVerifier
		from Df.Harness.Git.HookInstaller import HookInstaller
		from Df.Harness.Git.PushValidator import PushValidator
		from Df.Harness.Git.RepoGate import RepoGate
		from Df.Harness.Git.RepoWaiter import RepoWaiter
		from Df.Harness.Git.RetryableError import RetryableError
		from Df.Harness.Git.ShellInspector import ShellInspector
		from Df.Harness.Git.WorktreeTransaction import WorktreeTransaction
		from agent_tools import git_gate, repo_wait, shell_audit
		self.assertIs(RepoGate, git_gate.GitRepoGate)
		self.assertIs(WorktreeTransaction, git_gate.WorktreeCommitTransaction)
		self.assertIs(ShellInspector, shell_audit.ShellCommandInspector)
		self.assertIs(RetryableError, repo_wait.RetryableOperationError)
		self.assertTrue(callable(CommitVerifier))
		self.assertTrue(callable(HookInstaller))
		self.assertTrue(callable(PushValidator))
		self.assertTrue(callable(RepoWaiter))
	# @used-by :mod:`unittest`
	def test_grounding_subsystem_single_class_modules_exist_and_delegate(self) -> None:
		from Df.Harness.Grounding.LocalSourceAuditor import LocalSourceAuditor
		from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
		from Df.Harness.Grounding.Tier0Index import Tier0Index
		from agent_tools import response_grounding, source_grounding
		self.assertIs(LocalSourceAuditor, source_grounding.LocalSourceGroundingAuditor)
		self.assertIs(Tier0Index, source_grounding.Tier0SourceIndex)
		self.assertIs(ResponseAuditor, response_grounding.ResponseEvidenceAuditor)
	# @used-by :mod:`unittest`
	def test_issue_subsystem_single_class_modules_exist_and_delegate(self) -> None:
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.Linter import Linter
		from Df.Harness.Issue.ReadCache import ReadCache
		from Df.Harness.Issue.Service import Service
		from Df.Harness.Issue.TurnAuditor import TurnAuditor
		from agent_tools.issues import auditor, git_read_cache, linter, service, workspace
		self.assertIs(TurnAuditor, auditor.TurnIssueLifecycleAuditor)
		self.assertIs(ReadCache, git_read_cache.RepoReadCache)
		self.assertIs(Linter, linter.IssueMarkdownLinter)
		self.assertIs(Service, service.GitHubIssueService)
		self.assertIs(EvidenceWorkspace, workspace.IssueEvidenceWorkspace)
	# @used-by :mod:`unittest`
	def test_text_and_research_single_class_modules_exist_and_delegate(self) -> None:
		from Df.Harness.Research.HtmlData import HtmlData
		from Df.Harness.Research.HtmlReferences import HtmlReferences
		from Df.Harness.Research.LinkAuditor import LinkAuditor
		from Df.Harness.Research.Page import Page
		from Df.Harness.Research.Response import Response
		from Df.Harness.Research.SafeRedirects import SafeRedirects
		from Df.Harness.Text.Browser.CdpSession import CdpSession
		from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
		from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell
		from Df.Harness.Text.DiagnosticsScanner import DiagnosticsScanner
		from Df.Harness.Text.Finding import Finding
		from Df.Harness.Text.IntegrityVerifier import IntegrityVerifier
		from Df.Harness.Text.Line import Line
		from Df.Harness.Text.Workspace import Workspace
		from agent_tools import links, research, text_browser, text_core, text_diagnostics, text_workflow
		self.assertIs(HtmlReferences, links.HTMLReferences)
		self.assertIs(Page, links.Page)
		self.assertTrue(callable(LinkAuditor))
		self.assertIs(Response, research.Response)
		self.assertIs(SafeRedirects, research.SafeRedirects)
		self.assertIs(HtmlData, research.HTMLData)
		self.assertIs(CdpSession, text_browser.CDPSession)
		self.assertIs(HeadlessShell, text_browser.ManagedHeadlessShell)
		self.assertIs(GuardedCdp, text_browser.GuardedCDP)
		self.assertIs(Finding, text_core.Finding)
		self.assertIs(Line, text_core.Line)
		self.assertIs(Workspace, text_workflow.ClientTextWorkspace)
		self.assertIs(IntegrityVerifier, text_workflow.TextIntegrityVerifier)
		self.assertIs(DiagnosticsScanner, text_diagnostics.SourceDiagnosticsScanner)
if '__main__' == __name__:
	unittest.main()
