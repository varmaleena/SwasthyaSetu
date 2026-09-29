"""Private Supabase evidence; inline DB fallback is local-only and always labelled."""
import base64, os
import httpx
from services.api.domain import fail

def store(state,sid,eid,data,mime):
    url=os.getenv(f'STATE_{state}_STORAGE_URL'); key=os.getenv(f'STATE_{state}_STORAGE_KEY')
    path=f'{sid}/{eid}'
    if url and key:
        r=httpx.post(f'{url.rstrip("/")}/storage/v1/object/evidence/{path}',headers={'Authorization':f'Bearer {key}','apikey':key,'Content-Type':mime},content=data,timeout=20)
        if r.status_code not in [200,201]: fail('STORAGE_FAILURE','Private evidence upload failed',503)
        return {'path':path,'backend':'supabase-private'}
    if os.getenv('APP_ENV','local')!='local': fail('STORAGE_NOT_CONFIGURED','Configure a private evidence bucket for this state',503)
    return {'base64':base64.b64encode(data).decode(),'backend':'local-database-development-only'}

def load(state,payload):
    if payload['backend']=='local-database-development-only':
        if os.getenv('APP_ENV','local')!='local': fail('STORAGE_MODE','Local evidence not permitted in hosted mode',503)
        return base64.b64decode(payload['base64'])
    url=os.environ[f'STATE_{state}_STORAGE_URL']; key=os.environ[f'STATE_{state}_STORAGE_KEY']
    r=httpx.get(f'{url.rstrip("/")}/storage/v1/object/authenticated/evidence/{payload["path"]}',headers={'Authorization':f'Bearer {key}','apikey':key},timeout=20)
    if r.status_code!=200: fail('STORAGE_FAILURE','Private evidence unavailable',503)
    return r.content
