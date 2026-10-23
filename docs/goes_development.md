# Utilitários GOES — uso opcional

O MVP atual usa somente o CSV meteorológico. Estes utilitários são apoio à investigação futura de imagens e não são necessários para preparar a tabela meteorológica. Configure os caminhos GOES em `.env`, conforme `.env.example`.

## 3. Gerar e usar a amostra

Quem possui o ZIP executa:

```powershell
python scripts/make_sample.py
python scripts/check_dataset.py
```

O gerador escolhe deterministicamente o primeiro nome NPZ ordenado no ZIP, preserva seus bytes e metadados e grava `data/sample/sample.npz`. Pode escolher outro membro com `--member "dataset_goes/samples/.../nome.npz"`. Também aceita `--source caminho/arquivo.npz` e `--output caminho/amostra.npz`.

Não extrai o ZIP inteiro, não sobrescreve fonte/destino existente e exige amostra menor que 50.000.000 bytes. Usa o leitor validado do piloto: limite externo de 32 MiB por NPZ e expansão interna de 128 MiB. Recusa matriz totalmente inválida ou metadados incompatíveis; não procura silenciosamente outra imagem. O limite de arquivo não é garantia de pico de RAM inferior a 50 MB.

**Amostra é uma imagem inteira, não recorte de Londrina nem conjunto representativo de treinamento.** Isso preserva a geografia ainda não comprovada. A amostra real gerada nesta preparação tem 1.455.519 bytes e fica ignorada pelo Git.

Quem não possui o acervo pode executar os testes sintéticos imediatamente. Para o smoke test real, solicite `sample.npz` por armazenamento externo autorizado da equipe e coloque-o em `data/sample/`. Não existe URL pública de dados configurada nem download automático. Confira com o responsável a autorização de distribuição.

## 4. Alternar para a fonte completa

Mude `DATASET_MODE=full` e execute `python scripts/check_dataset.py`. Isso verifica **uma imagem** da fonte completa, não processa o acervo inteiro. `GOES_MEMBER` seleciona um membro específico; vazio usa o primeiro nome ordenado.

A configuração nova alimenta os utilitários de desenvolvimento. Os scripts científicos anteriores mantêm seus argumentos explícitos e não passam a aceitar `sample.npz` como se fosse o ZIP/CSV completo. Exemplo de auditoria, com saída local separada:

```powershell
python src/data/audit.py --csv D:/dados-goes/dataset_weather.csv --zip D:/dados-goes/dataset_goes.zip --readme D:/dados-goes/README.md --output data/local-reports/audit
```

EDA, piloto e viabilidade dependem de resultados de etapas anteriores, inclusive JSON/CSV locais deliberadamente excluídos do Git. Um clone contém a documentação histórica, não todos os insumos desses scripts. Para reproduzir a cadeia, gere auditoria, EDA e piloto em ordem, seguindo [o guia histórico](history/README_pre_github.md). Alguns scripts escrevem relatórios Markdown em caminhos fixos; faça reexecuções em branch própria e revise diferenças antes de commitá-las. Não execute `provenance_inventory.py` sem ajustar seus caminhos locais explícitos.
