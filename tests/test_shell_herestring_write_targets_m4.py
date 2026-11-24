# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Strip PowerShell here-strings before shell redirect write-target scanning":
# https://github.com/dmitry-ai/harness/issues/221
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.tdd.commands import shell_code_write_targets, shell_write_targets
class ShellHerestringWriteTargetsM4Tests(unittest.TestCase):
	def test_ignores_arrows_and_html_inside_powershell_herestring(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			cmd = (
				"[Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
				"@'\n"
				"from pathlib import Path\n"
				"# Replace 1ec1afe3bf226aa2.js -> 5a22ddc1f29847fc.js in prose/URLs first\n"
				"tag = '<script src=\"x\" defer></script>'\n"
				"# dependency order (facts -> identity -> concerns -> misconceptions -> causes -> methods)\n"
				"Path('analysis-candidate.json').write_text('{}', encoding='utf-8')\n"
				"'@ | python -"
			)
			all_targets = shell_write_targets(cmd, cwd=base)
			code_targets = shell_code_write_targets(cmd, cwd=base)
			self.assertEqual([base / 'analysis-candidate.json'], all_targets)
			self.assertEqual([], code_targets)
	def test_ignores_double_quoted_herestring_and_bash_heredoc_bodies(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			ps_cmd = '@"\n# foo.js -> bar.js\nprint("a => baz.py")\n"@ | python -'
			sh_cmd = "cat <<'EOF' | python -\n# alpha.js -> beta.js\necho hi > fake.py\nEOF"
			quoted_cmd = 'python -c "x = \'a -> bogus.js\'; y = \'c > bogus2.py\'"'
			self.assertEqual([], shell_code_write_targets(ps_cmd, cwd=base))
			self.assertEqual([], shell_code_write_targets(sh_cmd, cwd=base))
			self.assertEqual([], shell_code_write_targets(quoted_cmd, cwd=base))
	def test_preserves_real_shell_redirects_and_embedded_code_writes(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			redir_cmd = 'echo "a -> fake.js" > real.js'
			heredoc_redir = "cat <<EOF > generated.py\n# comment -> ignored.js\nprint(1)\nEOF"
			py_embed = "@'\nfrom pathlib import Path\nPath('prod.js').write_text('x', encoding='utf-8')\n'@ | python -"
			open_embed = "@'\nopen('worker.py', 'w', encoding='utf-8').write('x')\n'@ | python -"
			self.assertEqual([base / 'real.js'], shell_code_write_targets(redir_cmd, cwd=base))
			self.assertEqual([base / 'generated.py'], shell_code_write_targets(heredoc_redir, cwd=base))
			self.assertEqual([base / 'prod.js'], shell_code_write_targets(py_embed, cwd=base))
			self.assertEqual([base / 'worker.py'], shell_code_write_targets(open_embed, cwd=base))
if '__main__' == __name__:
	unittest.main()
