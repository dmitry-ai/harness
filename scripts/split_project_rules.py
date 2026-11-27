# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.lib.rule_splitter import dfh_slugify as slugify, dfh_split_rules as split_rules, dfh_split_rules_main as main
if '__main__' == __name__:
	main()