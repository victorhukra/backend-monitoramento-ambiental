"""Smoke test de uma imagem na fonte selecionada; não processa o acervo inteiro."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import settings
from scripts.make_sample import read_one
from src.features.goes import inspect_payload

if __name__ == '__main__':
    cfg=settings()
    source=cfg['sample'] if cfg['mode']=='sample' else cfg['full']
    payload,name=read_one(source,cfg['member'] if cfg['mode']=='full' else '')
    # sample.npz é um alias local: a identidade original está preservada no payload.
    if cfg['mode']=='sample':
        import io
        import numpy as np
        with np.load(io.BytesIO(payload),allow_pickle=False) as data:
            from src.data.audit import scalar
            name=str(scalar(data,'source_filename')).removesuffix('.nc')+'.npz'
    result=inspect_payload(payload,name)
    print(json.dumps(dict(mode=cfg['mode'],status=result.status,shape=result.diagnostics.get('shape'),
                         valid_pixels=result.diagnostics.get('valid_pixels'),
                         metadata_issues=result.diagnostics.get('metadata_issues'),spatial_status='not_validated'),indent=2))
    if result.status!='reconstructed' or result.diagnostics['metadata_issues']:
        raise SystemExit(1)
