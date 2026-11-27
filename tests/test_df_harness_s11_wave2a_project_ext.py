# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aProjectExtTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_project_knowledge_classes(self) -> None:
		from Df.Harness.Project.AttachmentInventory import AttachmentInventory
		from Df.Harness.Project.AttachmentKbSyncer import AttachmentKbSyncer
		from Df.Harness.Project.ExtraSourceBuilder import ExtraSourceBuilder
		from Df.Harness.Project.FactualNoteValidator import FactualNoteValidator
		from Df.Harness.Project.KbPopulator import KbPopulator
		from Df.Harness.Project.OnceFileWriter import OnceFileWriter
		from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			OnceFileWriter(root / '.md', '# Demo\n').write()
			self.assertEqual(b'{\n  "k": 1\n}\n', OnceFileWriter.json_bytes({'k': 1}))
			att_src = root / 'incoming/spec.txt'
			att_src.parent.mkdir(parents=True, exist_ok=True)
			att_b = b'Checkout bug description.'
			att_src.write_bytes(att_b)
			sha = hashlib.sha256(att_b).hexdigest()
			assets = AttachmentInventory(root).sync([{'path': str(att_src), 'filename': 'spec.txt', 'sha256': sha}])
			self.assertEqual(1, len(assets))
			self.assertEqual(1, len(AttachmentInventory(root).scan()['attachments']))
			data = {'job_id': '~02k1', 'title': 'Audit', 'description': 'Fix store.', 'asset_evidence': [{'file': assets[0]['file'], 'sha256': sha}]}
			extras = ExtraSourceBuilder(root, data, assets, fetch_videos=False).build()
			self.assertEqual('spec.txt', extras[0]['name'])
			snap = KbPopulator(root, {**data, 'extra_sources': extras}).populate()
			self.assertTrue(snap.is_file())
			(root / '\ua616/project.json').write_text(json.dumps({'job_id': '~02k1', 'snapshot': snap.relative_to(root).as_posix()}), encoding='utf-8')
			res = AttachmentKbSyncer(root, fetch_videos=False).sync()
			self.assertEqual(1, len(res['source_files']))
			ws_res = WebsiteCardSyncer.sync_initial(root, snap)
			self.assertIn(ws_res['status'], ('published', 'unchanged'))
			self.assertTrue(WebsiteCardSyncer.website_issues({'websites': []}))
			self.assertTrue(FactualNoteValidator(root / 'note.md', '## Hypotheses\nH-1 is root cause.\nArguments for: A.\nArguments against: B.\n').issues())
			self.assertEqual([], FactualNoteValidator(root / 'clean.md', '# Facts\nObserved 200 OK.  \n').issues())
	# @used-by :mod:`unittest`
	def test_project_rename_classes(self) -> None:
		from Df.Harness.Project.Rename.PostRenameVerifier import PostRenameVerifier
		from Df.Harness.Project.Rename.ProjectRenamer import ProjectRenamer
		from Df.Harness.Project.Rename.RenameLineage import RenameLineage
		from Df.Harness.Project.Rename.StateRewriter import StateRewriter
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			old_p = base / 'daily/2026/11/26/1 - Old Topic'
			new_p = base / 'daily/2026/11/26/1 - shop.test'
			(old_p / '\ua616/data').mkdir(parents=True, exist_ok=True)
			(old_p / '.agents/rules').mkdir(parents=True, exist_ok=True)
			(old_p / '.agents/rules/90-project.md').write_text('Folder name: `Old Topic`;\n', encoding='utf-8')
			(old_p / '\ua616/project.json').write_text(json.dumps({'job_id': '~02rn1', 'label': 'Old Topic', 'request_date': '2026-11-26'}), encoding='utf-8')
			self.assertEqual((base / 'daily').resolve(), ProjectRenamer.infer_daily_root(old_p, None))
			dom, bid = ProjectRenamer.resolve_promotable_target_domain({'identity': [{'id': 'H-1', 'probability_percent': 85}], 'websites': [{'role': 'target', 'url': 'https://shop.test', 'basis_id': 'H-1'}]})
			self.assertEqual(('shop.test', 'H-1'), (dom, bid))
			pairs = RenameLineage.path_pairs(old_p, new_p, None, None)
			self.assertTrue(any((str(old_p) == a for a, _ in pairs)))
			self.assertIsNotNone(RenameLineage.capture_file_sha(old_p / '\ua616/project.json'))
			res = ProjectRenamer(old_p, domain='shop.test', register_native=False).rename()
			self.assertTrue(res['valid'] and res['renamed'])
			self.assertTrue(new_p.is_dir())
			self.assertTrue(RenameLineage.same_project_root_check(new_p, old_p, lambda p: Path(p).resolve(), lambda p: p.as_posix().casefold()))
			self.assertIsNone(PostRenameVerifier.infer_launcher_root(new_p, None, None))
			self.assertTrue(callable(StateRewriter))
	# @used-by :mod:`unittest`
	def test_project_intake_classes(self) -> None:
		from Df.Harness.Project.Intake.CaptureCommitter import CaptureCommitter
		from Df.Harness.Project.Intake.IntakeIndexer import IntakeIndexer
		from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
		from Df.Harness.Project.Intake.ReceiptBuilder import ReceiptBuilder
		from Df.Harness.Project.Intake.ReceiptValidator import ReceiptValidator
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			inc = base / 'incoming'
			cap = inc / '02in1-abcd1234'
			cap.mkdir(parents=True, exist_ok=True)
			(cap / 'source.json').write_text(json.dumps({'job_id': '~02in1', 'title': 'T', 'description': 'D'}), encoding='utf-8')
			self.assertEqual(cap.resolve(), IntakePathGuard.plain(cap))
			self.assertEqual((cap / 'source.json').resolve(), IntakePathGuard.within(cap, 'source.json'))
			files, dirs = IntakePathGuard.inventory(cap)
			self.assertIn('source.json', files)
			self.assertEqual(set(), dirs)
			self.assertTrue(IntakePathGuard.retired_path(cap, 'source.json').name.startswith('.intake-retired-'))
			dry = CaptureCommitter.drain_incoming(incoming_root=inc, daily_root=base / 'daily', apply=False)
			self.assertFalse(dry['complete'])
			self.assertTrue(all((callable(c) for c in (IntakeIndexer, ReceiptBuilder, ReceiptValidator))))
	# @used-by :mod:`unittest`
	def test_project_context_classes(self) -> None:
		from Df.Harness.Project.Context.ContextAssembler import ContextAssembler
		from Df.Harness.Project.Context.ContextGenerator import ContextGenerator
		from Df.Harness.Project.Context.LetterDiscoverer import LetterDiscoverer
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			(root / '\ua616/KB/Evidence').mkdir(parents=True, exist_ok=True)
			(root / '\ua616/KB/Notes.md').write_text('# Notes\nVerified fact.  \n', encoding='utf-8')
			(root / '\ua616/KB/Evidence/raw.md').write_text('Raw excluded.\n', encoding='utf-8')
			l_dir = root / 'Letters/my/2026-11-26'
			l_dir.mkdir(parents=True, exist_ok=True)
			(l_dir / 'final.md').write_text('Hello client.  \n', encoding='utf-8')
			self.assertEqual([l_dir / 'final.md'], LetterDiscoverer(root / 'Letters/my').discover())
			self.assertEqual(l_dir / 'final.md', LetterDiscoverer.resolve_letter_file(l_dir))
			cfg = LetterDiscoverer.default_config(root)
			self.assertEqual(1, cfg['version'])
			ts = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)
			content, sources = ContextAssembler(root, cfg, now=ts).assemble()
			self.assertIn('2026-11-26T12:00:00+00:00', content)
			self.assertIn('Verified fact.', content)
			self.assertNotIn('Raw excluded.', content)
			self.assertEqual(1, len(sources))
			target, gen_txt, _ = ContextGenerator(root, cfg, now=ts).generate()
			self.assertTrue(target.is_file())
			self.assertEqual(content, gen_txt)
if '__main__' == __name__:
	unittest.main()
