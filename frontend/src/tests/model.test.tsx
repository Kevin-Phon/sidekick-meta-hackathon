import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ModelPanel from '../components/ModelPanel';
const source={id:'s1',content_hash:'hash1',provider_id:'p1',connection_id:'demo',kind:'lecture',title:'Sample lecture',body:'Intersection means both.',metadata:{},revision:1,fetched_at:'today',timezone_known:false};
afterEach(()=>vi.unstubAllGlobals());
it('requires source sharing approval and sends only the selected source id',async()=>{
 const fetcher=vi.fn(async()=>({ok:true,json:async()=>({draft_id:'d1'})}));vi.stubGlobal('fetch',fetcher);
 render(<ModelPanel sources={[source]} model={{configured:true,verified:false,model:'muse-spark-1.3',mode:'Standard',last_error:''}} changed={async()=>{}}/>);
 const generate=screen.getByRole('button',{name:'Generate with Muse Spark'});
 expect(generate).toBeDisabled();
 expect(screen.getByText('Intersection means both.')).toBeVisible();
 fireEvent.click(screen.getByRole('checkbox'));
 fireEvent.click(generate);
 await waitFor(()=>expect(fetcher).toHaveBeenCalled());
 const [url,options]=fetcher.mock.calls[0] as unknown as [string,RequestInit];
 expect(url).toBe('/api/model/generate');
 expect(JSON.parse(options.body as string)).toEqual({source_ids:['s1'],source_revisions:{s1:1},source_hashes:{s1:'hash1'},consent:true});
});
it('clears key input after memory-only setup and never uses localStorage',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({configured:true})})));
 render(<ModelPanel sources={[source]} changed={async()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Meta API key'),{target:{value:'fake-secret'}});
 fireEvent.click(screen.getByRole('button',{name:'Use key for this session'}));
 await waitFor(()=>expect(screen.getByLabelText('Meta API key')).toHaveValue(''));
 expect(localStorage.length).toBe(0);
});
