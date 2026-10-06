"""Prove the reproduction restriction never performs external transport."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class OfflineTransportTests(unittest.TestCase):
    def execute(self, program):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'events.jsonl'
            env = {**os.environ, 'PYTHONPATH': str(Path(__file__).parent / 'observer'),
                   'CCM_OFFICIAL_OFFLINE': '1', 'CCM_OFFICIAL_OBSERVE': '0',
                   'CCM_OFFICIAL_OBSERVATION': str(output)}
            result = subprocess.run([sys.executable, '-c', program], env=env,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return [json.loads(line) for line in output.read_text().splitlines()]

    def test_external_http_rejected_before_adapter_with_no_fake_response(self):
        events = self.execute("""
import requests
from unittest.mock import patch
with patch('requests.adapters.HTTPAdapter.send') as adapter:
    try: requests.get('https://example.invalid/private?token=never-publish')
    except requests.exceptions.ConnectionError: pass
    else: raise AssertionError('external request accepted')
    adapter.assert_not_called()
""")
        self.assertTrue(any(e['kind'] == 'external_http_rejected' for e in events))
        self.assertNotIn('never-publish', str(events))
        self.assertFalse(any(e['kind'] == 'http_response' for e in events))

    def test_external_dns_and_socket_rejected_but_loopback_resolves(self):
        events = self.execute("""
import socket
assert socket.getaddrinfo('127.0.0.1', 3307)
assert socket.getaddrinfo('0.0.0.0', 8002)
for action in (lambda: socket.getaddrinfo('example.invalid', 443),
               lambda: socket.socket().connect(('192.0.2.1', 443))):
    try: action()
    except PermissionError: pass
    else: raise AssertionError('external transport accepted')
""")
        self.assertEqual(sum(e['kind'] == 'external_transport_rejected' for e in events), 2)

    def test_official_in_memory_response_is_preserved_without_socket_or_registry_consumption(self):
        events = self.execute("""
import requests, responses, socket
from unittest.mock import patch
with responses.RequestsMock() as native:
    native.add(responses.POST, 'https://mocked.invalid/post', json={'fixture': 'official'}, status=201)
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('socket used')) as connect:
        result = requests.post('https://mocked.invalid/post')
        assert result.status_code == 201 and result.json() == {'fixture': 'official'}
        assert len(native.calls) == 1
        connect.assert_not_called()
""")
        self.assertTrue(any(e['kind'] == 'native_mock_dispatch' for e in events))
        self.assertFalse(any(e['kind'] == 'external_http_rejected' for e in events))

    def test_responses_passthrough_and_unmocked_provider_remain_rejected(self):
        events = self.execute("""
import requests, responses
from unittest.mock import patch
with responses.RequestsMock() as native:
    native.add_passthru('https://example.invalid/')
    with patch('responses._real_send', side_effect=AssertionError('transport called')) as real:
        try: requests.get('https://example.invalid/private?token=never-publish')
        except requests.exceptions.ConnectionError: pass
        else: raise AssertionError('passthrough accepted')
        real.assert_not_called()
try:
    with responses.RequestsMock() as native:
        native.add(responses.GET, 'https://example.invalid/', passthrough=True)
        try: requests.get('https://example.invalid/')
        except requests.exceptions.ConnectionError: pass
        else: raise AssertionError('passthrough response accepted')
        assert len(native.calls) == 0
except AssertionError as exc:
    assert 'Not all requests have been executed' in str(exc)
else:
    raise AssertionError('native assertion was unexpectedly bypassed')
""")
        self.assertEqual(sum(e['kind'] == 'external_http_rejected' for e in events), 2)
        self.assertNotIn('never-publish', str(events))

if __name__ == '__main__':
    unittest.main()
