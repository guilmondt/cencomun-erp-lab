import subprocess,json,hashlib
from pathlib import Path
from collections import Counter
repo=Path('/workspace/cencomun-erp-lab');sha='a2f462f67526af94409bd050bf277d78f4782387';base='e0190090fd137576ce273e350d7ce6686d66baf9'
files=subprocess.check_output(['git','ls-tree','-r','--name-only',sha,'labs/axelor/cencomun-baseline/src','labs/axelor/core-test','labs/axelor/ci'],cwd=repo,text=True).splitlines()
sources=[]
for path in files:
 raw=subprocess.check_output(['git','show',sha+':'+path],cwd=repo)
 name=Path(path);lines=raw.decode().splitlines();category='Java runtime' if name.suffix=='.java' and '/src/test/' not in path and '/src/native-test/' not in path else 'Java tests' if name.suffix=='.java' else 'module resources' if '/cencomun-baseline/src/' in path else 'Python regression tests' if name.name.startswith('test_') else 'Core harness' if '/core-test/' in path else 'CI runner'
 sources.append({'path':path,'category':category,'bytes':len(raw),'physical_lines':len(lines),'nonblank_lines':sum(bool(l.strip()) for l in lines),'sha256':hashlib.sha256(raw).hexdigest()})
summary={}
for category in sorted({s['category'] for s in sources}):
 group=[s for s in sources if s['category']==category];summary[category]={'files':len(group),'physical_lines':sum(s['physical_lines'] for s in group),'nonblank_lines':sum(s['nonblank_lines'] for s in group)}
changed=subprocess.check_output(['git','diff','--name-only',base,sha,'--','labs/axelor'],cwd=repo,text=True).splitlines()
result={'lab_commit':sha,'baseline_commit':base,'definition':'Tracked physical and nonblank source lines including comments; excludes generated code, build outputs, dependencies, evidence and Frappe. Does not estimate executed performance or code complexity.','categories':summary,'axelor_files_changed_from_pre_core_baseline':len(changed),'changed_paths':changed,'source_files':sources,'manual_interventions_in_this_correction_block':['B37: native company lock before order load; native bank statement FK; exact causal RPC permission denials; stable cash ordering by native ID; stable complete MCP request_rate type.','B38: outdated native finance Java test-count guard fixed without weakening required suites.','B40: exact scoped admin immutable diagnostic; complete consumer HTTP body/HTTP1.1 and retained process errors; no ERP Java changes or retries.', 'B39: supported native removeAll routes/current audit version, complete POST replay payload, both-direction transport and result parity; no business Java or expected-result changes.'],'schema':'11 native ORM models verified only when SUPPORTED-CONFIGURATION runtime succeeds; no manually applied SQL migration and no upgrade trial.'}
p=Path('/tmp/ccm-ci24-source-metrics.json');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'categories':summary,'changed_axelor_files':len(changed),'output':str(p)}))
