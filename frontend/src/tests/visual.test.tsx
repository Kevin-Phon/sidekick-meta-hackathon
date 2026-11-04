import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import LearningView from '../components/LearningView';
import type {Draft} from '../types';
const draft:Draft={id:'d',title:'States',kind:'study_guide',markdown:'A short overview.',status:'review_needed',provider:'meta',model:'muse-spark-1.3',source_refs:[],generated_at:'',
 steps:[{title:'Start here',explanation:'A state records where you are.',example:'Follow one arrow.'}],
 visuals:[{title:'One transition',explanation:'Read the arrow label.',source_id:'s',page:null,nodes:[{id:'a',label:'Start',detail:'Before input'},{id:'b',label:'Next',detail:'After input'}],edges:[{from:'a',to:'b',label:'input'}]}]};
it('shows small teaching steps and an interactive diagram',()=>{
 render(<LearningView draft={draft}/>);
 expect(screen.getByText('A state records where you are.')).toBeVisible();
 expect(screen.getByRole('img',{name:'One transition'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Explain Next'}));
 expect(screen.getByText('After input')).toBeVisible();
});
it('keeps external markdown images and HTML inert',()=>{
 render(<LearningView draft={{...draft,steps:[],visuals:[],markdown:'![tracker](https://evil.invalid/image)\n<script>alert(1)</script>'}}/>);
 expect(document.querySelector('img')).toBeNull();
 expect(document.querySelector('script')).toBeNull();
});

it('keeps the requested explanation target first when supporting notes are selected',async()=>{
 const {default:AgentPanel}=await import('../components/AgentPanel');
 const {request}=await import('../api');
 const fetcher=vi.fn(async(_url:unknown,_options?:RequestInit)=>({ok:true,json:async()=>({draft_id:'draft'})}));vi.stubGlobal('fetch',fetcher);
 const base={content_hash:'h',revision:1,provider_id:'x',connection_id:'imports',metadata:{},fetched_at:'',timezone_known:false};
 const sources=[{...base,id:'a',title:'Earlier lecture',kind:'lecture',body:'Concepts'},{...base,id:'b',title:'Target assignment',kind:'assignment',body:'Question'}];
 render(<AgentPanel purpose="explain" initialSourceIds={['b']} sources={sources} tasks={[]} drafts={[]} runs={[]} configured changed={async()=>{}} open={()=>{}}/>);
 fireEvent.click(screen.getByRole('checkbox',{name:/Earlier lecture/}));
 fireEvent.click(screen.getByRole('checkbox',{name:/Send these selected/}));
 fireEvent.click(screen.getByRole('button',{name:'Create explanation'}));
 const {waitFor}=await import('@testing-library/react');
 await waitFor(()=>expect(fetcher).toHaveBeenCalled());
 const options=fetcher.mock.calls[0][1] as RequestInit;
 expect(JSON.parse(options.body as string).source_ids).toEqual(['b','a']);
 vi.unstubAllGlobals();
});

it('keeps lengthy notes collapsed when a visual lesson is available',()=>{
 render(<LearningView draft={{...draft,markdown:'Overview paragraph.\n\nExtra detailed notes.'}}/>);
 expect(screen.getAllByText('Overview paragraph.').some(el=>!el.closest('details'))).toBe(true);
 expect(screen.getByText('Extra detailed notes.')).not.toBeVisible();
 expect(document.querySelector('details')?.open).toBe(false);
});
