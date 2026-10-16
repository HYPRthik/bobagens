# JLR OOH Amplifier RRS — faces JCDecaux (Out/Nov 26)

`upload/jlr_rrs_jcdecaux_nov26.txt` — **46 linhas** para 50 faces, ASCII, CRLF,
sem cabeçalho. Todas com rua + número + CEP da mesma rua.

## O cruzamento

As duas bases (`base_completa.csv` da plataforma e `roteiro.xlsx`) são **as
mesmas 50 faces, idênticas campo a campo** — nome, endereço, CEP, coordenada e
bairro. O CSV tem `formatted_address` vazio. O cruzamento confirma a base, mas
não acrescenta endereço: tudo vem do texto do roteiro.

## O que estava errado no roteiro

| Problema | Faces |
|---|---:|
| sem número de porta (`AV X, RUA Y, CANTEIRO CENTRAL`) | 28 |
| CEP de **outra rua** (transversal, ou trocado com outra face) | 18 |
| endereço a ~10 km da coordenada | 4 |

Em OOH a **coordenada é onde o painel está**; o texto descreve o cruzamento.
Por isso cada face foi resolvida contra a coordenada.

## Como cada face foi resolvida

**Número de porta**, nesta ordem:

| Origem | Faces |
|---|---:|
| número do próprio texto do roteiro | 22 |
| endereço **real** mais próximo do painel, na mesma rua ou numa transversal (bases de SP já processadas no repo, CEP conferido) | 25 |
| interpolado entre faces do roteiro com número na mesma avenida | 1 |
| início da faixa do CEP | 1 |
| inventado (`100`) | 1 |

Dois filtros evitam endereço real com coordenada errada:

- **Coerência com as âncoras do roteiro.** As 22 faces com número formam
  âncoras ao longo de Rebouças, Av. Brasil, Faria Lima, 23 de Maio e Hélio
  Pellegrino. Um vizinho cujo número contradiz essas âncoras é rejeitado —
  foi assim que "Rebouças **3970**" (coordenada errada na base de origem)
  virou **Rebouças 1822**, entre as faces 1384 e 2109.
- **Interpolação só dentro do trecho e com densidade plausível.** São Paulo
  numera por metro; âncoras que implicam 4 números/metro (23 de Maio, 615 e
  3101 a 600 m) são descartadas em vez de extrapoladas.

**CEP**: conferido contra o espelho aberto do OpenCEP. Tem de ser da mesma rua e,
havendo faixa, conter o número. Quando o da base não serve, busca-se o certo
(endereço real vizinho, CEP de outra face da própria base — pega CEP trocado
entre linhas — ou varredura do dataset). Resultado: **50 de 50 com CEP da mesma
rua**. Mediana entre o centroide do CEP e o painel: 280 m.

## As 4 faces com roteiro inconsistente

O endereço do texto fica a ~10 km da coordenada. O bairro do roteiro
(`Conurbation`) é um terceiro campo independente e desempata:

| Face | Texto | Bairro do roteiro | Decisão |
|---|---|---|---|
| MD-00428.01 | Av. Joaquina Ramalho (zona norte) | Jardim Paulistano | coordenada → Faria Lima 1478 |
| MD-00919.01 | Praça Trotadores (zona norte) | Bela Vista | coordenada → Faria Lima 1727 |
| MD-00670.01 | Av. Voluntários da Pátria (Santana) | Vila Nova Conceição | coordenada → Rua Bento de Andrade 483 |
| MD-00051.01 | Rua Melo Freire (Tatuapé) | Tatuapé | **texto** → Rua Melo Freire 100 (número inventado) |

**Vale confirmar essas 4 com quem montou o roteiro.**

## Faces que dividem uma linha

Quatro pares de faces próximas resolveram para o mesmo endereço real — daí 46
linhas para 50 faces:

| Linha | Faces |
|---|---|
| Rua Funchal 499 | MD-00414.20, MD-00415.01 |
| Av. Pres. Juscelino Kubitschek 2041 | MD-00409.01, MD-00412.01 |
| Av. Brig. Faria Lima 1478 | MD-00427.01, MD-00428.01 |
| Rua Sena Madureira 1355 | MD-00864.01, MD-00880.01 |

## Raio

Endereços tomados de um vizinho ficam até 300 m do painel (mediana ~100 m).
**Com raio de 300 m ou mais, toda face fica coberta**; abaixo disso, as faces
resolvidas por endereço vizinho a mais de 150 m (ver `origem_numero` na
conferência) podem ficar fora da cerca.

## Arquivos

| Arquivo | O quê |
|---|---|
| `upload/jlr_rrs_jcdecaux_nov26.txt` | upload da Yahoo |
| `upload/jlr_rrs_jcdecaux_nov26_conferencia.csv` | por face: linha gerada, origem do número, origem do CEP, distância ao painel, riscos |
| `gera.py` / `vizinhos.py` | geração reprodutível |
