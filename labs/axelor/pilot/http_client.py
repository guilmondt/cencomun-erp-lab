import http.cookiejar,json,urllib.request,urllib.parse,os
class Client:
 def __init__(self,user='admin',password='admin'):
  self.base=os.environ.get('CCM_PILOT_URL','http://127.0.0.1:18080/axelor-erp').rstrip('/');self.jar=http.cookiejar.CookieJar();self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar));self.request('/ws/public/app/info');self.request('/callback?client_name=AxelorFormClient',{'username':user,'password':password})
 def request(self,path,data=None):
  headers={'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}
  for c in self.jar:
   if c.name=='CSRF-TOKEN':headers['X-CSRF-Token']=c.value
  if data is not None:headers['Content-Type']='application/json';data=json.dumps(data).encode()
  with self.client.open(urllib.request.Request(self.base+path,data,headers),timeout=120) as r:
   body=r.read();return json.loads(body) if body else None
 def action(self,name,context={},model='com.axelor.apps.base.db.Company'):return self.request('/ws/action',{'action':name,'model':model,'data':{'context':context}})
