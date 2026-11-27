# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Completion.NarrowReconciler import NarrowReconciler
# @used-by unused
def resolve_saved_turn_requests(root: Path, native: dict, turn: dict, value: dict, *, recovered: bool, same_req_fn, journal_dir_fn) -> list:
	return NarrowReconciler(root, native, turn, value, recovered=recovered, same_req_fn=same_req_fn, journal_dir_fn=journal_dir_fn).run()