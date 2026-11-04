import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {it,expect,vi,afterEach} from 'vitest';
import App from '../App';
import * as navigation from '../navigation';
vi.mock('../navigation',()=>({openGoogleAuthorization:vi.fn()}));
afterEach(()=>vi.unstubAllGlobals());
it('starts Google authorization directly from Connect Gmail when developer setup exists',async()=>{
 const authorization_url='https://accounts.google.com/o/oauth2/v2/auth?client_id=test&state=once';
 const data={sources:[],tasks:[],drafts:[],checks:[],connections:[],profile:{name:'',goal:'',daily_enabled:false,timezone:'America/Los_Angeles'},gmail:{configured:true,connected:false,email:'',session_only:true,scope:'read-only'}};
 const requests:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{requests.push(url);return {ok:true,json:async()=>url.includes('bootstrap')?{token:'test'}:url.includes('gmail/start')?{authorization_url}:data};}));
 render(<App/>);await screen.findByText('Your day starts with your material.');
 fireEvent.click(screen.getByRole('button',{name:'Mail'}));
 fireEvent.click(screen.getByRole('button',{name:'Connect Gmail'}));
 await waitFor(()=>expect(navigation.openGoogleAuthorization).toHaveBeenCalledWith(authorization_url));
 expect(requests.filter(url=>url==='/api/gmail/start')).toHaveLength(1);
 expect(screen.queryByText('Google authorization setup is not configured')).toBeNull();
});
