# Mercado Livre 9.9 — OOH Set/26 (Rio de Janeiro)

```bash
python3 ../geofence-yahoo/geofence.py origem_ml_ooh.csv \
        -o upload --nome ml_99_ooh --separar-por Formato
```

**540 endereços** de 632 pontos de mídia (92 duplicatas removidas, zero descartes).
Todos no Rio — a coluna `Praça` tem um valor só.

Um arquivo por formato de mídia, já que cada um é uma audiência diferente:

| Formato | Pontos |
|---|---:|
| Tembici | 154 |
| Mix de Formatos | 99 |
| Mub Digital | 96 |
| Salões de Beleza | 64 |
| Banca Digital | 63 |
| Metrô | 28 |
| Shopping | 12 |
| demais (Aeroporto, Mega Painel, Topo de Pedágio) | 1 cada |

`ml_99_ooh.txt` tem os 540 juntos, se preferir um line item só.

## O que essa base tem de diferente

Inventário de OOH traz duas colunas que o `formatted_address` do Google não cobre:
`Endereço` (logradouro) e `Nº`. Elas salvaram 30 pontos onde o endereço principal
não tinha rua nenhuma:

```
Shopping Jardim Guadalupe, Guadalupe, Rio de Janeiro - RJ, 21515-001
   +  Endereço="Av. Brasil"  Nº="22155"
   ->  Avenida Brasil 22155 Rio de Janeiro RJ 21515001 Brazil
```

Mais 106 pontos ganharam o número de porta da coluna `Nº`.

A coluna `Endereço` descreve o ponto por referência visual, no padrão
`LOGRADOURO, E/F Nº 623, ESQUINA COM ...`. Fica o logradouro e o número de
referência — que é do mesmo quarteirão e serve de âncora para um raio:

```
RUA BARÃO DA TORRE, E/F Nº 623, ESQUINA COM RUA X  ->  RUA BARAO DA TORRE 623
AV RADIAL OESTE ENTRONCAMENTO COM AV OSWALDO ARANHA  ->  Avenida RADIAL OESTE
```

## Onde deve dar erro

247 ALTO, 33 MÉDIO em `ml_99_ooh_risco.csv`.

| Motivo | Qtd |
|---|---:|
| Sem número de porta | 228 |
| CEP genérico de cidade | 23 |
| Endereço de rodovia | 22 |

Os sem número são pontos que a origem não numera (estação de bike, banca, ponto
de metrô). 17 saíram sem CEP.

Depois do upload, passe o retorno da DSP em `--aprovados`.
