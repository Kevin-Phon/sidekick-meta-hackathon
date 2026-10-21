import {useState,useEffect,type FormEvent} from 'react';
import {Sparkles,KeyRound,LoaderCircle} from 'lucide-react';
import type {Source,ModelStatus} from '../types';
import {request} from '../api';

export default function ModelPanel({sources,model,changed}:{sources:Source[];model?:ModelStatus;changed:()=>Promise<void>}){
 const eligible=sources.filter(s=>['lecture','assignment','project_note'].includes(s.kind));
 const [key,setKey]=useState(''),[selected,setSelected]=useState(''),[consent,setConsent]=useState(false);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const source=eligible.find(s=>s.id===(selected||eligible[0]?.id));
 useEffect(()=>{setConsent(false);},[source?.id,source?.revision,source?.content_hash]);
 const restricted=Boolean(source?.metadata.active_assessment||source?.metadata.assistance_restricted);
 async function act(action:()=>Promise<unknown>,message:string){setBusy(true);setError('');setNotice('');try{await action();await changed();setNotice(message);}catch(e){setError(e instanceof Error?e.message:'Could not finish the request.');}finally{setBusy(false);}}
 async function saveKey(e:FormEvent){e.preventDefault();const value=key;setKey('');await act(()=>request('model/key','POST',{key:value}),'Key held in server memory for this session. Live generation is not verified yet.');}
 return <section className="panel model-panel"><div className="section-heading"><div><span className="eyebrow">Your model connection</span><h2><Sparkles size={20}/>Muse Spark</h2></div><span className="pill">{model?.verified?'Live generation verified':model?.configured?'Key set · unverified':'Key needed'}</span></div>
 <p>Muse Spark 1.3 · Standard mode. Only the material you select below is sent to Meta. Your profile, other files, and saved mail are excluded.</p>
 <form onSubmit={saveKey} className="model-key-form"><label>Meta API key<input type="password" value={key} onChange={e=>setKey(e.target.value)} autoComplete="off" spellCheck={false} placeholder="Paste here, not in chat" maxLength={1000}/></label><button className="button secondary" disabled={busy||!key.trim()}><KeyRound size={15}/>Use key for this session</button>{model?.configured&&<button type="button" className="text-link" disabled={busy} onClick={()=>void act(()=>request('model/key','POST',{key:''}),'Disconnected. Key removed from server memory. No future requests can use it.')}>Disconnect</button>}</form>
 <p className="tiny">The key is never saved to a file or browser storage. Restarting the service clears it unless supplied through its environment. Creating a key or adding billing stays under your control. Check your Meta credits before generating; this request may incur API usage.</p>
 <div className="model-selection"><label>Material to send<select value={source?.id||''} disabled={busy||!eligible.length} onChange={e=>{setSelected(e.target.value);setConsent(false);setNotice('');}}>{eligible.length?eligible.map(s=><option key={s.id} value={s.id}>{s.title} · v{s.revision}</option>):<option value="">Import a lecture first</option>}</select></label>
 {source&&<details open><summary>Exact source text sent to Meta · {new TextEncoder().encode(source.body).length.toLocaleString()} bytes</summary><pre className="source-text model-preview">{source.body}</pre><p className="tiny">Also included: source title, type, ID and revision, plus Sidekick’s study-guide instructions. No external links are fetched.</p></details>}
 {restricted&&<p className="error-box">This item has assessment restrictions. Worked generation is blocked.</p>}
 <label className="model-consent"><input type="checkbox" checked={consent} disabled={busy||!source||restricted} onChange={e=>setConsent(e.target.checked)}/><span>Send this selected material to Meta to generate a draft for my review.</span></label>
 <button className="button primary" disabled={busy||!model?.configured||!source||!consent||restricted} onClick={()=>void act(async()=>{await request('model/generate','POST',{source_ids:[source!.id],source_revisions:{[source!.id]:source!.revision},source_hashes:{[source!.id]:source!.content_hash},consent:true});setConsent(false);},'Muse Spark draft saved. Open it in School or Projects under Prepared for you.')}>
 {busy?<LoaderCircle size={17} className="spin"/>:<Sparkles size={17}/>}Generate with Muse Spark</button>
 </div>{(error||model?.last_error)&&<p role="alert" className="error-box">{error||model?.last_error}</p>}{notice&&<p role="status" className="toast">{notice}</p>}
 <p className="tiny">Preparing your day and the 9 AM schedule still review local material only. They do not trigger paid model requests.</p>
 </section>;
}
