# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class JournalWriteGate:
	NAME = 'FILE-3-JOURNAL-GATE'
	PRIORITY = 50
	TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.journal_write.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if name in ('write_file', 'edit_file'):
			path = (args.get('Path') or '').replace('\\', '/')
			if re.search('(?:^|/)\\ua66e/(?:[^/]+/)?(?:req|res|\\u227b|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?[^/]+\\.md$', path, re.IGNORECASE):
				r = 'FILE-3 / FILE-4: Direct write_file or edit_file to journal req/res (or \u227b/\u227a) files is prohibited; use harness.py answer-prepare to record primary responses with answer-groups receipts.'
		elif 'run_command' == name:
			cmd = args.get('CommandLine') or ''
			if re.search('\\brecord_step\\.py\\b', cmd, re.IGNORECASE) and (not re.search('\\bgit\\b[^;|\\n]*\\brm\\b[^;|\\n]*\\brecord_step\\.py\\b', cmd, re.IGNORECASE)):
				r = 'FILE-3 / FILE-4: Executing record_step.py is prohibited; use harness.py answer-prepare to record primary responses with answer-groups receipts.'
		return r
