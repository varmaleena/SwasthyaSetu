// Production uses the same Vercel origin. Local Vite development keeps the API on :8000.
export const BASE=import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV?'http://localhost:8000':'');
export class ApiError extends Error {constructor(public code:string,message:string){super(message)}}
export async function api(path:string,body?:unknown,key:string=crypto.randomUUID()):Promise<any>{
  const token=sessionStorage.getItem('token');
  const response=await fetch(BASE+path,{method:body===undefined?'GET':'POST',headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body!==undefined?{'Content-Type':'application/json','Idempotency-Key':key}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(45000)});
  const data=await response.json();if(!response.ok)throw new ApiError(data.code,data.message);return data;
}
export async function upload(file:File){const form=new FormData();form.append('file',file);const r=await fetch(BASE+'/api/v1/evidence',{method:'POST',headers:{Authorization:'Bearer '+sessionStorage.getItem('token'),'Idempotency-Key':crypto.randomUUID()},body:form,signal:AbortSignal.timeout(30000)});const data=await r.json();if(!r.ok)throw new Error(data.message);return data;}
export type Draft={id:string;session:string;captured_at:string;body:any};
export function drafts():Draft[]{return JSON.parse(localStorage.getItem('drafts')||'[]')}
export function saveDraft(body:any){const d={id:crypto.randomUUID(),session:sessionStorage.getItem('session_id')!,captured_at:new Date().toISOString(),body};localStorage.setItem('drafts',JSON.stringify([...drafts(),d]));}
