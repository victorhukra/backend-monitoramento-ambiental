"""Smoke test de uma imagem na fonte selecionada (sample ou full).

Valida integridade estrutural e metadados de uma imagem sem processar
o acervo completo.
"""

import io
import json
from pathlib import Path
import sys
import numpy as np

# Inclusão da raiz do projeto para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings
from scripts.make_sample import read_one
from src.data.audit import scalar
from src.features.goes import inspect_payload


def main() -> None:
    cfg = settings()
    is_sample_mode = cfg['mode'] == 'sample'
    source_path = cfg['sample'] if is_sample_mode else cfg['full']
    member_name = '' if is_sample_mode else cfg['member']

    payload, file_name = read_one(source_path, member_name)

    # sample.npz é um alias local: a identidade original está preservada no payload
    if is_sample_mode:
        with np.load(io.BytesIO(payload), allow_pickle=False) as data:
            file_name = str(scalar(data, 'source_filename')).removesuffix('.nc') + '.npz'

    result = inspect_payload(payload, file_name)

    output = {
        'mode': cfg['mode'],
        'status': result.status,
        'shape': result.diagnostics.get('shape'),
        'valid_pixels': result.diagnostics.get('valid_pixels'),
        'metadata_issues': result.diagnostics.get('metadata_issues'),
        'spatial_status': 'not_validated',
    }
    print(json.dumps(output, indent=2))

    if result.status != 'reconstructed' or result.diagnostics.get('metadata_issues'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
