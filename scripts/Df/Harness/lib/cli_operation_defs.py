# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.cli_input import dfh_add_arg_specs
from Df.Harness.lib.completion_core import COMMANDS as COMPLETION_COMMANDS
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
COMMAND_HELP = {'answer-check': 'Read-only pre-flight validation of candidate response (LINK-4/5, DOC-4, DOC-2, VERIFY-1, EXEC-2, EXEC-5)', 'check-project': 'All saved-source and local KB diagnostics; no network calls', 'collect': 'Batch GET/DOM observations and extraction with persistent project cache', 'collect-browser': 'Single- or multi-URL CDP browser DOM observation in headless shell or verified primary profile', 'collect-http': 'Single- or multi-URL GET/DOM observation and extraction with persistent Evidence cache', 'evidence-query': 'Compact read-only lookup of titles, h1, anchors, GitHub line ranges, and grep windows in Evidence/HTTP', 'issue-first-check': 'Read-only active-turn Issue-First chronological diagnostics (parent issue before tests and code)', 'ratchet-ok': 'Record an audited RATCHET-OK approval for an intentional requirement-driven test expectation change in the active turn', 'render-analysis': 'Publish tracked Markdown; preserve unknown/manual edits', 'resume': 'Continue the selected current-chat project from saved agent KB; no inspect/init', 'similar-project-exempt': 'Record an audited technical exemption for an unapplicable similar_projects peer in the active turn', 'status': 'Read-only current stage and agent KB navigation', 'sync-attachments': 'Sync client attachments to source/ and both KBs, including document/video/image transcriptions', 'sync-conversation-title': 'Synchronize an Antigravity conversation title to its project journal step numbers (e.g., 191, 204)', 'tdd-check': 'Read-only active-turn TDD Red-First and Full-Suite-Green diagnostics'}
COMMANDS = ('status', 'resume', 'collect', 'collect-http', 'collect-browser', 'capture-dom', 'extract', 'extract-file', 'evidence-query', 'sync-attachments', 'check-project', 'stage', 'question-add', 'question-claim', 'question-handoff', 'question-finish', 'question-search', 'prepare-review', 'review-input', 'native-review-proof', 'record-review', 'review-disposition', 'prepare-experiment', 'record-experiment', 'native-executor-metadata', 'adopt-requests', 'unadopt-requests', 'record-answer', 'metrics', 'source-ref', 'save-analysis', 'render-analysis', 'git-read', *COMPLETION_COMMANDS)
CONSUME_COMMANDS = {'collect', 'prepare-experiment', 'prepare-review', 'question-add', 'record-answer', 'record-experiment', 'record-review', 'save-analysis', 'sync-attachments'}
PROJECT_SPECS = {
	'adopt-requests': (('--conversation', {'required': True}), ('--allow-finalized', {'action': 'store_true', 'help': 'Permit adopting requests even if initial analysis finalize stage is complete'})),
	'capture-dom': (('--url', {'required': True}), ('--tab-id', {'required': True}), ('--session-id', {'required': True, 'help': 'Explicit authorized runtime text.browser.sessions entry'}), ('--refresh-reason', {})),
	'collect': (('--plan', {'required': True, 'type': Path}), ('--output', {'help': 'Optional project-owned result JSON'}), ('--browser', {'choices': ('auto', 'always', 'never'), 'default': 'auto', 'help': 'Browser CDP fallback mode (default: auto)'}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'}), ('--session-id', {'help': 'Optional authorized runtime text.browser.sessions entry'})),
	'collect-browser': (('urls_pos', {'nargs': '*', 'default': [], 'metavar': 'URL', 'help': 'Optional positional HTTP(S) URL(s)'}), ('--url', {'dest': 'url_list', 'action': 'append', 'default': [], 'help': 'HTTP(S) URL to capture via managed headless shell (public) or verified primary session (--session-id); repeatable'}), (('--profile', '--extract-profile'), {'dest': 'profile', 'choices': ('html', 'shopify', 'tracking', 'document', 'auto'), 'default': 'html'}), ('--scope', {'default': 'public'}), ('--session-id', {'help': 'Explicit authorized runtime text.browser.sessions entry for authenticated capture'}), ('--refresh-reason', {}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'})),
	'collect-http': (('urls_pos', {'nargs': '*', 'default': [], 'metavar': 'URL', 'help': 'Optional positional HTTP(S) URL(s)'}), ('--url', {'dest': 'url_list', 'action': 'append', 'default': [], 'help': 'HTTP(S) URL to fetch and persist in \ua616/KB/Evidence/HTTP; repeatable'}), (('--profile', '--extract-profile'), {'dest': 'profile', 'choices': ('html', 'shopify', 'tracking', 'document', 'auto'), 'default': 'auto'}), ('--scope', {'default': 'public'}), ('--session-id', {'help': 'Optional authorized runtime text.browser.sessions entry'}), ('--refresh-reason', {}), ('--browser', {'choices': ('auto', 'always', 'never'), 'default': 'auto', 'help': 'Browser CDP fallback mode (default: auto)'}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'})),
	'evidence-query': (('urls_pos', {'nargs': '*', 'default': [], 'metavar': 'URL', 'help': 'Optional positional URL filter(s)'}), ('--url', {'dest': 'url_list', 'action': 'append', 'default': [], 'help': 'Filter to exact or matching URL(s); repeatable'}), ('--anchors', {'action': 'store_true', 'help': 'Include semantic #anchor list and heading-to-anchor index'}), ('--grep', {'help': 'Case-insensitive regex to extract verbatim paragraph/line context windows'}), ('--context-lines', {'type': int, 'default': 2, 'help': 'Surrounding context lines around --grep matches (default: 2)'}), ('--max-matches', {'type': int, 'default': 20, 'help': 'Maximum --grep windows per observation (default: 20)'})),
	'extract': (('source', {}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document'), 'default': 'html'})),
	'extract-file': (('source', {}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document'), 'default': 'document'})),
	'native-executor-metadata': (('--conversation', {'required': True}), ('--save', {'action': 'store_true', 'help': 'Persist immutable native metadata; default is read-only'}), ('--role', {'choices': ('primary', 'AA', 'AF'), 'default': 'primary'}), ('--parent', {})),
	'native-review-proof': (('--parent', {'required': True}), ('--reviewer', {'required': True}), ('--wait-timeout', {'type': float, 'default': 0.0, 'help': 'Optional bounded wait in seconds for an in-flight reviewer to finish streaming its final response (capped at 300)'})),
	'prepare-experiment': (('--spec', {'required': True, 'type': Path}), ('--amendment-of', {}), ('--amendment-reason', {})),
	'prepare-review': (('--parent', {'required': True}), ('--spec', {'required': True, 'type': Path, 'help': 'Explicit risk/basis/request_scope/claim_ids/claims JSON'}), ('--response-file', {'required': True, 'type': Path, 'help': 'Exact candidate response; use - for stdin'})),
	'question-add': (('--spec', {'required': True, 'type': Path}),),
	'question-claim': (('id', {}), ('--owner', {'required': True})),
	'question-finish': (('id', {}), ('--owner', {'required': True}), ('--output', {'action': 'append', 'required': True}), ('--gap', {}), ('--results', {'required': True, 'type': Path, 'help': 'Structured experiment result list JSON; use - for stdin'})),
	'question-handoff': (('id', {}), ('--previous-owner', {'required': True}), ('--new-owner', {'required': True}), ('--reason', {'required': True})),
	'question-search': (('id', {}), ('--owner', {'required': True}), ('--query', {'required': True}), ('--useful', {'action': 'store_true'}), ('--method-change', {})),
	'record-answer': (('--response-file', {'required': True, 'type': Path}),),
	'record-experiment': (('--spec', {'required': True, 'type': Path}),),
	'record-review': (('--parent', {'required': True}), ('--reviewer', {'required': True}), ('--report', {'required': True}), ('--native-evidence', {'help': 'Separate native proof from the completed reviewer'})),
	'resume': (('--reason', {'required': True}), ('--request-file', {'type': Path, 'help': 'Exact current user message; kept in service state until final journal'})),
	'review-disposition': (('--review-id', {'required': True}), ('--finding-id', {'required': True}), ('--status', {'choices': ('resolved', 'rejected'), 'required': True}), ('--basis', {'required': True}), ('--evidence', {'action': 'append', 'required': True}), ('--parent', {'required': True})),
	'review-input': (('--package', {'required': True}),),
	'save-analysis': (('--candidate', {'required': True}), ('--expected-sha256', {}), ('--merge', {'action': 'store_true', 'help': 'Deep-merge candidate patch into existing Analysis.json or analysis-draft.json'}), ('--partial', {'action': 'store_true', 'help': 'Validate supplied claims and stage merged draft in \ua616/data/analysis-draft.json without committing Analysis.json'}), ('--promote-domain', {'action': 'store_true', 'help': 'Automatically promote a provisional topic folder to the resolved target domain'})),
	'source-ref': (('file', {}), ('--part', {'action': 'append', 'default': []})),
	'sync-attachments': (('--media-descriptions', {'type': Path, 'help': 'Optional JSON mapping attachment filename/sha256/video URL to Markdown transcription/analysis'}), ('--no-fetch-videos', {'action': 'store_true', 'help': 'Skip network fetching for external video transcripts'})),
	'unadopt-requests': (('--conversation', {}), ('--request-id', {'action': 'append', 'default': [], 'help': 'Specific request ID(s) to unadopt'})),
}
# @used-by :func:`dfh_add_operation_parsers()`
def _add_single_operation_parser(sub: Any, command: str, standalone: dict, stage_specs: tuple, add_completion_fn) -> None:
	parser = sub.add_parser(command, help=COMMAND_HELP.get(command, 'Internal ' + command + ' operation'))
	if command in COMPLETION_COMMANDS:
		if None is not add_completion_fn:
			add_completion_fn(parser, command)
		else:
			from Df.Harness.lib.completion_commands import dfh_add_completion_parser_arguments
			dfh_add_completion_parser_arguments(parser, command)
	elif command in standalone:
		dfh_add_arg_specs(parser, standalone[command])
	else:
		specs: list = [('project', {'type': Path, 'help': 'Exact existing project root from the current chat'})]
		if command in CONSUME_COMMANDS:
			specs.append(('--consume-input', {'action': 'store_true', 'help': 'After success remove an unchanged input only from project \ua616/data/scratch; use - for stdin'}))
		specs.extend(stage_specs if 'stage' == command else PROJECT_SPECS.get(command, ()))
		dfh_add_arg_specs(parser, specs)
# @used-by :func:`agent_tools.operations.add_parsers()`
def dfh_add_operation_parsers(sub: Any, *, add_completion_fn=None, settings_fn=None) -> None:
	from agent_tools.workflow import STAGES
	cfg = (settings_fn or (lambda: SettingsLoader().run()))()
	standalone = {
		'git-read': (('project', {'nargs': '?', 'type': Path, 'default': Path(cfg['workspace_root']).resolve()}), ('git_subcommand', {'choices': ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files'), 'nargs': '?', 'default': 'status'}), ('--short', {'action': 'store_true'}), ('--stat', {'action': 'store_true'}), ('--check', {'action': 'store_true'}), ('--arg', {'dest': 'git_args', 'action': 'append', 'default': []})),
		'metrics': (('traces', {'nargs': '*', 'type': Path}), ('--bindings', {'type': Path, 'help': 'conversation ID -> stage/first_step/last_step intervals'}), ('--project', {'type': Path, 'help': 'Optional exact project: observed cache/search/review metrics'}), ('--conversation', {'help': 'Conversation UUID resolved via runtime.json instances (or audit)'})),
		'render-analysis': (('input', {'type': Path}), ('--output', {'type': Path}), ('--promote-domain', {'action': 'store_true', 'help': 'Automatically promote a provisional topic folder to the resolved target domain'})),
	}
	stage_specs = (('stage', {'choices': STAGES}), ('--input', {'action': 'append', 'required': True}), ('--output', {'action': 'append', 'required': True}), ('--note', {}))
	for command in COMMANDS:
		_add_single_operation_parser(sub, command, standalone, stage_specs, add_completion_fn)