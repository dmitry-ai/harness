"""Conservative CDP session checks and a cooperative guard for text research.

The guard owns only calls made through this adapter. It does not claim to block
another shell, tool or human, nor infer a profile from a port or supplied JSON.
No application is launched, restarted or quit by this module.
"""

from contextlib import contextmanager
from copy import deepcopy
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import subprocess
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen

from .runtime import settings
from .storage import locked


_LOCKS, _LOCKS_GUARD = {}, threading.Lock()
_READ = frozenset({
    'DOM.getDocument', 'DOM.getOuterHTML', 'DOM.describeNode', 'DOM.querySelector',
    'DOM.querySelectorAll', 'DOM.getAttributes', 'DOM.getBoxModel',
    'Page.getFrameTree', 'Page.getLayoutMetrics', 'Page.getResourceTree',
    'Page.getNavigationHistory', 'Network.getResponseBody',
    'Runtime.getProperties', 'Accessibility.getFullAXTree',
    'Accessibility.getPartialAXTree', 'Browser.getWindowForTarget',
})
_NAVIGATE = frozenset({'Page.navigate', 'Page.reload', 'Page.navigateToHistoryEntry'})
_CLOSE = frozenset({'Target.closeTarget', 'Page.close'})
_NEVER = frozenset({'Browser.close', 'Target.createTarget', 'Target.disposeBrowserContext',
                    'Target.createBrowserContext', 'Target.attachToTarget',
                    'Target.sendMessageToTarget', 'Browser.crash', 'Page.crash'})
_LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
_NODE_CLIENT = r"""
let input='';for await(const chunk of process.stdin) input+=chunk;
const {url,method,params}=JSON.parse(input);
const result=await new Promise((resolve,reject)=>{
 const socket=new WebSocket(url);const timer=setTimeout(()=>{socket.close();reject(new Error('CDP timeout'));},12000);
 socket.onopen=()=>socket.send(JSON.stringify({id:1,method,params}));
 socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP connection failed'));};
 socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id!==1)return;
  clearTimeout(timer);socket.close();if(message.error)reject(new Error(JSON.stringify(message.error)));else resolve(message.result);};
 socket.onclose=()=>{clearTimeout(timer);reject(new Error('CDP socket closed before its response'));};
});process.stdout.write(JSON.stringify(result));
"""


def _http_json(url):
    with urlopen(url, timeout=8) as response:
        return json.load(response)


def _normal_path(value):
    return str(value).strip('"\'').replace('\\', '/').rstrip('/').casefold()


def _endpoint(session):
    endpoint = session.get('endpoint')
    if session.get('devtools_active_port'):
        if endpoint:
            raise ValueError('Choose endpoint or devtools_active_port, not both')
        # Antigravity's current port is intentionally read afresh on each check.
        first = Path(session['devtools_active_port']).expanduser().read_text(encoding='utf-8-sig').splitlines()[0]
        port = int(first)
        if not 0 < port < 65536:
            raise ValueError('Invalid DevToolsActivePort')
        endpoint = f'http://{session.get("host", "127.0.0.1")}:{port}'
    parsed = urlsplit(endpoint or '')
    if (parsed.scheme not in ('http', 'https') or parsed.hostname not in _LOCAL_HOSTS or
            parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('A configured loopback CDP endpoint is required')
    return endpoint.rstrip('/')


def _checked_ws(value, endpoint):
    actual, expected = urlsplit(value or ''), urlsplit(endpoint)
    if (actual.scheme not in ('ws', 'wss') or actual.hostname != expected.hostname or
            actual.port != expected.port or actual.username or actual.password or actual.query or actual.fragment):
        raise ValueError('Discovered CDP websocket does not belong to the configured endpoint')
    return value


def _session(spec, config):
    identifier = spec.get('session_id')
    sessions = config.get('text', {}).get('browser', {}).get('sessions', {})
    if not isinstance(identifier, str) or identifier not in sessions:
        raise ValueError('Select an explicitly authorized runtime text.browser.sessions session_id')
    value = deepcopy(sessions[identifier])
    if value.get('surface') not in ('browser', 'codex', 'antigravity'):
        raise ValueError('Session surface must distinguish browser, codex or antigravity')
    return value


def _profile(session, config):
    value = session.get('profile', {})
    if value.get('path') and (value.get('platform') or value.get('name')):
        raise ValueError('Use one profile path or one runtime profile reference')
    path = value.get('path')
    if not path and value.get('platform') and value.get('name'):
        path = config.get('platforms', {}).get(value['platform'], {}).get('homes', {}).get(value['name'])
    argument = value.get('argument')
    if not isinstance(path, str) or not path.strip() or not isinstance(argument, str) or not argument.startswith('--'):
        raise ValueError('Session needs a profile path/reference and its observable command-line argument')
    return path, argument


def _argument_values(arguments, flag):
    values = []
    for index, argument in enumerate(arguments):
        if not isinstance(argument, str):
            raise ValueError('Native browser command line contains a non-string argument')
        if argument.startswith(flag + '='):
            values.append(argument[len(flag) + 1:])
        elif argument == flag and index + 1 < len(arguments):
            values.append(arguments[index + 1])
    return values


def _transport(config, override):
    if override is not None:
        return override
    node = config.get('text', {}).get('browser', {}).get('node') or config.get('platforms', {}).get('codex', {}).get('node')
    def call(url, method, params):
        if not node:
            raise ValueError('Configure a Node runtime for the built-in CDP transport')
        result = subprocess.run([node, '--input-type=module', '-e', _NODE_CLIENT],
            input=json.dumps({'url': url, 'method': method, 'params': params}),
            capture_output=True, text=True, timeout=16,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('CDP request failed: ' + (result.stderr.strip() or 'no native response'))
        return json.loads(result.stdout)
    return call


def preflight(spec, *, config=None, http_get=None, cdp_call=None):
    """Read current discovery and profile metadata; never inspect page content.

    Dependency-injected transports are for trusted adapters and offline tests,
    not fields in a caller-supplied specification. Native arguments must come
    from the live CDP browser endpoint. Missing observation remains unknown.
    """
    config = settings() if config is None else config
    report = {'schema_version': 1, 'session_id': spec.get('session_id'), 'valid': False,
              'profile': {'status': 'unknown'}, 'target': {'status': 'unknown'},
              'account': {'status': 'unknown'}, 'issues': [],
              'independent_http_allowed': True,
              'limitation': 'Cooperative check of the configured live CDP endpoint; it does not prove server internals, model reading, or ownership of external calls'}
    try:
        session = _session(spec, config)
        report['surface'] = session['surface']
        endpoint = _endpoint(session)
        report['endpoint'] = endpoint
        get, call = http_get or _http_json, _transport(config, cdp_call)
        version, targets = get(endpoint + '/json/version'), get(endpoint + '/json/list')
        if not isinstance(version, dict) or not isinstance(targets, list):
            raise ValueError('Invalid CDP discovery response')
        browser_ws = _checked_ws(version.get('webSocketDebuggerUrl'), endpoint)
        if not urlsplit(browser_ws).path.startswith('/devtools/browser/'):
            raise ValueError('Discovery did not expose a browser endpoint')
        report['browser'] = {'product': version.get('Browser'), 'websocket_url': browser_ws}
        # Inventory is permitted before identity is known; no DOM or credentials
        # are fetched from any target during this stage.
        report['inventory'] = [{key: item.get(key) for key in ('id', 'type', 'url', 'title')}
                               for item in targets if isinstance(item, dict)]
        expected, argument = _profile(session, config)
        report['profile'].update(expected=expected, argument=argument)
        try:
            observed = call(browser_ws, 'Browser.getBrowserCommandLine', {})
            arguments = observed.get('arguments') if isinstance(observed, dict) else None
            if not isinstance(arguments, list):
                raise ValueError('Native browser command-line arguments are unavailable')
            values = _argument_values(arguments, argument)
            if not values:
                report['issues'].append('Expected profile argument is absent from the native browser command line')
            elif len({_normal_path(value) for value in values}) != 1:
                report['profile']['status'] = 'mismatch'
                report['issues'].append('Native browser command line has conflicting profile arguments')
            else:
                report['profile'].update(observed=values[0], evidence_method='Browser.getBrowserCommandLine',
                    status='verified' if _normal_path(values[0]) == _normal_path(expected) else 'mismatch')
                if report['profile']['status'] == 'mismatch':
                    report['issues'].append('Observed profile does not match the authorized profile')
            constraints = session.get('profile', {}).get('additional_arguments', {})
            if not isinstance(constraints, dict):
                raise ValueError('Profile additional_arguments must map observed flags to expected values')
            details = []
            for flag, expected_value in constraints.items():
                if not isinstance(flag, str) or not flag.startswith('--') or not isinstance(expected_value, str):
                    raise ValueError('Profile additional_arguments needs string flags and values')
                actual_values = _argument_values(arguments, flag)
                status = ('unknown' if not actual_values else 'verified' if actual_values == [expected_value] else 'mismatch')
                details.append({'argument': flag, 'expected': expected_value, 'observed': actual_values, 'status': status})
                if status != 'verified':
                    report['profile']['status'] = status
                    report['issues'].append(f'Additional profile argument {flag} is {status}')
            if details:
                report['profile']['additional_arguments'] = details
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            report['issues'].append('Profile cannot be verified: ' + str(exc))
        identifier = spec.get('target_id')
        matches = [item for item in targets if isinstance(item, dict) and item.get('id') == identifier]
        if not isinstance(identifier, str) or not identifier or len(matches) != 1:
            report['issues'].append('Select one explicit current target_id; no arbitrary target is chosen')
        else:
            target = matches[0]
            patterns = session.get('target_url_patterns', [])
            report['target'] = {key: target.get(key) for key in ('id', 'type', 'url', 'title')}
            report['target']['status'] = 'mismatch'
            if target.get('type') != 'page':
                report['issues'].append('Selected target is not a shell/browser page')
            elif not patterns or not all(isinstance(pattern, str) and pattern for pattern in patterns):
                report['issues'].append('Session needs explicit target_url_patterns')
            elif not any(fnmatchcase(target.get('url', ''), pattern) for pattern in patterns):
                report['issues'].append('Current target URL is outside the authorized session patterns')
            elif spec.get('target_url') is not None and target.get('url') != spec['target_url']:
                report['issues'].append('Current target URL differs from the explicitly selected URL')
            else:
                target_ws = _checked_ws(target.get('webSocketDebuggerUrl'), endpoint)
                if not urlsplit(target_ws).path.startswith('/devtools/page/'):
                    raise ValueError('Selected target has no page websocket')
                report['target'].update(status='verified', websocket_url=target_ws)
        account = session.get('account')
        if account is not None:
            if (not isinstance(account, dict) or not isinstance(account.get('expected'), str) or
                    not account['expected'] or not isinstance(account.get('expression'), str) or not account['expression']):
                raise ValueError('Configured account needs expected identity and a specific read-only observation expression')
            report['account']['expected'] = account['expected']
            if report['profile']['status'] == 'verified' and report['target']['status'] == 'verified':
                try:
                    native = call(report['target']['websocket_url'], 'Runtime.evaluate',
                                  {'expression': account['expression'], 'throwOnSideEffect': True, 'returnByValue': True})
                    if not isinstance(native, dict) or native.get('exceptionDetails'):
                        raise ValueError('Native account observation did not complete without side effects')
                    value = native.get('result', {}).get('value')
                    report['account'].update(observed=value,
                        status='unknown' if not isinstance(value, str) or not value else
                               'verified' if value == account['expected'] else 'mismatch',
                        evidence_method='Runtime.evaluate(throwOnSideEffect:true)',
                        limitation='This establishes only the configured application account marker, not server authorization internals')
                except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    report['issues'].append('Account cannot be verified: ' + str(exc))
            if report['account']['status'] != 'verified':
                report['issues'].append('Observed account is unknown or differs from the authorized account')
        report['valid'] = (report['profile']['status'] == 'verified' and
                           report['target']['status'] == 'verified' and not report['issues'])
    except (ValueError, OSError, RuntimeError, TypeError, KeyError, IndexError) as exc:
        report['issues'].append(str(exc))
    return report


def operation(method, params=None):
    """Classify conservatively; executable JavaScript is a write unless V8 guards it."""
    params = params or {}
    if method in _NEVER:
        return 'forbidden'
    if method in _READ:
        return 'read'
    if method == 'Page.captureScreenshot':
        return 'screenshot'
    if method in _NAVIGATE:
        return 'navigate'
    if method in _CLOSE:
        return 'close'
    if method in ('Runtime.evaluate', 'Runtime.callFunctionOn'):
        return 'read' if params.get('throwOnSideEffect') is True else 'write'
    if method.startswith(('Input.', 'DOM.set', 'DOM.remove', 'Runtime.')):
        return 'write'
    return 'forbidden'


class GuardedCDP:
    """Serializes only its own callers; existing user targets remain read-only.

    An agent target is owned only after this instance receives a successful
    Target.createTarget result. Caller JSON cannot assign target ownership.
    """
    def __init__(self, root, spec, *, config=None, http_get=None, cdp_call=None):
        if root is None or not str(root).strip():
            raise ValueError('An explicit project root is required')
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError('Project root is not a directory')
        self.config = settings() if config is None else deepcopy(config)
        self.spec = deepcopy(spec)
        self.session = _session(spec, self.config)
        self.get = http_get or _http_json
        self.call_native = _transport(self.config, cdp_call)
        self._owned = {}

    @contextmanager
    def _lock(self):
        endpoint = _endpoint(self.session)
        key = hashlib.sha256(endpoint.encode()).hexdigest()
        with _LOCKS_GUARD:
            lock = _LOCKS.setdefault(key, threading.Lock())
        # A workspace-level lock prevents two projects sharing a session from
        # interleaving preflight and action. It never modifies browser state.
        path = Path(self.config['workspace_root']).resolve() / 'ꘖ/data/browser-locks' / f'{key}.lock'
        with lock, locked(path):
            yield

    def _check(self):
        report = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
        if not report['valid']:
            raise PermissionError('; '.join(report['issues']) or 'CDP profile/target is unknown')
        return report

    def _permitted(self, op):
        allowed = set(self.session.get('allowed_operations', []))
        if 'allowed_operations' in self.spec:
            allowed &= set(self.spec['allowed_operations'])
        if op not in allowed:
            raise PermissionError(f'CDP {op} is not authorized for this session')

    def inspect(self):
        """Return live verified identity without reading the selected page's content."""
        with self._lock():
            return self._check()

    def call(self, method, params=None, *, include_identity=False):
        params = deepcopy(params or {})
        op = operation(method, params)
        if op == 'forbidden':
            raise PermissionError(f'Unsupported or unsafe CDP method: {method}')
        self._permitted(op)
        with self._lock():
            report = self._check()
            target, browser = report['target'], report['browser']
            owned = self._owned.get(target['id'])
            if op in ('navigate', 'write', 'close'):
                if self.session['surface'] != 'browser' or not owned:
                    raise PermissionError('Existing user/app targets permit only authorized reads and screenshots')
                if owned['browser'] != browser['websocket_url'] or owned['url'] != target['url']:
                    raise PermissionError('Owned target changed outside this guard; inspect ownership again')
            if 'targetId' in params and params['targetId'] != target['id']:
                raise PermissionError('CDP targetId differs from the verified selection')
            if any(key in params for key in ('sessionId', 'browserContextId')):
                raise PermissionError('Caller-supplied CDP context/session routing is unsupported')
            if op == 'navigate' and method == 'Page.navigate':
                url = params.get('url', '')
                if not any(fnmatchcase(url, pattern) for pattern in self.session['target_url_patterns']):
                    raise PermissionError('Navigation URL is outside the authorized session')
            endpoint = browser['websocket_url'] if method.startswith(('Target.', 'Browser.')) else target['websocket_url']
            if method in ('Target.closeTarget', 'Browser.getWindowForTarget'):
                params['targetId'] = target['id']
            result = self.call_native(endpoint, method, params)
            if owned:
                if op == 'close':
                    self._owned.pop(target['id'], None)
                else:
                    after = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
                    if after['valid']:
                        owned['url'] = after['target']['url']
            return (result, deepcopy(report)) if include_identity else result

    def create_target(self, url):
        """Create an isolated browser window only after profile/target checks.

        This never creates desktop-app windows and never closes/restarts an app.
        The returned receipt describes this real call, not caller-declared ownership.
        """
        if self.session['surface'] != 'browser':
            raise PermissionError('Desktop application window creation is unsupported')
        self._permitted('create')
        if not any(fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', [])):
            raise PermissionError('New target URL is outside the authorized session')
        with self._lock():
            report = self._check()
            result = self.call_native(report['browser']['websocket_url'], 'Target.createTarget',
                                      {'url': url, 'newWindow': True})
            identifier = result.get('targetId') if isinstance(result, dict) else None
            if not isinstance(identifier, str) or not identifier or identifier == report['target']['id']:
                raise RuntimeError('Browser did not return a distinct created target ID; no ownership is assigned')
            check_spec = {**self.spec, 'target_id': identifier, 'target_url': url}
            created = preflight(check_spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
            if not created['valid'] or created['browser']['websocket_url'] != report['browser']['websocket_url']:
                raise RuntimeError('Created target could not be verified in the same browser; it was left open without ownership')
            self._owned[identifier] = {'browser': report['browser']['websocket_url'], 'url': url}
            return {'target_id': identifier, 'owner': 'this-guard', 'session_id': self.spec['session_id'],
                    'new_window': True, 'browser': report['browser']['websocket_url']}

    def select_owned(self, identifier):
        with self._lock():
            if identifier not in self._owned:
                raise PermissionError('Target was not created by this guard')
            self.spec['target_id'] = identifier
            self.spec.pop('target_url', None)
