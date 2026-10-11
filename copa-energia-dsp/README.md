# Copa Energia D2C — Yahoo DSP

```bash
python3 preparar.py origem_copa_energia.csv
python3 ../geofence-yahoo/geofence.py preparado/glp.csv    -o upload --nome copa_glp    --nome-sem-endereco
python3 ../geofence-yahoo/geofence.py preparado/demais.csv -o upload --nome copa_demais --nome-sem-endereco
```

## Duas audiências

| | Origem | Únicos | Na audiência | Cidades |
|---|---:|---:|---:|---:|
| GLP — CNAE 47.84-9/00 | 3.169 | 3.149 | **3.149** | 40 |
| Demais CNAEs | 96.038 | 94.743 | **10.000** | 73 |

O grupo GLP cabe inteiro no teto. O outro não: 94.743 locais únicos em 73 cidades.

## A cota por cidade

Combinamos reduzir para uma audiência de 10.000 com cota igual por cidade. Uma
divisão simples (10.000 ÷ 73 = 136) desperdiçaria vagas, porque 9 cidades têm
menos que isso — Novo Gama tem 3 locais no total. A repartição usada entrega a
cidade pequena inteira e devolve a sobra para as demais:

| | |
|---|---:|
| Cidades na audiência | 73 (todas) |
| Cota máxima | 148 locais |
| Cidades no teto da cota | 43 |
| Menor | Novo Gama/GO, 3 (todos os que existem) |

Sem a cota, **Curitiba sozinha (10.211) consumiria a audiência inteira**.

Dentro de cada cidade, entra quem tem melhor sinal de geocodificação, nesta
ordem: CEP específico, coordenada no número, estabelecimento físico mais alto.
Funcionou — **96,5% da audiência tem CEP específico**, contra 91% na base de origem.

## A base não tem logradouro

Só `name`, `CNPJ`, `Razão social`, `city`, `uf`, `cep`, `lat`, `lng`. A coluna
`formatted_address` está **vazia nas 99.207 linhas**. A linha enviada é:

```
Flamagas Uberaba MG 38026380 Brazil
Fika Cozinha E Cafe Curitiba PR 80530030 Brazil
```

O CEP de 8 dígitos é o que aponta a rua, e **100% das linhas das duas audiências
têm CEP de 8 dígitos**. É um caso melhor que o do Ozempic e o do PDV do Campari,
que iam só com nome e município. Ainda assim, a DSP só aceita POI pelo nome em
Airports, Arena/Stadiums e Universities/Colleges, então tudo sai marcado ALTO.

Se chegar uma versão com `formatted_address` preenchido, é só rodar sem
`--nome-sem-endereco` — foi o que levou os PDVs do Campari de 66 por nome para
70 de 70 com endereço de verdade.

## Dois detalhes do preparo

**A coluna CNAE foi removida do arquivo entregue ao gerador.** Ela é texto longo
com dígitos e espaços, e o farejador de colunas a tomava por endereço — a
descrição da CNAE virava o endereço inteiro e `DE SUCOS E SIMILARES` virava
cidade. O detalhe completo ficou em `preparado/*_referencia.csv`.

**A deduplicação do preparo usa a mesma normalização do gerador.** Com chave
diferente, ele deduplicava de novo depois da cota e a audiência fechava abaixo
de 10.000.
