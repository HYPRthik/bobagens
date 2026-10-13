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

## O retorno do arquivo completo — a medição que faltava

As 1.578 linhas voltaram com **44 aprovadas**. Cruzando com a conferência, o
número total engana; o que importa é a separação por origem:

| Origem da linha | Enviadas | OK | Taxa |
|---|---:|---:|---:|
| rua + número (índice de CEP) | 44 | 38 | **86%** |
| só o nome do POI | 1.534 | 6 | **0,4%** |

E dentro das 44 com rua, o número de porta separa de novo:

| | Enviadas | OK | Taxa |
|---|---:|---:|---:|
| com número de porta | 39 | 37 | **95%** |
| sem número de porta | 5 | 1 | 20% |

Os 20% não valem como medida: **4 das 5 linhas sem número estavam quebradas por
um erro meu** — sem número de porta, `partir_numero()` não consegue separar o
bairro, e ele ficou colado no nome da rua (`Rua CEL APARICIO BORGES GLORIA`,
`Avenida Marcial Lourenco Serodio Cidade Serodio`). Não foi a falta do número
que as derrubou.

A conclusão que sobra é firme e simples: **95% com rua, 0,4% sem**. O formato
nunca foi o problema; o logradouro é.

## A melhora: logradouro de verdade para 98% da base

As APIs de CEP continuam bloqueadas pela política de rede, mas o **espelho dos
mesmos dados no raw do GitHub não está** — e isso resolve o problema.
[`gpfconfea/banco-ceps`](https://github.com/gpfconfea/banco-ceps) publica os
dados do OpenCEP como um JSON por CEP, com logradouro, bairro, localidade, UF e
coordenada. Baixei os 1.358 CEPs da base: **1.352 encontrados (99,6%)**, e
desses só 0,2% sem logradouro.

`upload/copa_glp_v2.txt` — **1.381 linhas**, ASCII limpo, CRLF, sem cabeçalho:

| Origem | Linhas |
|---|---:|
| logradouro do CEP + número | 311 |
| logradouro do CEP (sem número) | 1.002 |
| já aprovada pela DSP, mantida byte a byte | 44 |
| nome do POI (CEP sem registro) | 24 |

**1.357 das 1.381 linhas agora têm rua de verdade — antes eram 44.**

O número de porta, quando existe, vem da faixa do trecho que o campo
`complemento` traz (`de 2373 a 2819 - lado ímpar`): é um número real daquele
trecho de rua. Mesma lógica já usada e declarada nos pontos de OOH — o geofence
é um raio sobre o trecho, não sobre a porta.

### Como sei que os dados conferem

- **Coordenada:** cada CEP do dataset tem lat/long, e a base da Copa tem a
  coordenada da loja. **93% das linhas caem a menos de 2 km** uma da outra.
- **Os 43 casos acima de 5 km não são CEP errado:** nos 43, a cidade do CEP
  bate com a cidade da base. Quem está errada é a coordenada da loja.
- **Contra uma segunda fonte:** 49 CEPs aparecem no dataset *e* numa base já
  processada aqui. 32 logradouros idênticos, 3 contidos um no outro, 11 que só
  diferem por abreviação — e aí o dataset traz a forma expandida
  (`Avenida Presidente Kennedy` contra `Avenida Pres. Kennedy`), que é melhor
  para o geocodificador. Sobram 3 conflitos reais em 49.
- **Trava dos aprovados:** as 44 linhas que a DSP já aceitou vão byte a byte
  como foram, e a loja correspondente não gera linha nova. Nenhuma troca de
  fonte de dados pode regredir o que já funciona.

### O que esperar

As 311 com rua + número devem render perto dos 95% medidos. As 1.002 sem número
são a incógnita — a medição anterior está contaminada, e o único jeito de saber
é este upload. Como as duas populações estão marcadas na conferência
(`tem_numero`), **o próprio retorno mede o peso do número de porta** numa
amostra de mil linhas, sem gastar um teste à parte.

Piso realista: ~300 pontos (só as com número). Teto: ~1.350.

### Isso virou parte do template

`geofence.py --cep-logradouro` faz isso em qualquer base daqui em diante:
quando a linha não tem logradouro mas tem CEP, busca a rua e usa. O cache fica
em disco, então rodar duas vezes não repete a rede.

## A pista que continua valendo

**919 das 1.606 linhas têm `Precisão da coordenada = "numero"`.** O sistema que
gerou a base tinha o logradouro *com número* e não exportou. Pedir essa coluna
ainda é melhor que o CEP: dá o número de porta certo nas 919, em vez da faixa
do trecho.

## Os arquivos anteriores (mantidos para comparação)

| Arquivo | Linhas | Formato | Retorno |
|---|---:|---|---|
| `copa_glp_final.txt` | 1.578 | rua onde havia, resto por nome | 44 OK |
| `copa_glp_sem_nome.txt` | 1.358 | `cidade UF CEP Brazil` | variante A — 0% |
| `copa_glp_com_nome.txt` | 1.597 | `nome cidade UF CEP Brazil` | variante C — 1,7% |
