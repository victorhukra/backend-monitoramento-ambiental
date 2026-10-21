"""Bloqueia no índice Git arquivos que não sejam código/documentação pequenos."""
from pathlib import PurePosixPath
import subprocess


def allowed(name):
    path=PurePosixPath(name)
    if path.parts[0].lower()=='data' or any(p.lower() in {'work','.venv','venv','env','node_modules','__pycache__','build','dist','.aws','.ssh','logs','.idea','.vscode'} for p in path.parts):
        return False
    base=path.name.lower()
    if base.startswith(('credentials','secrets')) or (base.startswith('.env') and name!='.env.example'):
        return False
    return path.suffix in {'.py','.md'} or name in {'requirements.txt','.gitignore','.gitattributes','.env.example','.githooks/pre-commit'}


if __name__=='__main__':
    entries=subprocess.check_output(['git','ls-files','--stage','-z']).decode('utf-8').split('\0')
    failures=[]
    for entry in filter(None,entries):
        meta,name=entry.split('\t',1)
        mode,oid,stage=meta.split()
        if mode not in {'100644','100755'} or stage!='0' or not allowed(name):
            failures.append(name+': tipo/caminho não permitido'); continue
        size=int(subprocess.check_output(['git','cat-file','-s',oid]))
        if size>1_000_000:
            failures.append(name+': acima de 1 MB')
    if failures:
        raise SystemExit('COMMIT BLOQUEADO:\n'+'\n'.join(failures))
    print('Índice Git aprovado: código/documentação permitidos, até 1 MB por arquivo.')
