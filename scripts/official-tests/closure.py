"""Read-only post-CI preservation proof; never a Core rerun or cloud restore."""
from pathlib import Path
from contextlib import contextmanager
import os
import sys,hashlib,json,datetime,subprocess,urllib.request,urllib.parse
repo=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(repo/'scripts/official-tests'))
from run import ROOT,BENCH,PRIVATE,OUT,active_runners,SuiteLock

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


@contextmanager
def sites_workdir(bench=BENCH):
    """Native site log paths are relative to the sites directory."""
    previous = Path.cwd()
    os.chdir(bench / 'sites')
    try:
        yield
    finally:
        os.chdir(previous)


def main(label='final'):
    with SuiteLock():

        if active_runners(): raise SystemExit('Official native runner active: do not close yet.')
        old=json.loads((PRIVATE/'pre-final-attempt-hashes.json').read_text())
        changed=[name for name,h in old.items() if digest(OUT/name)!=h]
        assert not changed
        logs_checked = 0
        for name in old:
            if name.endswith('-observations.json'):
                continue
            result = json.loads((OUT / name).read_text())
            if result.get('log_sha256'):
                log = PRIVATE / (Path(name).stem + '.log')
                assert log.is_file() and digest(log) == result['log_sha256']
                logs_checked += 1
        prior=['ccm-upstream-frappe.test','ccm-upstream-erpnext.test','ccm-upstream-frappe-fresh.test','ccm-upstream-erpnext-fresh.test','ccm-upstream-frappe-diagnostic.test','ccm-upstream-erpnext-diagnostic.test','ccm-upstream-erpnext-fixture-audit.test','ccm-upstream-erpnext-fixture-order.test']
        import frappe
        sites=[]
        with sites_workdir():
            for site in prior+['ccm-upstream-frappe-final.test','ccm-upstream-erpnext-final.test']:
                assert (BENCH/'sites'/site/'site_config.json').exists()
                try:
                    frappe.init(site,sites_path=str(BENCH/'sites')); frappe.connect()
                    count=frappe.db.count('DocType'); assert count>0
                    sites.append({'site':site,'directory_retained':True,'native_database_readable':True,'doctype_count':count})
                finally: frappe.destroy()
        fixture_paths=subprocess.check_output(['git','ls-files','fixtures/ccm-core-v1'],text=True).splitlines()
        f=[]
        for name in fixture_paths:
            original=subprocess.check_output(['git','show','fcf690dbc58b2b2dcf8d045c49976e3613e804cf:'+name])
            assert hashlib.sha256(original).hexdigest()==digest(repo/name)
            f.append(name)
        assert digest(repo/'versions.lock')=='6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816'
        cloud=repo/'reports/evidence/frappe-cloud/restoration-fcf690d-external.json'
        assert digest(cloud)=='2c86f345b0ab9c545a21be3f28b164e85becf98094fea55b98dc536965f1e7c0'
        private=json.loads((ROOT/'core-private.json').read_text()); user=private['users']['reader']
        headers={'Authorization':'token '+user['api_key']+':'+user['api_secret']}
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        mapping=json.loads((repo/'reports/evidence/frappe-core/http-mapping.json').read_text())
        def get(base,path,native=False):
            req=urllib.request.Request(base+path,headers={**headers,**({'Host':'ccm-core.test'} if native else {})})
            with opener.open(req,timeout=30) as response:
                assert response.status==200
                return json.load(response)
        q=urllib.parse.urlencode({'company_id':mapping['company_id'],'q':'P001'})
        products=get('http://127.0.0.1:8090','/products/search?'+q)['items']
        product=next(r for r in products if r['id']=='P001')
        q=urllib.parse.urlencode({'company_id':mapping['company_id'],'warehouse':mapping['warehouse']})
        stock=get('http://127.0.0.1:8090','/inventory/P001?'+q)
        native=get('http://127.0.0.1:8000','/api/resource/Item/P001',True)['data']
        q=urllib.parse.urlencode({'filters':json.dumps({'item_code':'P001','warehouse':mapping['warehouse']}),'fields':json.dumps(['actual_qty'])})
        bins=get('http://127.0.0.1:8000','/api/resource/Bin?'+q,True)['data']
        from decimal import Decimal
        assert Decimal(product['price'])==Decimal(str(native['cashea_price']))==Decimal('50.00')
        assert len(bins)==1 and Decimal(stock['on_hand'])==Decimal(str(bins[0]['actual_qty']))==Decimal('5')
        data={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only closure, not a Core rerun or cloud restore','historical_attempt_artifacts':{'count':len(old),'hashes_unchanged':True},'official_sites':sites,'shared_oracle':{'files_compared_to_fcf690d':len(f),'all_byte_identical':True},'versions_lock_sha256':digest(repo/'versions.lock'),'cloud_receipt':{'sha256':digest(cloud),'unchanged':True,'reexecuted':False},'authenticated_read':{'site':'ccm-core.test','actor_role':'reader','item':'P001','currency':'USD','price':'50.00','stock':'5','adapter_matches_native':True,'mutations':0},'previous_core_groups':{'run':'20261006T042836Z','mandatory':34,'PASS':34,'rerun_in_this_task':False},'criterion_13':{'status':'BLOCKED','dependent_PATCH_UNRUN':6},'active_native_runners':0}
        data['historical_attempt_artifacts']['private_logs_checked_by_recorded_sha256'] = logs_checked
        with (OUT/(label+'-closure.json')).open('x') as stream: stream.write(json.dumps(data,indent=2)+'\n')
        print(json.dumps({'closure':'PASS','retained_sites':len(sites),'retained_attempt_files':len(old),'oracle_files':len(f),'authenticated_price':'50.00','authenticated_stock':'5'}))


if __name__ == "__main__":
    try:
        import argparse
        parser = argparse.ArgumentParser(); parser.add_argument('--label', default='final', choices=['final', 'cause'])
        main(parser.parse_args().label)
    except Exception as error:
        print("FAIL read-only closure:", type(error).__name__, "— inspect private setup and scripts/official-tests/README.md.")
        raise SystemExit(1) from None
