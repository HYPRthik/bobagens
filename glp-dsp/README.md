# Distribuidoras de Gás GLP Set/26 — Yahoo DSP

```bash
python3 ../geofence-yahoo/geofence.py origem_glp.csv -o upload --nome glp_distribuidoras
```

**3.579 endereços** de 3.622 distribuidoras (42 duplicatas, 1 descarte).
Cobertura nacional, 27 UFs — MG concentra 1.138, seguida de RS 372, BA 359 e GO 359.

Cabe num line item só (limite de 10.000). Se quiser separar, `--separar-por uf`
gera um arquivo por estado e `--separar-por bandeira_identificada` por bandeira —
embora 2.997 das 3.622 estejam como "Não identificada".

## Cabeçalho com colunas repetidas

Esta base traz `formatted_address`, `city`, `uf`, `cep`, `lat`, `storechain`,
`place_id` e `country` **duas vezes**, com conteúdo diferente. As duas versões do
endereço não coincidem em nenhuma das 3.622 linhas:

| | com número de porta | com `s/n` |
|---|---:|---:|
| 1ª coluna (Google) | 3.170 | 3 |
| 2ª coluna (bruta) | 53 | 52 |

A primeira é claramente melhor. Para `cep` e `city`, porém, a **segunda** tem mais
preenchimento. O mapeador passou a escolher, entre colunas do mesmo papel, a que
tem mais dados — antes ele pegava sempre a primeira.

## Cidade: mais 5 corrigidas

O mesmo defeito de sempre, agora na região metropolitana de Belo Horizonte: a
coluna diz "Belo Horizonte" para endereços que o CEP situa em Santa Luzia
(33xxx), Contagem (32235) e Ibirité (32404). Belo Horizonte (30000–31999) entrou
na tabela de faixas de capital, que agora tem São Paulo, Belo Horizonte, Belém,
Fortaleza e Cuiabá.

Um caso foi na direção oposta: CEP 30692 **é** Belo Horizonte, e ali a coluna
estava certa — o CEP confirma os dois sentidos.

Sobraram **6 divergências** em pares que não envolvem capital, fora do alcance da
tabela: Betim/Ibirité, Timóteo/Jaguaraçu, Mariana/Ouro Preto, Estrela/Bom Retiro
do Sul, Rio Grande/Pelotas e Sapucaia do Sul/Esteio. Estão marcadas no relatório
de risco, com a cidade da coluna mantida.

## Onde deve dar erro

471 ALTO: 420 sem número de porta, 65 rodovia, 21 logradouro sem nome.
Mais 823 MÉDIO, quase todos CEP genérico de cidade.
