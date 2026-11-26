# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import re
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.text.n.normalize import df_normalize
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.sha256 import df_sha256
from .storage import locked, replace_bytes
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`sync_block()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _digest(data):
	return df_sha256(data)
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.intake._index()`
# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
# @used-by :func:`agent_tools.knowledge.sync_website_card()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_website_card_uses_readable_iri_and_keeps_original_website_selection()`
def sync_block(root, target, key, content, position='after-title', *, check=False, source=None, attributes=None):
	root = Path(root).resolve()
	target = (root / target).resolve()
	if not target.is_relative_to(root):
		raise ValueError('Managed KB block must stay inside the project')
	if position not in ('start', 'after-title', 'append') or not re.fullmatch('[a-z][a-z0-9-]*', key):
		raise ValueError('Known block position and a lowercase block key required')
	if not isinstance(content, str) or '<!-- upwork-init:' in content:
		raise ValueError('Managed block content must be text without reserved markers')
	# 2026-10-17
	# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
	# https://github.com/dmitry-ai/harness/issues/9
	from .links import readable_link_issues
	issues = readable_link_issues(content)
	if issues:
		raise ValueError('\n'.join(issues))
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	directory = pp.data_dir
	receipt_path = pp.rendered_json
	result = {'target': str(target), 'block': key}
	# @used-by :func:`sync_block()`
	def conflict(detail):
		return {**result, 'status': 'conflict', 'detail': detail}
	with nullcontext() if check else locked(directory / 'render.lock'):
		try:
			receipts = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
			if not isinstance(receipts, dict):
				return conflict('Malformed publication receipt; preserved')
			entry = receipts.get(str(target), {})
			if not isinstance(entry, dict) or not isinstance(entry.get('managed_blocks', {}), dict):
				return conflict('Malformed block ownership receipt; preserved')
			blocks = entry.get('managed_blocks', {})
			owned = blocks.get(key)
			if None is not owned and (not isinstance(owned, dict) or not re.fullmatch('[a-f0-9]{64}', str(owned.get('sha256', '')))):
				return conflict('Malformed block ownership hash; preserved')
			previous = target.read_bytes() if target.exists() else b''
			previous.decode('utf-8-sig')
		except (OSError, UnicodeError, json.JSONDecodeError) as error:
			return conflict(f'Cannot read existing publication safely: {type(error).__name__}')
		newline = b'\r\n' if b'\r\n' in previous else b'\n'
		start = f'<!-- upwork-init:{key}:start -->'.encode()
		end = f'<!-- upwork-init:{key}:end -->'.encode()
		# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
		body = df_normalize(content).rstrip('\n').encode().replace(b'\n', newline)
		block = start + newline + newline + body + newline + end + newline
		if previous.count(start) or previous.count(end):
			if 1 != previous.count(start) or 1 != previous.count(end) or previous.index(start) > previous.index(end):
				return conflict('Malformed or repeated managed markers; surrounding text preserved')
			first, last = (previous.index(start), previous.index(end) + len(end))
			if previous[last:last + len(newline)] == newline:
				last += len(newline)
			current = previous[first:last]
			if current != block and (not owned or _digest(current) != owned['sha256']):
				return conflict('Managed block was manually changed or is unowned; reconcile explicitly')
			payload = previous[:first] + block + previous[last:]
		else:
			if owned and previous:
				return conflict('Previously published block was removed; manual text preserved')
			offset = 3 if previous.startswith(b'\xef\xbb\xbf') else 0
			if 'append' == position:
				offset = len(previous)
			elif 'after-title' == position and previous[offset:].startswith(b'# '):
				end_of_title = previous.find(b'\n', offset)
				offset = end_of_title + 1 if end_of_title >= 0 else len(previous)
			prefix, suffix = (previous[:offset], previous[offset:])
			before = newline if prefix and (not prefix.endswith(newline * 2)) else b''
			if prefix and (not prefix.endswith(newline)):
				before = newline * 2
			after = newline if suffix and (not suffix.startswith(newline)) else b''
			payload = prefix + before + block + after + suffix
		metadata = {'sha256': _digest(block), 'source': str(source) if None is not source else None}
		if None is not attributes:
			metadata['data'] = attributes
		changed = payload != previous
		receipt_changed = owned != metadata
		if check:
			return {**result, 'status': 'stale' if changed or receipt_changed else 'unchanged', 'sha256': _digest(block), 'detail': 'Read-only comparison; no files written'}
		if (target.read_bytes() if target.exists() else b'') != previous:
			return conflict('Target changed during publication; external edit preserved')
		if changed:
			replace_bytes(target, payload)
		if target.read_bytes() != payload:
			return conflict('Publication read-back differs; inspect the target before retrying')
		if receipt_changed:
			entry.setdefault('managed_blocks', {})[key] = metadata
			receipts[str(target)] = entry
			replace_bytes(receipt_path, (json.dumps(receipts, ensure_ascii=False, indent=2) + '\n').encode())
		return {**result, 'status': 'published' if changed else 'unchanged', 'sha256': _digest(block)}
