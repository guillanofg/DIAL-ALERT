"""Record actual loopback HTTP interactions. Start server.py first."""
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
ROOT=Path(__file__).resolve().parents[1]

def request(obj):
    req=urllib.request.Request('http://127.0.0.1:8099/ask',data=json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=125) as r:status,body=r.status,r.read()
    except urllib.error.HTTPError as r:status,body=r.code,r.read()
    return {'request':obj,'http_status':status,'response':json.loads(body),'seconds':round(time.perf_counter()-start,3)}

if __name__=='__main__':
    rows=[]
    for q in ['target','threshold','limitations','examples']:
        row=request({'question_id':q,'mode':'sources'})
        assert row['http_status']==200
        rows.append(row)
    rejected=request({'question_id':'target','mode':'sources','extra_field':'synthetic-field-rejection-test'})
    assert rejected['http_status']==400
    rows.append(rejected)
    rows.append(request({'question_id':'threshold','mode':'generate'}))
    out=ROOT/'evidence/http_demo.json'
    out.write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{'request':x['request'],'http_status':x['http_status'],'status':x['response'].get('status')} for x in rows],indent=2))
