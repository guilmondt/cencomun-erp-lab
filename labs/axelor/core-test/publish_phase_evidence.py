#!/usr/bin/env python3
"""Preserve exact completed phase files before attempting another runtime start."""
import json,sys
from pathlib import Path
from evidence_index import build_index,file_notices
from run import REFERENCE,publish_complete_evidence

root,directory,smoke=map(Path,sys.argv[1:])
phase='primary' if directory.name=='core-test' else 'repeat'
index=build_index(root,{phase:(directory,smoke)});index.update(reference=REFERENCE,case='EVIDENCE-PHASE-'+phase)
for item in file_notices(index,root):
    print('::notice title=Complete indexed evidence file::'+json.dumps(item),flush=True)
publish_complete_evidence(index)
