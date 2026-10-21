"""Seleciona um NPZ inteiro do ZIP ou copia NPZ pequeno, sem inferir recorte geográfico."""
import argparse
from pathlib import Path
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings
from src.features.goes import inspect_payload, MAX_MEMBER_BYTES

LIMIT = 50_000_000  # bytes; limite estrito solicitado


def read_one(source, member=''):
    source = Path(source)
    if source.suffix.lower() == '.npz':
        if source.stat().st_size > MAX_MEMBER_BYTES:
            raise ValueError('NPZ acima de 32 MiB: não carregar; obter NPZ menor ou conversão seletiva da origem')
        return source.read_bytes(), source.name
    if source.suffix.lower() != '.zip':
        raise ValueError('Fonte deve ser ZIP de NPZ ou um NPZ pequeno')
    with zipfile.ZipFile(source) as archive:
        candidates = sorted((i for i in archive.infolist() if i.filename.lower().endswith('.npz') and not i.is_dir()), key=lambda i:i.filename)
        if not candidates:
            raise ValueError('ZIP sem NPZ')
        selected = next((i for i in candidates if i.filename == member), None) if member else candidates[0]
        if selected is None or sum(i.filename == selected.filename for i in candidates) != 1:
            raise ValueError('Membro ausente ou nome duplicado')
        if selected.file_size > MAX_MEMBER_BYTES:
            raise ValueError('Membro acima do limite de 32 MiB; escolha outro explicitamente')
        return archive.read(selected), selected.filename


def make_sample(source, output, member=''):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError('Destino deve ser novo e diferente da fonte')
    if output.suffix.lower() != '.npz':
        raise ValueError('Destino deve terminar em .npz')
    payload, name = read_one(source, member)
    result = inspect_payload(payload, name)
    if result.status != 'reconstructed' or result.diagnostics['metadata_issues']:
        raise ValueError(f'Amostra não aceita: {result.status}; {result.diagnostics}')
    if len(payload) >= LIMIT:
        raise ValueError('Amostra precisa ter menos de 50 MB')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as target:
        target.write(payload)
    return name, len(payload)


if __name__ == '__main__':
    cfg=settings()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=cfg['full'])
    parser.add_argument('--output',type=Path,default=cfg['sample'])
    parser.add_argument('--member',default=cfg['member'])
    args=parser.parse_args()
    name,size=make_sample(args.source,args.output,args.member)
    print(f'Amostra: {args.output}\nOrigem: {name}\nBytes: {size} (<50 MB). Não versionar.')
