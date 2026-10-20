import {useEffect,useRef,type ReactNode} from 'react';
import {X} from 'lucide-react';
export default function Overlay({title,close,children,wide=false}:{title:string;close:()=>void;children:ReactNode;wide?:boolean}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;const el=ref.current;el?.focus();function key(e:KeyboardEvent){if(e.key==='Escape')close();if(e.key==='Tab'&&el){const list=Array.from(el.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input,select,textarea'));const first=list[0],last=list.at(-1);if(!first){e.preventDefault();return;}if(e.shiftKey&&(document.activeElement===first||document.activeElement===el)){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}}document.addEventListener('keydown',key);return()=>{document.removeEventListener('keydown',key);previous?.focus();};},[close]);
 return <div className="overlay" onMouseDown={e=>{if(e.target===e.currentTarget)close();}}><div ref={ref} tabIndex={-1} className={'dialog '+(wide?'wide':'')} role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button className="icon-button" onClick={close} aria-label="Close dialog"><X size={20}/></button></header>{children}</div></div>;
}
