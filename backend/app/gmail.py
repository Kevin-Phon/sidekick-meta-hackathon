"""Session-only, read-only Gmail OAuth. No inbox reads or Meta calls on connection."""
import base64
import hashlib
import logging
import os
import re
import secrets
import threading
import time
from urllib.parse import urlencode

import httpx

SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
REDIRECT = 'http://127.0.0.1:8765/oauth/google/callback'
CALLBACK_PATH = '/oauth/google/callback'
FLOW_COOKIE = 'sidekick_google_flow'


class CallbackLogFilter(logging.Filter):
    def filter(self, record):
        return CALLBACK_PATH not in record.getMessage()


class GmailError(Exception):
    pass


class GmailConnection:
    transport = None

    def __init__(self):
        logger=logging.getLogger('uvicorn.access')
        if not any(isinstance(f,CallbackLogFilter) for f in logger.filters):logger.addFilter(CallbackLogFilter())
        self.lock = threading.RLock()
        self.client_id = ''
        self.client_secret = ''
        self.pending = {}
        self.account = None
        client_id, secret = os.environ.get('GOOGLE_CLIENT_ID',''), os.environ.get('GOOGLE_CLIENT_SECRET','')
        if client_id and secret:
            self.configure({'web':{'client_id':client_id,'client_secret':secret,'redirect_uris':[REDIRECT]}})

    def configure(self, payload):
        value = payload.get('web') if isinstance(payload,dict) else None
        if not isinstance(value,dict) or not isinstance(value.get('client_id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{3,200}\.apps\.googleusercontent\.com',value['client_id']):
            raise ValueError('Choose the downloaded Web application OAuth client JSON from Google Cloud.')
        secret = value.get('client_secret')
        if not isinstance(secret,str) or not 5 <= len(secret) <= 1000 or any(ord(c)<33 or ord(c)>126 for c in secret) or not isinstance(value.get('redirect_uris'),list) or REDIRECT not in value['redirect_uris']:
            raise ValueError('The Google client must have a client secret and the exact Sidekick redirect URI.')
        with self.lock:
            if self.account and self.account['expires_at']<=time.time():self.account=None
            if self.account:
                raise ValueError('Disconnect the existing Gmail session before changing its developer setup.')
            self.client_id,self.client_secret = value['client_id'],secret
            self.pending.clear()

    def status(self, workspace):
        with self.lock:
            account = self.account
            connected = bool(account and account['workspace']==workspace and account['expires_at']>time.time())
            return {'configured':bool(self.client_id),'connected':connected,'email':account['email'] if connected else '',
                    'scope':'read-only','redirect_uri':REDIRECT,'session_only':True,
                    'detail':'Connected for this session. No messages imported.' if connected else 'Sign in to connect Gmail for this session.' if self.client_id else 'Google developer setup is required once before sign-in.'}

    def start(self, workspace):
        with self.lock:
            if not self.client_id:
                raise GmailError('Set up the Google OAuth client before connecting Gmail.')
            if self.account and self.account['expires_at']<=time.time():self.account=None
            if self.account:
                # Prevent silently replacing another workspace/account connection.
                raise GmailError('Disconnect the existing Gmail session before signing in again.')
            self.pending = {s:v for s,v in self.pending.items() if v['expires']>time.time()}
            if len(self.pending)>=10:
                raise GmailError('Too many pending sign-ins. Wait ten minutes before trying again.')
            state, cookie, verifier = secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(48)
            self.pending[state] = {'cookie':cookie,'verifier':verifier,'workspace':workspace,'expires':time.time()+600}
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':self.client_id,'redirect_uri':REDIRECT,'response_type':'code','scope':SCOPE,
                'state':state,'code_challenge':challenge,'code_challenge_method':'S256','access_type':'online','prompt':'select_account consent'}),cookie

    def _json(self, method, url, **kwargs):
        try:
            with httpx.Client(transport=self.transport,timeout=httpx.Timeout(20,connect=5),follow_redirects=False) as client:
                with client.stream(method,url,**kwargs) as response:
                    if response.status_code!=200:raise GmailError('Google could not complete the connection. Check setup and try signing in again.')
                    data=bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data)>256000:raise GmailError('Google returned an oversized response.')
                    import json
                    value=json.loads(data)
                    if not isinstance(value,dict):raise ValueError()
                    return value
        except GmailError:raise
        except Exception:
            raise GmailError('Google could not complete the connection. No automatic retry was made.') from None

    def finish(self, state, cookie, code, error, workspace):
        with self.lock:
            flow=self.pending.get(state)
            if not flow or not cookie or not secrets.compare_digest(flow['cookie'],cookie) or flow['expires']<=time.time():
                raise ValueError('This Google sign-in expired or does not belong to this browser. Start again from Sidekick.')
            self.pending.pop(state)
            if flow['workspace']!=workspace:
                raise ValueError('Your workspace changed during sign-in. Start again in the intended workspace.')
            if self.account and self.account['expires_at']>time.time():
                raise ValueError('Gmail is already connected. Disconnect before switching accounts.')
            if error:return False
            if not isinstance(code,str) or not code or len(code)>4000:
                raise ValueError('Google did not return a valid authorization code.')
            token=self._json('POST','https://oauth2.googleapis.com/token',data={'client_id':self.client_id,'client_secret':self.client_secret,
                'code':code,'code_verifier':flow['verifier'],'redirect_uri':REDIRECT,'grant_type':'authorization_code'})
            access,expiry=token.get('access_token'),token.get('expires_in')
            if not isinstance(access,str) or not access or len(access)>10000 or type(expiry) not in (int,float) or not 0<expiry<=86400 or set(str(token.get('scope','')).split())!={SCOPE}:
                raise GmailError('Google did not grant the required read-only Gmail permission.')
            profile=self._json('GET','https://gmail.googleapis.com/gmail/v1/users/me/profile',headers={'Authorization':'Bearer '+access})
            email=profile.get('emailAddress')
            if not isinstance(email,str) or not email or len(email)>320:raise GmailError('Google did not verify a Gmail account.')
            self.pending.clear()
            self.account={'token':access,'email':email,'workspace':workspace,'expires_at':time.time()+expiry-30}
            return True

    def disconnect(self):
        with self.lock:
            account,self.account=self.account,None
            self.pending.clear()
        revoked=False
        if account:
            try:
                with httpx.Client(transport=self.transport,timeout=10,follow_redirects=False) as client:
                    response=client.post('https://oauth2.googleapis.com/revoke',data={'token':account['token']})
                    revoked=response.status_code==200
            except Exception:pass
        return {'connected':False,'revoked':revoked}
