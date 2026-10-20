let token = '';
export async function bootstrap(){const response=await fetch('/api/bootstrap'); if(!response.ok)throw new Error('Could not establish a local session.'); token=(await response.json()).token;}
export async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const response=await fetch('/api/'+path,{method,headers:{...(method!=='GET'?{'X-Sidekick-Token':token}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:JSON.stringify(body)});
 if(!response.ok){const data=await response.json().catch(()=>({detail:'The local service could not complete this request.'}));throw new Error(data.detail||'Request failed.');}
 return response.json();
}
export async function upload(file:File,values:Record<string,string>){
 const params=new URLSearchParams({filename:file.name,...values});
 const response=await fetch('/api/import/file?'+params,{method:'POST',headers:{'X-Sidekick-Token':token,'Content-Type':'application/octet-stream'},body:file});
 const result=await response.json();if(!response.ok)throw new Error(result.detail||'Import failed.');return result;
}
