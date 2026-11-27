# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from agent_tools.storage import locked, replace_bytes, write_immutable_bytes
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class OwnedPublisher:
	# @used-by :func:`agent_tools.analysis.publish_owned()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, target, content, *, source=None, history: bool=True, replace_fn=None) -> None:
		self.__target = Path(target).resolve()
		self.__payload = content.encode('utf-8') if isinstance(content, str) else content
		self.__source = source
		self.__history = history
		self.__replace = replace_fn or replace_bytes
	# @used-by :meth:`OwnedPublisher.publish()`
	def __check_links(self) -> None:
		if self.__target.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm'):
			from agent_tools.links import readable_link_issues
			issues = readable_link_issues(self.__payload.decode('utf-8'))
			if issues:
				raise ValueError('\n'.join(issues))
	# @used-by :meth:`OwnedPublisher.publish()`
	def __commit_locked(self, state_dir: Path, state_file: Path) -> dict:
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		key = str(self.__target)
		previous = self.__target.read_bytes() if self.__target.exists() else None
		expected = receipt.get(key, {}).get('sha256')
		if None is not previous and previous != self.__payload and (df_sha256(previous) != expected):
			candidate = write_immutable_bytes(state_dir / 'render-candidates' / (df_sha256(key.encode())[:16] + '-' + df_sha256(self.__payload)[:16] + self.__target.suffix), self.__payload)
			r = {'status': 'conflict', 'target': str(self.__target), 'candidate': str(candidate), 'detail': 'Existing file is untracked or changed; preserved for reconciliation'}
		else:
			r = self.__write_new(state_dir, state_file, receipt, key, previous)
		return r
	# @used-by :meth:`OwnedPublisher.__write_new()`
	def __source_label(self):
		if isinstance(self.__source, dict):
			r = self.__source
		elif self.__source:
			r = str(self.__source)
		else:
			r = None
		return r
	# @used-by :meth:`OwnedPublisher.__commit_locked()`
	def __write_new(self, state_dir: Path, state_file: Path, receipt: dict, key: str, previous: bytes | None) -> dict:
		if self.__history and None is not previous and (previous != self.__payload):
			write_immutable_bytes(state_dir / 'render-history' / df_sha256(key.encode())[:16] / (df_sha256(previous) + self.__target.suffix), previous)
		self.__target.parent.mkdir(parents=True, exist_ok=True)
		if (self.__target.read_bytes() if self.__target.exists() else None) != previous:
			raise ValueError('Target changed during publication; preserve the external edit and retry reconciliation')
		if previous != self.__payload:
			self.__replace(self.__target, self.__payload)
		if self.__target.read_bytes() != self.__payload:
			raise OSError('Published file failed read-back verification')
		sha = df_sha256(self.__payload)
		receipt[key] = {**receipt.get(key, {}), 'sha256': sha, 'source': self.__source_label()}
		self.__replace(state_file, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
		return {'status': 'unchanged' if previous == self.__payload else 'published', 'target': str(self.__target), 'sha256': sha}
	# @used-by :func:`agent_tools.analysis.publish_owned()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def publish(self) -> dict:
		from agent_tools.path_registry import project_paths
		self.__check_links()
		pp = project_paths(self.__target)
		with locked(pp.data_dir / 'render.lock'):
			r = self.__commit_locked(pp.data_dir, pp.rendered_json)
		return r