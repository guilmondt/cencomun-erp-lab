"""Verify retained evidence/configs/sites without replacing any of them."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path
from run import ALLOWED_SITES, BENCH, PRIVATE, OUT, ROOT, SuiteLock, active_runners


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    with SuiteLock():
        assert not active_runners()
        old = json.loads((PRIVATE/'pre-auth-evidence-hashes.json').read_text())
        same = 0; appended = []
        for name, row in old.items():
            data = Path(name).read_bytes()
            if sha(data)==row['sha256']: same += 1
            else:
                assert len(data)>=row['bytes'] and sha(data[:row['bytes']])==row['sha256']
                appended.append({'path':name,'original_prefix_retained':True})
        protected = json.loads((PRIVATE/'pre-auth-protected-files.json').read_text())
        assert all(sha(Path(name).read_bytes())==digest for name,digest in protected.items())
        common = []
        for bench in ['bench','official-bench']:
            before = ROOT/'recovery/auth-preparation-before'/bench/'sites/common_site_config.json'
            assert before.read_bytes()==(ROOT/bench/'sites/common_site_config.json').read_bytes()
            common.append({'bench':bench,'byte_identical':True})
        sources = []
        for app in ('frappe','erpnext','payments'):
            directory = BENCH/'apps'/app
            changes = subprocess.check_output(['git','status','--porcelain'],cwd=directory,text=True).splitlines()
            assert not changes
            sources.append({'app':app,'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),'clean':True})
        previous = Path.cwd(); sites = []
        os.chdir(BENCH/'sites')
        import frappe
        try:
            for site in ALLOWED_SITES:
                try:
                    frappe.init(site);frappe.connect()
                    count = frappe.db.count('DocType');assert count>0
                    sites.append({'site':site,'native_database_readable':True,'doctype_count':count})
                finally: frappe.destroy()
        finally:os.chdir(previous)
        result = {'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'resume':{'checkout_before':'baad8f9f45373005b72e7c4609ad57ca35dfe34d',
                      'initial_native_runners':0,'retained_attempt_logs_before':81,
                      'same_filesystem_work_recovered':True,'same_kernel_instance_proven':False,
                      'services_initially_stopped':True,'services_started_without_reconstruction':True},
            'preservation':{'artifacts_checked':len(old),'byte_identical':same,
                            'append_only_private_service_logs':appended,'lost_or_replaced':0},
            'protected_retained_private_config_files':{'count':len(protected),'all_byte_identical':True},
            'common_configs':common,'copied_upstream_sources':sources,'official_sites':sites,
            'native_runners_at_close':0,'credential_or_access_changes_to_existing_sites':False,
            'coordinator_published_baad8f9':True,'publication_or_external_restore_repeated':False}
        with (OUT/'auth-preservation.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'preserved':len(old),'identical':same,'append_only':len(appended),'protected_configs':len(protected),'retained_official_sites':len(sites)}))


if __name__=='__main__':main()
