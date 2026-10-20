"""Offline regressions for provenance, preregistration and disconfirming data."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import experiments as exp, research
from agent_tools.platforms import codex


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'native-home'
        self.home.mkdir()
        self.cid = str(uuid.uuid4())
        self.requirement = {'id': 'R-CONTENT', 'claim': 'The received JSON says the link exists',
            'property': 'content', 'alternatives': ['The link is absent in the received response'],
            'method': 'http', 'scope': {'objects': ['https://example.invalid/de-de']}, 'conditions': {},
            'expected': 'present is true', 'falsification': 'present is false',
            'discriminating_test': 'Read the exact JSON field; parse failures are inconclusive',
            'completion_criterion': 'Save one raw response and its measured field',
            'assertions': [{'id': 'A-PRESENT', 'artifact_id': 'raw',
                'locator': {'type': 'json_pointer', 'value': '/present'}, 'operator': 'equals', 'expected': True,
                'disconfirming': {'operator': 'equals', 'expected': False}}]}

    def plan(self, requirement=None, **kwargs):
        self.last_plan = exp.prepare_experiment(self.root, requirement or self.requirement, **kwargs)
        return self.last_plan

    def observe(self, value, **kwargs):
        return research.collect(self.root, 'https://example.invalid/de-de', max_age=0,
            fetcher=lambda url, *args: research.Response(url, 200, 'application/json', json.dumps(value).encode()), **kwargs)

    def run_record(self, plan, observation=None, status='verified', **kwargs):
        return exp.record_experiment(self.root, {'plan': plan['plan'], 'plan_sha256': plan['plan_sha256'],
            'status': status, 'conditions': {}, 'actual_steps': [],
            'artifacts': [{'id': 'raw', 'observation': observation['observation']}] if observation else [],
            'actual_result': 'Interpretation of the separately saved raw result', **kwargs})

    def test_positive_http_observation_is_verified_and_hashed(self):
        plan = self.plan()
        result = self.run_record(plan, self.observe({'present': True}))
        run = exp.load_experiment(self.root, result['experiment'])
        self.assertEqual(run['evaluation']['status'], 'verified')
        self.assertIn('content', run['capabilities'])
        self.assertNotIn('interaction', run['capabilities'])
        self.assertEqual(exp.result_issues(self.root, self.requirement, result), [])

    def test_disconfirming_false_cannot_be_forced_to_verified(self):
        plan = self.plan(); observation = self.observe({'present': False})
        with self.assertRaisesRegex(ValueError, 'verdict contradicts'):
            self.run_record(plan, observation)
        result = self.run_record(plan, observation, 'refuted')
        self.assertEqual(exp.load_experiment(self.root, result['experiment'])['evaluation']['status'], 'refuted')

    def test_missing_and_unparsable_measurements_are_unverified_not_refuted(self):
        plan = self.plan()
        for value in ({'different_field': False}, 'not an object'):
            observation = self.observe(value)
            for verdict in ('verified', 'refuted'):
                with self.assertRaises(ValueError): self.run_record(plan, observation, verdict)
            result = self.run_record(plan, observation, 'unverified', limitation='Field absent or cannot be parsed')
            self.assertEqual(exp.load_experiment(self.root, result['experiment'])['evaluation']['status'], 'unverified')

    def test_preregistration_precedes_real_observation_not_result_write(self):
        old = self.observe({'present': True}); plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'after this exact plan'):
            self.run_record(plan, old)
        self.run_record(plan, self.observe({'present': True}))

    def test_amended_expectation_requires_new_observation_and_retains_original(self):
        first = self.plan(); old = self.observe({'present': False})
        original = self.run_record(first, old, 'refuted')
        changed = deepcopy(self.requirement)
        changed['expected'] = 'present is false'
        changed['assertions'][0].update(expected=False, disconfirming={'operator': 'equals', 'expected': True})
        second = self.plan(changed, amendment_of=first['plan'], amendment_reason='New question after the actual contrary observation')
        with self.assertRaises(ValueError): self.run_record(second, old)
        self.run_record(second, self.observe({'present': False}))
        self.assertEqual(exp.load_experiment(self.root, original['experiment'])['status'], 'refuted')
        self.assertTrue((self.root / 'ꘖ/KB' / first['plan']).is_file())

    def test_supplied_requirement_cannot_rewrite_test_or_expected_after_run(self):
        plan = self.plan(); observation = self.observe({'present': False})
        changed = deepcopy(self.requirement); changed['expected'] = 'Whatever was received'
        with self.assertRaisesRegex(ValueError, 'preregistered'):
            self.run_record(plan, observation, 'refuted', requirement=changed)

    def test_unavailable_run_preserves_gap_and_does_not_assert_property(self):
        result = self.run_record(self.plan(), status='unavailable', limitation='Authorized browser unavailable')
        self.assertEqual(exp.result_issues(self.root, self.requirement, result), [])
        self.assertEqual(exp.load_experiment(self.root, result['experiment'])['capabilities'], [])

    def test_free_form_manual_test_cannot_be_verified_without_raw_predicates(self):
        requirement = deepcopy(self.requirement); requirement.pop('assertions')
        plan = self.plan(requirement); observation = self.observe({'present': True})
        with self.assertRaisesRegex(ValueError, 'deterministic'):
            self.run_record(plan, observation)
        self.run_record(plan, observation, 'unverified', limitation='A.A must assess semantic entailment')

    def test_modified_primary_bytes_or_plan_is_rejected(self):
        plan = self.plan(); result = self.run_record(plan, self.observe({'present': True}))
        run = exp.load_experiment(self.root, result['experiment'])
        artifact = self.root / 'ꘖ/KB' / run['artifacts'][0]['path']
        artifact.write_bytes(b'{"present":false}')
        with self.assertRaisesRegex(ValueError, 'hash/size'): exp.load_experiment(self.root, result['experiment'])
        plan_path = self.root / 'ꘖ/KB' / plan['plan']
        changed = json.loads(plan_path.read_bytes()); changed['requirement']['expected'] = 'Changed'
        plan_path.write_text(json.dumps(changed))
        with self.assertRaises(ValueError): exp.load_plan(self.root, plan['plan'])

    def test_wayse_style_saved_json_read_is_not_new_native_browser_execution(self):
        plan = self.plan()
        saved = self.root / 'ga4_saved.json'; saved.write_text('{"present":true}')
        with self.assertRaisesRegex(ValueError, 'actual kind|after this exact plan'):
            self.run_record(plan, artifacts=[{'id': 'raw', 'path': 'ga4_saved.json', 'role': 'browser'}])

    def test_cache_distinguishes_network_country_language_and_session_state(self):
        headers = {'Accept-Language': 'de-DE'}
        base = {'session': {'mode': 'unknown'}, 'egress': {'country': 'TR'}, 'url_country': 'DE',
                'language': 'de', 'session_id': 'tab-A', 'state_fingerprint': 'before'}
        keys = {research.request_key('https://example.invalid/de-de', headers, 'public', base)[1]}
        for changed in ({'egress': {'country': 'DE'}}, {'language': 'en'},
                        {'session_id': 'tab-B'}, {'state_fingerprint': 'after'}):
            keys.add(research.request_key('https://example.invalid/de-de', headers, 'public', {**base, **changed})[1])
        self.assertEqual(len(keys), 5)
        self.assertEqual(research.request_key('https://example.invalid/de-de', headers, 'public', base)[1],
                         research.request_key('https://example.invalid/de-de', headers, 'public', dict(reversed(list(base.items()))))[1])

    def test_dom_is_fresh_and_never_proves_click(self):
        from test_text_browser import dom_fixture
        guard, native = dom_fixture(self.root, 'https://example.invalid/de-de', 'tab-A', '<p>EUR</p>')
        first = research.capture_dom(self.root, 'https://example.invalid/de-de', 'tab-A', session_id='offline-dom', guard=guard)
        second = research.capture_dom(self.root, 'https://example.invalid/de-de', 'tab-A', session_id='offline-dom', guard=guard)
        self.assertEqual(len([call for call in native.calls if call[1] == 'Runtime.evaluate']), 2)
        self.assertNotEqual(first['observation'], second['observation'])
        self.assertNotIn('interaction', research.observation_capabilities(first))

    def native_fixture(self, include_geo=False, action_code=None, incognito=None):
        identity = {'browser_id': 'browser-A', 'tab_id': 'TAB-A', 'context_id': 'CTX-A', 'session_id': 'SESSION-A'}
        states = {'before': {**identity, 'url': 'https://example.invalid/de-de', 'currency': 'EUR', 'language': 'de', 'selected_country': 'DE'},
                  'after': {**identity, 'url': 'https://example.invalid/products/one', 'currency': 'GBP', 'language': 'en', 'selected_country': 'GB'}}
        if incognito is not None: states['before']['incognito'] = incognito
        rows = [{'type': 'session_meta', 'payload': {'id': self.cid, 'source': 'vscode'}}]
        def append(ident, code, output, name='mcp__cua_repl.js'):
            now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
            rows.extend([{'timestamp': now, 'type': 'response_item', 'payload': {'type': 'function_call',
                'name': name, 'call_id': ident, 'arguments': json.dumps({'code': code})}},
                {'timestamp': now, 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': ident, 'output': output}}])
        append('plan-commit', 'python upwork_project.py prepare-experiment --spec plan.json', self.last_plan, name='functions.exec')
        ids = ['plan-commit']
        if include_geo:
            append('geo', "await tab.goto('https://ipapi.co/json/'); await tab.getState()", {**identity, 'ip': '192.0.2.1', 'country_code': 'TR'})
            ids.append('geo')
        append('before', 'await tab.getState()', states['before']); ids.append('before')
        append('click', action_code or "await tab.playwright.getByRole('link').click(); await tab.getState()", states['after']); ids.append('click')
        path = self.home / 'sessions' / (self.cid + '.jsonl'); path.parent.mkdir()
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        connection = sqlite3.connect(self.home / 'state_5.sqlite')
        connection.execute('CREATE TABLE threads(id TEXT,rollout_path TEXT)')
        connection.execute('INSERT INTO threads VALUES (?,?)', (self.cid, str(path))); connection.commit(); connection.close()
        return states, {'surface': 'codex-ui', 'conversation_id': self.cid, 'call_ids': ids, 'native_profile_home': str(self.home)}

    def browser_requirement(self, conditions=None):
        requirement = deepcopy(self.requirement)
        requirement.update(id='R-CURRENCY', claim='Click changes visible EUR to GBP in this session',
                           property='currency_transition', method='browser_scenario', conditions=conditions or {})
        requirement['assertions'] = [{'id': 'A-CURRENCY', 'artifact_id': 'after',
            'locator': {'type': 'json_pointer', 'value': '/currency'}, 'operator': 'equals', 'expected': 'GBP',
            'disconfirming': {'operator': 'equals', 'expected': 'EUR'}}]
        return requirement

    def browser_spec(self, plan, states, trace, conditions=None):
        return {'plan': plan['plan'], 'plan_sha256': plan['plan_sha256'], 'status': 'verified',
            'conditions': conditions or {}, 'native_trace': trace,
            'artifacts': [{'id': key, 'native_event_id': key if key == 'before' else 'click', 'role': key} for key in ('before', 'after')],
            'actual_result': 'Visible state changed in the recorded session only',
            'actual_steps': [{'action': 'click', 'native_event_id': 'click', 'evidence': ['after'],
                'before': {**states['before'], 'evidence': ['before']}, 'after': {**states['after'], 'evidence': ['after']}}]}

    def native_selected(self):
        return patch.object(codex, 'platform_settings', return_value={'homes': {'C2': str(self.home)}})

    def rewrite_native(self, change):
        path = self.home / 'sessions' / (self.cid + '.jsonl')
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        change(rows)
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')

    def test_native_action_before_after_states_and_raw_predicate_can_verify_transition(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        with self.native_selected():
            result = exp.record_experiment(self.root, self.browser_spec(plan, states, trace))
            self.assertIn('currency_transition', exp.load_experiment(self.root, result['experiment'])['capabilities'])

    def test_browser_label_http_and_action_in_comment_are_not_interaction_proof(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture(action_code='await tab.getState(); // .click()')
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'actual UI action|Actual UI action'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_false_branch_loops_definitions_and_dynamic_scripts_never_prove_executed_click(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        codes = [
            'if (false) { await tab.playwright.getByRole("link").click(); } await tab.getState()',
            'for (let i = 0; i < 0; i++) { await tab.playwright.getByRole("link").click(); } await tab.getState()',
            'async function hidden() { await tab.playwright.getByRole("link").click(); } await tab.getState()',
            'const example = "await tab.playwright.getByRole(\'link\').click()"; await tab.getState()',
            'await tab.getState(); false && await tab.playwright.getByRole("link").click()',
            'await tab.playwright.getByRole("link").click(); await otherTab.getState()',
            'await tab.playwright.getByRole("link").click(); await tab.playwright.getByRole("link").click()',
        ]
        for code in codes:
            def mutate(rows):
                for row in rows:
                    payload = row.get('payload', {})
                    if payload.get('call_id') == 'click' and payload.get('type') == 'function_call':
                        payload['arguments'] = json.dumps({'code': code})
            self.rewrite_native(mutate)
            with self.subTest(code=code), self.native_selected(), self.assertRaisesRegex(ValueError, 'Actual UI action'):
                exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_unconditional_literal_action_with_locator_options_remains_supported(self):
        code = "await tab.playwright.getByRole('link', {name: 'Item', exact: true}).click(); await tab.getState();"
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture(action_code=code)
        with self.native_selected():
            result = exp.record_experiment(self.root, self.browser_spec(plan, states, trace))
            self.assertIn('interaction', exp.load_experiment(self.root, result['experiment'])['capabilities'])

    def test_explicit_native_primitives_with_same_context_remain_supported(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call' and payload.get('call_id') in ('before', 'click'):
                    payload['name'] = 'browser_get_state' if payload['call_id'] == 'before' else 'browser_click'
                    payload['arguments'] = json.dumps({'tab_id': 'TAB-A', 'browser_id': 'browser-A'})
        self.rewrite_native(mutate)
        with self.native_selected():
            result = exp.record_experiment(self.root, self.browser_spec(plan, states, trace))
            self.assertIn('currency_transition', exp.load_experiment(self.root, result['experiment'])['capabilities'])

    def test_native_before_and_action_in_different_browser_tabs_are_rejected(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call' and payload.get('call_id') in ('before', 'click'):
                    before = payload['call_id'] == 'before'
                    payload['name'] = 'browser_get_state' if before else 'browser_click'
                    payload['arguments'] = json.dumps({'tab_id': 'TAB-A' if before else 'TAB-B',
                                                       'browser_id': 'browser-A' if before else 'browser-B'})
                if payload.get('type') == 'function_call_output' and payload.get('call_id') == 'click':
                    payload['output'].update(tab_id='TAB-B', browser_id='browser-B')
        self.rewrite_native(mutate)
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'identities differ'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_conflicting_native_action_parameter_and_output_identity_is_unknown(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call' and payload.get('call_id') == 'click':
                    payload['name'] = 'browser_click'
                    payload['arguments'] = json.dumps({'tab_id': 'TAB-B', 'browser_id': 'browser-B'})
        self.rewrite_native(mutate)
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'identity is unknown'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_missing_native_identity_cannot_be_repaired_by_declared_session(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call_output' and payload.get('call_id') in ('before', 'click'):
                    for field in ('browser_id', 'tab_id', 'context_id', 'session_id'): payload['output'].pop(field)
        self.rewrite_native(mutate)
        spec = self.browser_spec(plan, states, trace, {'session_id': 'SESSION-A'})
        with self.native_selected():
            with self.assertRaisesRegex(ValueError, 'identity is unknown'):
                exp.record_experiment(self.root, spec)
            spec.update(status='unverified', limitation='Native tab/context identity could not be established')
            result = exp.record_experiment(self.root, spec)
            self.assertEqual(exp.load_experiment(self.root, result['experiment'])['capabilities'], [])

    def test_context_or_session_difference_is_rejected_even_for_same_tab_ids(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call_output' and payload.get('call_id') == 'click':
                    payload['output'].update(context_id='other-context', session_id='other-session')
        self.rewrite_native(mutate)
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'identities differ'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_egress_must_be_measured_in_the_actual_action_browser_context(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture(include_geo=True)
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('type') == 'function_call_output' and payload.get('call_id') == 'geo':
                    payload['output'].update(browser_id='other-browser', tab_id='other-tab')
        self.rewrite_native(mutate)
        conditions = {'egress': {'country': 'TR', 'verification': 'verified', 'evidence': ['geo']}}
        spec = self.browser_spec(plan, states, trace, conditions)
        spec['artifacts'].append({'id': 'geo', 'role': 'geolocation', 'native_event_id': 'geo'})
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'identities differ'):
            exp.record_experiment(self.root, spec)

    def test_actual_exec_wrapper_with_nested_shell_plan_receipt_is_supported(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('call_id') != 'plan-commit': continue
                if payload.get('type') == 'function_call':
                    payload.update(type='custom_tool_call', name='exec', input=(
                        'const r = await tools.exec_command({cmd:"python C:/tools/upwork_project.py prepare-experiment --spec plan.json"});text(r.output);'))
                    payload.pop('arguments', None)
                else:
                    payload.update(type='custom_tool_call_output', output=[
                        {'type': 'input_text', 'text': 'Script completed\nWall time 0.5 seconds\nOutput:\n'},
                        {'type': 'input_text', 'text': json.dumps(self.last_plan)}])
        self.rewrite_native(mutate)
        with self.native_selected():
            result = exp.record_experiment(self.root, self.browser_spec(plan, states, trace))
            saved = exp.load_experiment(self.root, result['experiment'])
            commit = next(event for event in saved['native_trace']['events'] if event['id'] == 'plan-commit')
            self.assertEqual(commit['name'], 'exec')
            self.assertIn('tools.exec_command', commit['arguments']['code'])

    def test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity(self):
        from agent_tools.metrics import native_tool_trace
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        def mutate(rows):
            for row in rows:
                payload = row.get('payload', {})
                if payload.get('call_id') != 'before': continue
                if payload.get('type') == 'function_call':
                    payload.update(name='js', namespace='mcp__cua_repl', arguments=json.dumps({
                        'code': 'await qualityProbeTab.getAXState();'}))
                else:
                    payload['output'] = [{'type': 'input_text', 'text':
                        'Browser tab: 1, Title: "about:blank"\nURL: about:blank\nNo interactive elements found.'}]
        self.rewrite_native(mutate)
        with self.native_selected():
            native = native_tool_trace(self.root, trace)
            event = next(item for item in native['events'] if item['id'] == 'before')
            self.assertEqual(event['name'], 'js')
            self.assertEqual(event['namespace'], 'mcp__cua_repl')
            self.assertEqual(exp._event_actions(event), {'read'})
            self.assertIsNone(exp._event_browser_identity(event), 'Display text must never reconstruct a missing native identity')
            spec = self.browser_spec(plan, states, trace)
            with self.assertRaisesRegex(ValueError, 'identity is unknown'):
                exp.record_experiment(self.root, spec)
            spec.update(status='unverified', limitation='Actual CUA read exposed a display header but no structured native browser/tab identity')
            result = exp.record_experiment(self.root, spec)
            saved = exp.load_experiment(self.root, result['experiment'])
            self.assertEqual(saved['capabilities'], [])
            self.assertEqual(next(item for item in saved['native_trace']['events'] if item['id'] == 'before')['namespace'], 'mcp__cua_repl')

    def test_namespaced_documented_dom_snapshot_is_read_only_and_keeps_strict_grammar(self):
        event = {'name': 'js', 'namespace': 'mcp__cua_repl', 'successful': True,
                 'arguments': {'code': 'await qualityProbeTab.domSnapshot();'}, 'result': []}
        self.assertEqual(exp._event_actions(event), {'read'})
        self.assertIsNone(exp._event_browser_identity(event))
        event['arguments']['code'] = 'if (false) { await qualityProbeTab.domSnapshot(); }'
        self.assertEqual(exp._event_actions(event), set())

    def test_before_snapshot_cannot_be_taken_from_action_after_output(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        spec = self.browser_spec(plan, states, trace); spec['actual_steps'][0]['before']['evidence'] = ['after']
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'Before state'):
            exp.record_experiment(self.root, spec)

    def test_no_cookies_does_not_prove_incognito(self):
        conditions = {'session': {'mode': 'incognito', 'verification': 'verified', 'evidence': ['before']}}
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'Incognito'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace, conditions))

    def test_native_private_mode_requires_explicit_browser_context_inspection(self):
        conditions = {'session': {'mode': 'incognito', 'verification': 'verified', 'evidence': ['before']}}
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture(incognito=True)
        with self.native_selected():
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace, conditions))

    def test_german_url_and_turkish_ip_remain_distinct_actual_conditions(self):
        planned = {'url_country': 'DE', 'egress': {'country': 'TR'}}
        plan = self.plan(self.browser_requirement(planned)); states, trace = self.native_fixture(include_geo=True)
        actual = {'url_country': 'DE', 'egress': {'country': 'TR', 'verification': 'verified', 'evidence': ['geo']}}
        spec = self.browser_spec(plan, states, trace, actual)
        spec['artifacts'].append({'id': 'geo', 'role': 'geolocation', 'native_event_id': 'geo'})
        with self.native_selected():
            result = exp.record_experiment(self.root, spec)
            saved = exp.load_experiment(self.root, result['experiment'])
            self.assertEqual(saved['conditions']['egress']['country'], 'TR')
            self.assertEqual(saved['conditions']['url_country'], 'DE')
            spec['conditions']['egress']['country'] = 'DE'
            with self.assertRaisesRegex(ValueError, 'geolocation|preregistered'):
                exp.record_experiment(self.root, spec)

    def test_supplied_native_events_are_rejected(self):
        from agent_tools.metrics import native_tool_trace
        with self.assertRaisesRegex(ValueError, 'supplied events'):
            native_tool_trace(self.root, {'surface': 'codex-ui', 'conversation_id': self.cid, 'events': []})

    def test_native_actions_without_prior_plan_commit_receipt_cannot_be_verified(self):
        plan = self.plan(self.browser_requirement()); states, trace = self.native_fixture()
        trace['call_ids'].remove('plan-commit')
        with self.native_selected(), self.assertRaisesRegex(ValueError, 'plan commitment receipt'):
            exp.record_experiment(self.root, self.browser_spec(plan, states, trace))

    def test_authored_positive_json_cannot_replace_contrary_primary_response(self):
        requirement = deepcopy(self.requirement)
        requirement['assertions'][0]['artifact_id'] = 'authored'
        plan = self.plan(requirement); observation = self.observe({'present': False})
        (self.root / 'authored.json').write_text('{"present":true}')
        with self.assertRaisesRegex(ValueError, 'verdict contradicts'):
            self.run_record(plan, observation, artifacts=[{'id': 'raw', 'observation': observation['observation']},
                {'id': 'authored', 'path': 'authored.json'}])

    def test_observation_kind_alone_never_grants_extra_capabilities(self):
        self.assertEqual(research.observation_capabilities({'kind': 'browser', 'method': 'GET', 'status': 200}), set())
        self.assertNotIn('interaction', research.observation_capabilities({'kind': 'dom', 'method': 'READ_DOM'}))


if __name__ == '__main__': unittest.main()
