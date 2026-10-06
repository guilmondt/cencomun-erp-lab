import copy,hashlib,io,json,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from run import REFERENCE,publish_complete_evidence
from extract_log_evidence import extract
from benchmark import assert_benchmark
from repeat import assert_repeat

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'

def notices(e):
    out=io.StringIO()
    with redirect_stdout(out):publish_complete_evidence(e)
    return [line.replace('::notice title=Core executed group evidence::','##[notice]') for line in out.getvalue().splitlines()]

class TerminalEvidenceRegression(unittest.TestCase):
    def test_compressed_complete_proof_roundtrip_preserves_raw_failed_probe(self):
        e={'case':'PERM-API-NATIVE','reference':REFERENCE,'revision':2,'status':'FAIL','complete':False,'steps':[],'error':'Specific native refusal','raw_probe':{'request':{'id':'P'},'native_stack':['causal frame']*2000}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);log=root/'log';log.write_text('\n'.join(notices(e))+'\n');extract(log,root/'out','test','1'*40,FIXTURES)
            self.assertEqual(json.loads((root/'out/PERM-API-NATIVE.json').read_text()),e)
    def test_latest_partial_or_truncated_phase_cannot_keep_an_earlier_pass(self):
        first={'case':'IDEM03-LOST-RESTART','reference':REFERENCE,'revision':2,'status':'UNRUN','complete':False,'steps':[],'phase':'initial'}
        later={**first,'status':'FAIL','error':'Observed native failure','raw':''.join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(1000))}
        parts=notices(later);self.assertGreater(len(parts),1)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);log=root/'log';log.write_text('\n'.join(notices(first)+parts)+'\n');result=extract(log,root/'out','test','1'*40,FIXTURES)
            self.assertEqual(next(r for r in result['groups'] if r['case']==first['case'])['status'],'FAIL')
            log.write_text('\n'.join(notices(first)+parts[:-1])+'\n');result=extract(log,root/'truncated','test','1'*40,FIXTURES)
            self.assertEqual(next(r for r in result['groups'] if r['case']==first['case'])['status'],'UNRUN')
            self.assertFalse((root/'truncated'/('IDEM03-LOST-RESTART.json')).exists())
    def test_a_restart_script_or_benchmark_label_cannot_approve_runtime(self):
        with self.assertRaises((AssertionError,KeyError)):assert_repeat({'reference':REFERENCE,'status':'PASS','restart_script':'execute later'},FIXTURES)
        with self.assertRaises((AssertionError,KeyError)):assert_benchmark({'reference':REFERENCE,'status':'PASS','seed':100,'serial':True,'rows':[]},FIXTURES)
    def test_frozen_full_benchmark_requires_actual_query_metrics_all_samples_and_load(self):
        spec=json.loads((FIXTURES/'benchmark.json').read_text());native={'company_id':1,'read_boundary':'separate-http-after-benchmark-commit',
            'products':[{'code':r['id'],'name':r['name'],'price':r['price'],'cost':r['cost']} for r in spec['products']],
            'customers':[{'code':r['id'],'name':r['name'],'company_ids':[1]} for r in spec['customers']],
            'stock':[{'id':i+1,'product':r['id'],'qty':'5','cost':'1.00'} for i,r in enumerate(spec['products'])],
            'orders':[{'id':r['id'],'native_id':i+1,'state':'NEW','creator':'ccm-operator','saleOrder_id':None,'delivery_id':None,'invoice_id':None} for i,r in enumerate(spec['orders'])],
            'bank_rows':[{'key':str(i)} for i in range(1000)]}
        rows=[{'operation':kind,'warmup':int(w),'sample':i,'http_status':201 if kind=='create' else 200,'elapsed_ms':1,'query_count':2,'db_ms':.1,'server_ms':.5} for kind in ('search','inventory','create') for w,n in ((True,20),(False,1000)) for i in range(n)]
        final=copy.deepcopy(native);final['orders'] += [{'id':'SAMPLE-'+str(i),'native_id':1001+i,'state':'NEW','saleOrder_id':None} for i in range(1020)]
        e={'reference':REFERENCE,'status':'PASS','seed':100,'serial':True,'loaded':{'counts':{'products':1000,'customers':100,'orders':1000,'bank_rows':1000},'native':native},'after':final,'rows':rows,'operations':[{'operation':k,'samples':1000,'warmup':20,'errors':0,'p50':1,'p95':1,'p99':1} for k in ('search','inventory','create')],'resources':{'logical_cpus':2,'memory_total_kb':1000},'pagination':{'ids':[r['id'] for r in spec['products']]}}
        assert_benchmark(e,FIXTURES)
        for mutation in ('query','db','samples','load','duplicate_page','replayed_creation'):
            bad=copy.deepcopy(e)
            if mutation=='query':bad['rows'][0]['query_count']=None
            if mutation=='db':bad['rows'][0]['db_ms']=None
            if mutation=='samples':bad['rows'].pop()
            if mutation=='load':bad['loaded']['counts']['orders']=999
            if mutation=='duplicate_page':bad['pagination']['ids'][1]=bad['pagination']['ids'][0]
            if mutation=='replayed_creation':bad['rows'][-1]['http_status']=200
            with self.subTest(mutation=mutation),self.assertRaises((AssertionError,TypeError)):assert_benchmark(bad,FIXTURES)
