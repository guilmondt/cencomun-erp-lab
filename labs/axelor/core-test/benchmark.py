#!/usr/bin/env python3
"""Frozen exact load, 20 warmups + 1000 real serial requests per operation."""
import argparse,csv,json,math,os,platform,time,subprocess,sys
from pathlib import Path
from decimal import Decimal
from run import NativeClient,REFERENCE,publish_complete_evidence,verify_bundle,exception_status
from api_cases import ApiCases

def assert_benchmark(evidence,fixtures):
    spec=json.loads((fixtures/'benchmark.json').read_text())
    assert evidence['reference']==REFERENCE and evidence['seed']==spec['seed']==100
    assert evidence['status']=='PASS' and evidence['serial'] is True
    loaded=evidence['loaded'];assert loaded['counts']=={'products':1000,'customers':100,'orders':1000,'bank_rows':1000}
    native=loaded['native'];assert native['read_boundary']=='separate-http-after-benchmark-commit'
    products={r['code']:r for r in native['products']};customers={r['code']:r for r in native['customers']}
    for r in spec['products']:
        n=products[r['id']];assert n['name']==r['name'] and Decimal(str(n['price']))==Decimal(r['price']) and Decimal(str(n['cost']))==Decimal(r['cost'])
    assert set(products)=={r['id'] for r in spec['products']}
    assert set(customers)=={r['id'] for r in spec['customers']}
    for r in spec['customers']:assert customers[r['id']]['name']==r['name'] and customers[r['id']]['company_ids']==[native['company_id']]
    assert len(native['stock'])==1000 and {r['product'] for r in native['stock']}==set(products)
    assert all(Decimal(str(r['qty']))==5 and Decimal(str(r['cost']))==1 for r in native['stock'])
    orders={r['id']:r for r in native['orders']};assert set(orders)=={r['id'] for r in spec['orders']}
    for r in spec['orders']:
        o=orders[r['id']];assert o['state']=='NEW' and o['creator']=='ccm-operator' and o['native_id']>0
        assert o['saleOrder_id'] is None and o['delivery_id'] is None and o['invoice_id'] is None
    assert len(native['bank_rows'])==1000 and len({r['key'] for r in native['bank_rows']})==1000
    assert len(evidence['rows'])==3060
    for kind in ('search','inventory','create'):
        rows=[r for r in evidence['rows'] if r['operation']==kind]
        assert len(rows)==1020 and sum(r['warmup'] for r in rows)==20
        assert all(r['http_status']==(201 if kind=='create' else 200) for r in rows)
        assert all(isinstance(r['query_count'],int) and r['query_count']>0 and isinstance(r['db_ms'],(int,float)) and r['db_ms']>=0 and r['server_ms']>=r['db_ms'] for r in rows)
        samples=[r for r in rows if not r['warmup']];assert {r['sample'] for r in samples}==set(range(1000))
        result=next(r for r in evidence['operations'] if r['operation']==kind);ordered=sorted(r['elapsed_ms'] for r in samples)
        assert result['samples']==1000 and result['warmup']==20 and result['errors']==0
        for p in (50,95,99):assert result['p'+str(p)]==round(ordered[math.ceil(p/100*1000)-1],5)
    assert evidence['resources']['logical_cpus']>0 and evidence['resources']['memory_total_kb']>0
    final=evidence['after'];assert len(final['orders'])==2020 and len({r['native_id'] for r in final['orders']})==2020
    assert all(r['state']=='NEW' and r['saleOrder_id'] is None for r in final['orders'])
    assert sorted(native['stock'],key=lambda r:r['id'])==sorted(final['stock'],key=lambda r:r['id'])
    assert len(evidence['pagination']['ids'])==len(set(evidence['pagination']['ids']))==1000
    assert set(evidence['pagination']['ids'])==set(products)

def run_benchmark(admin,base,fixtures,output,rows):
    verify_bundle(fixtures);spec=json.loads((fixtures/'benchmark.json').read_text());runner=ApiCases(admin,base,fixtures,output,rows)
    e={'case':'BENCHMARK-FIXED-PROFILE','reference':REFERENCE,'revision':2,'status':'UNRUN','seed':100,'serial':True,'rows':[],'operations':[],'units':'milliseconds','percentile':'nearest-rank','steps':[]}
    def order(id,customer,product,qty,price,financed):return {'id':id,'company_id':'CCM-LAB-001','customer_id':customer,'warehouse':'WH-LAB-001-BENCH','channel':'STORE','currency':'USD','tax_rate':'0','financed_amount':financed,'shipping_expense':'0.00','guide':None,'datetime':spec['clock'],'lines':[{'product_id':product,'qty':qty,'unit_price':price}]}
    try:
        runner.adapter=subprocess.Popen([sys.executable,str(Path(__file__).with_name('adapter.py')),'--erp-base',base],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);runner.url='http://127.0.0.1:'+str(json.loads(runner.adapter.stdout.readline())['listening_port']);e['catalog']=admin.action('ccm-core-benchmark-prepare','BENCH');e['receipt']=admin.action('ccm-core-benchmark-seed','BENCH')
        assert e['receipt']['native_status']==3
        for row in spec['orders']:
            r=runner.api('operator','/cashea/orders',order(row['id'],row['customer_id'],row['product_id'],row['qty'],row['price'],row['financed']),'BENCH-SEED:'+row['id'])
            assert r['http_status']==201 and r['response']['status']=='NEW' and not r['response']['replay'],r
        native=admin.action('ccm-core-benchmark-inspect','BENCH');e['loaded']={'counts':{k:len(native[k]) for k in ('products','customers','orders','bank_rows')},'native':native}
        e['pagination']={'ids':[],'requests':[]}
        for page in range(1,11):
            r=runner.api('reader',runner.query('/products/search',q='BENCH-P',page=page,page_size=100));e['pagination']['requests'].append(r)
            assert r['http_status']==200 and r['response']['total']==1000
            e['pagination']['ids'] += [v['id'] for v in r['response']['items']]
        for kind in ('search','inventory','create'):
            for warmup,count in ((True,20),(False,1000)):
                for i in range(count):
                    started=time.perf_counter()
                    if kind=='search':r=runner.api('operator',runner.query('/products/search',**spec['selected']['search']))
                    elif kind=='inventory':r=runner.api('operator',runner.query('/inventory/BENCH-P0000',warehouse='WH-LAB-001-BENCH'))
                    else:
                        id=('BENCH-WARM-' if warmup else 'BENCH-SAMPLE-')+f'{i:04}';r=runner.api('operator','/cashea/orders',order(id,'BENCH-C000','BENCH-P0000','1','10.00','6.00'),id)
                    elapsed=round((time.perf_counter()-started)*1000,5);meta=r['response'].get('_meta',{})
                    sample={'operation':kind,'warmup':int(warmup),'sample':i,'http_status':r['http_status'],'elapsed_ms':elapsed,**{k:meta.get(k) for k in ('server_ms','query_count','db_ms')}};e['rows'].append(sample)
                    if r['http_status']!=(201 if kind=='create' else 200):e['failed_request']=r
                    assert r['http_status']==(201 if kind=='create' else 200),r
                    assert isinstance(meta.get('query_count'),int) and meta['query_count']>0,'Actual native JDBC metrics required'
                    if kind=='search':assert [v['id'] for v in r['response']['items']]==['BENCH-P0000']
                    elif kind=='inventory':assert r['response']['on_hand']=='5'
                    else:assert r['response']['status']=='NEW' and r['response']['replay'] is False
            measured=sorted(r['elapsed_ms'] for r in e['rows'] if r['operation']==kind and not r['warmup'])
            e['operations'].append({'operation':kind,'samples':1000,'warmup':20,'errors':0,**{'p'+str(p):round(measured[math.ceil(p/100*1000)-1],5) for p in (50,95,99)}})
        e['after']=admin.action('ccm-core-benchmark-inspect','BENCH')
        e['resources']={'platform':platform.platform(),'python':platform.python_version(),'logical_cpus':os.cpu_count(),'cpu_affinity':len(os.sched_getaffinity(0)),'memory_total_kb':int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:'))),**{p:Path('/sys/fs/cgroup/'+p).read_text().strip() if Path('/sys/fs/cgroup/'+p).exists() else None for p in ('cpu.max','memory.max')}}
        e['status']='PASS';assert_benchmark(e,fixtures)
    except Exception as error:
        e.update(status=exception_status(error),error=str(error),error_type=type(error).__name__)
        if hasattr(error,'native_failure'):e['native_action_failure']=error.native_failure
    finally:
        if getattr(runner,'adapter',None) and runner.adapter.poll() is None:runner.adapter.terminate();runner.adapter.wait(timeout=15)
    (output/'benchmark.json').write_text(json.dumps(e,indent=2)+'\n')
    with (output/'benchmark-raw.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['operation','warmup','sample','http_status','elapsed_ms','server_ms','query_count','db_ms']);writer.writeheader();writer.writerows(e['rows'])
    publish_complete_evidence(e);return e

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    c=NativeClient(args.base);c.login();coverage=json.loads((args.output/'coverage.json').read_text());run_benchmark(c,args.base,args.fixtures,args.output,{r['case']:r for r in coverage['groups']})
