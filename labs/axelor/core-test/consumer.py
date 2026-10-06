#!/usr/bin/env python3
"""Private durable test consumer. Its SQLite database is never the ERP database."""
import argparse
import json
import sqlite3
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

FIELDS={'schema_version','event_id','object_id','company_id','actor','occurred_at','correlation_id','type','data'}


def initialize(path):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS receipts(event_id TEXT PRIMARY KEY,payload TEXT NOT NULL,deliveries INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS effects(event_id TEXT PRIMARY KEY,effect_type TEXT NOT NULL,object_id TEXT NOT NULL,applications INTEGER NOT NULL)')


def apply(path,payload):
    assert FIELDS<=set(payload) and payload['schema_version']==1 and payload['company_id']=='CCM-LAB-001'
    assert all(payload[k] for k in FIELDS if k not in ('schema_version','data')) and isinstance(payload['data'],dict)
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'))
    with sqlite3.connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        previous=db.execute('SELECT payload FROM receipts WHERE event_id=?',(payload['event_id'],)).fetchone()
        if previous and previous[0]!=raw:raise ValueError('Event identity payload conflict')
        db.execute('INSERT INTO receipts VALUES(?,?,1) ON CONFLICT(event_id) DO UPDATE SET deliveries=deliveries+1',(payload['event_id'],raw))
        db.execute('INSERT INTO effects VALUES(?,?,?,1) ON CONFLICT(event_id) DO NOTHING',(payload['event_id'],payload['type'],payload['object_id']))


def snapshot(path):
    with sqlite3.connect(path) as db:
        receipts=[{'event_id':r[0],'payload':json.loads(r[1]),'deliveries':r[2]} for r in db.execute('SELECT event_id,payload,deliveries FROM receipts ORDER BY event_id')]
        effects=[{'event_id':r[0],'type':r[1],'object_id':r[2],'applications':r[3]} for r in db.execute('SELECT event_id,effect_type,object_id,applications FROM effects ORDER BY event_id')]
    return {'receipts':receipts,'effects':effects}


class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    disable_nagle_algorithm=True
    def log_message(self,*args):pass
    def reply(self,status,body):
        raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path!='/snapshot':return self.reply(404,{'error':'Unknown private consumer operation'})
        self.reply(200,snapshot(self.server.database))
    def do_POST(self):
        # Drain every body, including the intentional 503, before responding.
        # Otherwise an unread POST may reset the connection instead of yielding
        # the intended HTTP response to the real Java HttpClient.
        raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
        if self.path!='/events':return self.reply(404,{'error':'Unknown private consumer operation'})
        if self.server.fail_flag.exists():return self.reply(503,{'error':'Synthetic consumer unavailable'})
        try:payload=json.loads(raw);apply(self.server.database,payload)
        except (ValueError,AssertionError,KeyError) as error:return self.reply(409,{'error':str(error)})
        self.reply(200,{'accepted':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',type=Path,required=True);parser.add_argument('--fail-flag',type=Path,required=True);args=parser.parse_args()
    initialize(args.database);server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.database=args.database;server.fail_flag=args.fail_flag
    print(json.dumps({'listening_port':server.server_port}),flush=True);server.serve_forever()
