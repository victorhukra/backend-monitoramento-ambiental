"""Inventário limitado de proveniência; lê metadados de três NPZ, nunca pixels."""
import io
import json
from pathlib import Path
import sys
import zipfile
from collections import Counter
import numpy as np
from audit import fingerprint, scalar

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('C:/Users/CANAL/Downloads/Backend_UTFPR')
ZIP = Path('C:/Users/CANAL/Downloads/dataset_goes.zip')
OUTPUT = ROOT/'reports/temporal'
DETAILS = ROOT/'reports/eda/goes_sample_details.json'
before = [fingerprint(p) for p in (SOURCE/'dataset_weather.csv',SOURCE/'README.md',ZIP,DETAILS)]
inventory=[]
for root in (ROOT,SOURCE):
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or OUTPUT in path.parents:
            continue
        inventory.append({'root':str(root),'relative_path':str(path.relative_to(root)), 'bytes':path.stat().st_size})
details=json.loads(DETAILS.read_text(encoding='utf-8'))
representatives={}
for entry in sorted(details,key=lambda x:x['image_link']):
    meta=entry.get('metadata',{})
    key=(meta.get('satellite'),meta.get('grid_signature'))
    if all(key) and entry.get('valid_pixels',0)>0:
        representatives.setdefault(key,entry)
if len(representatives)>3:
    raise ValueError('Mais de três combinações: revisar escopo antes de ler')
samples=[]
with zipfile.ZipFile(ZIP) as archive:
    members=[x for x in archive.infolist() if not x.is_dir()]
    extensions=Counter(Path(x.filename).suffix for x in members)
    for key,entry in sorted(representatives.items()):
        info=archive.getinfo(entry['image_link'])
        if info.file_size>32*1024**2: raise ValueError('Membro excede limite')
        payload=archive.read(info)
        with np.load(io.BytesIO(payload),allow_pickle=False) as npz:
            meta={k:scalar(npz,k) for k in npz.files if k!='cmi_c13_raw'}
            if any(isinstance(v,(list,dict)) for v in meta.values()): raise ValueError('Metadado não escalar inesperado')
            sample={'image_link':entry['image_link'],'keys':list(npz.files),'metadata':meta,
                'shape_from_previous_eda':entry.get('shape'), 'pixels_read_this_stage':False}
        satellite=meta['satellite'].replace('GOES-','')
        sample['candidate_origin_url']='https://noaa-goes'+satellite+'.s3.amazonaws.com/'+meta['source_key']
        sample['remote_exists_verified']=False
        samples.append(sample)
        del payload
after=[fingerprint(p) for p in (SOURCE/'dataset_weather.csv',SOURCE/'README.md',ZIP,DETAILS)]
if before!=after: raise RuntimeError('Fontes mudaram')
result={'date':'2026-10-15','sources_before':before,'sources_after':after,'sources_unchanged':True,
    'search_roots':[str(ROOT),str(SOURCE)],'excluded':['__pycache__','reports/temporal (saídas desta etapa)', 'work/eda-deps (bibliotecas instaladas)'],
    'inventory':inventory,'zip_members':len(members),'zip_extensions':dict(extensions),
    'selection':'Primeiro nome com pixels válidos na EDA por par satellite/grid_signature; até três pares',
    'samples':samples,'python':sys.version,'numpy':np.__version__}
OUTPUT.mkdir(parents=True,exist_ok=True)
(OUTPUT/'evidence_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'zip_extensions':dict(extensions),'samples':samples},ensure_ascii=False,indent=2))
