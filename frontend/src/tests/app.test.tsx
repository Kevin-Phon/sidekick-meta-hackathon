import {describe,it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import App from '../App';

const state={sources:[],tasks:[],drafts:[],checks:[],profile:{name:'Kevin',goal:'Learn',daily_enabled:false,timezone:'America/Los_Angeles'},connections:[],next_run:'2026-10-21T16:00:00Z',mode:'local',eligibility:'Prototype'};
afterEach(()=>vi.unstubAllGlobals());
function respond(data:unknown){return {ok:true,json:async()=>data};}

describe('Companion interface',()=>{
 it('shows a genuine empty state instead of fabricated work',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>respond(url.includes('bootstrap')?{token:'test'}:state)));
  render(<App/>);
  expect(await screen.findByRole('button',{name:/Explore a sample day/})).toBeVisible();
  expect(screen.queryByText('Practice 03')).not.toBeInTheDocument();
 });
 it('explains connection failure without rendering sample results',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>{throw new Error('Local service is unavailable');}));
  render(<App/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Local service is unavailable');
  expect(screen.queryByText('Worked draft — review needed.')).not.toBeInTheDocument();
 });
 it('opens a saved draft and exposes its source without executing source HTML',async()=>{
  const data={...state,sources:[{id:'s1',provider_id:'p1',connection_id:'imports',kind:'assignment',title:'My homework',body:'<script>alert(1)</script>',metadata:{},revision:1,fetched_at:'2026-10-20T16:00:00Z'}],drafts:[{id:'d1',kind:'homework',title:'My homework',markdown:'## Worked steps\nTest reasoning\n![private image](https://example.invalid/tracker)',status:'review_needed',provider:'source_outline',source_refs:[{id:'s1',revision:1}],generated_at:'2026-10-20T16:00:00Z'}]};
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>respond(url.includes('bootstrap')?{token:'test'}:data)));
  render(<App/>);
  await screen.findByText('Good morning, Kevin.');
  fireEvent.click(screen.getByRole('button',{name:/Open My homework/}));
  expect(await screen.findByRole('dialog')).toHaveTextContent('Worked steps');
  expect(screen.getByRole('link',{name:'Download'})).toHaveAttribute('href','/api/drafts/d1/download');
  expect(document.querySelector('img')).toBeNull();
  expect(screen.getByRole('dialog')).toHaveTextContent('Image omitted');
  fireEvent.click(screen.getByRole('button',{name:'Source: My homework'}));
  expect(screen.getByRole('dialog')).toHaveTextContent('<script>alert(1)</script>');
  expect(document.querySelector('script')).toBeNull();
 });
});
