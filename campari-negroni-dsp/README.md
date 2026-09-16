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
| **Total (distintos)** | | **273** |

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

## O que ficou de fora

**`campari_pdvs_acima_75_notas.xlsx` não dá para subir.** Ele tem CNPJ, Razão
Social, Município, UF e coordenadas — mas **nenhum endereço de rua**. A DSP lê um
endereço por linha em texto livre, e PDV não está entre as categorias que podem
ir só com o nome (só Airports, Arena/Stadiums e Universities/Colleges).

`origem/pdvs_SEM_ENDERECO.csv` traz os 70 PDVs (a linha TOTAL foi excluída) com
uma coluna `ENDERECO_A_PREENCHER`. O caminho limpo é puxar o endereço pelo CNPJ
na base da Receita — tentei consultar daqui, mas o proxy de saída bloqueia. Com
o arquivo preenchido, é só rodar o mesmo comando.

Três bares também ficaram de fora ou marcados, por limitação da origem:

- `Boteco Rita Maria` — o endereço é só `Florianópolis - SC`, descartado
- `Florianópolis (verificar endereço atual)` e `Porto Alegre (verificar endereço
  atual)` — o texto é literalmente esse
- `Bairro Cambuí, Campinas - SP` e `Região da Rua Bocaiúva` — bairro, não endereço

Fora esses, o risco ALTO é quase todo rodovia (6) e endereço sem número (12).
