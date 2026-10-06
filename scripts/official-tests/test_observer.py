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

if __name__ == '__main__':
    unittest.main()
