import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.github_issue import lint_issue_markdown, main


class TestGitHubIssueTool(unittest.TestCase):
    def test_clean_markdown_passes(self):
        clean = (
            "## 1. Root Cause\n"
            "In `Magento\\PageCache\\Model\\Cache\\Warmer` (`vendor/magento/module-page-cache/Model/Cache/Warmer.php`, lines 122–125 — see §6.1):\n"
            "```php\n"
            "$identifier = $this->cookieManager->getCookie('affiliate_identifier') ?: null;\n"
            "if ($identifier && $this->customerSession->getId()) {\n"
            "    $this->accountService->ensureCustomerRelation((string)$identifier, `0`);\n"
            "}\n"
            "```\n"
            "```xml\n"
            "    <type name=\"Magento\\Framework\\Data\\Form\\FormKey\">\n"
            "        <arguments>\n"
            "            <argument name=\"session\" xsi:type=\"object\">Magento\\Framework\\Session\\Generic\\Proxy</argument>\n"
            "        </arguments>\n"
            "    </type>\n"
            "```\n"
            "Paginated URLs like `/water-pipes.html?p=2` work across «Customers» in `0.131–0.325` seconds.\n"
        )
        self.assertEqual(lint_issue_markdown(clean), [])

    def test_detects_all_seven_powershell_corruption_classes(self):
        # Class A: Truncated end & NUL byte from `0
        errs_a = lint_issue_markdown("### Problem\nOut of Stock (\\")
        codes_a = {e['code'] for e in errs_a}
        self.assertIn('TRUNCATED_END', codes_a)

        errs_nul = lint_issue_markdown("### Problem\nversion \x000.0.1")
        self.assertIn('CONTROL_CHAR', {e['code'] for e in errs_nul})

        # Class B: Control chars (`a -> \x07, `b -> \x08, `v -> \x0b, `f -> \x0c, `t -> \t)
        errs_b = lint_issue_markdown("### Problem\nIn (\x0bendor/magento) and (\true) and (\\x08in/magento)")
        codes_b = {e['code'] for e in errs_b}
        self.assertIn('CONTROL_CHAR', codes_b)
        self.assertIn('INLINE_TAB_ESCAPE', codes_b)

        # Class C: Stripped backticks, \token\ from \`token\`, broken ``php fence
        errs_c1 = lint_issue_markdown("### Problem\nRun \\bin/magento page-cache:warm\\ to warm `cache`.")
        self.assertIn('BACKSLASH_WRAPPED_CODE', {e['code'] for e in errs_c1})

        errs_c2 = lint_issue_markdown(
            "### Problem\n`Mirasvit` calls:\n``php\n$x = 1;\n``\n"
        )
        self.assertIn('BROKEN_CODE_FENCE', {e['code'] for e in errs_c2})

        errs_c3 = lint_issue_markdown(
            "### Problem\n" + "In vendor/magento/module-page-cache/Model/Cache/Warmer.php::execute() " * 4
        )
        self.assertIn('STRIPPED_ALL_BACKTICKS', {e['code'] for e in errs_c3})

        # Class D: Eaten PHP $variables
        errs_d = lint_issue_markdown(
            "### Problem\nWhen `!->shouldRedirectToCart()`, call `->updateCache(, )` and `empty()` or `(?callable  = null)`."
        )
        codes_d = {e['code'] for e in errs_d}
        self.assertIn('EATEN_VARIABLE_ARROW', codes_d)
        self.assertIn('EATEN_VARIABLE_ARG', codes_d)

        # Class E: ASCII '?' replacing en-dash/em-dash/guillemets/section sign
        errs_e = lint_issue_markdown(
            "### Problem\nTakes `43?45` seconds on every request?even when rows ? causing `?Customers?` in ?6.1."
        )
        codes_e = {e['code'] for e in errs_e}
        self.assertIn('QUESTION_MARK_RANGE', codes_e)
        self.assertIn('QUESTION_MARK_WORD_JOIN', codes_e)
        self.assertIn('QUESTION_MARK_SPACED', codes_e)
        self.assertIn('QUESTION_MARK_QUOTES', codes_e)
        self.assertIn('QUESTION_MARK_SECTION', codes_e)

        # Class F: Leading UTF-8 BOM
        errs_f = lint_issue_markdown("\ufeff### Problem\nValid `code` here.")
        self.assertIn('UTF8_BOM', {e['code'] for e in errs_f})

        # Class G: Unquoted XML attributes from PowerShell --body $body
        errs_g = lint_issue_markdown(
            "### Problem\n```xml\n<type name=Magento\\Framework\\Data\\Form\\FormKey>\n"
            "<argument name=session xsi:type=object>Proxy</argument>\n</type>\n```"
        )
        self.assertIn('UNQUOTED_XML_ATTR', {e['code'] for e in errs_g})

    def test_create_and_consume_input_with_readback_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            body_path = Path(tmp) / 'body.md'
            body_text = "## Summary\nFix `Magento\\Framework\\Data\\Form\\FormKey` in lines 10–20.\n"
            body_path.write_text(body_text, encoding='utf-8')

            def fake_run(cmd, *, input=None, capture_output=True, check=False):
                class DummyProc:
                    returncode = 0
                    stderr = b''
                    stdout = b''
                proc = DummyProc()
                if '-X' in cmd and 'POST' in cmd:
                    payload = json.loads(input.decode('utf-8'))
                    proc.stdout = json.dumps({'number': 46, 'title': payload['title'], 'body': payload['body']}).encode('utf-8')
                else:
                    proc.stdout = json.dumps({
                        'number': 46,
                        'title': 'Test issue title',
                        'body': body_text,
                        'html_url': 'https://github.com/smokeday-com/m/issues/46',
                    }).encode('utf-8')
                return proc

            with patch('agent_tools.github_issue.subprocess.run', side_effect=fake_run):
                rc = main([
                    'create',
                    '--repo', 'smokeday-com/m',
                    '--title', 'Test issue title',
                    '--body-file', str(body_path),
                    '--consume-input',
                ])
                self.assertEqual(rc, 0)
                self.assertFalse(body_path.exists())


if __name__ == '__main__':
    unittest.main()
