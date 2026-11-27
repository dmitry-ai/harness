# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.IssueFetcher import IssueFetcher
from Df.Harness.Issue.IssueLintRunner import IssueLintRunner
from Df.Harness.Issue.Linter import Linter
from Df.Harness.Issue.RepoAuditor import RepoAuditor
from Df.Harness.Issue.RepoTransferRunner import RepoTransferRunner
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def run_audit_repo(api_fn, linter: Linter, args: argparse.Namespace) -> int:
	return RepoAuditor(api_fn, linter, args).audit()
# @used-by unused
def run_fetch(service, args: argparse.Namespace) -> int:
	return IssueFetcher(service, args).fetch()
# @used-by unused
def run_lint(linter: Linter, args: argparse.Namespace) -> int:
	return IssueLintRunner(linter, args).run()
# @used-by unused
def run_transfer_repo(api_fn, linter: Linter, workspace: EvidenceWorkspace, args: argparse.Namespace) -> int:
	return RepoTransferRunner(api_fn, linter, workspace, args).transfer()
