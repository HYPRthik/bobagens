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
| Copa GLP — teste de formato | 4 formatos sem logradouro | 1 de 237 |

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

## Teste de formato — o que o retorno da DSP disse

`teste/teste_formatos.txt` subiu com **237 linhas: 4 formatos × as mesmas 60
lojas**, embaralhadas. `teste/retorno.csv` é o que a DSP devolveu.

| Variante | Formato | Enviadas | OK | Taxa | Motivos da recusa |
|---|---|---:|---:|---:|---|
| A | `cidade UF CEP Brazil` | 59 | 0 | 0% | Cannot match 33 · Incomplete 26 |
| B | `CEP cidade UF Brazil` | 59 | 0 | 0% | Cannot match 34 · Incomplete 25 |
| C | `nome cidade UF CEP Brazil` | 60 | **1** | **1,7%** | Cannot match 58 · Incomplete 1 |
| D | `cidade UF CEP-com-hífen Brazil` | 59 | 0 | 0% | **Incomplete 59 (100%)** |

A única que passou: `Vip Distribuidora 24 Horas Ltda Porto Alegre RS 90660080 Brazil`.

Dois aprendizados que valem para as próximas bases:

1. **O hífen no CEP quebra a linha inteira.** A variante D é a A com `14066-446`
   no lugar de `14066446` e foi de "Cannot match" (a DSP leu e não achou) para
   100% "Incomplete address" (a DSP nem leu). Isso confirma na prática a
   guideline da Yahoo sobre caracteres especiais — e explica por que o
   `ascii_puro()` do template remove o `-`. **Nunca mandar CEP hifenizado.**
2. **O nome ajuda o parser, não atrapalha.** Era o contrário da minha aposta
   registrada na versão anterior deste README. Com nome, 58 de 60 chegaram em
   "Cannot match full address" — ou seja, a DSP *parseou* a linha e só não achou
   o ponto. Sem nome, metade nem é parseada ("Incomplete address"). O nome não
   substitui o logradouro, mas é melhor que o vazio.

**O que o teste não salva:** nenhuma reordenação resolve. 1,7% na melhor
variante é ruído, não solução.

## O arquivo para subir

`upload/copa_glp_final.txt` — **1.578 linhas**, ASCII limpo, CRLF, sem
cabeçalho, dentro do limite de 10.000. Ele combina as duas únicas fontes de
endereço que existem:

| Origem | Linhas | Formato |
|---|---:|---|
| Logradouro vindo do índice de CEP | 44 | `rua número cidade UF CEP Brazil` |
| Só o nome do POI (sem logradouro) | 1.534 | `nome cidade UF CEP Brazil` |

As 44 saem de **68 lojas** da Copa cujo CEP *e* cidade batem com uma base já
processada; essas 68 ocupam só **44 CEPs distintos**, e como a linha gerada é
`rua cidade UF CEP`, lojas do mesmo CEP viram a mesma linha. O número da porta
vem de outro estabelecimento no mesmo CEP — mesmo trecho de rua, o que para um
geofence por raio é indiferente e é justamente o que torna o endereço
resolvível. Mesmo critério usado nos pontos de OOH.

`upload/copa_glp_final_conferencia.csv` liga cada linha à loja, ao CNPJ, ao CEP
e, quando houve, ao endereço que veio do índice.

**Expectativa honesta:** as 44 com rua devem passar na mesma faixa do Nissan
(~80%); as 1.534 por nome devem render ~1,7%, isto é, perto de 26 pontos. Total
realista: **60 a 70 de 1.578**. O arquivo está no melhor formato possível para o
dado que existe — o que falta não é formato, é a coluna de logradouro.

## Os arquivos anteriores (mantidos para comparação)

| Arquivo | Linhas | Formato | Teste |
|---|---:|---|---|
| `copa_glp_sem_nome.txt` | 1.358 | `cidade UF CEP Brazil` | variante A — 0% |
| `copa_glp_com_nome.txt` | 1.597 | `nome cidade UF CEP Brazil` | variante C — 1,7% |
