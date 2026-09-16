# SOMPO / Eletromidia — PROSPECTS e BROKERS para a Yahoo DSP

```bash
python3 ../geofence-yahoo/geofence.py origem/prospects.csv -o upload --nome sompo_prospects
python3 ../geofence-yahoo/geofence.py origem/brokers.csv   -o upload --nome sompo_brokers
```

Duas audiências separadas, uma por aba da planilha.

| Audiência | Telas na origem | Endereços no upload |
|---|---:|---:|
| Prospects | 37 | 37 |
| Brokers | 18 | 6 |

Zero descartes e **zero endereços de risco ALTO** nas duas — é inventário de
edifício comercial em São Paulo, com logradouro, número, bairro e CEP em colunas
próprias. A melhor qualidade de origem de todas as bases desta pasta.

## Brokers: 18 telas, 6 endereços

O colapso é correto. As telas se repetem no mesmo complexo, e um geofence por
raio cobre o prédio inteiro — a DSP também não aceita o mesmo endereço duas vezes:

| Endereço | Telas |
|---|---:|
| Avenida das Nações Unidas 14401 (Parque da Cidade) | 9 |
| Avenida das Nações Unidas 14171 (Rochaverá) | 5 |
| demais | 1 cada |

Prospects não tem repetição: 37 telas em 37 endereços.

## Inteiro lido como float

A coluna `Numero` vem do Excel como `1842.0`. Convertido direto, o ponto virava
espaço e o número se partia (`Avenida Paulista 1842 0`). A conversão da planilha
já grava inteiro, e o `geofence.py` passou a tolerar `.0` e `.00` caso a origem
venha como CSV exportado do Excel.
