"""Hook de pré-commit: bloqueia no índice Git arquivos que não sejam código/documentação leves.

Garante que bases de dados (data/), ambientes virtuais (.venv/), arquivos grandes
(> 1 MB) ou arquivos de credenciais/segredos não sejam comitados acidentalmente.
"""

from pathlib import PurePosixPath
import subprocess

DISALLOWED_DIRS = {
    'work',
    '.venv',
    'venv',
    'env',
    'node_modules',
    '__pycache__',
    'build',
    'dist',
    '.aws',
    '.ssh',
    'logs',
    '.idea',
    '.vscode',
}

ALLOWED_EXPLICIT_FILES = {
    'requirements.txt',
    '.gitignore',
    '.gitattributes',
    '.env.example',
    '.githooks/pre-commit',
}


def allowed(filename: str) -> bool:
    """Verifica se o arquivo é permitido no repositório com base em extensão e pasta."""
    path = PurePosixPath(filename)

    # Impede arquivos na pasta data/ ou em diretórios de ambiente/build
    if path.parts[0].lower() == 'data':
        return False
    if any(part.lower() in DISALLOWED_DIRS for part in path.parts):
        return False

    base_name = path.name.lower()
    if base_name.startswith(('credentials', 'secrets')):
        return False
    if base_name.startswith('.env') and filename != '.env.example':
        return False

    return path.suffix in {'.py', '.md'} or filename in ALLOWED_EXPLICIT_FILES


is_allowed_path = allowed


def main() -> None:
    git_output = subprocess.check_output(['git', 'ls-files', '--stage', '-z']).decode('utf-8')
    staged_entries = git_output.split('\0')
    validation_failures = []

    for entry in filter(None, staged_entries):
        metadata, filename = entry.split('\t', 1)
        mode, object_id, stage = metadata.split()

        if mode not in {'100644', '100755'} or stage != '0' or not is_allowed_path(filename):
            validation_failures.append(f'{filename}: tipo ou caminho não permitido')
            continue

        size_bytes = int(subprocess.check_output(['git', 'cat-file', '-s', object_id]))
        if size_bytes > 1_000_000:
            validation_failures.append(f'{filename}: tamanho excede o limite de 1 MB')

    if validation_failures:
        raise SystemExit('COMMIT BLOQUEADO:\n' + '\n'.join(validation_failures))

    print('Índice Git aprovado: código e documentação permitidos (todos abaixo de 1 MB).')


if __name__ == '__main__':
    main()
