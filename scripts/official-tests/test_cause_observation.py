"""Regression controls for evidence; these are not upstream suite results."""
import importlib.util
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from web_telemetry import sample


class CauseObservationTests(unittest.TestCase):
    def test_native_responses_registry_is_a_method_and_import_survives_profile(self):
        path = Path(__file__).parent / 'observer/sitecustomize.py'
        spec = importlib.util.spec_from_file_location('unactivated_observer_registry', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        import responses
        mock = responses.RequestsMock()
        mock.add(responses.POST, 'https://mocked.invalid/path?key=secret', json={})
        self.assertEqual(module.registered_requests(mock), [{'method': 'POST',
            'url': 'https://mocked.invalid/path', 'hostname': 'mocked.invalid', 'port': 443,
            'path': '/path'}])

    def test_url_drops_credentials_query_and_fragment(self):
        path = Path(__file__).parent / 'observer/sitecustomize.py'
        spec = importlib.util.spec_from_file_location('unactivated_observer', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual = module.safe_url('http://user:secret@127.0.0.1:8002/api/resource/User?token=private#secret')
        self.assertEqual(actual, {'url': 'http://127.0.0.1:8002/api/resource/User',
            'hostname': '127.0.0.1', 'port': 8002, 'path': '/api/resource/User'})

    def test_listener_ownership_is_separate_from_process_liveness(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            log = Path(folder) / 'web.log'; log.write_text('')
            handle = SimpleNamespace(pid=os.getpid(), poll=lambda: None)
            row = sample(handle, listener.getsockname()[1], log, 'during')
            self.assertTrue(row['listeners'])
            self.assertTrue(row['web_processes'][0]['owned_listener_inodes'])
            self.assertIsNone(row['web_exit_code'])
            port = listener.getsockname()[1]; listener.close()
            row = sample(handle, port, log, 'listener_closed')
            self.assertFalse(row['listeners'])
            self.assertEqual(row['web_processes'][0]['state'], 'R')

    def test_exited_process_is_recorded_without_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'web.log'; log.write_text('')
            process = subprocess.Popen(['true']); process.wait()
            row = sample(process, 65530, log, 'before_cleanup')
            self.assertEqual(row['web_exit_code'], 0)
            self.assertEqual(row['web_processes'][0]['state'], 'GONE')


if __name__ == '__main__':
    unittest.main()
