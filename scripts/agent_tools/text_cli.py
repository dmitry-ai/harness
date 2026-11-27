# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.CliRunner import CliRunner, _DOC_SPECS, _FLOW_OPTIONS
from .cli_common import read_input_json as data, read_input_text as read
# @used-by unused
def findings_output(findings, path, as_json=False):
	return CliRunner.findings_output(findings, path, as_json=as_json)
# @used-by :func:`agent_tools.article.main()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
# @used-by :mod:`df_proposal`
# @used-by :mod:`df_text`
def main(argv=None, *, default_kind='article'):
	return CliRunner(argv, default_kind=default_kind).run()
