# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
# https://github.com/dmitry-ai/harness/issues/5
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
import json
from .diagnostics import problem
from .storage import create_bytes, locked, replace_bytes
FLAGS = {'RF-CLIENT-INTERMEDIARY': ('Client is an intermediary', ('confirmed', 'suspected')), 'RF-WEBSITE-UNIDENTIFIED': ('Target website is unidentified', ('unresolved',))}
STATUSES = {'confirmed': 'confirmed', 'suspected': 'hypothesis', 'unresolved': 'unresolved from available data'}
START = b'<!-- upwork-init:red-flags:start -->'
END = b'<!-- upwork-init:red-flags:end -->'
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
# https://github.com/dmitry-ai/harness/issues/5
def red_flag_issues(value, claims):
	if 'red_flags' not in value:
		r = []
	else:
		flags = value['red_flags']
		if not isinstance(flags, list):
			r = [problem('red_flags.list', '/red_flags', 'red_flags must be a list')]
		else:
			issues, seen = ([], set())
			for index, flag in enumerate(flags):
				field = f'/red_flags/{index}'
				if not isinstance(flag, dict):
					issues.append(problem('red_flags.object', field, 'A red flag must be an object'))
					continue
				ident = flag.get('id')
				if not isinstance(ident, str) or ident not in FLAGS or ident in seen:
					issues.append(problem('red_flags.id', field + '/id', 'Unknown or duplicate red flag ID'))
				else:
					seen.add(ident)
					if flag.get('status') not in FLAGS[ident][1]:
						issues.append(problem('red_flags.status', field + '/status', 'Use the status allowed for this flag'))
				if not isinstance(flag.get('summary'), str) or not flag['summary'].strip():
					issues.append(problem('red_flags.summary', field + '/summary', 'Explain this project-specific risk'))
				refs = flag.get('basis_ids')
				if not isinstance(refs, list) or not refs or any((not isinstance(ref, str) or 'identity' != claims.get(ref) for ref in refs)):
					issues.append(problem('red_flags.basis', field + '/basis_ids', 'Reference existing identity claims with evidence'))
			r = issues
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
# https://github.com/dmitry-ai/harness/issues/5
def render_red_flags(value, *, project_card=False):
	flags = value.get('red_flags', [])
	if not flags:
		r = ''
	else:
		by_id = {flag['id']: flag for flag in flags}
		lines = [f'# Red Flags — {len(flags)}', '']
		if 2 == len(by_id):
			qualifier = ' (intermediation is currently a hypothesis)' if 'suspected' == by_id['RF-CLIENT-INTERMEDIARY']['status'] else ''
			lines += [f'**Both Red Flags simultaneously{qualifier}: high likelihood of declining the project.**', '']
		pointers = {claim['id']: f'ꘖ/KB/Analysis.json#/identity/{index}' for index, claim in enumerate(value['identity'])}
		for ident in FLAGS:
			if ident not in by_id:
				continue
			flag = by_id[ident]
			lines += [f"- **{FLAGS[ident][0]}.** Status: {STATUSES[flag['status']]}.", '  ' + flag['summary'].strip().replace('\n', '\n  '), '  Basis: ' + ', '.join((f"[{ref}](<{(pointers[ref] if project_card else '#' + ref.lower())}>)" for ref in flag['basis_ids'])) + '.', '']
		r = '\n'.join(lines) + '\n'
	return r
def sync_project_red_flags(root, value):
	from .analysis import digest, validate_analysis
	validate_analysis(value)
	root = Path(root).resolve()
	target = root / '.md'
	if 'red_flags' not in value:
		return {'status': 'unassessed', 'target': str(target)}
	state_dir = root / 'ꘖ/data'
	state_file = state_dir / 'red-flags.json'
	with locked(state_dir / 'red-flags.lock'):
		original = target.read_bytes()
		original.decode('utf-8-sig')
		newline = b'\r\n' if b'\r\n' in original else b'\n'
		rendered = render_red_flags(value, project_card=True)
		title, content = rendered.split('\n\n', 1) if rendered else ('', '')
		heading = (title + '\n\n').encode('utf-8').replace(b'\n', newline) if title else b''
		content = content.encode('utf-8').replace(b'\n', newline)
		block = START + newline + newline + content + END + newline if content else b''
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		current, body = (b'', original)
		if START in original or END in original:
			if 1 != original.count(START) or 1 != original.count(END) or original.index(START) > original.index(END):
				return {'status': 'conflict', 'target': str(target), 'detail': 'Malformed Red Flags block; card preserved'}
			start, end = (original.index(START), original.index(END) + len(END))
			ending = newline if receipt.get('heading') else newline * 2
			if original[end:end + len(ending)] == ending:
				end += len(ending)
			elif original[end:end + len(newline)] == newline:
				end += len(newline)
			current = original[start:end]
			if current != block and digest(current) != receipt.get('block_sha256'):
				return {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags block was manually edited; reconcile it explicitly'}
			previous_heading = receipt.get('heading', '').encode('utf-8')
			if previous_heading:
				if not original[:start].endswith(previous_heading):
					return {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags heading was manually edited; reconcile it explicitly'}
				start -= len(previous_heading)
				separator = receipt.get('separator', '').encode('utf-8')
				if separator and original[:start].endswith(separator):
					start -= len(separator)
			elif heading and original[:start].endswith(heading) and (current == block):
				start -= len(heading)
			body = original[:start] + original[end:]
		separator = b''
		if block and body not in (b'', b'\xef\xbb\xbf'):
			separator = b'' if body.endswith(newline * 2) else newline if body.endswith(newline) else newline * 2
		payload = body + separator + heading + block if block else body
		if payload != original:
			archive = state_dir / 'red-flags-history' / (digest(original) + '.md')
			archive.parent.mkdir(parents=True, exist_ok=True)
			if not archive.exists():
				create_bytes(archive, original)
			if target.read_bytes() != original:
				raise ValueError('Project card changed during publication; reread and reconcile')
			replace_bytes(target, payload)
		if target.read_bytes() != payload:
			raise OSError('Project card failed read-back verification')
		metadata = {'block_sha256': digest(block), 'heading': heading.decode('utf-8'), 'separator': separator.decode('utf-8')}
		replace_bytes(state_file, (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	return {'status': 'unchanged' if payload == original else 'published', 'target': str(target), 'sha256': digest(payload)}
