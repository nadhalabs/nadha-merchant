export const API=import.meta.env.VITE_API_URL||'/api';
export const token=()=>localStorage.getItem('token');
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{const r=await fetch(API+path,{...options,headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`}:{}) ,...options.headers}});if(!r.ok)throw new Error((await r.json().catch(()=>({detail:'Request failed'}))).detail);return r.status===204?undefined as T:r.json()}
export const money=(value:string|number|undefined)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(value||0));
