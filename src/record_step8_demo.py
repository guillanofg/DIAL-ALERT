"""Record real localhost HTTP requests using a declared synthetic session."""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'step8_deployment/demo';out.mkdir(exist_ok=True)
    server=subprocess.Popen([sys.executable,str(ROOT/'step8_deployment/app.py')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base='http://127.0.0.1:8000'
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base+'/health',timeout=1) as r:health=json.load(r)
                break
            except (OSError,urllib.error.URLError):time.sleep(.1)
        else:raise RuntimeError('Local service did not start')
        sample=json.loads((ROOT/'step8_deployment/sample_request.json').read_text())
        req=urllib.request.Request(base+'/predict',data=json.dumps(sample).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:result=json.load(r)
        transcript={'input_type':'synthetic; not a patient record','health':health,'prediction':result}
        (out/'http_execution.json').write_text(json.dumps(transcript,indent=2)+'\n')
        print(json.dumps(transcript,indent=2))
    finally:
        server.terminate();server.wait(timeout=10)

if __name__=='__main__':main()
