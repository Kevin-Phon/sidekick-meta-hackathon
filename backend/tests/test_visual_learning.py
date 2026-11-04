from io import BytesIO
import json
import httpx
import pytest
from pypdf import PdfWriter
from app.model import MetaClient,ModelError


def pdf_bytes():
    w=PdfWriter();w.add_blank_page(width=500,height=300);w.add_blank_page(width=500,height=300)
    out=BytesIO();w.write(out);return out.getvalue()


def test_pdf_pages_retained_privately_and_workspace_scoped(tmp_path):
    from test_api import connected
    c=connected(tmp_path)
    assert c.post('/api/import/file?filename=diagram.pdf&kind=lecture',content=pdf_bytes()).status_code==200
    source=c.get('/api/state').json()['sources'][0]
    assert source['visual_document']['page_count']==2
    image=c.get('/api/sources/'+source['id']+'/pages/1')
    assert image.status_code==200 and image.headers['content-type'].startswith('image/jpeg')
    assert image.content.startswith(b'\xff\xd8')
    c.post('/api/workspaces',json={'name':'Other workspace'})
    assert c.get('/api/sources/'+source['id']+'/pages/1').status_code==404


def test_same_text_different_pdf_visuals_keep_distinct_identity(tmp_path):
    from test_api import connected
    c=connected(tmp_path)
    a=pdf_bytes();w=PdfWriter();w.add_blank_page(width=600,height=300);out=BytesIO();w.write(out)
    for data in [a,out.getvalue()]:
        assert c.post('/api/import/file?filename=diagram.pdf&kind=lecture',content=data).status_code==200
    assert len(c.get('/api/state').json()['sources'])==2


def visual_result():
    return {'kind':'study_guide','markdown':'A short overview.','source_refs':[{'id':'s1','revision':1}],'missing_information':[],
      'steps':[{'title':'Start here','explanation':'A state records where the machine is.','example':'Read one input and follow its arrow.'}],
      'visuals':[{'title':'A small state transition','explanation':'Follow the labeled arrow.','source_id':'s1','page':1,
                  'nodes':[{'id':'a','label':'Start','detail':'Before input'},{'id':'b','label':'Next','detail':'After input'}],
                  'edges':[{'from':'a','to':'b','label':'input'}]}]}


def test_approved_images_and_learning_structure_reach_meta():
    source={'id':'s1','revision':1,'kind':'lecture','title':'States','body':'A state changes on input.','metadata':{},
            '_vision_images':[{'page':1,'data_url':'data:image/jpeg;base64,/9j/2Q=='}]}
    def serve(request):
        payload=json.loads(request.content);blocks=payload['messages'][1]['content']
        assert isinstance(blocks,list) and any(b['type']=='image_url' for b in blocks)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(visual_result())}}]})
    result=MetaClient('test',transport=httpx.MockTransport(serve)).generate([source])
    assert result['steps'][0]['title']=='Start here'
    assert result['visuals'][0]['nodes'][1]['label']=='Next'


@pytest.mark.parametrize('mutation',['unknown_edge','unknown_source','unapproved_page'])
def test_untrusted_diagrams_cannot_reference_unknown_inputs(mutation):
    source={'id':'s1','revision':1,'kind':'lecture','title':'States','body':'Notes','metadata':{}}
    data=visual_result()
    if mutation=='unknown_edge':data['visuals'][0]['edges'][0]['to']='missing'
    elif mutation=='unknown_source':data['visuals'][0]['source_id']='unselected'
    with pytest.raises(ModelError):
        MetaClient('test',transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(data)}}]}))).generate([source])


def test_page_consent_is_bounded_and_does_not_accept_archived_assets(tmp_path):
    from test_api import connected
    from app.visual_learning import approve_pages
    from app.repository import Repository
    c=connected(tmp_path);c.post('/api/import/file?filename=diagram.pdf',content=pdf_bytes())
    source=c.get('/api/state').json()['sources'][0];repo=Repository(tmp_path/'sidekick.db')
    for pages in ({source['id']:[True]}, {source['id']:[3]}, {source['id']:[1,1]}, {'other':[1]}):
        with pytest.raises(ValueError):approve_pages(repo,[source],pages)
    assert approve_pages(repo,[source],{})[0]['_vision_images']==[]


def test_recovering_original_pdf_preserves_identity_and_changes_approval_hash(tmp_path):
    from app.repository import Repository
    repo=Repository(tmp_path/'test.db');repo.import_items([{'title':'Older import','body':'Text only','kind':'lecture'}])
    source=repo.snapshot()['sources'][0]
    repo.attach_document(source['id'],source['content_hash'],pdf_bytes(),2)
    updated=repo.snapshot()['sources'][0]
    assert updated['id']==source['id'] and updated['revision']==2
    assert updated['content_hash']!=source['content_hash']
    assert updated['visual_document']['page_count']==2
    with pytest.raises(ValueError):repo.attach_document(source['id'],source['content_hash'],pdf_bytes(),2)


def test_page_preview_rejects_a_stale_version(tmp_path):
    from test_api import connected
    c=connected(tmp_path);c.post('/api/import/file?filename=diagram.pdf',content=pdf_bytes())
    source=c.get('/api/state').json()['sources'][0]
    assert c.get('/api/sources/'+source['id']+'/pages/1?version=old-preview').status_code==409
