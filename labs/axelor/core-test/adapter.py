#!/usr/bin/env python3
"""Loopback six-route adapter. Forwards actual AOP sessions; no ERP DB access."""
import argparse
import json
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTES={
    ('GET','/products/search'):'/ws/ccm/products/search',
    ('GET','/cash/status'):'/ws/ccm/cash/status',
    ('POST','/purchases/drafts'):'/ws/ccm/lab/finance/purchase/create',
    ('POST','/cashea/orders'):'/ws/ccm/lab/orders/create',
}


def route(method,path):
    if (method,path) in ROUTES:return ROUTES[(method,path)]
    parts=path.strip('/').split('/')
    if method=='GET' and len(parts)==2 and parts[0]=='inventory':return '/ws/ccm'+path
    if method=='GET' and len(parts)==3 and parts[0]=='customers' and parts[2]=='balance':return '/ws/ccm'+path
    return None


def normalize(path,result):
    result=dict(result)
    if path=='/products/search':
        result['items']=[{**row,'price':format(Decimal(str(row['cashea_price'])),'.2f')} for row in result['items']]
    if path in ('/purchases/drafts','/cashea/orders') and 'error' not in result:
        result['replay']=result.pop('replayed')
        if path=='/purchases/drafts':
            result['state']={'DRAFT':'Draft','PENDING':'Pending','APPROVED':'Approved'}[result['state']]
            result['approval_amount']=result['usd_base']
        else:result['status']=result.pop('state')
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,value):
        raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def dispatch(self):
        url=urllib.parse.urlsplit(self.path);target=route(self.command,url.path)
        if target is None:return self.reply(404,{'error':'Unknown six-route operation'})
        cookie=self.headers.get('Cookie')
        if not cookie:return self.reply(401,{'error':'Native authenticated session required'})
        headers={'Cookie':cookie,'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}
        if self.headers.get('X-CSRF-Token'):headers['X-CSRF-Token']=self.headers['X-CSRF-Token']
        try:
            raw=None;payload={}
            if self.command=='POST':
                length=int(self.headers.get('Content-Length','0'))
                if length>2_000_000:return self.reply(422,{'error':'LAB payload too large'})
                payload=json.loads(self.rfile.read(length));key=self.headers.get('Idempotency-Key')
                if not key:return self.reply(422,{'error':'Idempotency-Key required'})
                payload={**payload,'request_key':key};raw=json.dumps(payload).encode();headers['Content-Type']='application/json'
            elif url.query:target+='?'+url.query
            req=urllib.request.Request(self.server.erp_base+target,raw,headers,method=self.command)
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(req,timeout=600) as response:status=response.status;data=response.read()
            except urllib.error.HTTPError as error:status=error.code;data=error.read()
            try:result=json.loads(data)
            except ValueError:result={'error':data.decode(errors='replace')[:2200]}
            if status<400:
                result=normalize(url.path,result)
                if (os.environ.get('CCM_ENABLE_FAULTS')=='1' and self.headers.get('X-CCM-Lab-Lose-Response')=='once'
                    and payload.get('id')=='IDEM-LOST' and status==201):
                    os._exit(73)  # Backend commit has returned; kill only this private adapter process.
            else:
                result={'code':str(status),'message':str(result.get('error',result.get('message','Native request rejected')))[:1800],
                        'correlation_id':self.headers.get('Idempotency-Key') or str(uuid.uuid4())}
            self.reply(status,result)
        except (ValueError,KeyError,TypeError) as error:self.reply(422,{'error':'Invalid adapter payload: '+str(error)[:200]})
        except Exception as error:self.reply(503,{'error':'Native ERP transport failure: '+type(error).__name__})
    do_GET=dispatch
    do_POST=dispatch


def serve(erp_base,port):
    url=urllib.parse.urlsplit(erp_base)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost'):raise ValueError('Private LAB loopback ERP required')
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.erp_base=erp_base.rstrip('/')
    print(json.dumps({'listening_port':server.server_port,'routes':6}),flush=True)
    server.serve_forever()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--erp-base',required=True);parser.add_argument('--port',type=int,default=0)
    args=parser.parse_args();serve(args.erp_base,args.port)
