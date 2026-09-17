# Ozempic — lojas com 3+ notas fiscais · Yahoo DSP

```bash
python3 juntar.py                                   # cruza coordenada com as bases desta pasta
python3 ../geofence-yahoo/geofence.py enriquecido/ozempic.csv \
        -o upload --nome ozempic --nome-sem-endereco
```

## A planilha não tem endereço

Apesar do `enderecos` no nome do arquivo, as colunas são CNPJ, Razão Social,
Nome Fantasia, Rede, Município, UF, Latitude, Longitude e métricas de venda.
**Nenhum logradouro.** É a mesma situação do PDV do Campari, que só se resolveu
quando veio a base com `formatted_address`.

São 42 lojas (a linha TOTAL e o rodapé da planilha ficaram de fora; o cabeçalho
está na linha 4, depois do título e da fonte).

## O que deu para recuperar

Cruzei as coordenadas com as bases de endereço já processadas nesta pasta —
13.556 pontos, incluindo as 2.003 farmácias de SP-CE-MT-PA. **3 lojas casaram:**

| Loja | Distância | Endereço |
|---|---:|---|
| DROGASIL RUA AUGUSTA | 2 m | R. Augusta 2899, Cerqueira César |
| DROGASIL PAMPLONA | 5 m | R. Pamplona 1792, Jardim Paulista |
| DROGARIA SÃO GERALDO | 13 m | R. Caraíbas 600, Perdizes |

O casamento exige **distância curta e termo próprio em comum no nome**. Perto de
uma farmácia costuma haver outra, e colar o endereço do vizinho é pior que não
ter endereço. Três candidatos foram rejeitados por isso:

```
DROGARIA PENAMAR      x  "FARMACIA"     34 m  -> nome genérico, não prova nada
DROGA DEZ CAMPOS SALES x  (sem nome)    54 m  -> rua diferente (Francisco Glicério)
DROGAL JARDIM         x  (sem nome)     38 m  -> sem nome para conferir
```

"Drogasil" conta como termo próprio; "drogaria" e "farmácia", não.

## As outras 39

Vão pelo nome do POI + município, com `--nome-sem-endereco`:

```
FARMACIA CENTRAL SAO JOSE DO RIO PRETO SP Brazil
DROGARIA SANTA RITA DE OLIMPIA OLIMPIA SP Brazil
```

**Expectativa baixa**, e todas saem marcadas ALTO: a DSP só aceita POI pelo nome
em Airports, Arena/Stadiums e Universities/Colleges. Farmácia não está na lista.

`enriquecido/ozempic_SEM_ENDERECO.csv` traz as 39 com coluna
`ENDERECO_A_PREENCHER`. Preenchido, é só rodar sem a opção — foi o que resolveu
o caso do Campari.
