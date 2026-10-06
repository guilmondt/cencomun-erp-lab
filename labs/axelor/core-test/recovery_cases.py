#!/usr/bin/env python3
"""Real adapter death after ERP commit, native service restart and durable consumer."""
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from run import REFERENCE, NativeClient, exception_status, publish_complete_evidence, verify_bundle, criteria_for
from order_cases import effects
from api_cases import ApiCases, functional, BOUNDARY
from consumer import snapshot
from collections import Counter

RECOVERY_CHECKS={
 'IDEM03-LOST-RESTART': {'lost-response','adapter-replay','services-restart','durable-replay'},
 'IDEM04-EVENTS-RECOVERY': {'consumer-503','first-delivery','consumer-restart','durable-event-replay'},
}


def assert_recovery_group(evidence,fixtures):
    assert evidence['reference']==REFERENCE and evidence['revision']==2
    case=evidence['case'];steps=evidence['steps'];assert {s['name'] for s in steps}==RECOVERY_CHECKS[case] and len(steps)==len(RECOVERY_CHECKS[case])
    for s in steps:assert s.get('executed') is True and s['status']=='PASS' and s['read_boundary']==BOUNDARY,s['name']
    x={s['name']:s for s in steps}
    if case=='IDEM03-LOST-RESTART':
        lost=x['lost-response'];assert lost['adapter_exit']==73 and lost['transport_error']
        assert not lost['before']['order'] and lost['after']['order']['state']=='NEW'
        assert len(lost['after']['keys'])==1 and not lost['after']['events']
        first=x['adapter-replay'];last=x['durable-replay']
        for r in (first,last):
            assert r['http_status']==200 and r['response']['replay'] is True
            assert r['response']['native_id']==lost['after']['order']['native_id']>0
            assert effects(r['before'])==effects(r['after'])
        assert functional(first['response'])==functional(last['response'])
        restart=x['services-restart']['receipt'];assert restart['app_pid_before']!=restart['app_pid_after']
        assert restart['postgres_before']!=restart['postgres_after'] and restart['postgres_restart_status']=='PASS'
        assert len(last['native_counts']['order_counts']['IDEM-LOST'])==1
    else:
        failed=x['consumer-503'];first=x['first-delivery'];restart=x['consumer-restart'];replay=x['durable-event-replay']
        n=failed['native_response']['failed'];assert n>0 and failed['native_response']['delivered']==0
        assert all(r['http_status']==503 for r in failed['native_response']['attempts'])
        assert failed['consumer']=={'receipts':[],'effects':[]} and all(not r['delivered'] and r['attempts']==1 for r in failed['native_after'])
        assert first['native_response']['delivered']==n and first['native_response']['failed']==0
        assert len(first['consumer']['receipts'])==len(first['consumer']['effects'])==n
        assert all(r['deliveries']==1 for r in first['consumer']['receipts']) and all(r['applications']==1 for r in first['consumer']['effects'])
        assert restart['pid_before']!=restart['pid_after'] and restart['before']==restart['after']==first['consumer']
        assert replay['native_response']['delivered']==n and replay['native_response']['failed']==0
        assert replay['consumer']['effects']==first['consumer']['effects']
        assert all(r['deliveries']==2 for r in replay['consumer']['receipts'])
        assert [{k:v for k,v in r.items() if k!='deliveries'} for r in replay['consumer']['receipts']]==[{k:v for k,v in r.items() if k!='deliveries'} for r in first['consumer']['receipts']]
        assert all(r['delivered'] and r['attempts']==3 for r in replay['native_after'])
        original={r['event_id']:json.loads(r['payload']) for r in failed['native_before']}
        assert set(original)=={r['event_id'] for r in replay['consumer']['receipts']}
        for r in replay['consumer']['receipts']:
            p=r['payload'];assert p==original[r['event_id']] and p['event_id']==r['event_id']
            assert p['schema_version']==1 and p['company_id']=='CCM-LAB-001' and p['actor'] and p['correlation_id'] and p['occurred_at']
            assert p['object_id']==p['data']['id']
        assert {'cashea.approved','cash.closing.confirmed','purchase.approved'}<={p['type'] for p in original.values()}
    return True


def review_recovery_group(row,evidence,fixtures):
    if row['case'] not in RECOVERY_CHECKS:return
    if not evidence or evidence.get('status')!='PASS':
        if evidence:row.update(status=evidence['status'],complete=False,reason=evidence.get('error','Restart proof pending'))
        return
    try:assert_recovery_group(evidence,fixtures)
    except (AssertionError,KeyError,TypeError,ValueError) as error:row.update(status='FAIL',complete=False,reason='Recovery proof rejected: '+str(error))
    else:row.update(status='PASS',complete=True,observed_revision=2,evidence=row['case']+'.json',reason='Real process loss/restart and durable native/consumer reads verified')


class RecoveryCases(ApiCases):
    def store(self,e):
        (self.output/(e['case']+'.json')).write_text(json.dumps(e,indent=2)+'\n')
        self.rows[e['case']].update(status=e['status'],complete=e['complete'],observed_revision=2,evidence=e['case']+'.json',reason=e.get('error','Recovery execution'))
        review_recovery_group(self.rows[e['case']],e,self.fixtures);publish_complete_evidence(e)
    def transport(self):
        self.adapter=subprocess.Popen([sys.executable,str(Path(__file__).with_name('adapter.py')),'--erp-base',self.base],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=dict(os.environ,CCM_ENABLE_FAULTS='1'))
        self.url='http://127.0.0.1:'+str(json.loads(self.adapter.stdout.readline())['listening_port'])
    def stop_adapter(self):
        if self.adapter and self.adapter.poll() is None:self.adapter.terminate();self.adapter.wait(timeout=15)
    def prepare_lost(self):
        start=time.perf_counter();e={'case':'IDEM03-LOST-RESTART','reference':REFERENCE,'revision':2,'complete':False,'status':'UNRUN','steps':[]}
        try:
            self.orders.fixture('IDEM-LOST');self.transport();body=self.orders.payload('CO00','IDEM-LOST',warehouse='WH-LAB-001-IDEM-LOST');body.pop('request_key');e['replay_payload']=body
            def lost(step):
                c=self.actor('operator');headers={'Cookie':'; '.join(c.name+'='+c.value for c in c.cookies),'Content-Type':'application/json','Idempotency-Key':'IDEM-LOST','X-CCM-Lab-Lose-Response':'once','X-CSRF-Token':next((c.value for c in c.cookies if c.name=='CSRF-TOKEN'),'')}
                step.update(request=body,actor='ccm-operator',before=self.snapshot('IDEM-LOST'),transport_error='')
                try:
                    urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(self.url+'/cashea/orders',json.dumps(body).encode(),headers),timeout=600)
                except Exception as error:
                    step['transport_error']=type(error).__name__+': '+str(error)
                    if isinstance(error,urllib.error.HTTPError):step.update(http_status=error.code,response=error.read().decode(errors='replace'))
                try:step['adapter_exit']=self.adapter.wait(timeout=20)
                except subprocess.TimeoutExpired:step['adapter_exit']=None
                finally:step['after']=self.snapshot('IDEM-LOST')
                assert step['transport_error'] and step['adapter_exit']==73,'Lost response requires actual post-commit adapter exit73'
                assert step['after']['order']['state']=='NEW' and len(step['after']['keys'])==1
            self.step(e,'lost-response',lost);self.transport()
            self.attempted(e,'adapter-replay','IDEM-LOST','order','operator','/cashea/orders',body,200,'IDEM-LOST')
            e['phase']='adapter-recovered; native services restart pending'
        except Exception as error:e.update(status=exception_status(error),error=str(error),error_type=type(error).__name__)
        finally:self.stop_adapter()
        e['seconds']=round(time.perf_counter()-start,3);self.store(e);return e
    def after_restart(self,receipt):
        e=json.loads((self.output/'IDEM03-LOST-RESTART.json').read_text());start=time.perf_counter()
        if e['status']!='UNRUN' or len(e['steps'])!=2:
            e['restart_skipped_reason']='Initial post-commit lost response/replay failed; original complete cause retained';self.store(e);return e
        try:
            self.step(e,'services-restart',lambda step:step.update(receipt=json.loads(receipt.read_text())))
            self.transport();step=self.attempted(e,'durable-replay','IDEM-LOST','order','operator','/cashea/orders',e['replay_payload'],200,'IDEM-LOST')
            step['native_counts']=self.admin.action('ccm-core-audit-inspect','AUDIT');assert_recovery_group(e,self.fixtures);e.update(status='PASS',complete=True)
        except Exception as error:e.update(status=exception_status(error),error=str(error),error_type=type(error).__name__)
        finally:self.stop_adapter()
        e['seconds']+=round(time.perf_counter()-start,3);self.store(e);return e
    def events(self):
        e={'case':'IDEM04-EVENTS-RECOVERY','reference':REFERENCE,'revision':2,'complete':False,'steps':[]};start=time.perf_counter();process=None
        def native():return self.admin.action('ccm-core-audit-inspect','AUDIT')['events']
        with tempfile.TemporaryDirectory(prefix='ccm-private-consumer-') as directory:
            database=Path(directory)/'consumer.sqlite';flag=Path(directory)/'unavailable'
            def launch():
                process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('consumer.py')),'--database',str(database),'--fail-flag',str(flag)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                return process,'http://127.0.0.1:'+str(json.loads(process.stdout.readline())['listening_port'])+'/events'
            try:
                def dispatch(step,request):
                    step.update(request=request,native_before=native(),actor='admin')
                    try:step['native_response']=self.admin.request('/ws/ccm/lab/events/dispatch',request)
                    finally:step.update(native_after=native(),consumer=snapshot(database))
                process,url=launch();flag.write_text('Synthetic503')
                def failed(step):
                    dispatch(step,{'consumer_url':url,'replay':False})
                    assert step['native_response']['failed']>0 and step['native_response']['delivered']==0
                self.step(e,'consumer-503',failed);flag.unlink()
                def delivered(step):
                    dispatch(step,{'consumer_url':url,'replay':False});assert step['native_response']['failed']==0
                self.step(e,'first-delivery',delivered)
                def restart(step):
                    nonlocal process,url
                    step.update(before=snapshot(database),pid_before=process.pid);process.terminate();process.wait(timeout=15);process,url=launch();step.update(after=snapshot(database),pid_after=process.pid)
                    assert step['before']==step['after'] and step['pid_before']!=step['pid_after']
                self.step(e,'consumer-restart',restart)
                def replay(step):
                    dispatch(step,{'consumer_url':url,'replay':True})
                self.step(e,'durable-event-replay',replay);assert_recovery_group(e,self.fixtures);e.update(status='PASS',complete=True)
            except Exception as error:e.update(status=exception_status(error),error=str(error),error_type=type(error).__name__)
            finally:
                if process:process.terminate();process.wait(timeout=15)
        e['seconds']=round(time.perf_counter()-start,3);self.store(e);return e


def prepare_recovery(admin,base,fixtures,output,rows):
    runner=RecoveryCases(admin,base,fixtures,output,rows);return [runner.prepare_lost(),runner.events()]


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--restart-receipt',type=Path,required=True);args=parser.parse_args()
    coverage=json.loads((args.output/'coverage.json').read_text());rows={r['case']:r for r in coverage['groups']};admin=NativeClient(args.base);admin.login()
    RecoveryCases(admin,args.base,args.fixtures,args.output,rows).after_restart(args.restart_receipt)
    coverage['counts']=dict(Counter(r['status'] for r in coverage['groups']));coverage['criteria']=criteria_for(coverage['groups'])
    (args.output/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
