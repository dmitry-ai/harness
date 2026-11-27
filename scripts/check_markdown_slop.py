# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Df.Harness.Hook.JsonRunner import JsonRunner
from Df.Harness.Hook.MarkdownSlopGate import MarkdownSlopGate
from Df.Harness.lib.hook_markdown_ops import dfh_check_doc_grounding_and_links as _check_doc_grounding_and_links, dfh_check_markdown_content as check_markdown_content, dfh_check_turn_budget_gate as _check_turn_budget_gate, dfh_infer_project_root as _infer_project_root, dfh_is_abbreviation_end as is_abbreviation_end, dfh_is_request_journal_file as _is_request_journal_file, dfh_is_scratch_draft_file as _is_scratch_draft_file, dfh_markdown_slop_issues as markdown_slop_issues, dfh_resolve_markdown_content as _resolve_markdown_content
from Df.Harness.lib.hook_runtime_ops import ABBREVIATIONS, ABBR_RE, MULTI_SENT_RE
# @used-by :func:`main()`
def _evaluate_payload(payload: dict) -> dict:
	return MarkdownSlopGate(payload).run()
# @used-by :mod:`check_markdown_slop`
def main():
	JsonRunner(_evaluate_payload).run()
if '__main__' == __name__:
	main()