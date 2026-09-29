"""Owner-invoked real provider check; never runs during readiness or CI."""
import argparse,json,time
from pathlib import Path
from ai.provider import extract,validate_media

def main():
    parser=argparse.ArgumentParser();parser.add_argument('file');args=parser.parse_args()
    data=Path(args.file).read_bytes();mime=validate_media(data);start=time.perf_counter()
    draft,meta=extract(data,mime)
    result={'draft':draft,'metadata':meta,'latency_seconds':round(time.perf_counter()-start,3),'file':Path(args.file).name}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
