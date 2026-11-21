# Geolocalização GOES e recuperação da navegação

Etapa 6 — 15/10/2026. **Não foi validada a geolocalização pixel a pixel. Nenhuma máscara regional foi criada.** Foram identificados três produtos de origem exatos, que permitem uma recuperação dirigida em vez de busca de pixels no acervo inteiro.

## Evidências locais

O inventário do projeto e da pasta original não encontrou NetCDF, código produtor dos NPZ, vetores de navegação ou tabela lat/lon. O ZIP contém 59.033 arquivos NPZ e nenhum outro tipo de arquivo. Isso delimita o material examinado, não prova que os originais não existam em outra localização.

Foram selecionados deterministicamente os primeiros nomes, entre os casos válidos já examinados na EDA, de cada par satélite/assinatura: três combinações. Nesta etapa foram abertos somente os metadados desses três NPZ; formatos vêm da EDA, sem releitura dos pixels. As chaves confirmadas são `cmi_c13_raw`, `scale_factor`, `add_offset`, `fill_value`, `units`, `timestamp_utc`, `satellite`, `source_filename`, `source_key` e `grid_signature`.

**Preservados:** identidade do produto, chave de origem, início da aquisição, identificador da grade e escala/unidade/fill. **Ausentes nessas amostras:** x/y, lat/lon, projeção completa, mapeamento do recorte e flags de qualidade originais. Sem código produtor, não se pode afirmar em que etapa esses campos foram descartados, nem se todas as imagens possuem exatamente o mesmo conjunto de chaves.

| Satélite | Assinatura abreviada | Formato da EDA | O que demonstra |
|---|---|---|---|
| GOES-16 | 44738571… | 885×1217 | Primeira grade no sensor anterior |
| GOES-19 | 44738571… | 885×1217 | Mudança de satélite não implica automaticamente mudança de assinatura |
| GOES-19 | 4d1d6811… | 882×1217 | Duas grades coexistem no histórico desse sensor |

O README original §8 fornece longitude central −75°, altura 35.786.023 m e sweep x. Fornece também limites projetados diferentes: x passa de 710424,572…–3147309,486… para 712428,538…–3149313,452…; y de −3299614,626…–−1528063,452… para −3283582,366…–−1518043,623…. Não presumir que a diferença equivale a cortar três linhas: os limites também mudam.

**Precisão documental:** o exemplo do README especifica `origin="upper"` no desenho. Portanto, há uma orientação sugerida para exibição; o problema não é ausência absoluta dessa indicação. Falta comprovar que ela corresponde à ordem real do recorte, se os limites são centros ou bordas, o elipsoide usado e a ligação aos vetores originais. Defaults de Cartopy e um mapa visualmente plausível não validam essa ligação. `grid_signature` é um identificador opaco, não coordenadas nem algoritmo de navegação recuperável sozinho.

## Produtos exatos a recuperar

As chaves abaixo foram lidas dos metadados reais e os nomes coincidem com `source_filename`. As assinaturas completas e os URLs candidatos constam de `evidence_inventory.json`.

1. **GOES-16 / 44738571…** — chave:
   `ABI-L2-MCMIPF/2020/001/00/OR_ABI-L2-MCMIPF-M6_G16_s20200010000216_e20200010009536_c20200010010028.nc`
2. **GOES-19 / 44738571…** — chave:
   `ABI-L2-MCMIPF/2025/097/16/OR_ABI-L2-MCMIPF-M6_G19_s20250971600208_e20250971609522_c20250971610007.nc`
3. **GOES-19 / 4d1d6811…** — chave:
   `ABI-L2-MCMIPF/2026/147/22/OR_ABI-L2-MCMIPF-M6_G19_s20261472200204_e20261472209524_c20261472209581.nc`

O bucket candidato é `noaa-goes16` ou `noaa-goes19`, conforme o satélite. O `source_key` não inclui um bucket: essa composição é uma hipótese de localização no catálogo público, não prova de armazenamento atual. Foram tentadas três consultas HTTP HEAD, sem baixar conteúdo; todas falharam com `getaddrinfo failed`. Isso é falha de resolução de endereço, **não 404 nem prova de inexistência**. Resultado em `remote_metadata_checks.json`. Não foi possível confirmar tamanho, ETag ou disponibilidade remota. Nenhum produto externo foi baixado. As convenções de nomes já foram documentadas nos estágios anteriores a partir da [NOAA](https://raw.githubusercontent.com/NOAA-Big-Data-Program/nodd-data-docs/main/GOES/README.md).

Para repetir a verificação, executar HEAD nos três `candidate_origin_url` do manifesto, com timeout de 12 s e registrar código HTTP/cabeçalhos ou erro. Mesmo um HEAD bem-sucedido provaria somente presença atual; `Last-Modified` e criação do produto não demonstram recebimento histórico pelo projeto.

## Metadados necessários e método mais confiável

Recuperar inicialmente os cabeçalhos e variáveis de navegação desses produtos, evitando baixar matrizes multicanais se a fonte permitir leitura seletiva. Se necessário, obter os três NetCDF originais, sequencialmente, verificando tamanhos antes e mantendo-os fora dos dados originais.

Informações a procurar, **sem pressupor seus valores**:

- Vetores x/y originais com dimensão, ordem, unidade e eventual scale_factor/add_offset; centros e, quando presentes, limites dos pixels.
- Atributo de grid mapping da CMI_C13 e variável de projeção correspondente: origem, altura de perspectiva, sweep, semi-eixos do elipsoide e demais parâmetros necessários.
- Metadados de navegação/geometria e qualidade disponíveis no produto; tempo de cobertura e identificadores/versão de processamento.
- Código/versionamento da conversão para NPZ: seleção C13, slices de linhas/colunas, limites geográficos usados, orientação/transposição, strides, eventuais reamostragem e criação do `grid_signature`.

**Caminho preferido:** reproduzir exatamente o recorte a partir dos vetores e da projeção do produto original. Comparar dimensões, ordem, cantos, ponto central e amostras de valores C13 após aplicar corretamente as escalas de cada representação. Confirmar que a matriz NPZ corresponde ao recorte, e não apenas a uma área de mesmo tamanho. Verificar os três pares sensor/grade; dois representantes, um por assinatura, seriam o mínimo espacial, mas o terceiro testa a continuidade na troca de satélite.

Se o código de recorte não puder ser recuperado, procurar vetores recortados ou lat/lon por pixel fornecidos pelo produtor, acompanhados de método e validação. Encontrar os NetCDF por nome recupera a navegação do produto completo, **mas não determina sozinho onde o recorte NPZ começa**. Uma inferência a partir dos limites do README só pode ser hipótese de diagnóstico, a confrontar com o original antes de aceitar índices.

Após comprovar o vínculo, transformar os centros reais para coordenadas geográficas usando os parâmetros efetivos. Validar pontos e orientação, visibilidade geostacionária e consistência da transformação inversa. Definir então uma única região geográfica, com regra de inclusão por centro/interseção e máscaras específicas de cada grade. Registrar número de pixels, cobertura, tolerância de validação e tratamento de bordas. Mesmo com geolocalização válida, a representação de nuvens sobre um elipsoide pode exigir análise adicional de deslocamento aparente por altura; não se assume correção feita.

O README cita aproximadamente −23,304°, −51,186° na descrição meteorológica e usa −23,3045°, −51,1696° no marcador de Londrina do exemplo cartográfico. São referências diferentes: escolher explicitamente ponto/célula ou área de estudo antes de definir raio/contorno. Nenhuma foi promovida a localização exata neste estágio. Não escolher tamanho de região por desempenho no teste e não igualar formatos por redimensionamento.

## Resultado e limite

Há rastreabilidade nominal suficiente para solicitar produtos específicos. Não há navegação e mapeamento suficientes para afirmar coordenadas dos pixels NPZ. A unidade Kelvin, o formato e os limites aproximados não resolvem isso. Os dados e relatórios históricos foram preservados; o diagnóstico não gera máscaras, estatísticas regionais ou atributos.
