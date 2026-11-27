# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.journal_core import TURN_RESERVATIONS_FILE, dfh_state_dir
from Df.Harness.lib.journal_reservations import dfh_read_turn_reservations, dfh_write_turn_reservations
from Df.Harness.lib.storage import dfh_locked
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class NarrowReconciler:
	# @used-by :func:`Df.Harness.lib.completion_state._merge_turn_requests()`
	# @used-by :func:`agent_tools.reconcile_helpers.resolve_saved_turn_requests()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def __init__(self, root: Path, native: dict, turn: dict, value: dict, *, recovered: bool, same_req_fn, journal_dir_fn) -> None:
		self.__root = root
		self.__native = native
		self.__turn = turn
		self.__value = value
		self.__recovered = recovered
		self.__same_req_fn = same_req_fn
		self.__journal_dir_fn = journal_dir_fn
	# @used-by :meth:`NarrowReconciler.run()`
	def __can_narrow_open_turn(self, old: list, current: list) -> bool:
		uncommitted = self.__recovered and 'open' == self.__value.get('status') and (not self.__value.get('prepared')) and (not self.__value.get('delivery')) and (not self.__value.get('journal_record'))
		prefix_ok = bool(current) and len(current) < len(old) and all((self.__same_req_fn(o, c, self.__root) for o, c in zip(old, current)))
		return uncommitted and prefix_ok and self.__tail_present_in_other_turns(old[len(current):])
	# @used-by :meth:`NarrowReconciler.__can_narrow_open_turn()`
	def __tail_present_in_other_turns(self, tail: list) -> bool:
		cur_tid = self.__turn.get('turn_id')
		other_reqs = [req for other in self.__native.get('turns') or () if other.get('turn_id') != cur_tid for req in other.get('requests') or () if isinstance(req, dict)]
		return all((any((o.get('id') == t.get('id') and self.__same_req_fn(t, o, self.__root) for o in other_reqs)) for t in tail))
	# @used-by :meth:`NarrowReconciler.run()`
	def __trim_narrowed_reservation(self, jdir: Path, current: list) -> None:
		eff = Path(jdir).resolve()
		jstate = dfh_state_dir(eff)
		res_file = jstate / TURN_RESERVATIONS_FILE
		cur_ids = [req['id'] for req in current if isinstance(req, dict) and req.get('id')]
		turn_key = str(self.__value.get('key') or '')
		if turn_key and res_file.is_file():
			with dfh_locked(jstate / 'writer.lock'):
				reservations = dfh_read_turn_reservations(eff)
				entry = reservations.get(turn_key)
				if isinstance(entry, dict):
					pairs = [(rid, st) for rid, st in zip(entry.get('request_ids') or (), entry.get('steps') or ()) if rid in cur_ids]
					if not pairs:
						reservations.pop(turn_key, None)
					else:
						reservations[turn_key] = {'conversation_id': entry.get('conversation_id', ''), 'request_ids': [p[0] for p in pairs], 'steps': [p[1] for p in pairs]}
					dfh_write_turn_reservations(eff, reservations)
					if isinstance(self.__value.get('reserved_journal_steps'), list):
						self.__value['reserved_journal_steps'] = [p[1] for p in pairs]
	# @used-by :func:`Df.Harness.lib.completion_state._merge_turn_requests()`
	# @used-by :func:`agent_tools.reconcile_helpers.resolve_saved_turn_requests()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def run(self) -> list:
		if self.__turn.get('clarifications'):
			self.__value['clarifications'] = list(self.__turn['clarifications'])
		old, current = (self.__value['requests'], self.__turn['requests'])
		prefix_ok = all((self.__same_req_fn(o, c, self.__root) for o, c in zip(old, current)))
		if len(current) >= len(old) and prefix_ok:
			r = [*old, *current[len(old):]]
		elif self.__can_narrow_open_turn(old, current):
			self.__trim_narrowed_reservation(self.__journal_dir_fn(self.__root, self.__value['journal']), current)
			r = list(current)
		else:
			raise ValueError('Native requests changed before the saved boundary; preserved')
		return r
