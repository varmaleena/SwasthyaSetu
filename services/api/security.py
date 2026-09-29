import base64, hashlib, hmac, json, os, secrets, time
from pathlib import Path

def secret():
    value = os.getenv('DEMO_TOKEN_SECRET','')
    if len(value)<32:
        if os.getenv('APP_ENV','local')!='local': raise RuntimeError('DEMO_TOKEN_SECRET must contain at least 32 characters')
        p=Path('.local-secret')
        if not p.exists(): p.write_text(secrets.token_hex(32))
        value=p.read_text().strip()
    return value.encode()

def sign(payload, key):
    raw=base64.urlsafe_b64encode(json.dumps(payload,sort_keys=True).encode()).decode().rstrip('=')
    return raw+'.'+hmac.new(key,raw.encode(),hashlib.sha256).hexdigest()

def verify(token,key):
    raw,sig=token.split('.')
    if not hmac.compare_digest(sig,hmac.new(key,raw.encode(),hashlib.sha256).hexdigest()): raise ValueError('Invalid token')
    payload=json.loads(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
    if payload['exp']<time.time() or payload['state'] not in ['A','B']: raise ValueError('Expired token')
    return payload

def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
