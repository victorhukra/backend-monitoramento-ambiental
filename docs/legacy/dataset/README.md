# Conjunto de dados meteorológicos multimodal + GOES

Este conjunto de dados reúne, em uma mesma linha temporal, **dados meteorológicos horários** e o **caminho para a imagem de satélite GOES correspondente**.

A estrutura foi pensada para facilitar experimentos com:

- dados tabulares;
- imagens de satélite;
- modelos multimodais que combinam as duas fontes.

O pacote compartilhado contém apenas:

```text
README.md
dataset_weather.csv
dataset_goes/
└── samples/
    └── ANO/
        └── MES/
            └── DIA/
                └── *.npz
```

> O nome do arquivo CSV pode variar. Nos exemplos abaixo é usado `dataset_weather.csv`.

---

## 1. Fontes dos dados

### 1.1 Dados meteorológicos

Os dados tabulares foram obtidos do **Open-Meteo Historical Weather API**, para a região de Londrina, Paraná, Brasil.

Coordenadas de referência:

- latitude: aproximadamente **-23.304°**;
- longitude: aproximadamente **-51.186°**;
- fuso horário: **America/Sao_Paulo**.

Documentação:

https://open-meteo.com/en/docs/historical-weather-api

Os dados do Open-Meteo utilizados aqui são dados históricos derivados de modelos/reanálises para as coordenadas informadas. Portanto, **não devem ser interpretados como medições diretas de uma estação meteorológica física**.

### 1.2 Dados de satélite

As imagens são derivadas do **GOES-East Advanced Baseline Imager (ABI)**, distribuídas pela NOAA por meio do NOAA Open Data Dissemination / AWS Open Data.

Neste conjunto de dados são utilizadas as seguintes fontes:

- produto: **ABI-L2-MCMIPF**;
- variável: **CMI_C13**;
- canal: **ABI Band 13**;
- tipo: infravermelho;
- comprimento de onda central aproximado: **10.3 µm**;
- nome do canal: **Clean Longwave Infrared Window**.

O canal 13 pode ser usado durante o dia e a noite e é especialmente útil para observar nuvens e temperaturas de brilho no infravermelho.

Referências:

https://www.goes.noaa.gov/abispectralattributes.php

https://registry.opendata.aws/noaa-goes/

O conjunto utiliza dados do GOES-East ao longo do período disponível, incluindo **GOES-16** e **GOES-19**.

---

## 2. Organização temporal

O CSV usa horário local do Brasil:

```text
America/Sao_Paulo
```

Os nomes originais dos arquivos GOES, por outro lado, usam horário **UTC**.

Por exemplo:

```text
OR_ABI-L2-MCMIPF-M6_G16_s20200010300216_....npz
```

O trecho:

```text
s20200010300216
```

indica aproximadamente:

```text
2020 = ano
001  = primeiro dia do ano
03   = hora UTC
00   = minuto
21.6 = segundo
```

Logo:

```text
2020-01-01 03:00:21.6 UTC
```

corresponde a aproximadamente:

```text
2020-01-01 00:00:21.6 America/Sao_Paulo
```

Por isso essa imagem é associada à linha:

```text
2020-01-01T00:00:00
```

O pareamento foi realizado procurando a captura GOES temporalmente mais próxima do horário da linha do CSV, após converter internamente o horário local para UTC.

Não é realizada interpolação temporal da imagem.

---

## 3. Estrutura do CSV

Cada linha representa uma hora.

A coluna `image_link` aponta para o arquivo `.npz` de satélite associado àquela hora. Quando não existe imagem correspondente, o valor é `NaN`.

### Colunas

| Coluna | Unidade / tipo | Descrição |
|---|---|---|
| `time` | ISO-8601 | Data e hora local em `America/Sao_Paulo`. |
| `image_link` | texto / NaN | Caminho para o arquivo `.npz` GOES associado ao horário. |
| `temperature_2m` | °C | Temperatura do ar a 2 m. |
| `relative_humidity_2m` | % | Umidade relativa do ar a 2 m. |
| `dew_point_2m` | °C | Temperatura do ponto de orvalho a 2 m. |
| `apparent_temperature` | °C | Temperatura aparente. |
| `weather_code` | código WMO | Código de condição meteorológica. |
| `cloud_cover` | % | Cobertura total de nuvens. |
| `pressure_msl` | hPa | Pressão atmosférica reduzida ao nível médio do mar. |
| `surface_pressure` | hPa | Pressão atmosférica na superfície. |
| `wind_speed_10m` | m/s | Velocidade do vento a 10 m. |
| `wind_direction_10m` | graus | Direção do vento a 10 m. |
| `wind_gusts_10m` | m/s | Velocidade das rajadas de vento a 10 m. |
| `shortwave_radiation` | W/m² | Radiação solar global de onda curta na superfície. |
| `direct_radiation` | W/m² | Componente direta da radiação solar na superfície. |
| `diffuse_radiation` | W/m² | Componente difusa da radiação solar na superfície. |
| `direct_normal_irradiance` | W/m² | Irradiância direta normal (DNI). |
| `is_day` | 0 ou 1 | Indica período diurno (`1`) ou noturno (`0`). |
| `sunshine_duration` | s | Duração de insolação dentro do intervalo. |
| `soil_moisture_0_to_7cm` | m³/m³ | Umidade volumétrica do solo entre 0 e 7 cm. |
| `rain` | mm | Quantidade de chuva no intervalo. |
| `precipitation` | mm | Precipitação total no intervalo. |

### Leitura simples do CSV

```python
import pandas as pd

csv_path = "dataset_weather.csv"

df = pd.read_csv(csv_path)
df["time"] = pd.to_datetime(df["time"])

print(df.head())
print(df.columns)
```

Selecionando apenas registros que possuem imagem:

```python
df_images = df[df["image_link"].notna()].copy()
```

---

## 4. Estrutura dos arquivos `.npz`

Cada arquivo `.npz` contém uma amostra do canal 13 e metadados suficientes para interpretar os valores armazenados.

As principais chaves são:

| Chave | Descrição |
|---|---|
| `cmi_c13_raw` | Matriz CMI do canal 13 armazenada nos valores compactados originais. |
| `scale_factor` | Fator de escala necessário para reconstruir o valor físico. |
| `add_offset` | Offset necessário para reconstruir o valor físico. |
| `fill_value` | Valor usado para representar pixels inválidos/ausentes. |
| `units` | Unidade do dado reconstruído. |
| `timestamp_utc` | Horário UTC do início da captura. |
| `satellite` | Satélite de origem, por exemplo `GOES-16` ou `GOES-19`. |
| `source_filename` | Nome do arquivo NOAA original. |
| `source_key` | Caminho/chave do objeto original na fonte NOAA. |
| `grid_signature` | Identificador da grade/projeção usada pela amostra. |

Para verificar as chaves de um arquivo:

```python
import numpy as np

sample = "dataset_goes/samples/2020/01/01/exemplo.npz"

with np.load(sample, allow_pickle=False) as data:
    print(data.files)
```

---

## 5. Reconstruindo os valores físicos

A matriz `cmi_c13_raw` não deve ser interpretada diretamente como temperatura.

A reconstrução é feita por:

```text
valor_fisico = raw * scale_factor + add_offset
```

Quando a unidade armazenada for Kelvin:

```text
temperatura_C = temperatura_K - 273.15
```

Exemplo:

```python
import numpy as np

sample = "dataset_goes/samples/2020/01/01/exemplo.npz"

with np.load(sample, allow_pickle=False) as data:
    raw = data["cmi_c13_raw"].astype(np.float32)

    scale_factor = np.asarray(data["scale_factor"]).item()
    add_offset = np.asarray(data["add_offset"]).item()
    fill_value = np.asarray(data["fill_value"]).item()

    units = np.asarray(data["units"]).item()
    if isinstance(units, bytes):
        units = units.decode("utf-8")

valid = raw != fill_value

physical = np.full(raw.shape, np.nan, dtype=np.float32)
physical[valid] = raw[valid] * scale_factor + add_offset

if str(units).lower() in {"k", "kelvin"}:
    temperature_c = physical - 273.15
else:
    temperature_c = physical

print("Formato:", temperature_c.shape)
print("Mínimo:", np.nanmin(temperature_c))
print("Máximo:", np.nanmax(temperature_c))
```

---

## 6. Convertendo um `.npz` para imagem PNG

O exemplo abaixo gera uma imagem simples em escala de cinza.

Instalação:

```bash
pip install numpy matplotlib
```

Código:

```python
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

npz_path = Path("dataset_goes/samples/2020/01/01/exemplo.npz")

with np.load(npz_path, allow_pickle=False) as data:
    raw = data["cmi_c13_raw"].astype(np.float32)
    scale = np.asarray(data["scale_factor"]).item()
    offset = np.asarray(data["add_offset"]).item()
    fill = np.asarray(data["fill_value"]).item()

valid = raw != fill

temperature_k = np.full(raw.shape, np.nan, dtype=np.float32)
temperature_k[valid] = raw[valid] * scale + offset

temperature_c = temperature_k - 273.15

plt.figure(figsize=(10, 7))
plt.imshow(
    temperature_c,
    cmap="gray_r",
    vmin=-80,
    vmax=40,
)
plt.colorbar(label="Temperatura de brilho (°C)")
plt.title("GOES ABI - Band 13")
plt.axis("off")
plt.tight_layout()
plt.savefig("goes_band13.png", dpi=150, bbox_inches="tight")
plt.show()
```

O resultado é uma representação visual da temperatura de brilho do canal infravermelho.

> A temperatura de brilho medida pelo satélite não é equivalente à temperatura do ar medida a 2 m da superfície.

---

## 7. Abrindo automaticamente a imagem indicada pelo CSV

Uma forma comum de trabalhar com o conjunto de dados é selecionar uma linha do CSV e carregar a imagem associada.

```python
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(".")
df = pd.read_csv(root / "dataset_weather.csv")

row = df[df["image_link"].notna()].iloc[0]

print("Horário:", row["time"])
print("Imagem:", row["image_link"])

npz_path = root / row["image_link"]

with np.load(npz_path, allow_pickle=False) as data:
    raw = data["cmi_c13_raw"]
    satellite = np.asarray(data["satellite"]).item()
    timestamp_utc = np.asarray(data["timestamp_utc"]).item()

print("Satélite:", satellite)
print("Timestamp UTC:", timestamp_utc)
print("Formato:", raw.shape)
```

---

## 8. Adicionando cidades e limites territoriais

Os dados numéricos armazenados no `.npz` **não possuem nomes de cidades ou fronteiras desenhados na matriz**. Essas informações devem ser adicionadas apenas no momento da visualização.

Isso é importante porque mantém os dados utilizados por modelos de aprendizado de máquina livres de anotações visuais artificiais.

Para uma visualização geográfica, pode-se usar `Cartopy`.

Instalação:

```bash
pip install numpy matplotlib cartopy
```

### Informações da projeção

As amostras usam projeção geoestacionária com:

```text
central_longitude = -75.0
satellite_height  = 35786023.0 m
sweep_axis        = x
```

O campo `grid_signature` dentro de cada `.npz` identifica qual grade deve ser utilizada.

As grades presentes neste conjunto de dados são:

```python
GRID_INFO = {
    # GOES-16 / também presente em algumas amostras GOES-19
    "44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876": {
        "shape": (885, 1217),
        "x_min": 710424.5721944869,
        "x_max": 3147309.4861819297,
        "y_min": -3299614.6266644895,
        "y_max": -1528063.4525660723,
    },

    # GOES-19
    "4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8": {
        "shape": (882, 1217),
        "x_min": 712428.538085401,
        "x_max": 3149313.452072844,
        "y_min": -3283582.3662838787,
        "y_max": -1518043.6231115013,
    },
}
```

### Exemplo completo com cidades e fronteiras

```python
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature

NPZ_FILE = "dataset_goes/samples/2020/01/01/exemplo.npz"

GRID_INFO = {
    "44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876": {
        "x_min": 710424.5721944869,
        "x_max": 3147309.4861819297,
        "y_min": -3299614.6266644895,
        "y_max": -1528063.4525660723,
    },
    "4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8": {
        "x_min": 712428.538085401,
        "x_max": 3149313.452072844,
        "y_min": -3283582.3662838787,
        "y_max": -1518043.6231115013,
    },
}

CITIES = {
    "Londrina": (-51.1696, -23.3045),
    "Curitiba": (-49.2733, -25.4284),
    "Maringá": (-51.9333, -23.4205),
    "Cascavel": (-53.4552, -24.9555),
    "Foz do Iguaçu": (-54.5882, -25.5478),
    "Ponta Grossa": (-50.1619, -25.0950),
}

with np.load(NPZ_FILE, allow_pickle=False) as data:
    raw = data["cmi_c13_raw"].astype(np.float32)
    scale = np.asarray(data["scale_factor"]).item()
    offset = np.asarray(data["add_offset"]).item()
    fill = np.asarray(data["fill_value"]).item()

    grid_signature = np.asarray(data["grid_signature"]).item()
    if isinstance(grid_signature, bytes):
        grid_signature = grid_signature.decode("utf-8")

valid = raw != fill

temperature_k = np.full(raw.shape, np.nan, dtype=np.float32)
temperature_k[valid] = raw[valid] * scale + offset

temperature_c = temperature_k - 273.15

grid = GRID_INFO[str(grid_signature)]

satellite_crs = ccrs.Geostationary(
    central_longitude=-75.0,
    satellite_height=35786023.0,
    sweep_axis="x",
)

fig = plt.figure(figsize=(12, 9))
ax = plt.axes(projection=satellite_crs)

image = ax.imshow(
    temperature_c,
    origin="upper",
    extent=[
        grid["x_min"],
        grid["x_max"],
        grid["y_min"],
        grid["y_max"],
    ],
    transform=satellite_crs,
    cmap="gray_r",
    vmin=-80,
    vmax=40,
)

# Fronteiras entre países
ax.add_feature(
    cfeature.BORDERS.with_scale("10m"),
    linewidth=0.8,
)

# Limites administrativos de primeiro nível, como estados/províncias
ax.add_feature(
    cfeature.STATES.with_scale("10m"),
    linewidth=0.5,
)

# Cidades
for city, (lon, lat) in CITIES.items():
    ax.plot(
        lon,
        lat,
        marker="o",
        markersize=4,
        transform=ccrs.PlateCarree(),
    )

    ax.text(
        lon + 0.15,
        lat + 0.10,
        city,
        fontsize=8,
        transform=ccrs.PlateCarree(),
    )

# Área geral coberta pelo conjunto de dados
ax.set_extent(
    [-67.17, -43.17, -32.30, -14.30],
    crs=ccrs.PlateCarree(),
)

plt.colorbar(
    image,
    ax=ax,
    orientation="vertical",
    pad=0.02,
    label="Temperatura de brilho (°C)",
)

plt.title("GOES ABI Band 13 - cidades e limites territoriais")
plt.tight_layout()
plt.show()
```

Na primeira execução, o Cartopy pode baixar automaticamente arquivos do Natural Earth para desenhar fronteiras e limites administrativos.

---

## 9. Exemplo focado no Paraná

Depois de criar o mapa anterior, é possível limitar a visualização aproximadamente ao estado do Paraná usando:

```python
ax.set_extent(
    [-55.5, -47.5, -27.5, -22.0],
    crs=ccrs.PlateCarree(),
)
```

Isso não altera os dados do `.npz`; apenas modifica a região exibida no gráfico.

---

## 10. Cuidados importantes

### Horário

A coluna `time` está em horário local `America/Sao_Paulo`, enquanto os timestamps originais do GOES são UTC.

Não compare os dois horários diretamente sem considerar o fuso horário.

### Valores ausentes

Quando `image_link` é `NaN`, não existe imagem associada àquela linha dentro dos critérios de sincronização utilizados.

Em Python:

```python
if pd.isna(row["image_link"]):
    print("Esta linha não possui imagem associada.")
```

### Temperatura do canal 13

O canal 13 mede radiação infravermelha e seus valores podem ser representados como temperatura de brilho.

Essa temperatura **não é a mesma variável que `temperature_2m`** do CSV.

- `temperature_2m`: temperatura atmosférica próxima à superfície, derivada do conjunto meteorológico;
- Band 13: informação radiométrica infravermelha observada pelo satélite.

### Treinamento de modelos

Para treinamento de redes neurais, normalmente é melhor utilizar a matriz reconstruída diretamente, sem desenhar cidades, fronteiras, textos ou barras de cor sobre a imagem.

As marcações geográficas apresentadas neste README servem para inspeção, interpretação e criação de figuras.

---

## 11. Exemplo de preparação para aprendizado de máquina

Uma função simples para retornar a matriz de temperatura de brilho pode ser definida como:

```python
import numpy as np


def load_goes_temperature(npz_path):
    with np.load(npz_path, allow_pickle=False) as data:
        raw = data["cmi_c13_raw"].astype(np.float32)
        scale = np.asarray(data["scale_factor"]).item()
        offset = np.asarray(data["add_offset"]).item()
        fill = np.asarray(data["fill_value"]).item()

    valid = raw != fill

    values = np.full(raw.shape, np.nan, dtype=np.float32)
    values[valid] = raw[valid] * scale + offset

    return values - 273.15
```

Uso:

```python
image = load_goes_temperature("dataset_goes/samples/2020/01/01/exemplo.npz")
```

Antes de usar a matriz em uma rede neural, defina uma estratégia consistente para:

- pixels `NaN`;
- normalização;
- redimensionamento;
- recorte espacial;
- divisão treino/validação/teste.

Evite gerar PNG/JPEG como etapa intermediária quando o objetivo for treinamento. O `.npz` preserva os valores numéricos originais e é mais adequado para uso científico e aprendizado de máquina.

---

## 12. Dependências dos exemplos

Para leitura dos dados:

```bash
pip install numpy pandas
```

Para gerar imagens:

```bash
pip install matplotlib
```

Para mapas com cidades e fronteiras:

```bash
pip install cartopy
```

---

## 13. Resumo

O fluxo básico recomendado é:

```text
CSV
 │
 ├── time
 ├── variáveis meteorológicas
 └── image_link
          │
          ▼
       arquivo .npz
          │
          ├── cmi_c13_raw
          ├── scale_factor
          ├── add_offset
          ├── fill_value
          └── metadados GOES
          │
          ▼
 reconstrução dos valores físicos
          │
          ├── entrada para aprendizado de máquina
          └── visualização / mapas / cidades / fronteiras
```

O CSV é o índice principal do conjunto de dados. Para cada horário, ele fornece as variáveis meteorológicas e, quando disponível, o caminho da amostra GOES correspondente.
