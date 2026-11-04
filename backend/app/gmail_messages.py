"""Bounded, inert text extraction for Gmail message snapshots."""
import base64
import re
from datetime import datetime,timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote

class TextOnly(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.hidden=0;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','head'}:self.hidden+=1
        if not self.hidden and tag in {'p','div','br','li','tr'}:self.text.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style','head'}:self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.text.append(data)


def snapshot(message,email):
    payload=message.get('payload',{})
    if not isinstance(payload,dict):raise ValueError('Invalid message.')
    headers={}
    for header in payload.get('headers',[])[:100]:
        if isinstance(header,dict) and isinstance(header.get('name'),str) and isinstance(header.get('value'),str):
            headers[header['name'].lower()]=header['value'][:1000]
    plain,html=[],[];visited=0;truncated=False
    def walk(part,depth=0):
        nonlocal visited,truncated
        if not isinstance(part,dict) or depth>8 or visited>=40:truncated=True;return
        visited+=1
        part_headers=part.get('headers',[])
        disposition=next((h.get('value','') for h in part_headers if isinstance(h,dict) and str(h.get('name','')).lower()=='content-disposition'),'') if isinstance(part_headers,list) else ''
        if part.get('filename') or str(disposition).split(';')[0].strip().lower()=='attachment' or part.get('mimeType')=='message/rfc822':return
        mime=part.get('mimeType','')
        body=part.get('body') or {}
        data=body.get('data') if isinstance(body,dict) else None
        if mime in {'text/plain','text/html'} and isinstance(data,str):
            if len(data)>60000:truncated=True
            data=data[:60000]
            text=base64.urlsafe_b64decode(data+'='*((-len(data))%4)).decode('utf-8',errors='replace')
            if mime=='text/plain':plain.append(text)
            else:
                parser=TextOnly();parser.feed(text);html.append(''.join(parser.text))
        parts=part.get('parts',[])
        if isinstance(parts,list):
            for child in parts[:40]:walk(child,depth+1)
    walk(payload)
    text='\n'.join(plain or html).strip()
    text=re.sub(r'\n[ \t]*\n[ \t]*\n+','\n\n',text)
    if len(text)>10000:truncated=True
    text=text[:10000] or 'No inline message text available. Attachments and images were not imported; open the original in Gmail.'
    sender=headers.get('from','').strip()[:500] or 'Unknown sender';subject=headers.get('subject','').strip()[:300] or '(No subject)'
    try:
        stamp=int(message.get('internalDate',''))
        received=datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat() if stamp>0 else ''
    except (ValueError,TypeError,OverflowError,OSError):received=''
    message_id=message['id']
    labels=message.get('labelIds',[])
    return {'provider_id':message_id,'kind':'mail','title':subject,'body':f'From: {sender}\nDate: {headers.get("date",received)}\nSubject: {subject}\n\n{text}'+('\n\n[Excerpt truncated. Open the original message for complete context.]' if truncated else ''),
            'url':'https://mail.google.com/mail/?authuser='+quote(email,safe='')+'#all/'+message_id,
            'metadata':{'provider':'gmail','sender':sender,'received_at':received,'preview':unescape(str(message.get('snippet','')))[:500],
                        'gmail_important':'IMPORTANT' in labels,'body_truncated':truncated,'attachments_imported':False}}
