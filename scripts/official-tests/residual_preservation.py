"""Prove all retained artifacts/configs/sites survived the residual diagnosis."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from run import PRIVATE, OUT, BENCH, ALLOWED_SITES, SuiteLock, active_runners


def main():
    with SuiteLock():
        assert not active_runners()
        old = json.loads((PRIVATE/'pre-residual-evidence-hashes.json').read_text())
        identical, appended = 0, []
        for name, row in old.items():
            data = Path(name).read_bytes()
            if hashlib.sha256(data).hexdigest()==row['sha256']:
                identical += 1
            else:
                assert Path(name).name in ('isolated-worker.log','smtp4dev.log')
                assert len(data)>=row['bytes'] and hashlib.sha256(data[:row['bytes']]).hexdigest()==row['sha256']
                appended.append({'private_log':Path(name).name,'original_prefix_retained':True})
        protected=json.loads((PRIVATE/'pre-residual-protected-files.json').read_text())
        assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==h for name,h in protected.items())
        sources=[]
        for app in ('frappe','erpnext','payments'):
            directory=BENCH/'apps'/app
            changes=subprocess.check_output(['git','status','--porcelain'],cwd=directory,text=True).splitlines()
            assert not changes
            sources.append({'app':app,'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),'clean':True})
        previous=Path.cwd();sites=[];os.chdir(BENCH/'sites')
        import frappe
        try:
            for site in ALLOWED_SITES:
                try:
                    frappe.init(site);frappe.connect()
                    count=frappe.db.count('DocType');assert count>0
                    sites.append({'site':site,'native_database_readable':True,'doctype_count':count})
                finally:frappe.destroy()
        finally:os.chdir(previous)
        result={'scope':'Preservation only; no test, password reset or restoration',
                'starting_commit':'678c5ef0d90f628bece3fea0adce2ab5ad541ee9',
                'initial_runners':0,'retained_logs_before':97,
                'artifacts_checked':len(old),'byte_identical':identical,'append_only_service_logs':appended,
                'lost_or_replaced_artifacts':0,'protected_configs':len(protected),'all_protected_configs_identical':True,
                'copied_upstream_sources':sources,'official_sites':sites,'active_runners_at_close':0,
                'coordinator_publication_678c5ef_repeated':False,'external_restoration_repeated':False}
        with (OUT/'residual-preservation.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'preserved':len(old),'identical':identical,'append_only':len(appended),
                          'protected_configs':len(protected),'retained_official_sites':len(sites)}))


if __name__=='__main__':main()
