# POIs Unificados JLR — arquivos de geofencing para a Yahoo DSP

Gerado de `origem_pois_completa.csv` pelo template em `../geofence-yahoo/`:

```bash
python3 ../geofence-yahoo/geofence.py origem_pois_completa.csv \
        -o upload --nome pois_jlr --separar-por POI
```

## O que saiu

| Arquivo | Endereços |
|---|---:|
| `pois_jlr.txt` — todos | 2.343 |
| `pois_jlr_bancos.txt` | 933 |
| `pois_jlr_joalherias.txt` | 354 |
| `pois_jlr_concessionarias.txt` | 240 |
| `pois_jlr_helipontos.txt` | 236 |
| `pois_jlr_restaurantes.txt` | 199 |
| `pois_jlr_marinas.txt` | 181 |
| `pois_jlr_clubes.txt` | 138 |
| `pois_jlr_golf_clubs.txt` | 47 |
| `pois_jlr_shoppings.txt` | 20 |
| `pois_jlr_decor.txt` | 13 |
| `pois_jlr_resorts.txt` | 10 |

De 2.686 linhas de origem: 316 duplicatas removidas, 29 descartadas por não terem
endereço (só `Cidade, UF, Brasil`), restando 2.343. Todos ASCII puro, um endereço
por linha, dentro do limite de 10.000.

## Transformações aplicadas

| | |
|---|---:|
| Bairro descartado | 1.590 |
| Nome do estabelecimento cortado do início | 689 |
| Acentos e hífens removidos | todos |

```
Churrascaria Ponteio Mogi das Cruzes, Avenida Francisco Ferreira Lopes, 460,
Centro, Mogi das Cruzes - SP, 08710-000, Brasil
   ->  Avenida Francisco Ferreira Lopes 460 Mogi das Cruzes SP 08710000 Brazil
```

## Onde deve dar erro

`pois_jlr_risco.csv` marca 801 endereços ALTO e 449 MÉDIO.

| Motivo | Qtd | Observação |
|---|---:|---|
| Sem número de porta | 745 | **A origem não tem o número** — o Google não devolveu. Não é perda do script: conferido linha a linha, 745 dos 745 já vinham sem número |
| CEP genérico de cidade | 211 | Termina em `000`; 2,4x mais falha |
| Endereço de rodovia | 138 | 57–67% falharam no teste do Nissan |
| Logradouro sem nome | 38 | Origem quebrada, ex.: `62, Itaipava, Petrópolis - RJ` |

124 endereços saíram sem CEP porque a origem não tinha.

O teste do Nissan sugere ~20% de falha em lista não calibrada. Depois deste
upload, passe o arquivo de retorno da DSP em `--aprovados` para reenviar sem
alteração tudo o que passou e reescrever só o que falhou.
