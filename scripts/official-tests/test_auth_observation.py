"""Harness evidence/privacy controls, separate from official test counters."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from prepare import retained_native_admin

spec = importlib.util.spec_from_file_location('auth_diag_controls', Path(__file__).parent / 'observer/auth_diagnostics.py')
diag = importlib.util.module_from_spec(spec); spec.loader.exec_module(diag)


class AuthObservationControls(unittest.TestCase):
    def test_redirect_reports_names_never_tokens_cookies_or_values(self):
        response = SimpleNamespace(url='http://localhost/callback#access_token=secret-value',
            history=[SimpleNamespace(status_code=302, url='http://localhost/authorize?client_id=private-id',
                headers={'Location': '/callback?state=private-state#access_token=private-token', 'Set-Cookie': 'private-cookie'})],
            headers={'Location': '/login?redirect-to=private-redirect'},
            json=lambda: {'exc_type': 'SecurityException', 'message': 'private-message', 'exc': 'private-trace'})
        data = diag.response_data(response)
        self.assertEqual(data['redirect_history'][0]['location']['fragment_parameter_names'], ['access_token'])
        self.assertEqual(data['native_exception_type'], 'SecurityException')
        self.assertIsNone(data['native_reason'])
        self.assertNotIn('private-', json.dumps(data))
        self.assertNotIn('secret-value', json.dumps(data))

    def test_truthy_request_with_missing_cache_control_is_distinguished(self):
        class RequestDict(dict):
            def __getattr__(self, key): return self.get(key)
        f = SimpleNamespace(local=SimpleNamespace(request=RequestDict(method='POST')))
        state = diag.context(f)
        self.assertFalse(state['request_is_none'])
        self.assertTrue(state['request_truthy'])
        self.assertTrue(state['cache_control_is_none'])
        self.assertFalse(state['cache_control_has_no_cache'])

    def test_native_context_transition_observation_does_not_install_request(self):
        f = SimpleNamespace(local=SimpleNamespace(request=None))
        frame = SimpleNamespace(f_code=SimpleNamespace(co_name='__setattr__', co_filename='/x/werkzeug/local.py'),
                                f_locals={'name': 'request'}, f_back=None)
        events = []
        with patch.dict(sys.modules, {'frappe': f}):
            diag.profile(frame, 'return', None, lambda kind, **data: events.append(data))
        self.assertIsNone(f.local.request)
        self.assertEqual(events[0]['operation'], '__setattr___return')

    def test_pinned_frappe_uses_its_own_local_not_only_werkzeug(self):
        f = SimpleNamespace(local=SimpleNamespace(request=None))
        frame = SimpleNamespace(f_code=SimpleNamespace(co_name='release_local', co_filename='/x/frappe/utils/local.py'),
                                f_locals={}, f_back=None)
        events = []
        with patch.dict(sys.modules, {'frappe': f}):
            diag.profile(frame, 'return', None, lambda kind, **data: events.append(data))
        self.assertEqual(events[0]['operation'], 'release_local_return')
        self.assertIsNone(f.local.request)

    def test_new_site_credential_respects_native_precedence_without_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            common, fallback = Path(folder)/'common.json', Path(folder)/'private.json'
            common.write_text(json.dumps({'admin_password': 'retained-common-synthetic'}))
            fallback.write_text(json.dumps({'admin_password': 'retained-per-site-synthetic'}))
            original = (common.read_bytes(), fallback.read_bytes())
            self.assertEqual(retained_native_admin(common, fallback), {'admin_password': 'retained-common-synthetic'})
            self.assertEqual(original, (common.read_bytes(), fallback.read_bytes()))

    def test_native_http_reason_is_strictly_whitelisted(self):
        r = SimpleNamespace(url='http://localhost/', history=[], headers={},
                            json=lambda: {'message': 'Invalid login credentials', 'exc_type': 'AuthenticationError'})
        self.assertEqual(diag.response_data(r)['native_reason'], 'Invalid login credentials')

    def test_common_retained_credential_does_not_require_missing_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            common = Path(folder)/'common.json'
            common.write_text(json.dumps({'admin_password':'retained-synthetic'}))
            self.assertEqual(retained_native_admin(common, Path(folder)/'missing.json'),
                             {'admin_password':'retained-synthetic'})


if __name__ == '__main__': unittest.main()
