# STATUS — Preparação para colaboração no GitHub

## Atualização do MVP — 22/10/2026

Implementada a primeira preparação meteorológica com refatoração mínima: constantes de entradas/fuso e caminho de saída em `config.py`, script comentado `scripts/prepare_weather.py`, oito testes novos e guia em `docs/prepare_weather.md`. Auditoria, EDA, GOES e contratos anteriores foram preservados.

A tabela local tem **59.159 linhas**, quatro entradas meteorológicas e alvo experimental de chuva na próxima hora: **10.120 positivos e 49.039 negativos**. Uma linha foi excluída por ausência do timestamp futuro. O CSV original não mudou. Hipótese explícita: rain(u) representa a hora anterior; essa semântica local ainda não foi comprovada na origem. Portanto, agora há um alvo experimental, sem afirmar alvo científico definitivo ou disponibilidade operacional.

Foram gerados CSV de treinamento, JSON de rastreabilidade, CSV de exclusões, prévia de dez linhas e gráfico de classes, todos ignorados pelo Git. **38 testes passaram** e todas as associações futuras foram conferidas independentemente. Não houve divisão temporal, treinamento, imputação, normalização ou push nesta etapa. Próximo passo: definir períodos cronológicos e preparar o primeiro treino usando somente as quatro entradas. O conteúdo abaixo registra a preparação anterior do repositório.

**Atualizado em 21/10/2026.** Este documento substitui o resumo da raiz; o retrato anterior está preservado em [docs/history/STATUS_pre_github.md](docs/history/STATUS_pre_github.md).

## Resumo geral

Existe uma base substancial de auditoria, EDA e diagnóstico, mas a pesquisa ainda está na preparação científica. Não há dataset supervisionado definitivo, target aprovado, máscara regional GOES validada ou modelo treinado. A preparação para colaboração foi implementada e verificada localmente; não houve criação de remoto, commit ou push.

## Implementado

- Auditoria de 59.160 registros meteorológicos e índice de 59.033 NPZ; verificação de continuidade, ausências, duplicatas e preservação.
- EDA temporal/distribucional, verificações físicas, chuva/precipitação, cobertura e reuso; 192 imagens amostradas e 12 gráficos locais.
- Proposta metodológica e prevenção de vazamento temporal, ainda sujeitas a confirmação.
- Piloto de 19 imagens, reconstrução física em Kelvin, metadados e máscara de fill/não finitos; 15 reconstruções e quatro totalmente inválidas. Uma reconstrução tinha somente 1,61% dos pixels válidos.
- Viabilidade estrutural dos horizontes 1/3/6/7 horas, sem criação de rótulos. Contagens condicionais: 59.159/59.157/59.154/59.153 janelas.
- Investigação de proveniência e geolocalização; três produtos originais identificados, sem transformação geográfica validada.
- Configuração nova em `config.py` e `.env.example`: modo sample/full, caminhos de NPZ/ZIP, CSV e README e membro opcional.
- `scripts/make_sample.py`: seleção determinística de um NPZ inteiro, sem extração em massa ou sobrescrita; saída estritamente menor que 50 MB.
- `scripts/check_dataset.py`: smoke test de uma imagem na fonte configurada. O modo full troca a origem; não executa processamento integral.
- `.gitignore` com negação por padrão: somente código/documentação explicitamente permitidos. Dados NPZ/ZIP/CSV, resultados JSON/PNG, ambientes e credenciais locais ficam excluídos.
- `.githooks/pre-commit` e `scripts/check_staged.py`: inspecionam todo o índice, rejeitam tipos/caminhos proibidos e arquivos acima de 1 MB, inclusive NPZ adicionado à força.
- README de onboarding, comandos Git, branches e instruções de compartilhamento externo da amostra.

## Arquitetura atual

```text
config.py / .env.example   configuração dos utilitários
scripts/                  amostra, smoke test e bloqueio do índice Git
src/data/                 audit, eda, eda_figures, eda_report,
                          horizon_feasibility, provenance_inventory
src/features/             goes (leitor físico), pilot (executor amostral)
tests/                    cinco arquivos de testes unitários
reports/                  relatórios Markdown; tabelas/figuras locais ignoradas
docs/history/             README e STATUS anteriores preservados
.githooks/                hook local, ativado em cada clone
 data/                    dados e amostra somente locais
```

Os scripts científicos antigos continuam recebendo caminhos explícitos; os utilitários novos leem `.env`. Um `sample.npz` não substitui o CSV e o ZIP em uma EDA completa. Certas etapas dependem de JSON/CSV gerados localmente nas anteriores: um clone somente de código/documentação não contém essas saídas. O README explica essa dependência e a ordem histórica.

## Dados e validações desta preparação

O acervo real é um ZIP de 79.201.181.103 bytes (aproximadamente 73,8 GiB), não um único NPZ gigante. A amostra gerada em `data/sample/sample.npz` tem **1.455.519 bytes**, preserva uma imagem inteira e metadados e não deve ser publicada no Git. Não é um recorte geográfico validado nem amostra estatística para modelagem.

- **30 testes unitários passaram**, incluindo os 27 anteriores e três testes novos para amostra, preservação/recusa de sobrescrita, membro ausente e política de arquivos.
- Smoke tests sample e full passaram: matriz 885×1217, 1.077.045 pixels válidos e sem inconsistências de identidade, com geolocalização ainda não validada.
- Em repositório temporário, regras de ignore verificadas para NPZ/NPZ maiúsculo, ZIP, `.env`, dados, node_modules e resultados; código/documentação permitidos.
- Staging de código/documentação passou no verificador. NPZ forçado no índice foi bloqueado. O repositório real não foi inicializado nesta validação.
- Nenhuma instalação nova nem extração integral; originais e relatórios técnicos anteriores preservados. A amostra é um novo artefato local ignorado.

Dependências diretas: NumPy, pandas e Matplotlib. Pins mantidos: 2.5.4/3.0.1/3.11.2. Runtime de verificação: Python 3.12.14, NumPy 2.3.5 e pandas 3.0.1. Persistem divergência de ambiente e necessidade de testar instalação limpa; não há lock completo das dependências transitivas. O histórico registra a instalação da EDA em pasta de apoio externa ao repositório.

## Pendências

### Antes de publicar

1. Definir URL, visibilidade e colaboradores do repositório GitHub; executar os comandos do README com identidade e remoto reais.
2. Revisar documentação histórica para decidir se caminhos locais e detalhes do dataset devem ser públicos. Nenhum segredo deve ser colocado em arquivos permitidos.
3. Ativar o hook em cada clone e exigir revisão por Pull Request na main. `.gitignore`/hooks podem ser contornados; não usar `git add -f` para dados nem `--no-verify`.
4. Validar instalação limpa em ambiente da equipe e definir armazenamento externo autorizado para amostras/acervo. Não há licença de redistribuição de dados aprovada nem URL de download configurada.

### Antes de modelar

1. Recuperar requisição, resposta e código de exportação meteorológica para confirmar o intervalo de rain/precipitation.
2. Recuperar projeção, vetores de navegação e vínculo do recorte GOES para validar a mesma região nas duas grades.
3. Aprovar semântica dos alvos, região, qualidade mínima e regra de disponibilidade/idade das imagens. Os 50 links com fim/criação até t não são exemplos operacionais confirmados.
4. Só então construir o dataset supervisionado, separação cronológica e comparação com/sem GOES.

### Organização futura

Parametrizar caminhos fixos e saídas dos scripts legados; evitar reescrever documentação histórica sem revisão. Considerar configuração central e CI quando o fluxo estiver definido. Não há API, frontend, banco de dados ou serviço operacional. O projeto segue como pesquisa baseada em scripts; nenhuma dessas funcionalidades foi prometida como implementada.

Para detalhes científicos, consultar os relatórios em `reports/temporal/`, `reports/horizons/` e `reports/pilot/`. O histórico anterior continua disponível em `docs/history/`.

## Registro de publicação autorizado

Destino confirmado pela API: repositório privado `victorhukra/backend-monitoramento-ambiental`, com permissão de escrita. Integração baseada no commit remoto existente, sem force-push. O README original remoto foi preservado em `docs/dataset/README.md`. O relato acima descreve a preparação anterior à autorização de envio.
