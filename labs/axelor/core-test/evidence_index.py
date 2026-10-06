"""Content-addressed index; all files are loaded and checked, never just the index.

This changes packaging only. Business expectations remain in the native reviewers.
Final derived coverage and the index itself are excluded from their own hashes;
phase-coverage.json retains the complete immutable pre-index coverage instead.
"""
import base64,hashlib,json,zlib
from pathlib import Path,PurePosixPath

FORMAT='ccm-isolated-repeat-index-v1'

class EvidenceUnavailable(AssertionError):
    """Missing complete files cannot establish a reviewed repetition verdict."""

def file_notices(index,root):
    """Stream each original file once; no aggregate tree is logged or built."""
    root=Path(root).resolve();entries={e['path']:e for v in index['phases'].values() for e in v['files']}
    if index.get('restore'):entries[index['restore']['path']]=index['restore']
    for relative,entry in sorted(entries.items()):
        raw=(root/relative).read_bytes()
        assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
        encoded=base64.b64encode(zlib.compress(raw,9)).decode();count=max(1,(len(encoded)+2799)//2800)
        for i in range(count):
            yield {'complete_evidence_file':relative,'reference':index['reference'],'bytes':len(raw),
                'content_sha256':entry['sha256'],'encoding':'zlib+base64','fragment_count':count,
                'fragment_index':i,'base64_fragment':encoded[i*2800:(i+1)*2800],
                **({'role':entry['role']} if entry.get('role') else {})}

def recover_files(notices,root,reference):
    """Missing/truncated/conflicting fragments never become a recovered file."""
    root=Path(root).resolve();bundles={};recovered=[]
    for item in notices:
        if not item.get('complete_evidence_file') or item.get('reference')!=reference:continue
        key=(item['complete_evidence_file'],item.get('content_sha256'),item.get('bytes'))
        bundles.setdefault(key,[]).append(item)
    for (relative,sha,size),parts in bundles.items():
        try:
            p=PurePosixPath(relative);assert p.parts and not p.is_absolute() and '..' not in p.parts
            path=root.joinpath(*p.parts).resolve();assert path.is_relative_to(root)
            count=parts[0]['fragment_count'];assert count>0 and len(parts)==count and {v['fragment_index'] for v in parts}==set(range(count))
            assert all(v['fragment_count']==count and v['encoding']=='zlib+base64' for v in parts)
            raw=zlib.decompress(base64.b64decode(''.join(v['base64_fragment'] for v in sorted(parts,key=lambda v:v['fragment_index'])),validate=True))
            assert len(raw)==size and hashlib.sha256(raw).hexdigest()==sha
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():assert path.read_bytes()==raw,'Existing complete file differs; do not overwrite'
            else:path.write_bytes(raw)
            recovered.append(relative)
        except (AssertionError,KeyError,TypeError,ValueError,zlib.error):continue
    return recovered

def descriptor(root,path,role=None):
    root=root.resolve();path=path.resolve();relative=path.relative_to(root).as_posix();raw=path.read_bytes()
    return {'path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),**({'role':role} if role else {})}

def build_index(root,phases,restore=None):
    root=root.resolve();result={'format':FORMAT,'phases':{}}
    if restore is not None:result['restore']=descriptor(root,restore,'restore')
    for phase,(directory,smoke) in phases.items():
        directory=directory.resolve();coverage_path=directory/'phase-coverage.json'
        # Preserve the exact coverage before any final derived criterion updates.
        if not coverage_path.exists():coverage_path.write_bytes((directory/'coverage.json').read_bytes())
        coverage=json.loads(coverage_path.read_bytes());assert len(coverage['groups'])==34
        roles={coverage_path:'coverage',directory/'build-evidence.json':'build_evidence',directory/'benchmark.json':'benchmark',smoke.resolve():'smoke'}
        for name in ('CO00','TAX01-W'):roles[directory/(name+'-gate.json')]='gate:'+name
        for row in coverage['groups']:roles[directory/(row['case']+'.json')]='group:'+row['case']
        paths=set(p for p in directory.rglob('*') if p.is_file() and p.name not in ('coverage.json','isolated-repeat.json'))|set(roles)
        result['phases'][phase]={'files':[descriptor(root,path,roles.get(path)) for path in sorted(paths)]}
    return result

def _reader(root):
    if root is None:raise EvidenceUnavailable('Index requires its evidence directory; index alone cannot establish PASS')
    root=Path(root).resolve();checked={};receipt={'files_loaded':0,'bytes_loaded':0,'all_hashes_verified':True}
    def read(entry):
        relative=PurePosixPath(entry['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and relative.parts,'Unsafe evidence path'
        path=root.joinpath(*relative.parts).resolve();assert path.is_relative_to(root),'Evidence escaped its directory'
        if not path.is_file():raise EvidenceUnavailable('Missing complete evidence: '+entry['path'])
        raw=path.read_bytes();assert len(raw)==entry['bytes'],'Evidence byte size differs: '+entry['path']
        assert hashlib.sha256(raw).hexdigest()==entry['sha256'],'Evidence hash differs: '+entry['path']
        # No duplicated references may hide a second value under the same path.
        if entry['path'] in checked:assert checked[entry['path']]==(entry['bytes'],entry['sha256'])
        else:
            checked[entry['path']]=(entry['bytes'],entry['sha256'])
            receipt['files_loaded']+=1;receipt['bytes_loaded']+=len(raw)
        return raw
    return read,receipt

def _phase(files,read,phase_roles):
    assert files,'Empty phase is not executed evidence';roles={};case_paths=set();parsed={}
    # Check every referenced file, including raw CSV/logs/supporting exports.
    # Only role-marked JSON becomes input to the original native assertions.
    for entry in files:
        assert entry['path'] not in case_paths,'Duplicate file in a phase';case_paths.add(entry['path'])
        raw=read(entry)
        if entry.get('role'):
            role=entry['role'];assert role not in roles,'Duplicate evidence role';roles[role]=entry['path'];parsed[role]=json.loads(raw)
            assert entry['path'] not in phase_roles,'Independent phases cannot reuse the same role file';phase_roles.add(entry['path'])
    for role in ('coverage','build_evidence','benchmark','smoke','gate:CO00','gate:TAX01-W'):assert role in parsed,'Missing referenced evidence role: '+role
    coverage=parsed['coverage'];assert len(coverage['groups'])==34
    required={'group:'+r['case'] for r in coverage['groups']};assert len(required)==34,'Coverage must contain 34 distinct groups'
    assert {r for r in parsed if r.startswith('group:')}==required,'All 34 complete case files must be referenced'
    return {'coverage':coverage,'build_evidence':parsed['build_evidence'],'benchmark':parsed['benchmark'],'smoke':parsed['smoke'],
        'gates':{name:parsed['gate:'+name] for name in ('CO00','TAX01-W')},'groups':{row['case']:parsed['group:'+row['case']] for row in coverage['groups']}}

def load_phase(index,root,phase):
    """A full phase can be reviewed alone, never accepted as a full repetition."""
    assert index.get('format')==FORMAT and set(index['phases'])=={phase}
    read,receipt=_reader(root)
    return _phase(index['phases'][phase]['files'],read,set()),receipt

def load_index(index,root):
    assert index.get('format')==FORMAT,'Complete indexed repeat evidence required'
    read,receipt=_reader(root);phase_roles=set()
    payload={'reference':index['reference'],'restore':json.loads(read(index['restore']))}
    assert set(index['phases'])=={'primary','repeat'}
    for phase in ('primary','repeat'):
        payload[phase]=_phase(index['phases'][phase]['files'],read,phase_roles)
    return payload,receipt

if __name__=='__main__':
    import argparse,sys
    parser=argparse.ArgumentParser(description='Load every indexed file, verify bytes/SHA256 and apply the original native repeat assertions')
    parser.add_argument('--index',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,required=True);args=parser.parse_args()
    try:
        payload,receipt=load_index(json.loads(args.index.read_bytes()),args.root)
        from repeat import assert_repeat_contents
        assert_repeat_contents(payload,args.fixtures)
    except Exception as error:
        print(json.dumps({'status':'FAIL','error':type(error).__name__+': '+str(error)}));sys.exit(1)
    print(json.dumps({'status':'PASS',**receipt}))
