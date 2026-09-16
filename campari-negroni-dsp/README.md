# Campari Negroni Week Set/26 — audiências para a Yahoo DSP

```bash
for n in consistencia desenvolvimento mb_consistencia mb_desenvolvimento; do
  python3 ../geofence-yahoo/geofence.py "origem/$n.csv" -o upload --nome "campari_$n"
done
```

## Quatro listas prontas

| Audiência | Bares na origem | Endereços no upload |
|---|---:|---:|
| Consistência | 151 | 150 |
| Desenvolvimento | 54 | 54 |
| MB Consistência | 52 | 51 |
| MB Desenvolvimento | 19 | 18 |
| PDVs | 70 | 70 |
| **Total (distintos)** | | **343** |

`campari_todas.txt` junta as quatro, se preferir um line item só.

Qualidade bem melhor que as bases anteriores: 21 de 273 marcados ALTO, contra
~30% nas listas de POI. São listas curadas, com endereço completo.

## Um número de porta que estava sendo destruído

Quatro endereços vinham com ponto de milhar no número — `Alameda Franca, 1.151`.
O ponto era removido junto com a pontuação e o número virava **dois**:

```
Alameda Franca, 1.151, 1º andar   ->  Alameda Franca 1 151   (errado)
                                  ->  Alameda Franca 1151    (corrigido)
```

Afetava `Alameda Franca 1.151`, `Rua Joaquim Antunes 1.026`, `Avenida Paulista
2.584` e `Av. Amazonas 1.049`. Agora o número é normalizado antes de qualquer
corte de pontuação, o que também faz o bairro voltar a ser descartado
corretamente nessas linhas.

Também trata `nº 2153`, onde o símbolo some ao virar ASCII e deixa um `n` colado
ao número. A regra exige o `º`/`°` de propósito — um `n` solto pode ser nome de rua.

## PDVs — resolvido

A base completa (`origem/pdvs_base_completa.csv`) trouxe `formatted_address`, e os
**70 PDVs saíram**, contra 66 por nome na tentativa anterior.

Dois não têm rua na origem (`Barretos, SP, Brasil` e `Ibitinga, SP, Brasil`);
esses dois usam `--nome-sem-endereco` e vão identificados pela Razão Social,
marcados ALTO. Os outros 68 têm endereço de verdade.

O `formatted_address` vinha com POI vizinho errado no início em sete linhas — o
geocodificador pegou o estabelecimento ao lado. O corte de nome resolve:

```
SUBWAY, Avenida Parada Pinto, 2262, ...       ->  Avenida Parada Pinto 2262 ...
BURGER KING, Avenida Luis Stamatis, 431, ...  ->  Avenida Luis Stamatis 431 ...
Banco 24horas, Avenida Presidente Vargas, ... ->  Avenida Presidente Vargas ...
```

Risco: 28 ALTO, quase todo endereço sem número de porta (25).

