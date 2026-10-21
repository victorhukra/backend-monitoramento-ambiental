"""Piloto pequeno de engenharia. Sem máscara geográfica presumida ou dataset de treino."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from src.data.audit import fingerprint
from src.features.goes import read_member

KNOWN_SHAPES = {
    "44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876": [885,1217],
    "4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8": [882,1217],
}


def clean_json(value):
    if isinstance(value, dict): return {k:clean_json(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [clean_json(v) for v in value]
    if isinstance(value, (float,np.floating)) and not np.isfinite(value):
        return str(value)  # Representação de metadado, nunca substituição de pixel.
    if isinstance(value, np.generic): return value.item()
    return value


def write_json(path,value):
    path.write_text(json.dumps(clean_json(value),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


def select_sample(csv_path, eda_path):
    # Ler apenas as referências, sem carregar variáveis meteorológicas ou criar target.
    frame=pd.read_csv(csv_path,usecols=["time","image_link"])
    parsed=pd.to_datetime(frame.time,format="ISO8601")
    january=frame.loc[(parsed>=pd.Timestamp("2023-01-01"))&(parsed<pd.Timestamp("2023-02-01"))].dropna(subset=["image_link"])
    unique=january.drop_duplicates("image_link").sort_values(["time","image_link"])
    reasons={}
    def add(name,reason): reasons.setdefault(name,set()).add(reason)
    for index in np.unique(np.linspace(0,len(unique)-1,min(12,len(unique)),dtype=int)) if len(unique) else []:
        add(unique.iloc[index].image_link,"janeiro2023_12_posicoes_equiespacadas")
    details=json.loads((eda_path/"goes_sample_details.json").read_text(encoding="utf-8"))
    invalid=[x for x in details if x.get("valid_pixels")==0]
    for item in invalid: add(item["image_link"],"matriz_totalmente_invalida_identificada_EDA")
    reuse=pd.read_csv(eda_path/"image_reuse.csv").sort_values(["span_hours","image_link"],ascending=[False,True])
    for name in reuse.head(2).image_link: add(name,"reuso_identificado_EDA")
    for signature in sorted({x.get("metadata",{}).get("grid_signature") for x in details if x.get("metadata",{}).get("grid_signature")}):
        candidates=sorted([x for x in details if x.get("valid_pixels",0)>0 and x.get("metadata",{}).get("grid_signature")==signature],key=lambda x:x["image_link"])
        if candidates: add(candidates[0]["image_link"],"exemplo_valido_assinatura_EDA")
    metadata_cases=[x for x in details if x.get("missing_metadata") or any(x.get(k) is False for k in ("filename_satellite_matches","source_filename_matches","source_key_basename_matches"))]
    for item in metadata_cases[:2]: add(item["image_link"],"problema_metadados_identificado_EDA")
    if len(reasons)>30: raise ValueError("Amostra excede limite de 30 imagens únicas; rever seleção")
    manifest=[{"image_link":name,"reasons":sorted(reason),
               "csv_reference_times":frame.loc[frame.image_link.eq(name).fillna(False),"time"].tolist()}
              for name,reason in sorted(reasons.items())]
    return manifest,{"january_rows_with_link":len(january),"january_unique_links":len(unique),
                     "known_invalid_candidates":len(invalid),"known_metadata_problem_candidates":len(metadata_cases)}


def report(output):
    run=json.loads((output/"run_manifest.json").read_text(encoding="utf-8"))
    results=json.loads((output/"image_diagnostics.json").read_text(encoding="utf-8"))
    successful=[x for x in results if x["status"]=="reconstructed"]
    partial=[x for x in successful if x['diagnostics']['invalid_pixels']>0]
    partial_text='\n'.join(f"- `{x['image_link']}`: {x['diagnostics']['valid_pixels']} pixels válidos e {x['diagnostics']['invalid_pixels']} inválidos; fração válida {100*x['diagnostics']['valid_fraction']:.4f}%." for x in partial)
    tests=(output/"tests.txt").read_text(encoding="utf-8") if (output/"tests.txt").exists() else "Testes ainda não registrados."
    rows=[]
    metadata_groups=Counter((str(x.get('diagnostics',{}).get('shape')),x.get('diagnostics',{}).get('dtype'),
        x.get('diagnostics',{}).get('metadata',{}).get('satellite'),
        x.get('diagnostics',{}).get('metadata',{}).get('grid_signature')) for x in results)
    group_text='\n'.join(f"| {sat} | {sig} | {shape} | {dtype} | {count} |" for (shape,dtype,sat,sig),count in sorted(metadata_groups.items(),key=str))
    for i,item in enumerate(results,1):
        d=item.get("diagnostics",{}); meta=d.get("metadata",{})
        rows.append(f"| {i} | {meta.get('timestamp_utc','—')} | {meta.get('satellite','—')} | {d.get('shape','—')} | {item['status']} | {d.get('valid_pixels','—')} | {d.get('invalid_pixels','—')} | {d.get('physical_min_K','—')} | {d.get('physical_max_K','—')} |")
    text=f"""# Piloto técnico GOES — estágio 4

## 1. Escopo e amostra

Piloto de engenharia, executado em 15/10/2026. Nenhum target, dataset de modelagem, associação a previsão, elegibilidade temporal definitiva, imputação ou modelo foi criado. Fontes abertas somente para leitura. O ZIP real é `{run['sources_before'][1]['path']}`, confirmado no ambiente, com {run['sources_before'][1]['bytes']} bytes. Foram usados `ZipFile.read(ZipInfo)` e `numpy.load(..., allow_pickle=False)`, sem extração em disco.

Seleção: **até 12 links únicos de janeiro/2023**, ordenados por time/nome e escolhidos em posições equiespaçadas por linspace inteiro entre primeiro e último. Nenhuma amostragem aleatória/seed é necessária. Janeiro contém {run['selection']['january_rows_with_link']} linhas com link e {run['selection']['january_unique_links']} links únicos; não foram lidas as 744 imagens do mês. Acrescentados os quatro casos totalmente inválidos já identificados na EDA, dois casos de maior intervalo de reuso (desempate por nome), e o primeiro exemplo válido de cada assinatura da EDA. Nomes são deduplicados antes da leitura.

Resultado: **{len(results)} imagens únicas selecionadas**. `sample_manifest.json` registra cada nome, motivos e referências locais do CSV. São referências para inspeção, não emissões de previsão. O resultado não estima frequência de falhas do acervo. Exemplos de metadados ausentes/inconsistentes conhecidos no manifesto da EDA: **{run['selection']['known_metadata_problem_candidates']}**. Não foi realizada busca de pixels por todo o ZIP; esses cenários foram exercitados em matrizes artificiais nos testes.

## 2. Implementação e reuso

`src/features/goes.py` separa leitura seletiva, diagnóstico de identidade e reconstrução física. Reutiliza `scalar` e `stats` de `src/data/audit.py`; `stats` é usado nos testes artificiais, não para gerar features regionais reais. Reutiliza-se também `fingerprint` no executor `src/features/pilot.py`. Os módulos anteriores não foram modificados.

A função histórica `inspect_npz` faz estatísticas da imagem inteira e falha para matriz totalmente inválida. Por isso não foi utilizada como extrator deste estágio: o novo contrato retorna estados explícitos e não emite cinco features para o domínio inteiro. `reconstructed` significa apenas que a leitura/transformação física funcionou; não certifica geolocalização, QA radiométrico completo ou disponibilidade temporal.

Limites: 30 imagens únicas no piloto, 32 MiB por membro externo e 128 MiB de expansão interna do NPZ. Uma imagem por vez; arrays liberados ao final da inspeção. Nenhum PNG/JPEG criado. Dependências efetivamente usadas: numpy/pandas e biblioteca padrão; nenhuma instalação nova.

## 3. Metadados e reconstrução física

Inspecionados `satellite`, `grid_signature`, `timestamp_utc`, `source_filename`, `source_key`, `units`, `scale_factor`, `add_offset` e `fill_value`. Chaves, shape/dtype e diagnósticos individuais estão em `image_diagnostics.json`. A tabela resumida está em `image_diagnostics.csv`.

| Satélite | Assinatura | Shape | Dtype | Imagens |
|---|---|---|---|---|
{group_text}

Problemas de metadados/identidade registrados nesta execução: {sum(bool(x.get('diagnostics',{}).get('metadata_issues')) for x in results)} arquivos. O manifesto e os detalhes preservam os valores reais por arquivo, sem propagar defaults de uma imagem para outra.

O preenchimento é obtido de cada arquivo, não fixado em −1. Para inteiros, um fill incompatível com o dtype é rejeitado, sem reinterpretar sinais. Fill NaN em matriz flutuante é explicitamente tratado. A máscara combina finitude e ausência de fill antes da multiplicação. Contagens de fill e não finitos podem se sobrepor; `invalid_pixels` conta a união, e a sobreposição é registrada.

Escala e offset devem ser escalares numéricos finitos. Este leitor C13 aceita escala positiva e unidade K/Kelvin; outras unidades ficam como não suportadas, sem valores inventados. Metadados físicos ausentes impedem reconstrução. Falhas de identidade são registradas separadamente e impedem considerar o arquivo plenamente validado, mesmo que sua transformação numérica seja possível. Timestamps sem offset são sinalizados sem assumir fuso.

Resultado por estado: `{run['status_counts']}`. Nos arquivos reconstruídos, a faixa global dos **diagnósticos de leitura da matriz inteira**, em Kelvin, foi {min((x['diagnostics']['physical_min_K'] for x in successful),default=None)} a {max((x['diagnostics']['physical_max_K'] for x in successful),default=None)} K. Esses extremos não são estatísticas de Londrina, não são features e não demonstram qualidade de todos os pixels. Não houve conversão para Celsius ou confusão com temperatura do ar a 2 m.

| ID | Timestamp do NPZ | Satélite | Shape | Estado físico | Válidos | Inválidos | Mínimo diagnóstico K | Máximo diagnóstico K |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## 4. Seleção espacial: não validada

**Fatos observados:** todos os conjuntos de chaves lidos estão no JSON. Os NPZ examinados contêm matriz e metadados escalares; não contêm vetores x/y, latitude/longitude por pixel ou objeto completo de projeção. A listagem do ZIP não encontrou arquivos auxiliares não NPZ: {run['non_npz_file_count']}. Essa listagem não é leitura de todas as matrizes. `grid_signature` é identificador, não função de geolocalização.

O README original, §8 “Informações da projeção”, fornece longitude central −75°, altura 35.786.023 m, sweep x e limites distintos de cada assinatura:

| Grade | Shape | x_min / x_max (m conforme exemplo) | y_min / y_max (m conforme exemplo) |
|---|---|---|---|
| 44738571… | 885×1217 | 710424,5721944869 / 3147309,4861819297 | −3299614,6266644895 / −1528063,4525660723 |
| 4d1d6811… | 882×1217 | 712428,538085401 / 3149313,452072844 | −3283582,3662838787 / −1518043,6231115013 |

**Interpretação:** esses valores permitem uma visualização aproximada documentada, mas não fecham a correspondência inequívoca entre centros dos pixels e coordenadas. Não há declaração suficiente de centros versus bordas, vetores/ordem da grade, elipsoide e correspondência ao recorte original. Inferir tudo com linspace e defaults de projeção criaria hipóteses não validadas.

**Decisão do piloto:** não construir máscara, não escolher raio/contorno, não redimensionar e não calcular estatísticas regionais reais. O futuro centro de referência do README é aproximadamente −23,304°, −51,186°; isso não define sozinho a região. Não assumir que índices iguais nas duas grades indicam o mesmo lugar.

Para destravar, obter pelo menos um netCDF de origem de cada assinatura com coordenadas x/y (unidades, centros e ordem), atributos completos da projeção geoestacionária (altura, longitude de origem, sweep, eixos do elipsoide), e código/índices de recorte que relacionem a matriz NPZ ao netCDF; alternativamente, fornecer matrizes lat/lon validadas por assinatura. Confirmar limites de pixel e orientação. Validar o ponto de Londrina e uma região geográfica fixa nas duas grades. Depois definir contorno, critério de pixels e cobertura mínima, sem desempenho preditivo como critério. Não foi feito download de dados adicionais.

## 5. Estatísticas e qualidade

Entre as reconstruções, **{len(successful)-len(partial)} matrizes têm todos os pixels válidos segundo fill/finitude e {len(partial)} é parcialmente inválida**. Isso não certifica qualidade radiométrica. Casos parciais:

{partial_text or 'Nenhum caso parcial encontrado nesta amostra.'}

O caso parcial de setembro/2024 já está no JSON detalhado da EDA, com a mesma contagem de inválidos, e foi confirmado pelo piloto. A generalização no texto da EDA de que os demais arquivos tinham zero pixels inválidos não corresponde a esse registro detalhado. O relatório anterior foi preservado; esta ressalva corrige sua interpretação. Nenhum limiar mínimo de cobertura foi escolhido: reconstrução bem-sucedida não implica imagem elegível para features.

**As cinco features regionais não foram extraídas**, porque a condição de validação espacial do pedido não foi atendida. `region_statistics` permanece null e `spatial_status` é `not_validated`. As contagens e frações registradas referem-se exclusivamente à matriz lida, como diagnóstico de máscara. Não foram apresentadas como qualidade de uma região de Londrina.

Média, desvio padrão populacional, mínimo, máximo e mediana foram verificados somente em pequenas matrizes artificiais de valores físicos com máscara conhecida, reutilizando a função `stats`. Isso testa a aritmética sem fabricar uma máscara geográfica. Em matriz totalmente inválida: estado `all_invalid`, nenhuma matriz física retornada, extremos físicos ausentes, nenhuma substituição por zeros. Casos de metadados físicos inválidos são distintos de ausência de pixels válidos.

## 6. Limitações, falhas e temporalidade

Os casos totalmente inválidos da EDA foram incluídos deliberadamente. Metadados ausentes ou identidade incompatível não tinham exemplos reais identificados disponíveis; os testes sintéticos não são evidências de que esses problemas ocorram no acervo. Um fill diferente do esperado ou campo ausente nunca aciona preenchimento silencioso.

Shapes distintos são suportados como matrizes numéricas; a compatibilidade entre assinatura e shape é conferida com o mapa do README apenas como diagnóstico, não validação geográfica. Unidade e escala compartilhadas não provam equivalência espacial ou calibração entre sensores.

O piloto registra referências do CSV e timestamps do NPZ sem estabelecer emissão, target, tolerância temporal, nova associação ou elegibilidade definitiva. Não transforma as capturas futuras em entradas autorizadas. Permanecem pendentes a semântica do CSV e logs históricos de disponibilidade. Não é um pipeline operacional em tempo real.

## 7. Testes e reprodutibilidade

Cada membro real foi lido e reconstruído **duas vezes sequencialmente**; compararam-se SHA-256 do payload e representação determinística de todos os diagnósticos (sem tempos). Resultado: {run['reproducible_files']} de {len(results)} arquivos com resultados idênticos nas duas leituras. Isso verifica reexecução no ambiente atual, não identidade bit a bit entre plataformas. Os testes unitários também comparam arrays físicos, máscaras e diagnósticos, sem depender do ZIP original.

Testes originais preservados. Saída da execução em `tests.txt`:

```text
{tests.strip()}
```

## 8. Tempo, memória e preservação

Tempo da execução completa do piloto antes da escrita dos relatórios: **{run['elapsed_seconds']:.3f} s**, incluindo índice, seleção, duas leituras por imagem e fingerprints. Total de bytes de membros selecionados, por passagem: {run['selected_member_bytes']} bytes; não representa tráfego físico exato do disco/cache. Pico rastreado por tracemalloc: **{run['tracemalloc_peak_bytes']/1024**2:.2f} MiB**. Essa medida não é RSS total do processo e pode omitir alocações nativas; não se afirma um limite máximo total de RAM. O JSON guarda limite inferior de bytes de arrays vivos por imagem, excluindo temporários. Leituras sequenciais evitam acumular matrizes.

Fontes e evidências de entrada inalteradas na verificação antes/depois: **{run['sources_unchanged']}**. SHA-256 para arquivos pequenos, tamanho/mtime para ZIP; sem hash integral de 79 GB. Relatórios anteriores e código original não são regenerados. O ambiente efetivo é registrado no manifesto: `{run['environment']}`.

## 9. Recomendação para a próxima etapa

**Concluído:** seleção pequena reproduzível, leitura NPZ, inspeção de metadados, reconstrução em Kelvin, máscara de fill/não finitos, estados de falha e testes independentes do acervo.

**Limitação confirmada neste piloto:** metadados geográficos insuficientes para validar a região fixa sem hipóteses adicionais. Portanto, a etapa condicional de features regionais não foi executada. Obter a correspondência de geolocalização por assinatura e definir a região antes de ampliar o processamento. Não avançar para dataset de treinamento, target ou modelo. O protocolo temporal continua sujeito à confirmação.

Fontes: `reports/dataset_audit.md`; `reports/eda/eda_report.md`, §§7–10; `reports/eda/goes_sample_details.json`; `reports/eda/image_reuse.csv`; `reports/protocol/protocol_proposal.md`, §§3, 7 e 9; README original, §§4, 5 e 8. Os caminhos absolutos e fingerprints usados nesta execução constam de `run_manifest.json`.
"""
    (output/"goes_pilot_report.md").write_text(text,encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",type=Path); parser.add_argument("--zip",type=Path)
    parser.add_argument("--readme",type=Path)
    parser.add_argument("--report-only",action="store_true")
    args=parser.parse_args()
    output=ROOT/"reports"/"pilot"
    if args.report_only:
        report(output); return
    if not all([args.csv,args.zip,args.readme]): parser.error("Informar --csv, --zip e --readme")
    eda=ROOT/"reports"/"eda"
    sources=[args.csv,args.zip,args.readme,eda/"goes_sample_details.json",eda/"image_reuse.csv"]
    if any(output.resolve() in p.resolve().parents for p in sources): parser.error("Fontes não podem estar no diretório de saída")
    before=[fingerprint(p) for p in sources]
    tracemalloc.start(); started=time.perf_counter()
    manifest,selection=select_sample(args.csv,eda)
    results=[]; selected_bytes=0
    with zipfile.ZipFile(args.zip,"r") as archive:
        members={}; duplicates=set(); non_npz=0
        for item in archive.infolist():
            if item.is_dir(): continue
            if not item.filename.endswith('.npz'): non_npz+=1
            if item.filename in members: duplicates.add(item.filename)
            members[item.filename]=item
        for item in manifest:
            name=item["image_link"]; tick=time.perf_counter()
            result={"image_link":name,"reasons":item["reasons"]}
            try:
                if name not in members: raise ValueError("Membro selecionado ausente no ZIP")
                if name in duplicates: raise ValueError("Nome duplicado no ZIP: associação ambígua")
                selected_bytes+=members[name].file_size
                snapshots=[]
                for _ in range(2):
                    payload,physical=read_member(archive,members[name])
                    detail=physical.diagnostics
                    signature=detail.get("metadata",{}).get("grid_signature")
                    if signature not in KNOWN_SHAPES:
                        detail["metadata_issues"].append("Assinatura não reconhecida no mapa do README")
                    elif detail["shape"]!=KNOWN_SHAPES[signature]:
                        detail["metadata_issues"].append("Shape diverge da assinatura descrita no README")
                    snapshot={"status":physical.status,"sha256":hashlib.sha256(payload).hexdigest(),"diagnostics":clean_json(detail)}
                    snapshots.append(snapshot)
                    del payload,physical
                result.update(snapshots[0]); result["reproducible"]=snapshots[0]==snapshots[1]
            except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as error:
                result.update(status="read_error",error=f"{type(error).__name__}: {error}",reproducible=False)
            result["elapsed_seconds"]=time.perf_counter()-tick
            results.append(result)
    after=[fingerprint(p) for p in sources]
    elapsed=time.perf_counter()-started; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    run={"sources_before":before,"sources_after":after,"sources_unchanged":before==after,
         "selection":selection,"selected_images":len(manifest),"status_counts":dict(Counter(x["status"] for x in results)),
         "selected_member_bytes":selected_bytes,"non_npz_file_count":non_npz,
         "reproducible_files":sum(x.get("reproducible",False) for x in results),
         "elapsed_seconds":elapsed,"tracemalloc_peak_bytes":peak,
         "environment":{"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"pandas":pd.__version__}}
    output.mkdir(parents=True,exist_ok=True)
    write_json(output/"sample_manifest.json",manifest); write_json(output/"image_diagnostics.json",results)
    write_json(output/"run_manifest.json",run)
    flat=[]
    for item in results:
        d=item.get("diagnostics",{}); meta=d.get("metadata",{})
        flat.append({"image_link":item["image_link"],"status":item["status"],**meta,
                     **{k:d.get(k) for k in ["shape","dtype","pixels","valid_pixels","invalid_pixels","valid_fraction","fill_pixels","nonfinite_pixels","physical_min_K","physical_max_K","spatial_status","region_statistics"]},
                     "issues":json.dumps(d.get("issues",[])+d.get("metadata_issues",[]),ensure_ascii=False),
                     "reproducible":item["reproducible"]})
    pd.DataFrame(flat).to_csv(output/"image_diagnostics.csv",index=False)
    report(output)
    print(json.dumps({k:run[k] for k in ["selected_images","status_counts","reproducible_files","sources_unchanged","elapsed_seconds","tracemalloc_peak_bytes"]},indent=2))
    if before!=after or any(x["status"]=="read_error" or not x["reproducible"] for x in results):
        raise SystemExit("Piloto com falhas de leitura/reprodutibilidade/preservação; consultar relatório")


if __name__=="__main__": main()
