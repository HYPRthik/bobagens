# Copa Energia GLP (Out/13) — por que só 5 passaram, e o que fazer

## O diagnóstico

Esta base **não tem logradouro**: `formatted_address` está vazia nas 1.606
linhas. O que existe é nome, CNPJ, razão social, cidade, UF, CEP e coordenada.

O upload anterior usou `<nome> <cidade> <UF> <CEP>` e a DSP reconheceu **5 de
3.149**. Isso é consistente com tudo que ela já nos mostrou nesta campanha:

| Upload | Formato | Resultado |
|---|---|---:|
| POIs unificados | coordenadas | 0 de 2.424 |
| POIs unificados | 5 colunas com `Estado`/`POI` | 3 de 2.686 |
| Nissan | rua, número, cidade, UF, CEP | **162 de 202** |
| Copa GLP | nome, cidade, UF, CEP | 5 de 3.149 |

A diferença é sempre o **logradouro**. A própria mensagem de erro da DSP diz o
que ela procura: *"Check street address, city & postal code are correct"*.

## A pista que importa

**919 das 1.606 linhas têm `Precisão da coordenada = "numero"`.** Isso só é
possível se o sistema que gerou a base geocodificou até o número da porta — ou
seja, **ele tinha o logradouro** e não o exportou para `formatted_address`.

Pedir essa coluna a quem gera a base resolve o problema por inteiro. Foi o que
aconteceu no Campari: os PDVs saíram de 66 linhas por nome para 70 de 70 com
endereço de verdade.

## O que tentei antes de concluir isso

| Tentativa | Resultado |
|---|---|
| Cruzar coordenadas com as bases já processadas (17.121 pontos com endereço, incluindo 3.613 distribuidoras de GLP) | 24 lojas a menos de 60 m — **1%** |
| Índice CEP → logradouro montado das mesmas bases (11.000 CEPs) | 77 CEPs encontrados — **5%** |
| Consultar ViaCEP, BrasilAPI e OpenCEP | **bloqueados** pela política de rede da organização |

## Teste de formato — um upload resolve

`teste/teste_formatos.txt` tem **240 linhas: 4 formatos × as mesmas 60 lojas**,
embaralhadas. Suba esse arquivo e o retorno diz qual formato a DSP aceita sem
logradouro, se algum:

```
A   Ribeirao Preto SP 14066446 Brazil          <- sem nome, CEP no fim
B   14066446 Ribeirao Preto SP Brazil          <- CEP na frente
C   Fran Gas Ribeirao Preto SP 14066446 Brazil <- o formato dos 5 (controle)
D   Ribeirao Preto SP 14066-446 Brazil         <- CEP com hífen
```

`teste/teste_de_para.csv` liga cada linha à loja e ao formato. As 60 escolhidas
têm CEP específico e coordenada no número — se nem elas passarem, nenhuma passa.

A variante D desobedece a regra da DSP sobre hífen de propósito: o `-` só foi
testado em endereços **com** logradouro, onde 162 passaram. Vale descobrir se
ele ajuda quando o CEP é a única âncora.

## Os arquivos completos

| Arquivo | Linhas | Formato |
|---|---:|---|
| `copa_glp_sem_nome.txt` | 1.358 | `<cidade> <UF> <CEP> Brazil` |
| `copa_glp_com_nome.txt` | 1.597 | `<nome> <cidade> <UF> <CEP> Brazil` |

O sem-nome tem 1.358 e não 1.606 porque **a base tem 1.358 CEPs distintos**. Sem
logradouro e sem nome, a granularidade real do dado é o CEP: cada um é um trecho
de rua, e um geofence por raio cobre o trecho inteiro. As lojas que compartilham
CEP estão no mesmo trecho — `copa_glp_sem_nome_conferencia.csv` mostra quais
lojas caíram em cada linha.

Minha aposta é no sem-nome: o nome na frente faz a DSP tratar a linha como busca
de POI, que ela só aceita em Airports, Arena/Stadiums e Universities/Colleges.
Mas é aposta — o teste de formato é que responde.
