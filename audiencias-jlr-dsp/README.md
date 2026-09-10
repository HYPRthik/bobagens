# Audiências JLR — 11 categorias formatadas para a Yahoo DSP

```bash
python3 juntar.py                                    # resolve coordenada -> endereço
for f in enriquecido/*.csv; do                       # gera os arquivos de upload
  python3 ../geofence-yahoo/geofence.py "$f" -o upload --nome "jlr_$(basename $f .csv)"
done
```

## O problema

As 11 planilhas do zip têm **só coordenadas** (`lat,lon,0.3`), sem endereço — o
mesmo formato que a DSP rejeitou nas tentativas anteriores. O geofencing lê
**um endereço por linha** em texto livre; coordenada não geocodifica em nada.

A saída: cruzar cada coordenada com a base de endereços que você já enviou
(`../pois-jlr-dsp/origem_pois_completa.csv`). Isso resolve **79%** dos pontos.

## Resultado

| Audiência | Pontos no zip | Com endereço | Endereços no upload |
|---|---:|---:|---:|
| Bancos | 1.199 | 942 | 932 |
| Joalherias | 490 | 374 | 354 |
| Helipontos | 329 | 254 | 236 |
| Concessionárias | 315 | 243 | 240 |
| Marinas | 264 | 187 | 181 |
| Restaurantes | 226 | 202 | 199 |
| Clubes | 175 | 143 | 138 |
| GolfClubs | 54 | 47 | 47 |
| Shoppings | 25 | 21 | 20 |
| Decor | 15 | 14 | 13 |
| Resorts | 10 | 10 | 10 |
| **Total** | **3.102** | **2.437** | **2.370** |

A última coluna é menor que a do meio porque o geofence.py ainda remove
duplicatas de endereço — dois POIs no mesmo prédio viram um geofence só.

`jlr_todas_audiencias.txt` junta as 11 em 2.342 endereços distintos, se preferir
um line item só.

## Os 665 que ficaram de fora

`upload/SEM_ENDERECO_consolidado.csv` lista todos, por audiência. São
coordenadas que não existem na base de endereços — Bancos concentra 257 deles.

Para recuperá-los é preciso um export dessas categorias **com endereço**, como o
que você mandou para os POIs unificados. Só coordenada não sobe.

## Dois consertos na leitura da origem

**Coordenada corrompida por locale de vírgula decimal.** Uma linha de Decor vinha
como `-23.531.969,-46.715.334`. As duas leituras possíveis (`-2.35,-46.72` e
`-23.53,-46.72`) caem dentro do Brasil, então a bounding box não desempata. Vence
a que fica mais perto da mediana dos outros pontos da mesma audiência — no caso,
São Paulo, junto com as outras 14 lojas de decoração da Alameda Gabriel Monteiro
da Silva.

**Helipontos** vem com `;;;` no fim de cada linha; a leitura tolera isso.

Duas linhas de Restaurantes são `,,0.3` — sem coordenada nenhuma, nada a recuperar.

## Conteúdo

- `origem/` — as 11 planilhas do zip, como vieram
- `juntar.py` — cruza coordenada com a base de endereços
- `enriquecido/` — CSV por categoria com o endereço resolvido, mais os `_sem_endereco`
- `upload/` — os arquivos prontos para a DSP, com conferência e risco por audiência
