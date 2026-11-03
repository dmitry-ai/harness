# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))

from agent_tools.knowledge import validate_kb_factual_note
from agent_tools.review import authorize
from agent_tools import completion


class TestIssue44(unittest.TestCase):
	def test_validate_kb_factual_note_clean(self):
		clean_text = """# Dev-Server Research (2026-11-04)
The development server is hosted at `https://ba53a028dc.nxcli.io/`.
The IP address is `209.87.149.81` on Nexcess hosting.
The git branch `hyva-theme-install` was checked out on 2026-01-05.
"""
		issues = validate_kb_factual_note("Dev-Server-Research.md", clean_text)
		self.assertEqual(issues, [])

	def test_validate_kb_factual_note_hypothesis_id(self):
		text = """# Research Note
We observe issue H-1 in the storefront.
"""
		issues = validate_kb_factual_note("Research.md", text)
		self.assertTrue(any("Hypothesis/method identifier 'H-1' forbidden" in iss for iss in issues))

	def test_validate_kb_factual_note_analytical_heading(self):
		text = """# Research Note
## Hypotheses
The theme is broken.
"""
		issues = validate_kb_factual_note("Research.md", text)
		self.assertTrue(any("Analytical heading '## Hypotheses' forbidden" in iss for iss in issues))

	def test_validate_kb_factual_note_pro_con(self):
		text = """# Research Note
Arguments for: server is slow.
Arguments against: cache is disabled.
"""
		issues = validate_kb_factual_note("Research.md", text)
		self.assertTrue(any("Structured pro/con arguments" in iss for iss in issues))

	def test_validate_kb_factual_note_root_cause(self):
		text = """# Research Note
The root cause is missing varnish configuration.
"""
		issues = validate_kb_factual_note("Research.md", text)
		self.assertTrue(any("Causal assertion 'root cause'" in iss for iss in issues))

	@patch('agent_tools.review._analysis')
	def test_authorize_post_finalize_ignores_historical_questions(self, mock_analysis):
		mock_analysis.return_value = {"schema_version": 3}
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			state = {
				"reviews": [],
				"stages": {
					"finalize": {"status": "complete", "time": "2026-10-27T00:00:00+00:00"}
				},
				"questions": {
					"Q-HISTORICAL": {
						"id": "Q-HISTORICAL",
						"status": "pending",
						"created_at": "2026-10-26T12:00:00+00:00",
						"time": "2026-10-26T12:00:00+00:00"
					}
				}
			}
			# Does not raise questions error because Q-HISTORICAL was created before finalize
			with self.assertRaises(ValueError) as cm:
				authorize(root, state, response="Simple answer without H/M")
			self.assertNotIn("Complete current research questions/gaps", str(cm.exception))

	@patch('agent_tools.review._analysis')
	def test_authorize_post_finalize_enforces_post_finalize_questions(self, mock_analysis):
		mock_analysis.return_value = {"schema_version": 3}
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			state = {
				"reviews": [],
				"stages": {
					"finalize": {"status": "complete", "time": "2026-10-27T00:00:00+00:00"}
				},
				"questions": {
					"Q-NEW": {
						"id": "Q-NEW",
						"status": "pending",
						"created_at": "2026-10-28T12:00:00+00:00",
						"time": "2026-10-28T12:00:00+00:00"
					}
				}
			}
			with self.assertRaises(ValueError) as cm:
				authorize(root, state, response="Simple answer without H/M")
			self.assertIn("Complete current research questions/gaps before publication", str(cm.exception))

	@patch('agent_tools.review._analysis')
	def test_authorize_post_finalize_enforces_request_scoped_questions(self, mock_analysis):
		mock_analysis.return_value = {"schema_version": 3}
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			state = {
				"reviews": [],
				"stages": {
					"finalize": {"status": "complete", "time": "2026-10-27T00:00:00+00:00"}
				},
				"questions": {
					"Q-REQ": {
						"id": "Q-REQ",
						"request_id": "REQ-1",
						"status": "pending",
						"created_at": "2026-10-25T12:00:00+00:00",
						"time": "2026-10-25T12:00:00+00:00"
					}
				}
			}
			with self.assertRaises(ValueError) as cm:
				authorize(root, state, response="Simple answer without H/M", request_ids={"REQ-1"})
			self.assertIn("Complete current research questions/gaps before publication", str(cm.exception))

	def test_completion_commands_has_reconcile_unprepared_delivery(self):
		self.assertIn('reconcile-unprepared-delivery', completion.COMMANDS)


if __name__ == "__main__":
	unittest.main()
