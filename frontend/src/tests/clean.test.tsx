import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi,afterEach} from 'vitest';
import App from '../App';
import type {State} from '../types';
const empty:State={sources:[],tasks:[],drafts:[],checks:[],agent_runs:[],profile:{name:'Kevin',goal:'Learn',daily_enabled:false,timezone:'America/Los_Angeles'},connections:[],workspaces:[],next_run:'',mode:'local',eligibility:'Prototype'};
afterEach(()=>vi.unstubAllGlobals());
function setup(data=empty){vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>url.includes('bootstrap')?{token:'test'}:data})));render(<App/>);}
it('starts quietly and gives each section its own genuine empty state',async()=>{
 setup();
 expect(await screen.findByText('Your day starts with your material.')).toBeVisible();
 expect(screen.queryByRole('button',{name:/Load demo/})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'School'}));
 expect(screen.getByText('Bring your schoolwork here.')).toBeVisible();
 expect(screen.getByRole('button',{name:'Add material'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Projects'}));
 expect(screen.getByText('Your project context will come together here.')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Mail'}));
 expect(screen.getByRole('button',{name:'Connect Gmail'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Connect Gmail'}));
 expect(screen.getByRole('dialog')).toHaveTextContent('Google authorization setup is not configured');
 expect(screen.getByRole('dialog')).toHaveTextContent('No inbox has been accessed');
});
it('keeps source selection out of Today until preparation is requested',async()=>{
 const source={id:'s1',content_hash:'h',provider_id:'p',connection_id:'imports',kind:'lecture',title:'My lecture',body:'Intersection means both.',metadata:{course:'CS'},revision:1,fetched_at:'2026-11-03T12:00:00Z',timezone_known:false};
 setup({...empty,sources:[source]});
 await screen.findByRole('button',{name:'Prepare next steps'});
 expect(screen.queryByText(/Approved context/)).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Prepare next steps'}));
 expect(screen.getByRole('dialog')).toHaveTextContent('My lecture');
});
