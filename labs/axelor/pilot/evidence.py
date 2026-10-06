"""Write evidence before asserting and retain failure context on every exit."""
import json,traceback,threading
from pathlib import Path
class EvidenceRun:
 def __init__(self,path):self.path=Path(path);self.data={};self.checks=[];self.status='RUNNING';self.lock=threading.RLock()
 def save(self):
  with self.lock:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   temporary=self.path.with_suffix('.tmp')
   temporary.write_text(json.dumps({'status':self.status,'checks':self.checks,'data':self.data},indent=2,default=str));temporary.replace(self.path)
 def __enter__(self):self.save();return self
 def check(self,name,condition,actual=None,expected=None):
  self.checks.append({'name':name,'status':'PASS' if condition else 'FAIL','actual':actual,'expected':expected});self.save()
  assert condition,name
 def __exit__(self,kind,error,tb):
  self.status='FAIL' if error is not None else 'PASS'
  if error is not None:self.data['failure']={'type':kind.__name__,'message':str(error),'traceback':traceback.format_exception(kind,error,tb)}
  self.save();return False
