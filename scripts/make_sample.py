"""Utilitário para extrair ou copiar uma amostra leve (NPZ) para desenvolvimento local.

Seleciona um arquivo .npz a partir de um ZIP de dados do GOES ou valida um .npz pequeno,
assegurando que o arquivo tenha menos de 50 MB para ser manipulado em modo de teste/sample.
"""

import argparse
from pathlib import Path
import sys
from typing import Tuple
import zipfile

# Inclusão da raiz do projeto para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings
from src.features.goes import MAX_MEMBER_BYTES, inspect_payload

# Limite estrito de 50 MB para amostras locais
MAX_SAMPLE_BYTES = 50_000_000


def read_one(source: Path, member: str = '') -> Tuple[bytes, str]:
    """Lê uma imagem .npz a partir de um arquivo .npz individual ou de um arquivo .zip."""
    source_path = Path(source)

    if source_path.suffix.lower() == '.npz':
        if source_path.stat().st_size > MAX_MEMBER_BYTES:
            raise ValueError(
                'NPZ acima de 32 MiB: não carregar; obter NPZ menor ou conversão seletiva da origem.'
            )
        return source_path.read_bytes(), source_path.name

    if source_path.suffix.lower() != '.zip':
        raise ValueError('Fonte deve ser um arquivo ZIP contendo NPZ ou um NPZ pequeno individual.')

    with zipfile.ZipFile(source_path) as archive:
        candidates = sorted(
            [
                info for info in archive.infolist()
                if info.filename.lower().endswith('.npz') and not info.is_dir()
            ],
            key=lambda info: info.filename,
        )
        if not candidates:
            raise ValueError('O arquivo ZIP não contém arquivos .npz.')

        selected = next(
            (info for info in candidates if info.filename == member), None
        ) if member else candidates[0]

        if selected is None or sum(info.filename == selected.filename for info in candidates) != 1:
            raise ValueError('Membro ausente ou com nome duplicado no ZIP.')

        if selected.file_size > MAX_MEMBER_BYTES:
            raise ValueError('Membro acima do limite de 32 MiB; escolha outro explicitamente.')

        return archive.read(selected), selected.filename


def make_sample(source: Path, output: Path, member: str = '') -> Tuple[str, int]:
    """Extrai ou valida a amostra e grava no caminho de saída especificado."""
    source_path = Path(source)
    output_path = Path(output)

    if source_path.resolve() == output_path.resolve() or output_path.exists():
        raise ValueError('Destino deve ser novo e diferente da fonte.')
    if output_path.suffix.lower() != '.npz':
        raise ValueError('Destino deve terminar em .npz.')

    payload, name = read_one(source_path, member)
    result = inspect_payload(payload, name)

    if result.status != 'reconstructed' or result.diagnostics.get('metadata_issues'):
        raise ValueError(f'Amostra não aceita: {result.status}; {result.diagnostics}')

    if len(payload) >= MAX_SAMPLE_BYTES:
        raise ValueError('A amostra precisa ter menos de 50 MB.')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('xb') as target_file:
        target_file.write(payload)

    return name, len(payload)


def main() -> None:
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=cfg['full'])
    parser.add_argument('--output', type=Path, default=cfg['sample'])
    parser.add_argument('--member', default=cfg['member'])
    args = parser.parse_args()

    name, size = make_sample(args.source, args.output, args.member)
    print(f'Amostra: {args.output}\nOrigem: {name}\nBytes: {size} (<50 MB). Não versionar.')


if __name__ == '__main__':
    main()
