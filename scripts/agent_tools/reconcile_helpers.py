# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from . import journal
from .storage import locked
# @used-by :func:`resolve_saved_turn_requests()`
def _can_narrow_open_turn(root: Path, native: dict, turn: dict, value: dict, old: list, current: list, *, recovered: bool, same_req_fn) -> bool:
	uncommitted = recovered and 'open' == value.get('status') and (not value.get('prepared')) and (not value.get('delivery')) and (not value.get('journal_record'))
	prefix_ok = bool(current) and len(current) < len(old) and all((same_req_fn(o, c, root) for o, c in zip(old, current)))
	return uncommitted and prefix_ok and _tail_present_in_other_turns(root, native, turn, old[len(current):], same_req_fn)
# @used-by :func:`_can_narrow_open_turn()`
def _tail_present_in_other_turns(root: Path, native: dict, turn: dict, tail: list, same_req_fn) -> bool:
	cur_tid = turn.get('turn_id')
	other_reqs = [req for other in native.get('turns') or () if other.get('turn_id') != cur_tid for req in other.get('requests') or () if isinstance(req, dict)]
	return all((any((o.get('id') == t.get('id') and same_req_fn(t, o, root) for o in other_reqs)) for t in tail))
# @used-by :func:`resolve_saved_turn_requests()`
def _trim_narrowed_reservation(jdir: Path, value: dict, current: list) -> None:
	eff = Path(jdir).resolve()
	jstate = journal.state_dir(eff)
	res_file = jstate / journal.TURN_RESERVATIONS_FILE
	cur_ids = [req['id'] for req in current if isinstance(req, dict) and req.get('id')]
	turn_key = str(value.get('key') or '')
	if turn_key and res_file.is_file():
		with locked(jstate / 'writer.lock'):
			reservations = journal._read_turn_reservations(eff)
			entry = reservations.get(turn_key)
			if isinstance(entry, dict):
				pairs = [(rid, st) for rid, st in zip(entry.get('request_ids') or (), entry.get('steps') or ()) if rid in cur_ids]
				if not pairs:
					reservations.pop(turn_key, None)
				else:
					reservations[turn_key] = {'conversation_id': entry.get('conversation_id', ''), 'request_ids': [p[0] for p in pairs], 'steps': [p[1] for p in pairs]}
				journal._write_turn_reservations(eff, reservations)
				if isinstance(value.get('reserved_journal_steps'), list):
					value['reserved_journal_steps'] = [p[1] for p in pairs]
# 2026-11-25
# "Ensure atomic answer-prepare workflow alignment and safe open-turn reconciliation":
# https://github.com/dmitry-ai/harness/issues/232
# @used-by :func:`agent_tools.completion._state()`
def resolve_saved_turn_requests(root: Path, native: dict, turn: dict, value: dict, *, recovered: bool, same_req_fn, journal_dir_fn) -> list:
	# 2026-11-25
	# "Extract ask_question clarification metadata and prohibit Stop Gate bypass via ask_question":
	# https://github.com/dmitry-ai/harness/issues/234
	if turn.get('clarifications'):
		value['clarifications'] = list(turn['clarifications'])
	old, current = (value['requests'], turn['requests'])
	prefix_ok = all((same_req_fn(o, c, root) for o, c in zip(old, current)))
	if len(current) >= len(old) and prefix_ok:
		r = [*old, *current[len(old):]]
	elif _can_narrow_open_turn(root, native, turn, value, old, current, recovered=recovered, same_req_fn=same_req_fn):
		_trim_narrowed_reservation(journal_dir_fn(root, value['journal']), value, current)
		r = list(current)
	else:
		raise ValueError('Native requests changed before the saved boundary; preserved')
	return r
