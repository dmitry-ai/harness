# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import claims, completion, github_issue, review, source_grounding
from agent_tools.platforms import antigravity


def _wire(field: int, payload: bytes) -> bytes:
    def _varint(val: int) -> bytes:
        out = bytearray()
        while val >= 128:
            out.append((val & 127) | 128)
            val >>= 7
        out.append(val)
        return bytes(out)

    return _varint((field << 3) | 2) + _varint(len(payload)) + payload


class Issue45To48Tests(unittest.TestCase):
    def test_issue45_provenance_tiers_and_tier2_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules_dir = root / '.agents' / 'rules'
            rules_dir.mkdir(parents=True, exist_ok=True)
            rule_file = rules_dir / '91-servers.md'
            rule_file.write_text('# Servers\nServer A has 20 GB RAM and 40 cores.\n', encoding='utf-8')

            ticket_dir = root / 'tickets' / '1465836'
            ticket_dir.mkdir(parents=True, exist_ok=True)
            source_file = ticket_dir / 'source.md'
            source_file.write_text(
                '# Ticket 1465836\n```json\n{"plan": "M6", "vcpu": null, "mem_total": 24379, "cpus": 20}\n```\n',
                encoding='utf-8',
            )
            analysis_file = ticket_dir / 'analysis.md'
            analysis_file.write_text(
                '# Analysis\nServer has 15-20 GB RAM and 40 cores on M6.\n',
                encoding='utf-8',
            )

            self.assertEqual(source_grounding.classify_provenance_tier(source_file, root), 'tier_0')
            self.assertEqual(source_grounding.classify_provenance_tier(analysis_file, root), 'tier_1')
            self.assertEqual(source_grounding.classify_provenance_tier(rule_file, root), 'tier_2')

            # 1. Citing Tier 2 rule file as sole evidence for factual server metric must fail
            resp_tier2 = (
                'Сервер имеет 20 ГБ ОЗУ согласно '
                f'[91-servers.md](<{rule_file.as_posix()}>).  \n'
            )
            issues_tier2 = source_grounding.local_source_grounding_issues(root, resp_tier2)
            self.assertTrue(
                any('Tier 2 file' in item and 'cannot serve as sole primary evidence' in item for item in issues_tier2),
                f'Expected Tier 2 rejection, got: {issues_tier2}',
            )

            # 2. Citing analysis.md without sibling source.md having "15" or "20" (for RAM) must fail
            resp_tier1 = (
                'Сервер имеет 15 ГБ ОЗУ согласно '
                f'[analysis.md](<{analysis_file.as_posix()}>).  \n'
            )
            issues_tier1 = source_grounding.local_source_grounding_issues(root, resp_tier1)
            self.assertTrue(
                any('source.md' in item and '15' in item for item in issues_tier1),
                f'Expected sibling Tier 0 mismatch error, got: {issues_tier1}',
            )

            # 3. Entity Tier 0 auto-discovery finds source.md for ticket 1465836 / M6 / mem_total
            discovered = source_grounding.discover_entity_tier0_sources(
                root, 'В тикете 1465836 тариф M6 и параметр mem_total.'
            )
            discovered_paths = [d['path'] for d in discovered]
            self.assertIn('tickets/1465836/source.md', discovered_paths)

    def test_issue46_fact_tuple_ledger_and_contradictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ticket_dir = root / 'tickets' / '1465836'
            ticket_dir.mkdir(parents=True, exist_ok=True)
            source_file = ticket_dir / 'source.md'
            source_file.write_text(
                '# Ticket 1465836\n'
                '```json\n'
                '{"plan": "M6", "vcpu": null, "mem_total": 24379, "cpus": 20}\n'
                '```\n'
                'load average: 15.61, 14.20, 12.10\n',
                encoding='utf-8',
            )

            ledger = source_grounding.sync_fact_ledger(root)
            self.assertTrue((root / 'ꘖ' / 'data' / 'facts.json').is_file())
            self.assertGreaterEqual(ledger['tuple_count'], 4)

            # 1. Null vcpu fabrication ("40 ядер" on M6 when vcpu is null)
            resp_vcpu = (
                'В тикете 1465836 тариф M6 дает 40 ядер (против 20 ранее) '
                f'[source.md](<{source_file.as_posix()}>).  \n'
            )
            issues_vcpu = source_grounding.local_source_grounding_issues(root, resp_vcpu)
            self.assertTrue(
                any('vcpu=null' in item for item in issues_vcpu),
                f'Expected null vcpu contradiction, got: {issues_vcpu}',
            )

            # 2. RAM contradiction ("20 ГБ ОЗУ" when mem_total is 24379 MB ~ 24 GB)
            resp_ram = (
                'У сервера 20 ГБ ОЗУ согласно '
                f'[source.md](<{source_file.as_posix()}>).  \n'
            )
            issues_ram = source_grounding.local_source_grounding_issues(root, resp_ram)
            self.assertTrue(
                any('mem_total=24379' in item for item in issues_ram),
                f'Expected mem_total contradiction, got: {issues_ram}',
            )

            # 3. Unnormalized load average overload claim when load_avg (15.61) < cpus (20)
            resp_la = (
                'Наблюдается перегрузка CPU: load average 15.61 при 20 ядрах '
                f'[source.md](<{source_file.as_posix()}>).  \n'
            )
            issues_la = source_grounding.local_source_grounding_issues(root, resp_la)
            self.assertTrue(
                any('load average' in item and 'below the core count' in item for item in issues_la),
                f'Expected load average normalization contradiction, got: {issues_la}',
            )

    def test_issue46_ast_arithmetic_grounding(self) -> None:
        val, lit_tokens = claims.evaluate_safe_arithmetic(
            'round((a - b) / a * 100, 2)', {'a': 12285, 'b': 10133}
        )
        self.assertIsNotNone(val)
        self.assertEqual(lit_tokens, {'100', '2'})
        self.assertAlmostEqual(float(val), 17.52, places=2)

        # Unsafe calls must be rejected
        bad_val, bad_tokens = claims.evaluate_safe_arithmetic('__import__("os").system("echo hi")', {})
        self.assertIsNone(bad_val)
        self.assertEqual(bad_tokens, set())

        # Inline arithmetic grounding in text when operands are in primary evidence
        grounded = {'12285', '10133', '15.61', '20'}
        text_ok = 'Рост составил 12285 - 10133 = 2152, а загрузка 15.61 / 20 = 0.78.'
        derived_ok, calc_errs_ok = claims.extract_verified_inline_calc_numbers(text_ok, grounded)
        self.assertEqual(calc_errs_ok, [])
        self.assertIn('2152', derived_ok)
        self.assertIn('0.78', derived_ok)

        text_bad = 'Рост составил 12285 - 10133 = 3500.'
        _, calc_errs_bad = claims.extract_verified_inline_calc_numbers(text_bad, grounded)
        self.assertEqual(len(calc_errs_bad), 1)
        self.assertIn('2152', calc_errs_bad[0])

        # Verify source_grounding accepts derived inline arithmetic without flagging 2152 as ungrounded
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / 'source'
            src_dir.mkdir(parents=True, exist_ok=True)
            src = src_dir / 'source.md'
            src.write_text('# Metrics\nBefore: 10133\nAfter: 12285\n', encoding='utf-8')
            line_ok = f'Прирост равен 12285 - 10133 = 2152 по данным [source.md](<{src.as_posix()}>).  \n'
            self.assertEqual(source_grounding.local_source_grounding_issues(root, line_ok), [])

            line_bad = f'Прирост равен 12285 - 10133 = 3500 по данным [source.md](<{src.as_posix()}>).  \n'
            bad_issues = source_grounding.local_source_grounding_issues(root, line_bad)
            self.assertTrue(
                any('inline arithmetic mismatch' in item for item in bad_issues),
                f'Expected inline arithmetic error, got: {bad_issues}',
            )

    def test_issue47_merkle_cache_blind_predicates_and_falsifier_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kb_dir = root / 'ꘖ' / 'KB'
            kb_dir.mkdir(parents=True, exist_ok=True)
            ev_rel = 'ꘖ/KB/Evidence/ticket.md'
            ev_path = root / ev_rel
            ev_path.parent.mkdir(parents=True, exist_ok=True)
            ev_path.write_text('# Ticket\nmem_total: 24379\ncpus: 20\n', encoding='utf-8')

            analysis_val = {
                'schema_version': 3,
                'facts': [
                    {
                        'id': 'F-1',
                        'knowledge_type': 'observation',
                        'essence': 'Server has 24379 MB RAM and 20 CPUs with 95% confidence.',
                        'primary_evidence': [{'source': ev_rel}],
                    }
                ],
            }
            manifest = [
                {
                    'claim_id': 'F-1',
                    'claim_sha256': 'claim-sha-1',
                    'knowledge_type': 'observation',
                    'essence': 'Server has 24379 MB RAM and 20 CPUs with 95% confidence.',
                    'response_excerpt': 'Server has 24379 MB RAM and 20 CPUs.',
                }
            ]
            ev_digests = {ev_rel: 'sha256-abc123'}

            # Initially F-1 is uncached
            delta1 = review.compute_claim_merkle_delta(root, manifest, analysis_val, ev_digests)
            self.assertEqual(delta1['unverified_claim_ids'], ['F-1'])
            self.assertEqual(delta1['cached_claim_ids'], [])

            # Blind verification predicates strip "with 95% confidence" and form neutral questions
            preds = review.build_blind_verification_predicates(manifest, analysis_val)
            self.assertEqual(len(preds), 1)
            self.assertEqual(preds[0]['claim_id'], 'F-1')
            self.assertNotIn('95%', preds[0]['atomic_predicate'])
            self.assertIn('Does the Tier 0 primary evidence directly entail or falsify', preds[0]['question'])

            # Update Merkle cache and verify F-1 becomes cached
            pkg_for_cache = {
                'claims': manifest,
                'evidence_inputs': ev_digests,
                'merkle_delta': delta1,
                'response': {'sha256': 'resp-sha-1'},
            }
            review.update_verified_claims_cache(root, pkg_for_cache, analysis_val)
            delta2 = review.compute_claim_merkle_delta(root, manifest, analysis_val, ev_digests)
            self.assertEqual(delta2['unverified_claim_ids'], [])
            self.assertEqual(delta2['cached_claim_ids'], ['F-1'])

            # Falsifier report validation
            pkg = {
                'schema_version': review.REVIEW_SCHEMA,
                'review_mode': 'falsifier',
                'risk': 'significant',
                'scope': list(review.SCOPES),
                'claims': manifest,
                'merkle_delta': delta1,
            }
            good_falsifier_report = {
                'schema_version': review.REVIEW_SCHEMA,
                'review_mode': 'falsifier',
                'result': 'approved',
                'scope': list(review.SCOPES),
                'disproved_claims': [],
                'findings': [],
            }
            self.assertEqual(review.report_issues(good_falsifier_report, pkg), [])

            bad_falsifier_report = dict(good_falsifier_report)
            bad_falsifier_report['disproved_claims'] = [
                {
                    'claim_id': 'F-1',
                    'excerpt_from_answer': 'Server has 20 GB RAM',
                    'contradicting_tier0_source': ev_rel,
                    'verbatim_quote_from_source': 'mem_total: 24379',
                    'falsification_reason': '24379 MB is ~24 GB, not 20 GB',
                }
            ]
            bad_issues = review.report_issues(bad_falsifier_report, pkg)
            self.assertTrue(
                any('non-empty disproved_claims requires needs_changes' in item for item in bad_issues),
                f'Expected disproved_claims error, got: {bad_issues}',
            )

    def test_issue47_partial_candidate_read_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cand = root / 'ꘖ' / 'data' / 'scratch' / 'answer.md'
            cand.parent.mkdir(parents=True, exist_ok=True)
            cand.write_text('\n'.join(f'Line {i}' for i in range(1, 109)) + '\n', encoding='utf-8')

            partial_rows = [
                {
                    'type': 'tool_call',
                    'tool_calls': [
                        {
                            'name': 'view_file',
                            'args': {
                                'AbsolutePath': str(cand),
                                'StartLine': 1,
                                'EndLine': 60,
                            },
                        }
                    ],
                }
            ]
            issues_partial = antigravity.reviewer_isolation_issues(root, partial_rows)
            self.assertTrue(
                any('partial/truncated read of candidate response' in item and '1-60 of 108' in item for item in issues_partial),
                f'Expected partial candidate read violation, got: {issues_partial}',
            )

            full_rows = partial_rows + [
                {
                    'type': 'tool_call',
                    'tool_calls': [
                        {
                            'name': 'view_file',
                            'args': {
                                'AbsolutePath': str(cand),
                                'StartLine': 61,
                                'EndLine': 108,
                            },
                        }
                    ],
                }
            ]
            issues_full = antigravity.reviewer_isolation_issues(root, full_rows)
            self.assertEqual(issues_full, [])

    def test_issue45_post_checkpoint_evicted_citation_gate_and_issue48_defect_filing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code_dir = base / 'code'
            code_dir.mkdir(parents=True, exist_ok=True)
            git_dir = code_dir / '.git'
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / 'config').write_text(
                '[remote "origin"]\n\turl = https://github.com/dmitry-ai/harness.git\n',
                encoding='utf-8',
            )
            (code_dir / 'scripts' / 'agent_tools').mkdir(parents=True, exist_ok=True)
            (code_dir / 'scripts' / 'agent_tools' / 'git_gate.py').write_text('# gate\n', encoding='utf-8')
            root = base / '_'
            root.mkdir(parents=True, exist_ok=True)

            # Verify _find_local_code_repo resolves <base>/code from <base>/_
            self.assertEqual(
                github_issue._find_local_code_repo('dmitry-ai/harness', project_root=root),
                code_dir.resolve(),
            )

            # Verify diagnostic defect audit in a code repo without GitHub issues is blocked
            diag_response = (
                '# Разбор проблем\n'
                '1. `C-1` — дефект в `scripts/agent_tools/review.py` и `source_grounding.py`.  \n'
                '1. `M-1` — изменить `review.py` и `source_grounding.py` для устранения ошибки.  \n'
            )
            fake_turn = {
                'touched_files': [],
                'issue_actions': [],
                'exec5_violations': [],
            }
            lifecycle = completion._code_and_issue_lifecycle_status(
                root, fake_turn, turn_state={}, response=diag_response
            )
            self.assertFalse(lifecycle['verified'])
            self.assertTrue(
                any('Diagnostic audit of dmitry-ai/harness identifies repository defects' in v for v in lifecycle['violations']),
                f'Expected diagnostic defect filing violation, got: {lifecycle["violations"]}',
            )

            # And when an OPEN issue is filed during an analysis-only turn (no code touched), it passes!
            ev_issue = (
                root / 'ꘖ' / 'KB' / 'Evidence' / 'GitHub' / 'dmitry-ai__harness' / 'issue-45.json'
            )
            ev_issue.parent.mkdir(parents=True, exist_ok=True)
            ev_issue.write_text(
                json.dumps(
                    {
                        'verified': True,
                        'issue': {
                            'number': 45,
                            'url': 'https://github.com/dmitry-ai/harness/' + 'issues/45',
                            'title': 'Enforce typed source provenance tiers',
                            'body': '# 1. Problem\nDetails here.  \n',
                            'state': 'OPEN',
                        },
                    }
                ),
                encoding='utf-8',
            )
            fake_turn_with_open_issue = {
                'touched_files': [],
                'issue_actions': [
                    {
                        'action': 'create',
                        'repo': 'dmitry-ai/harness',
                        'number': 45,
                        'url': 'https://github.com/dmitry-ai/harness/' + 'issues/45',
                        'state': 'open',
                    }
                ],
                'exec5_violations': [],
            }
            lifecycle_ok = completion._code_and_issue_lifecycle_status(
                root, fake_turn_with_open_issue, turn_state={}, response=diag_response
            )
            self.assertTrue(lifecycle_ok['verified'], f'Expected verified=True, got violations: {lifecycle_ok["violations"]}')
            self.assertEqual(lifecycle_ok['violations'], [])

    def test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / 'project'
            project.mkdir()
            backend = root / 'ag'
            (backend / 'conversations').mkdir(parents=True)
            cid = str(uuid.uuid4())
            coord_cid = str(uuid.uuid4())
            worker_cid = str(uuid.uuid4())

            res_file = project / 'ꙮ' / '1 - Analysis' / 'res' / '143.md'
            res_file.parent.mkdir(parents=True, exist_ok=True)
            res_file.write_text('# Prior response 143\nContent here.\n', encoding='utf-8')
            (project / 'ꙮ' / '1 - Analysis' / 'req').mkdir(parents=True, exist_ok=True)
            (project / 'ꙮ' / '1 - Analysis' / 'req' / '143.md').write_text('Prior request\n', encoding='utf-8')

            c = sqlite3.connect(backend / 'conversation_summaries.db')
            c.execute(
                'CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_user_input_step_index INTEGER,agent_name TEXT)'
            )
            c.execute(
                'INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)',
                (cid, '', json.dumps([project.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, 'primary'),
            )
            c.execute(
                'INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)',
                (coord_cid, cid, json.dumps([project.as_uri()]), 'CASCADE_RUN_STATUS_IDLE', 0, 0, 0, 'coordinator'),
            )
            c.execute(
                'INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)',
                (worker_cid, coord_cid, json.dumps([project.as_uri()]), 'CASCADE_RUN_STATUS_IDLE', 0, 0, 0, 'worker'),
            )
            c.commit()
            c.close()

            c = sqlite3.connect(backend / 'conversations' / (cid + '.db'))
            c.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
            c.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (_wire(19, _wire(2, b'Inspect res/143.md')),))
            c.commit()
            c.close()

            # Coordinator transcript references worker_cid
            coord_log = backend / 'brain' / coord_cid / '.system_generated/logs/transcript_full.jsonl'
            coord_log.parent.mkdir(parents=True, exist_ok=True)
            coord_log.write_text(
                json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Coordinate task'}) + '\n'
                + json.dumps({'step_index': 1, 'type': 'GENERIC', 'content': f'Spawned worker {worker_cid}'}) + '\n',
                encoding='utf-8',
            )

            # Worker transcript edits a file and creates an issue via df_github_issue.py
            worker_file = project / 'notes.md'
            worker_log = backend / 'brain' / worker_cid / '.system_generated/logs/transcript_full.jsonl'
            worker_log.parent.mkdir(parents=True, exist_ok=True)
            issue_out = json.dumps(
                {
                    'ok': True,
                    'action': 'create',
                    'repo': 'dmitry-ai/harness',
                    'number': 45,
                    'html_url': 'https://github.com/dmitry-ai/harness/' + 'issues/45',
                    'verified': True,
                }
            )
            worker_log.write_text(
                json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Execute task'}) + '\n'
                + json.dumps(
                    {
                        'step_index': 1,
                        'type': 'PLANNER_RESPONSE',
                        'content': '',
                        'tool_calls': [
                            {'id': 'w1', 'name': 'write_to_file', 'args': {'TargetFile': str(worker_file)}},
                            {'id': 'c1', 'name': 'run_command', 'args': {'CommandLine': 'python df_github_issue.py create'}},
                        ],
                    }
                )
                + '\n'
                + json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': issue_out})
                + '\n',
                encoding='utf-8',
            )

            # Parent transcript reads res/143.md BEFORE CHECKPOINT, then invokes coord_cid, then compacts
            parent_log = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
            parent_log.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {'step_index': 0, 'type': 'USER_INPUT', 'content': 'Inspect res/143.md'},
                {
                    'step_index': 1,
                    'type': 'PLANNER_RESPONSE',
                    'content': '',
                    'tool_calls': [
                        {'id': 'r1', 'name': 'view_file', 'args': {'AbsolutePath': str(res_file)}},
                        {'id': 's1', 'name': 'invoke_subagent', 'args': {'TypeName': 'coordinator'}},
                    ],
                },
                {'step_index': 2, 'type': 'GENERIC', 'content': f'Subagent {coord_cid} completed'},
                {'step_index': 3, 'type': 'CHECKPOINT', 'content': 'Compacted summary'},
            ]
            parent_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

            # Check recursive subagent aggregation in native_answers
            ans = antigravity.native_answers(project, cid, backend=backend)
            active_turn = ans['turns'][-1]
            self.assertIn(str(worker_file), active_turn['touched_files'])
            self.assertTrue(any(ia.get('number') == 45 and ia.get('subagent_id') == worker_cid for ia in active_turn['issue_actions']))

            # Recover checkpoint, then verify citing evicted res/143.md without re-reading is blocked
            completion.recover_checkpoint(project, cid, platform='antigravity', backend=backend)
            with self.assertRaisesRegex(
                ValueError,
                'COMPACT-1 / KB-3 violation in active turn: primary source file\\(s\\) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint',
            ):
                completion.prepare(
                    project,
                    'According to res/143.md the prior turn succeeded.',
                    cid,
                    platform='antigravity',
                    backend=backend,
                    watch=False,
                )


if __name__ == '__main__':
    unittest.main()
