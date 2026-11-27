# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.journal import _raw_state_dir, resolve_journal_dir
from agent_tools.path_registry import project_paths
from agent_tools.storage import replace_bytes
from datetime import datetime, timezone
from Df.Core.lib.text.source import df_text_rewrite_pairs
from Df.Harness.lib.project import dfh_rewrite_value
from Df.Harness.Project.Rename.RenameLineage import RenameLineage
import hashlib
import json
import os
from pathlib import Path
import re
_FOLDER_RULE_RE = re.compile(r'(?m)^Folder name:\s*`[^`]+`;')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StateRewriter:
	# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__apply_mutations()`
	def __init__(self, old_root: Path, new_root: Path, new_label: str, new_label_kind: str, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> None:
		self.__old_root, self.__new_root = (old_root, new_root)
		self.__new_label, self.__new_label_kind = (new_label, new_label_kind)
		self.__backups, self.__state_moves = (backups, state_moves)
	# @used-by :meth:`StateRewriter.__rewrite_json_file()`
	# @used-by :meth:`StateRewriter.__update_folder_rule()`
	# @used-by :meth:`StateRewriter.__update_project_json()`
	# @used-by :meth:`StateRewriter.rewrite()`
	# @used-by :meth:`StateRewriter.rewrite_launcher_handoffs()`
	@staticmethod
	def __record_backup(path: Path, backups: list[tuple[Path, bytes | None]] | None) -> None:
		if None is not backups and (not any((p == path for p, _ in backups))):
			backups.append((path, path.read_bytes() if path.is_file() else None))
	# @used-by :meth:`StateRewriter.migrate_journal_state()`
	# @used-by :meth:`StateRewriter.refresh_workflow_file_hash()`
	# @used-by :meth:`StateRewriter.rewrite()`
	@classmethod
	def __rewrite_json_file(cls, path: Path, pairs: list[tuple[str, str]], backups: list[tuple[Path, bytes | None]] | None=None) -> None:
		if path.is_file():
			cls.__record_backup(path, backups)
			updated = dfh_rewrite_value(json.loads(path.read_text(encoding='utf-8-sig')), pairs)
			replace_bytes(path, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	# @used-by :meth:`StateRewriter.rewrite()`
	@classmethod
	def __update_folder_rule(cls, new_root: Path, new_label: str, backups: list[tuple[Path, bytes | None]] | None=None) -> None:
		rule_f = new_root / '.agents/rules/90-project.md'
		if rule_f.is_file():
			orig = rule_f.read_text(encoding='utf-8')
			updated = _FOLDER_RULE_RE.sub(lambda _m: f'Folder name: `{new_label}`;', orig)
			if updated != orig:
				cls.__record_backup(rule_f, backups)
				replace_bytes(rule_f, updated.encode('utf-8'))
	# @used-by :meth:`StateRewriter.rewrite()`
	@classmethod
	def __update_project_json(cls, old_root: Path, new_root: Path, new_label: str, new_label_kind: str, backups: list[tuple[Path, bytes | None]] | None=None) -> tuple[dict, str, str]:
		pj_path = project_paths(new_root, exact_root=True).project_json
		cls.__record_backup(pj_path, backups)
		old_raw = pj_path.read_bytes()
		state = json.loads(old_raw.decode('utf-8-sig'))
		history = list(state.get('renamed_from') or [])
		history.append({'from': str(old_root), 'to': str(new_root), 'from_name': old_root.name, 'to_name': new_root.name, 'at': datetime.now(timezone.utc).isoformat()})
		state['label'], state['label_kind'], state['renamed_from'] = (new_label, new_label_kind, history)
		new_raw = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		replace_bytes(pj_path, new_raw)
		return (state, hashlib.sha256(old_raw).hexdigest(), hashlib.sha256(new_raw).hexdigest())
	# @used-by :func:`agent_tools.project_rename_state.migrate_journal_state()`
	# @used-by :meth:`StateRewriter.rewrite()`
	@classmethod
	def migrate_journal_state(cls, old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> tuple[Path, Path]:
		new_pp = project_paths(new_root, exact_root=True)
		new_jdir = resolve_journal_dir(new_root)
		old_jdir = old_root / new_jdir.relative_to(new_root)
		old_state, new_state = (_raw_state_dir(old_jdir, data_root=new_pp.data_dir), _raw_state_dir(new_jdir, data_root=new_pp.data_dir))
		if old_state.is_dir() and old_state.resolve() != new_state.resolve():
			(old_state / 'writer.lock').unlink(missing_ok=True)
			if not new_state.exists():
				new_state.parent.mkdir(parents=True, exist_ok=True)
				os.replace(old_state, new_state)
				if None is not state_moves:
					state_moves.append((old_state, new_state))
		pairs = RenameLineage.path_pairs(old_root, new_root, old_state, new_state)
		if new_state.is_dir():
			for item in sorted(new_state.rglob('*.json')):
				cls.__rewrite_json_file(item, pairs, backups)
		return (old_state, new_state)
	# @used-by :func:`agent_tools.project_rename_state.refresh_workflow_file_hash()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_registrations()`
	@classmethod
	def refresh_workflow_file_hash(cls, new_root: Path, target_file: Path, old_sha: str | None) -> None:
		new_sha = RenameLineage.capture_file_sha(target_file)
		if old_sha and new_sha and old_sha != new_sha:
			cls.__rewrite_json_file(project_paths(new_root, exact_root=True).data_dir / 'workflow.json', [(old_sha, new_sha)])
	# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__apply_mutations()`
	def rewrite(self) -> dict:
		old_state, new_state = self.migrate_journal_state(self.__old_root, self.__new_root, backups=self.__backups, state_moves=self.__state_moves)
		pairs = RenameLineage.path_pairs(self.__old_root, self.__new_root, old_state, new_state)
		state, old_pj_sha, new_pj_sha = self.__update_project_json(self.__old_root, self.__new_root, self.__new_label, self.__new_label_kind, self.__backups)
		self.__update_folder_rule(self.__new_root, self.__new_label, self.__backups)
		pp = project_paths(self.__new_root, exact_root=True)
		self.__rewrite_json_file(pp.data_dir / 'workflow.json', [*pairs, (old_pj_sha, new_pj_sha)], self.__backups)
		self.__rewrite_json_file(pp.data_dir / 'rendered.json', pairs, self.__backups)
		if pp.turns_dir.is_dir():
			for tf in sorted(pp.turns_dir.glob('*.json')):
				self.__rewrite_json_file(tf, pairs, self.__backups)
		if pp.scratch_dir.is_dir():
			for df in sorted(pp.scratch_dir.glob('answer-*.md')):
				orig = df.read_text(encoding='utf-8-sig')
				updated = df_text_rewrite_pairs(orig, pairs)
				if updated != orig:
					self.__record_backup(df, self.__backups)
					replace_bytes(df, updated.encode('utf-8'))
		return state
	# @used-by :func:`agent_tools.project_rename_state.rewrite_launcher_handoffs()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__apply_mutations()`
	@classmethod
	def rewrite_launcher_handoffs(cls, launcher_root: Path, old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None) -> int:
		turns_dir = project_paths(Path(launcher_root).resolve(), exact_root=True).turns_dir
		pairs = RenameLineage.path_pairs(old_root, new_root, None, None)
		count = 0
		if turns_dir.is_dir():
			for sf in sorted(turns_dir.glob('*.json')):
				try:
					data = json.loads(sf.read_text(encoding='utf-8-sig'))
				except (OSError, ValueError):
					continue
				updated = dfh_rewrite_value(data, pairs)
				if updated != data:
					cls.__record_backup(sf, backups)
					replace_bytes(sf, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
					count += 1
		return count
