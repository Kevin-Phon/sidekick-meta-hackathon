"""Bounded source-page rendering and safe structured teaching output."""
from io import BytesIO
from contextlib import closing
import base64
import threading
import pypdfium2 as pdfium

PDF_LOCK = threading.Lock()


def render_page(content, page):
    with PDF_LOCK, pdfium.PdfDocument(content) as document:
        if type(page) is not int or not 1 <= page <= len(document):
            raise ValueError('Choose an available PDF page.')
        with closing(document[page - 1]) as sheet:
            width,height=sheet.get_size()
            if width<=0 or height<=0:
                raise ValueError('This PDF page has invalid dimensions.')
            bitmap=sheet.render(scale=min(1400/max(width,height),3))
            try:
                image=bitmap.to_pil().convert('RGB')
                result=BytesIO();image.save(result,format='JPEG',quality=78)
                if len(result.getvalue())>400000:
                    image.thumbnail((1000,1000));result=BytesIO();image.save(result,format='JPEG',quality=65)
                image.close()
                if len(result.getvalue())>400000:
                    raise ValueError('Page is too detailed for this request. Use a smaller excerpt.')
                return result.getvalue()
            finally:
                bitmap.close()


def approve_pages(repo,sources,pages):
    if not isinstance(pages,dict) or any(k not in {s['id'] for s in sources} for k in pages):
        raise ValueError('Choose pages only from selected sources.')
    total=0;result=[]
    for source in sources:
        chosen=pages.get(source['id'],[])
        if not isinstance(chosen,list) or any(type(p) is not int for p in chosen) or len(set(chosen))!=len(chosen):
            raise ValueError('Choose distinct page numbers.')
        total+=len(chosen)
        if total>4:
            raise ValueError('Include at most four page images per run.')
        document=repo.document(source)
        if chosen and (not document or any(not 1<=p<=document['page_count'] for p in chosen)):
            raise ValueError('Original page images are unavailable. Re-add the original PDF.')
        images=[]
        for page in chosen:
            image=render_page(document['content'],page)
            images.append({'page':page,'data_url':'data:image/jpeg;base64,'+base64.b64encode(image).decode()})
        result.append({**source,'_vision_images':images})
    return result


def image_content(text,sources):
    images=[(s,image) for s in sources for image in s.get('_vision_images',[])]
    if not images:return text
    blocks=[{'type':'text','text':text}]
    for source,image in images:
        blocks.extend([{'type':'text','text':f'Approved source {source["id"]}, revision {source["revision"]}, PDF page {image["page"]}:'},
                       {'type':'image_url','image_url':{'url':image['data_url']}}])
    return blocks


STEP_SCHEMA={'type':'object','additionalProperties':False,'properties':{k:{'type':'string'} for k in ('title','explanation','example')},'required':['title','explanation','example']}
NODE_SCHEMA={'type':'object','additionalProperties':False,'properties':{k:{'type':'string'} for k in ('id','label','detail')},'required':['id','label','detail']}
EDGE_SCHEMA={'type':'object','additionalProperties':False,'properties':{k:{'type':'string'} for k in ('from','to','label')},'required':['from','to','label']}
VISUAL_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'title':{'type':'string'},'explanation':{'type':'string'},'source_id':{'type':'string'},'page':{'type':['integer','null']},
    'nodes':{'type':'array','items':NODE_SCHEMA},'edges':{'type':'array','items':EDGE_SCHEMA}},
    'required':['title','explanation','source_id','page','nodes','edges']}


def validate_teaching(result,sources):
    def text(value,limit,allow_empty=False):
        return isinstance(value,str) and len(value)<=limit and (allow_empty or bool(value.strip()))
    steps,visuals=result.get('steps',[]),result.get('visuals',[])
    if not isinstance(steps,list) or len(steps)>6 or any(not isinstance(s,dict) or not text(s.get('title'),100) or not text(s.get('explanation'),700) or not text(s.get('example'),400,True) for s in steps):
        raise ValueError('Invalid learning steps.')
    if not isinstance(visuals,list) or len(visuals)>2:raise ValueError('Invalid visual lesson.')
    allowed={s['id']:{i['page'] for i in s.get('_vision_images',[])} for s in sources}
    for visual in visuals:
        if not isinstance(visual,dict) or not text(visual.get('title'),100) or not text(visual.get('explanation'),500) or not isinstance(visual.get('source_id'),str) or visual['source_id'] not in allowed:
            raise ValueError('Invalid visual source.')
        page=visual.get('page')
        if page is not None and (type(page) is not int or page not in allowed[visual['source_id']]):raise ValueError('Unapproved diagram page.')
        nodes,edges=visual.get('nodes'),visual.get('edges')
        if not isinstance(nodes,list) or not 1<=len(nodes)<=6 or any(not isinstance(n,dict) or not text(n.get('id'),40) or not text(n.get('label'),60) or not text(n.get('detail'),300,True) for n in nodes):raise ValueError('Invalid diagram nodes.')
        ids={n['id'] for n in nodes}
        if len(ids)!=len(nodes) or not isinstance(edges,list) or len(edges)>10:raise ValueError('Invalid diagram connections.')
        if any(not isinstance(e,dict) or not isinstance(e.get('from'),str) or not isinstance(e.get('to'),str) or e['from'] not in ids or e['to'] not in ids or not text(e.get('label'),60,True) for e in edges):raise ValueError('Unknown diagram connection.')
    return steps,visuals


def teaching_markdown(draft):
    result=draft['markdown']
    for i,step in enumerate(draft.get('steps',[]),1):
        result+=f'\n\n## {i}. {step["title"]}\n{step["explanation"]}'
        if step['example']:result+='\n\nExample: '+step['example']
    for diagram in draft.get('visuals',[]):
        labels={n['id']:n['label'] for n in diagram['nodes']}
        result+='\n\n## Concept diagram: '+diagram['title']+'\n'+diagram['explanation']
        for edge in diagram['edges']:result+=f'\n- {labels[edge["from"]]} -> {labels[edge["to"]]} ({edge["label"]})'
    return result
