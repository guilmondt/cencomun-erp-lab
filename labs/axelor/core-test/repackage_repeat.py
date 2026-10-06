#!/usr/bin/env python3
"""Repackage an already executed legacy repeat without executing ERP business.

The original capsule is retained outside the evidence tree. Every complete
phase JSON is preserved, loaded and hashed before the capsule is replaced.
This is log recovery, not a claim that unavailable artifact files were fetched.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
from evidence_index import build_index,load_index
from repeat import assert_repeat_contents

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def repackage(capsule,root,archive,fixtures):
    root=root.resolve();capsule=capsule.resolve();archive=archive.resolve()
    assert capsule.is_relative_to(root),'Capsule must belong to the evidence tree'
    assert not archive.is_relative_to(root),'Retain the legacy aggregate outside the Git evidence tree'
    raw=capsule.read_bytes();original=json.loads(raw)
    assert all(name in original for name in ('reference','primary','repeat','restore')),'Complete two-phase legacy capsule required'
    archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists():assert archive.read_bytes()==raw,'Archive already contains different evidence'
    else:shutil.copyfile(capsule,archive)
    assert hashlib.sha256(archive.read_bytes()).digest()==hashlib.sha256(raw).digest()
    phases={}
    for phase,directory_name in [('primary','core-test'),('repeat','core-test-repeat')]:
        directory=root/directory_name;directory.mkdir(exist_ok=True);e=original[phase]
        files={'coverage.json':e['coverage'],'build-evidence.json':e['build_evidence'],
            'benchmark.json':e['benchmark'],'smoke.json':e['smoke']}
        files.update({name+'-gate.json':value for name,value in e['gates'].items()})
        files.update({name+'.json':value for name,value in e['groups'].items()})
        for name,value in files.items():
            existing=root/name
            # Preserve a distinct secondary reviewer result as well as the
            # complete runtime result. Equal trees have only one file copy.
            if phase=='primary' and existing.exists() and existing!=capsule and existing!=directory/name and name!='coverage.json':
                destination=directory/name
                if json.loads(existing.read_bytes())!=value:destination=directory/('log-review-'+name)
                assert not destination.exists(),'Recovery destination already exists: '+str(destination)
                existing.rename(destination)
            target=directory/name
            if target.exists():assert json.loads(target.read_bytes())==value,'Existing complete phase evidence differs: '+str(target)
            else:write(target,value)
        # This immutable coverage is the actual phase result from the capsule.
        (directory/'phase-coverage.json').write_bytes((directory/'coverage.json').read_bytes())
        phases[phase]=(directory,directory/'smoke.json')
    # Keep primary supplementary exports in the same tree, without duplicating
    # them. Source receipts and the final reviewed matrix stay at the root.
    for path in list(root.glob('*.json')):
        if path==capsule or path.name in ('coverage.json','evidence-source.json','isolated-restore.json'):continue
        target=root/'core-test'/path.name
        if target.exists():continue
        path.rename(target)
    restore=root/'isolated-restore.json';write(restore,original['restore'])
    index=build_index(root,phases,restore)
    index.update(case=original['case'],reference=original['reference'],revision=original['revision'],
        status='UNRUN',complete=False,
        recovery={'source':'complete legacy Actions notice capsule; no new ERP execution',
            'legacy_capsule_sha256':hashlib.sha256(raw).hexdigest(),'legacy_capsule_bytes':len(raw),
            'legacy_review':{k:original[k] for k in ('status','complete','error') if k in original},
            'limitation':'Files absent from the legacy capsule and recovered log are not recreated or represented as downloaded. The original full CI artifact remains the source for those files.'})
    payload,receipt=load_index(index,root)
    assert payload=={k:original[k] for k in ('reference','restore','primary','repeat')},'Repackaging changed complete business evidence'
    index['file_verification']=receipt
    try:assert_repeat_contents(payload,fixtures);index.update(status='PASS',complete=True)
    except Exception as error:index.update(status='FAIL',error=type(error).__name__+': '+str(error))
    # Only after full equality, loading and hash verification replace the
    # duplicate aggregate. Its complete original remains in the archive.
    write(capsule,index)
    return index

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--capsule',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,required=True);args=parser.parse_args()
    result=repackage(args.capsule,args.root,args.archive,args.fixtures)
    print(json.dumps({k:result[k] for k in ('case','status','complete','file_verification')}))
