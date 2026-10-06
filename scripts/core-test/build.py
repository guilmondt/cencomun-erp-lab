"""Build actual app wheel; verify packaged DocTypes/resources and unchanged pins."""
import hashlib,json,subprocess,time,zipfile,os
from pathlib import Path
from flit_core.buildapi import build_wheel
REPO=Path(__file__).resolve().parents[2];ROOT=Path('/workspace/.local/frappe-integral');APP=REPO/'labs/frappe/cencomun_erp';OUT=REPO/'reports/evidence/frappe-core';DIST=ROOT/'core-dist';DIST.mkdir(exist_ok=True)
started=time.monotonic();os.chdir(APP);filename=build_wheel(str(DIST));artifact=DIST/filename
with zipfile.ZipFile(artifact) as wheel:
 names=wheel.namelist();models=[p for p in names if '/doctype/' in p and p.endswith('.json')]
 assert len(models)==10,models
 for path in models:assert wheel.read(path)==(APP/path).read_bytes()
 assert 'cencomun_erp/cencomun_erp/.frappe' in names
 assert 'cencomun_erp/core/api.py' in names and 'cencomun_erp/core/permissions.py' in names
 assert 'Version: 0.0.1' in wheel.read('cencomun_erp-0.0.1.dist-info/METADATA').decode()
upstream=[]
for app in ['frappe','erpnext']:
 folder=ROOT/'bench/apps'/app
 diff=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=folder,text=True).strip()
 tag=subprocess.check_output(['git','describe','--tags','--exact-match'],cwd=folder,text=True).strip();assert not diff and tag=='v16.36.1'
 upstream.append({'app':app,'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=folder,text=True).strip(),'tag':tag,'changes':[]})
result={'status':'PASS','wheel':filename,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'bytes':artifact.stat().st_size,'seconds':round(time.monotonic()-started,4),'packaged_doctypes':models,'upstream':upstream,'versions_lock_sha256':hashlib.sha256((REPO/'versions.lock').read_bytes()).hexdigest()}
(OUT/'build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
