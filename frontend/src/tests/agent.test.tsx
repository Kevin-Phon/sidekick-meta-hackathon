import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {vi,test,expect} from 'vitest';
import AgentPanel from '../components/AgentPanel';
import {TodayView} from '../components/Views';
import {request} from '../api';
vi.mock('../api',()=>({request:vi.fn()}));
const source={id:'s1',content_hash:'h',revision:1,provider_id:'one',connection_id:'agent-demo',kind:'lecture',title:'Sample sets',body:'Intersection means both.',timezone_known:false,metadata:{demo:true},fetched_at:'2026-11-03T12:00:00Z'};
test('agent requires preview consent and shows no-change result',async()=>{
 vi.mocked(request).mockResolvedValue({status:'unchanged',message:'No changes. No Meta calls made.'});
 render(<AgentPanel sources={[source]} tasks={[]} drafts={[]} runs={[]} configured={true} changed={async()=>{}} open={()=>{}}/>);
 const run=screen.getByRole('button',{name:'Run Sidekick'});
 expect(run).toBeDisabled();
 expect(screen.getByText('Intersection means both.')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('checkbox',{name:/Send these/}));
 fireEvent.click(run);
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('No changes'));
 expect(request).toHaveBeenCalledWith('agent/run','POST',expect.objectContaining({source_ids:['s1'],source_hashes:{s1:'h'},consent:true}));
});
test('historical plan clearly marked stale and prepared outputs open',()=>{
 const draft={id:'d1',kind:'study_guide',title:'Prepared guide',markdown:'Draft',status:'review_needed',source_refs:[],provider:'meta',model:'muse-spark-1.3',generated_at:''};
 const open=vi.fn();
 render(<TodayView state={{sources:[source],tasks:[],drafts:[draft],checks:[],profile:{name:'Kevin',goal:'',daily_enabled:false,timezone:'America/Los_Angeles'},connections:[],next_run:'',mode:'local',eligibility:'',agent_runs:[{id:'r1',status:'completed',stale:true,finished_at:'',source_refs:[],call_count:2,draft_ids:['d1'],changes:[],plan:{summary:'Prepare school work',priorities:[{source_id:'s1',reason:'Practice before the meeting'}],actions:[]}}]}} sourceOpen={()=>{}} draftOpen={open} toggle={()=>{}} setView={()=>{}} prepare={()=>{}} add={()=>{}} connect={()=>{}}/>);
 expect(screen.getByText(/Inputs changed/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Open Prepared guide Study guide'}));
 expect(open).toHaveBeenCalledWith(draft);
});
