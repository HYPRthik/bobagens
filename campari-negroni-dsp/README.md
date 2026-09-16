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

## PDVs — arquivo de última tentativa

`campari_pdvs_acima_75_notas.xlsx` não tem **nenhum endereço de rua**: só CNPJ,
Razão Social, Nome Fantasia, Município, UF e coordenada. Foram tentadas duas
saídas antes de recorrer ao nome:

1. Cruzar as coordenadas com as bases de endereço já processadas (JLR, cinemas,
   Mercado Livre — 5.521 coordenadas). **Zero casaram**: universo de POI diferente.
2. Puxar o endereço pelo CNPJ na base da Receita. **O proxy de saída bloqueia**
   as duas APIs públicas testadas.

`campari_pdvs.txt` tem então 66 linhas no formato `<Nome Fantasia> <Município>
<UF> Brazil`, geradas com `--nome-sem-endereco`:

```
SUPERMERCADO JVA JUNDIAI SP Brazil
EMPORIO PAVANELLI PIRACICABA SP Brazil
```

**Expectativa baixa.** A DSP só aceita POI pelo nome em Airports, Arena/Stadiums
e Universities/Colleges — supermercado não está na lista. As 70 linhas saem
marcadas ALTO. A favor: 65 dos 66 são nomes de estabelecimento reais, vários de
rede conhecida (GOOD BOM, JAU SERVE, TONIN); só um é pessoa física.

O caminho que funciona continua sendo endereço. `origem/pdvs_SEM_ENDERECO.csv`
traz os 70 PDVs (a linha TOTAL foi excluída) com coluna `ENDERECO_A_PREENCHER`.
Preenchido, é só rodar o mesmo comando sem a opção.

Três bares também ficaram de fora ou marcados, por limitação da origem:

- `Boteco Rita Maria` — o endereço é só `Florianópolis - SC`, descartado
- `Florianópolis (verificar endereço atual)` e `Porto Alegre (verificar endereço
  atual)` — o texto é literalmente esse
- `Bairro Cambuí, Campinas - SP` e `Região da Rua Bocaiúva` — bairro, não endereço

Fora esses, o risco ALTO é quase todo rodovia (6) e endereço sem número (12).
