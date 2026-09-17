# Beleza SP-CE-MT-PA Set/26 — Yahoo DSP

```bash
python3 ../geofence-yahoo/geofence.py origem_beleza.csv -o upload --nome beleza --separar-por uf
```

**5.152 endereços** de 5.545 salões e lojas de beleza. Um arquivo por UF:

| UF | Endereços |
|---|---:|
| SP | 4.473 |
| CE | 371 |
| MT | 167 |
| PA | 141 |

347 duplicatas removidas e 46 descartes — esses 46 não têm `formatted_address`
nenhum na origem, só coordenada (`EMMA DIAS BRAIDS`, `THAUANE BEAUTY STUDIO`).
Estão em `beleza_descartados.csv`.

## O defeito de cidade, de novo — e agora generalizado

Mesmo problema das farmácias: a coluna `city` traz a **capital** para endereços
que estão num município vizinho. Aqui apareceu em Belém:

```
R. NOVA REPUBLICA  25 - ANANINDEUA - PA  67013-120
   coluna city = "Belém"      <- erro; 67xxx é Ananindeua, 66xxx é Belém
```

A regra do CEP, que antes só cobria a capital paulista, virou uma tabela de
faixas de capital. Só entram faixas conferidas — capital ausente da tabela
significa "não sei arbitrar", não "a coluna está certa":

| Capital | Faixa de CEP |
|---|---|
| São Paulo | 01000–05999, 08000–08499 |
| Belém | 66000–66999 |
| Fortaleza | 60000–60999 |
| Cuiabá | 78000–78109 |

Isso corrigiu 2 endereços em Ananindeua aqui e 1 em Caucaia na base de farmácias.

Sobraram **3 divergências** de 5.499, todas sem CEP na origem — nada pode
arbitrar. Duas são ruído do extrator (`CEP`, `EM FRENTE AO COLÉGIO DAS FLERAS`)
e uma é um provável Taboão da Serra. Estão marcadas no relatório de risco.

Uma linha da origem vem com mojibake (`BELÃ©M` no lugar de `BELÉM`) — é uma só,
e como a coluna diz Belém corretamente, o endereço saiu certo.

## Onde deve dar erro

478 ALTO: 366 sem número de porta, 127 rodovia, 9 logradouro sem nome.
Mais 1.047 MÉDIO, quase todos CEP genérico de cidade.
