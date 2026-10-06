#!/usr/bin/env python3
"""Fixed MCP2025-03-26 stdio protocol, ONLY six HTTP adapter tools, no ERP imports."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOOLS={
 'searchProducts':('GET','/products/search'),
 'getInventory':('GET','/inventory/{product_id}'),
 'getCustomerBalance':('GET','/customers/{customer_id}/balance'),
 'createPurchaseDraft':('POST','/purchases/drafts'),
 'getCashStatus':('GET','/cash/status'),
 'createCasheaOrder':('POST','/cashea/orders'),
}


def adapter_arguments(name,args):
    """Remove only transport keys and fields actually consumed by URL placeholders."""
    method,path=TOOLS[name];payload=dict(args);key=payload.pop('idempotency_key',None)
    for field in ('product_id','customer_id'):
        if '{'+field+'}' in path:path=path.replace('{'+field+'}',urllib.parse.quote(str(payload.pop(field)),safe=''))
    return method,path,payload,key


def call(name,args):
    method,path,payload,key=adapter_arguments(name,args)
    headers={'Cookie':os.environ['CCM_MCP_COOKIE'],'Content-Type':'application/json'}
    if os.environ.get('CCM_MCP_CSRF'):headers['X-CSRF-Token']=os.environ['CCM_MCP_CSRF']
    if key:headers['Idempotency-Key']=key
    raw=None
    if method=='GET':path+='?'+urllib.parse.urlencode(payload)
    else:raw=json.dumps(payload).encode()
    req=urllib.request.Request(os.environ['CCM_ADAPTER_URL']+path,raw,headers,method=method)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req,timeout=600) as response:result=json.load(response);status=response.status
    except urllib.error.HTTPError as error:result=json.load(error);status=error.code
    return {'content':[{'type':'text','text':json.dumps({'status':status,'result':result})}],'isError':status>=400}


def dispatch(request):
    method=request['method']
    if method=='notifications/initialized':return None
    if method=='initialize':result={'protocolVersion':'2025-03-26','capabilities':{'tools':{}},'serverInfo':{'name':'ccm-axelor-core-lab','version':'0.1.0'}}
    elif method=='tools/list':result={'tools':[{'name':name,'description':'LAB '+name+' via native authenticated adapter','inputSchema':{'type':'object','properties':{'company_id':{'type':'string'},'idempotency_key':{'type':'string'}},'required':['company_id'],'additionalProperties':True}} for name in TOOLS]}
    elif method=='tools/call':result=call(request['params']['name'],request['params']['arguments'])
    else:raise KeyError(method)
    return {'jsonrpc':'2.0','id':request.get('id'),'result':result}


if __name__=='__main__':
    for line in sys.stdin:
        request={}
        try:
            request=json.loads(line);response=dispatch(request)
            if response is None:continue
        except Exception:
            response={'jsonrpc':'2.0','id':request.get('id'),'error':{'code':-32602,'message':'Invalid MCP method/tool/arguments'}}
        print(json.dumps(response),flush=True)
