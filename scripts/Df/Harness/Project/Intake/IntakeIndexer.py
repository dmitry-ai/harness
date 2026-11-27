# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.path_registry import project_paths
from Df.Harness.Analysis.OwnedPublisher import OwnedPublisher
from Df.Harness.Project.CardSyncer import CardSyncer
from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class IntakeIndexer:
	# @used-by :func:`agent_tools.intake._index()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__init__()`
	def __init__(self, project: Path) -> None:
		self.__project = project
	# @used-by :meth:`IntakeIndexer.rebuild()`
	def __render_lines(self, kb_rel: str, ev_rel: str) -> list[str]:
		ev_in_kb = Path(ev_rel).relative_to(kb_rel).as_posix() if Path(ev_rel).is_relative_to(kb_rel) else 'Evidence'
		r = [IntakePathGuard.INDEX_MARKER.rstrip(), '# Source Materials', '', 'Previous paths in receipts record provenance only. Working links point to permanent evidence.', '']
		for path in sorted(IntakePathGuard.within(self.__project, f'{ev_rel}/Intake').glob('*.json')):
			receipt = json.loads(IntakePathGuard.read_stable(path).decode('utf-8-sig'))
			r.extend([f"## {receipt['capture_id']}", '', f'[Receipt]({ev_in_kb}/Intake/{path.name}).', ''])
			for entry in receipt['entries']:
				rel = Path(entry['durable_file']).relative_to(kb_rel).as_posix()
				label = entry['original_relative_provenance'].replace('[', '\\[').replace(']', '\\]')
				r.append(f"- [{label}](<{rel}>) — SHA-256 `{entry['sha256']}`.")
			r.append('')
		return r
	# @used-by :func:`agent_tools.intake._index()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__init__()`
	def rebuild(self) -> None:
		pp = project_paths(self.__project, exact_root=True)
		kb_rel, ev_rel = (pp.rel_to_root(pp.kb_dir), pp.rel_to_root(pp.evidence_dir))
		target = IntakePathGuard.within(self.__project, f'{kb_rel}/Intake.md')
		if target.exists() and (not IntakePathGuard.read_stable(target).decode('utf-8-sig').startswith(IntakePathGuard.INDEX_MARKER)):
			raise ValueError('Manual KB/Intake.md is preserved; intake drain is deferred')
		lines = self.__render_lines(kb_rel, ev_rel)
		if 'conflict' == OwnedPublisher(target, '\n'.join(lines) + '\n', history=False).publish()['status']:
			raise ValueError('Intake index was manually changed; preserve it and reconcile the publication candidate')
		nav = CardSyncer(self.__project, IntakePathGuard.within(self.__project, f'{kb_rel}/.md'), 'intake-navigation', '## Source Materials\n\n[Saved sources and import receipts](Intake.md).\n', position='append', source=target).sync()
		if 'conflict' == nav['status']:
			raise ValueError('Intake navigation was manually changed; staging is preserved for reconciliation')
