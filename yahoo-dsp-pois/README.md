# POIs Unificados HYPR/JLR — arquivos de geofencing para a Yahoo DSP

## O que aconteceu no upload original

O arquivo `HYPR_JLR_POIs_Unificados_2.xlsx` foi enviado no campo de upload por
**endereço** da DSP (o relatório de retorno se chama `line4353189geofencing`**`addresslist`**`.csv`).
Esse campo geocodifica texto — ele nunca leu as coordenadas.

Das 2.686 linhas: **3 foram aceitas**, 2.170 falharam e **513 sumiram sem aparecer no relatório**.

Duas evidências de que o problema é o campo de upload, não os dados:

1. A própria linha de **cabeçalho** (`Latitude,Longitude,Radius Distance,Estado,POI`)
   voltou marcada como `successful` — a DSP geocodificou o texto do cabeçalho como
   se fosse um endereço.
2. O motivo do erro acompanha exatamente a coluna `Estado`, que a DSP leu como o
   campo "state" de um endereço:

   | Estado          | Erro retornado                | Linhas |
   |-----------------|-------------------------------|-------:|
   | `SP` (UF válida)| `Incomplete address`          | 1.030 |
   | `Demais Praças` | `Unknown error`               | 1.021 |
   | `Demais Praças` | `Cannot match full address`   |   119 |

Os 3 "successful" foram coincidência de geocodificação, não acerto de coordenada.

**As coordenadas estão corretas.** As 2.686 são válidas e caem dentro do Brasil.

## O que fazer

Subir os arquivos abaixo no campo de **latitude/longitude** da DSP, não no de endereço.

| Arquivo | Geofences |
|---|---:|
| `upload/pois_unificados_TODOS.csv` | 2.424 |
| `por_estado/sp.csv` | 1.016 |
| `por_estado/demais_pracas.csv` | 1.408 |
| `por_poi/*.csv` (11 categorias) | 2.436 |

Os arquivos por POI somam 2.436 porque 12 coordenadas pertencem a duas categorias
(ex.: um clube que também é golf club). Cada lista de targeting é independente, então
elas aparecem nas duas — mas só uma vez no arquivo único, que não aceita geofence repetido.

## Limpeza aplicada

1. **Cabeçalho removido** — a DSP lê a primeira linha como dado.
2. **Colunas `Estado` e `POI` retiradas** do upload — viravam campos de endereço.
   A segmentação foi preservada nos arquivos separados por estado e por categoria.
3. **Duplicatas removidas** — 2.686 → 2.424 coordenadas distintas.
4. **Coordenadas arredondadas para 6 casas** (~11 cm), eliminando ruído de float
   (`-46,72234770000001` → `-46,722348`).
5. **Formato**: 3 colunas, ASCII, quebra de linha CRLF.

## Atenção: unidade do raio

O valor `0,3` foi mantido como estava. Confirme a unidade no painel da DSP — se ela
interpretar em **milhas**, 0,3 vira **483 m** em vez dos 300 m pretendidos.

## Arquivos

- `HYPR_JLR_POIs_Unificados_LIMPO.xlsx` — planilha de referência (LEIA-ME, base completa
  com Estado/POI, e resumo por categoria). **Não é o arquivo de upload.**
- `build.py` — regenera tudo a partir da planilha de origem, com validação.
  `python3 build.py origem_pois_unificados.csv`
- `origem_pois_unificados.csv` — export original, para rastreabilidade.
