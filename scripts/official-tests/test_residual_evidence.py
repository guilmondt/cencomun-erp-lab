"""Harness/evidence controls; not native Frappe suite results."""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from residual_evidence import latest


class ResidualEvidenceControls(unittest.TestCase):
    def test_empty_startup_result_never_overwrites_real_method_failure(self):
        identifier='frappe.tests.test_db.TestDbConnectWithEnvCredentials.test_connect_fails_with_wrong_credentials_by_env'
        attempts=[('1',Path('socket.json'),{'cases':[{'id':identifier,'status':'FAIL'}],
                   'scope':'selected methods','site':'isolated'}),
                  ('2',Path('tcp.json'),{'cases':[],'scope':'selected methods','site':'isolated'})]
        self.assertEqual(latest(attempts,{identifier})[identifier]['status'],'FAIL')

    def test_backup_exception_does_not_publish_message_or_private_locals(self):
        spec=importlib.util.spec_from_file_location('residual_privacy_control',Path(__file__).parent/'observer/residual_diagnostics.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        frame=SimpleNamespace(f_code=SimpleNamespace(co_filename='/x/frappe/utils/backups.py',
                              co_name='setup_backup_directory'),f_lineno=107,
                              f_locals={'password':'never-publish'})
        error=OSError(30,'never-publish',os.path.expanduser('~/backups'))
        rows=[]
        self.assertTrue(module.trace(frame,'exception',(OSError,error,None),
                                   lambda kind,**data:rows.append({'kind':kind,**data})))
        self.assertEqual(rows[0]['errno'],30)
        self.assertTrue(rows[0]['filename_under_home'])
        self.assertNotIn('never-publish',json.dumps(rows))


if __name__=='__main__':unittest.main()
