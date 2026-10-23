"""Repository guidance generation, safe updates and preservation of manual files."""

import json
import shutil
import tomllib

from test_agent_tools import TemporaryCase
from agent_tools import configuration, runtime


class AgentsLoaderTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.primary = self.root / 'canonical'
        for relative in ('rules', 'platforms', 'skills/upwork-init', 'agents'):
            (self.primary / relative).mkdir(parents=True, exist_ok=True)
        for path in runtime.PRIMARY.joinpath('rules').glob('*.md'):
            shutil.copyfile(path, self.primary / 'rules' / path.name)
        for relative in ('runtime.json', 'platforms/codex.md',
                         'skills/upwork-init/SKILL.md', 'agents/worker.md'):
            shutil.copyfile(runtime.PRIMARY / relative, self.primary / relative)
        self.output = self.root / 'workspace'

    def build(self, *, check=False):
        return configuration.build_native(self.output, primary=self.primary, check=check)

    def snapshot(self):
        return {p.relative_to(self.output).as_posix(): p.read_bytes()
                for p in self.output.rglob('*')
                if p.is_file() and p.relative_to(self.output).as_posix() != 'ꘖ/data/native-config.lock'}

    def test_guidance_uses_current_canonical_loader_without_copying_rule_bodies(self):
        rule = self.primary / 'rules/90-loader-test.md'
        rule.write_text('CANONICAL BODY MUST STAY IN ITS SOURCE\n', encoding='utf-8')
        result = self.build()
        self.assertTrue(result['valid'], result)
        guidance = self.output / 'AGENTS.md'
        text = guidance.read_text(encoding='utf-8')
        for source in [*self.primary.joinpath('rules').glob('*.md'),
                       self.primary / 'platforms/codex.md']:
            self.assertIn(source.as_posix(), text)
        self.assertIn('.agents/rules/*.md', text)
        self.assertIn('.agents/rules.json', text)
        self.assertIn('turn-begin', text)
        self.assertIn('answer-prepare', text)
        self.assertNotIn('CANONICAL BODY MUST STAY IN ITS SOURCE', text)
        native = tomllib.loads((self.output / '.codex/config.toml').read_text(encoding='utf-8'))
        loader = native['developer_instructions'].split(configuration.START, 1)[1]
        loader = loader.split(configuration.END, 1)[0].strip()
        self.assertIn(loader, text)
        receipt = json.loads((self.output / 'ꘖ/data/native-config.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt[str(guidance.resolve())], configuration._digest(guidance.read_bytes()))

    def test_check_detects_missing_guidance_without_writing_and_build_repairs_it(self):
        self.assertTrue(self.build()['valid'])
        guidance = self.output / 'AGENTS.md'
        wanted = guidance.read_bytes()
        guidance.unlink()
        before = self.snapshot()
        result = self.build(check=True)
        self.assertFalse(result['valid'])
        self.assertTrue(any(item['file'] == str(guidance.resolve()) for item in result['issues']))
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.build()['valid'])
        self.assertEqual(guidance.read_bytes(), wanted)
        self.assertTrue(self.build(check=True)['valid'])
        self.assertEqual(self.build()['written'], [])

    def test_existing_unowned_guidance_is_preserved_without_partial_installation(self):
        self.output.mkdir()
        guidance = self.output / 'AGENTS.md'
        guidance.write_bytes(b'User rules\r\nKeep exact bytes.\r\n')
        before = self.snapshot()
        result = self.build()
        self.assertFalse(result['valid'])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.primary / 'agents/af-worker.md').exists())

    def test_edit_to_generated_guidance_blocks_other_pending_configuration_updates(self):
        self.assertTrue(self.build()['valid'])
        guidance = self.output / 'AGENTS.md'
        guidance.write_bytes(guidance.read_bytes() + b'\nManual user addition.\n')
        (self.primary / 'rules/91-new.md').write_text('New rule.\n', encoding='utf-8')
        before = self.snapshot()
        result = self.build()
        self.assertFalse(result['valid'])
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(any(item['file'] == str(guidance.resolve()) for item in result['issues']))

    def test_new_source_path_updates_guidance_and_existing_toml_together(self):
        self.assertTrue(self.build()['valid'])
        rule = self.primary / 'rules/91-new.md'
        rule.write_text('Read this policy by reference.\n', encoding='utf-8')
        before = self.snapshot()
        self.assertFalse(self.build(check=True)['valid'])
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.build()['valid'])
        self.assertIn(rule.as_posix(), (self.output / 'AGENTS.md').read_text(encoding='utf-8'))
        native = tomllib.loads((self.output / '.codex/config.toml').read_text(encoding='utf-8'))
        self.assertIn(rule.as_posix(), native['developer_instructions'])
        self.assertTrue(self.build(check=True)['valid'])
