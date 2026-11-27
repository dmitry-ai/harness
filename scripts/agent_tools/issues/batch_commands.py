# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Issue.BatchRunner import BatchRunner
from Df.Harness.lib.issue import dfh_extract_actions_from_decoded_obj
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def extract_actions_from_decoded_obj(obj: dict[str, Any]) -> list[dict[str, Any]]:
	return dfh_extract_actions_from_decoded_obj(obj)
# @used-by unused
def register_issue_subparsers(sub, sub_defs, common_tail_specs, service_fn) -> None:
	BatchRunner.register_subparsers(sub, sub_defs, common_tail_specs, service_fn)
# @used-by unused
def run_batch_close(service, args: argparse.Namespace) -> int:
	return BatchRunner(service, args, 'close').run()
# @used-by unused
def run_batch_create(service, args: argparse.Namespace) -> int:
	return BatchRunner(service, args, 'create').run()
