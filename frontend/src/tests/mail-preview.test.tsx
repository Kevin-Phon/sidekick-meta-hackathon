import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import {MailView} from '../components/Views';
import type {State} from '../types';
it('shows recent mail with provenance and lets the user request a recommendation for one message',()=>{
 const message={id:'m',provider_id:'one',connection_id:'gmail:mailbox',kind:'mail',title:'Team meeting',body:'Please review the agenda.',metadata:{provider:'gmail',sender:'Alex <alex@example.test>',gmail_important:true,received_at:'2026-11-04T15:00:00Z'},revision:1,content_hash:'h',fetched_at:'2026-11-04T16:00:00Z',timezone_known:false};
 const state:State={sources:[message],tasks:[],drafts:[],checks:[],profile:{name:'',goal:'',daily_enabled:false,timezone:'America/Los_Angeles'},connections:[],next_run:'',mode:'local',eligibility:'',gmail:{configured:true,connected:true,email:'reader@example.test',scope:'read-only',session_only:true,redirect_uri:'',detail:''}};
 const refreshMail=vi.fn(),explain=vi.fn();
 render(<MailView state={state} sourceOpen={()=>{}} draftOpen={()=>{}} toggle={()=>{}} setView={()=>{}} prepare={()=>{}} add={()=>{}} connect={()=>{}} refreshMail={refreshMail} explain={explain}/>);
 expect(screen.getByText('Alex <alex@example.test>')).toBeVisible();
 expect(screen.getByText('Gmail marked important')).toBeVisible();
 expect(screen.queryByText(/No messages imported/)).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Load 5 recent emails'}));expect(refreshMail).toHaveBeenCalledOnce();
 fireEvent.click(screen.getByRole('button',{name:'Summary & next steps'}));expect(explain).toHaveBeenCalledWith(message);
});
