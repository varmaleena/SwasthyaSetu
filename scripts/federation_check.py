"""Spawn two independent nodes with only their own database URL. No raw rows cross pipes."""
import json,os,subprocess,sys
from pathlib import Path
from federation.coordinator import aggregate

def main():
    processes=[];messages=[]
    try:
        for state in ['A','B']:
            env={k:v for k,v in os.environ.items() if not k.startswith('STATE_') and 'GEMINI' not in k and 'TOKEN_SECRET' not in k}
            env.update(NODE_STATE=state)
            env[f'STATE_{state}_DATABASE_URL']=os.getenv(f'STATE_{state}_DATABASE_URL',f'sqlite:///state_{state.lower()}.db')
            proc=subprocess.Popen([sys.executable,'-m','federation.node'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
            processes.append(proc)
        for proc in processes:
            line=proc.stdout.readline()
            if not line: raise RuntimeError(proc.stderr.read())
            messages.append(json.loads(line))
        candidate=aggregate(messages);decisions=[]
        for proc in processes:
            proc.stdin.write(json.dumps(candidate)+'\n');proc.stdin.flush()
        for proc in processes:
            out,err=proc.communicate(timeout=45)
            if proc.returncode: raise RuntimeError(err)
            decisions.append(json.loads(out))
        evidence={'status':'measured separate-process exchange','messages':messages,'candidate':candidate,'decisions':decisions,
            'raw_rows_exchanged':False,'limitations':'Synthetic model parameters can leak information; no secure aggregation.'}
        Path('data/evaluation').mkdir(exist_ok=True);Path('data/evaluation/federation.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))
    finally:
        for proc in processes:
            if proc.poll() is None: proc.kill()
if __name__=='__main__': main()
