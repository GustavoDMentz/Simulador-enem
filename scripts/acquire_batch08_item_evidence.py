"""Read only official item metadata; never read participant CSV entries."""
import urllib.request,io,zipfile,json,csv,hashlib,tempfile,concurrent.futures,ssl
SSL=ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
def open_url(req,timeout):
 try:return urllib.request.urlopen(req,timeout=timeout,context=SSL)
 except Exception as e:
  if req.full_url.startswith("https://download.inep.gov.br/"):
   return open_url(urllib.request.Request(req.full_url.replace("https:","http:"),headers=dict(req.header_items())),timeout=timeout)
  raise
from pathlib import Path
class RangeReader(io.RawIOBase):
 def __init__(self,url):
  self.url=url;self.pos=0;self.cache={}
  r=open_url(urllib.request.Request(url,headers={'Range':'bytes=-131072'}),timeout=60)
  if r.status!=206:raise RuntimeError('Range unavailable; refusing to download participant data')
  h=r.headers['Content-Range'];self.size=int(h.split('/')[-1]);start=int(h.split()[1].split('-')[0]);self.cache[start]=r.read()
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,n,whence=0):self.pos=n if whence==0 else self.pos+n if whence==1 else self.size+n;return self.pos
 def read(self,n=-1):
  n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
  if n<=0:return b''
  for start,data in self.cache.items():
   if start<=self.pos and self.pos+n<=start+len(data):a=self.pos-start;self.pos+=n;return data[a:a+n]
  start=self.pos;r=open_url(urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{start+n-1}'}),timeout=60)
  if r.status!=206 or not r.headers['Content-Range'].startswith(f'bytes {start}-'):raise RuntimeError('Range response mismatch')
  data=r.read();assert len(data)==n;self.cache[start]=data;self.pos+=n;return data
qs=list(map(json.loads,Path('data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines()))
published={q['id_unico_sistema'] for q in map(json.loads,Path('data/blue-published/questions.jsonl').read_text().splitlines())}
qs=[q for q in qs if q['id_unico_sistema'] not in published]
def fetch(year):
 url=f'https://download.inep.gov.br/microdados/microdados_enem_{year}.zip';wanted={str(q['co_item']) for q in qs if q['ano']==year}
 try:
  with zipfile.ZipFile(RangeReader(url)) as z:
   names=[n for n in z.namelist() if 'ITENS_PROVA' in n.upper() and n.lower().endswith('.csv')];assert len(names)==1,names
   raw=z.read(names[0]);reader=csv.DictReader(io.StringIO(raw.decode('latin1')),delimiter=';')
   rows=[{k:v for k,v in row.items() if k.startswith(('CO_','TP_','TX_','SG_','IN_'))} for row in reader if row.get('CO_ITEM') in wanted]
   return dict(year=year,url=url,entry=names[0],sha256=hashlib.sha256(raw).hexdigest(),rows=rows)
 except Exception as e:return dict(year=year,url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(fetch,sorted({q['ano'] for q in qs})):print('ITEM_METADATA_JSON '+json.dumps(result,ensure_ascii=False),flush=True)
