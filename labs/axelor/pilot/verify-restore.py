#!/usr/bin/env python3
"""Backup/restore check for the authorized local disposable Docker PostgreSQL.
Creates a separate database, keeps the source and private backup untouched.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess
if os.environ.get('CCM_PILOT_DISPOSABLE')!='1':raise SystemExit('Disposable fixture required')
source=os.environ['CCM_PILOT_DB'];target=os.environ['CCM_PILOT_RESTORE_DB']
if source==target or not all(re.fullmatch('[a-z][a-z0-9_]+',v) for v in (source,target)):raise SystemExit('Distinct safe database names required')
container=os.environ.get('CCM_PILOT_DB_CONTAINER','ccm-pilot-local-db');user='ccm_pilot'
backup=Path(os.environ['CCM_PILOT_BACKUP_FILE']);out=Path(os.environ['CCM_PILOT_RESULTS'])
if backup.exists():raise SystemExit('Choose a new private backup path')
def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
with backup.open('xb') as f:run(['docker','exec',container,'pg_dump','-U',user,'-Fc',source],stdout=f)
os.chmod(backup,0o600)
run(['docker','exec',container,'createdb','-U',user,target])
with backup.open('rb') as f:run(['docker','exec','-i',container,'pg_restore','-U',user,'-d',target,'--exit-on-error'],stdin=f)
tables=['core_ccm_pilot_session','core_ccm_pilot_sale','core_ccm_pilot_line','stock_stock_location_line','stock_stock_move','stock_stock_move_line','account_payment_voucher','account_invoice','account_move','account_move_line','sale_sale_order']
def fingerprints(db):
 result={}
 for table in tables:
  sql=f"SELECT count(*),md5(COALESCE(string_agg(row_to_json(t)::text,'' ORDER BY id),'')) FROM {table} t"
  value=subprocess.check_output(['docker','exec',container,'psql','-U',user,'-d',db,'-Atc',sql],text=True).strip()
  result[table]=value
 return result
original=fingerprints(source);restored=fingerprints(target);assert original==restored
proof={'status':'PASS','source':source,'restored_database':target,'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'fingerprints':original,'method':'pg_dump -Fc / pg_restore --exit-on-error; row fingerprints equal for 11 economic tables','uploads':'No uploaded business files in fixture; external deployment still needs uploads/config backup'}
(out/'restore.json').write_text(json.dumps(proof,indent=2));print('Backup restored into isolated database; 11 economic table counts/hashes match PASS')
