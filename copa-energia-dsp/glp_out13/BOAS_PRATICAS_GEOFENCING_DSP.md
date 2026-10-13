# Geofencing na Yahoo DSP — o que aumenta a taxa de aprovação

Especificação de implementação, escrita a partir de **7 uploads reais** e dos
arquivos de retorno da própria DSP. Todo número aqui é medido, não estimado.

---

> ## ⚠️ Leia isto antes de implementar o passo 3.5
>
> Em várias partes deste documento aparece o número de porta **`100`**. Ele é
> **inventado**. Não é o número da loja, não foi extraído de lugar nenhum e não
> tem relação com o endereço real do POI.
>
> Ele existe por um motivo só: a DSP **rejeita rua sem número de porta** (1
> aprovação em 1.026 linhas testadas). Quando a base não traz o número, escrever
> `100` faz o geocodificador ancorar em *algum ponto da rua certa, dentro do CEP
> certo* — erro mediano de **170 m** em relação à loja — em vez de rejeitar a
> linha inteira.
>
> **É um último recurso, não o caminho principal.** Se vocês conseguem o número
> real (via CNPJ na Receita ou geocodificação reversa da coordenada), usem o
> real: vale **80% contra 73%**, sem dado sintético e sem o erro de posição.
>
> Se implementarem o `100`, implementem junto: flag opt-in, coluna no relatório
> marcando a linha como sintética, e visibilidade para quem sobe a campanha.

---

## 1. O problema, em uma frase

O campo de geofencing da DSP **não é uma planilha de colunas**. Ele recebe uma
linha de texto livre por POI e manda essa linha inteira para um geocodificador.
A mensagem de erro da própria DSP diz o que ele procura:

> `Cannot match full address. Check street address, city & postal code are correct`

Logo: **rua, número, cidade e CEP**. Qualquer outra coisa na linha é ruído, e o
que falta não é compensável por formatação.

---

## 2. A escada de resultados

Tudo medido em retorno real da DSP. É esta tabela que justifica cada regra do
pipeline:

| O que a linha continha | Enviadas | Aprovadas | Taxa |
|---|---:|---:|---:|
| rua + **número real da loja** + cidade + UF + CEP | 202 | 162 | **80%** |
| rua + **número inventado `100`** + cidade + UF + CEP | 251 | 183 | **73%** |
| rua + número `100` + **bairro** + cidade + UF + CEP | 250 | 176 | 70% |
| rua + **número do início da faixa do CEP** + cidade + UF + CEP | 311 | 188 | 61% |
| rua + número inventado `1` + cidade + UF + CEP | 250 | 74 | 30% |
| rua + número real + bairro (relançadas após falha) | 123 | 15 | 12% |
| nome do POI + cidade + UF + CEP | 1.534 | 6 | 0,4% |
| rua + **bairro, sem número** | 250 | 3 | 1,2% |
| rua + cidade + UF + CEP, **sem número** | 1.002 | 1 | **0,1%** |
| cidade + UF + CEP (sem rua) | 59 | 0 | 0% |
| CEP + cidade + UF (sem rua) | 59 | 0 | 0% |
| CEP **com hífen**, sem rua | 59 | 0 | 0% |
| latitude/longitude | 2.424 | 0 | **0%** |
| planilha de 5 colunas (`Estado`, `POI`, etc.) | 2.686 | 3 | 0,1% |

**As três leituras que importam:**

1. **Sem logradouro, nada funciona.** Nenhuma reordenação, nenhum campo extra.
2. **Sem número de porta, quase nada funciona** — 1 em 1.026. O número não é
   detalhe, é requisito.
3. **Coordenada não é aceita.** 0 de 2.424. Se a plataforma hoje exporta
   lat/long para este campo, está exportando lixo.

Aplicando isso numa base de 1.606 lojas que chegou **sem nenhum logradouro**, a
taxa saiu de **5 aprovados para mais de 1.000**.

---

## 3. O pipeline

Ordem importa. Cada passo depende do anterior.

### 3.1 Formato do arquivo

| Regra | Valor |
|---|---|
| Formato | TXT ou CSV |
| Conteúdo | **um endereço por linha**, sem cabeçalho |
| Quebra de linha | CRLF (`\r\n`) |
| Encoding | ASCII puro |
| Limite | **10.000 endereços** por arquivo e por line item |

### 3.2 Normalização para ASCII

A DSP documenta que caracteres especiais podem dar erro (`é`, `à`, `ç`, `#`,
`-`). **Isso foi confirmado na prática e o efeito é total**: as mesmas 59 linhas
com `14066-446` deram **100% `Incomplete address`**; com `14066446` deram
`Cannot match` — ou seja, com hífen a DSP **nem chega a parsear** a linha.

```python
def ascii_puro(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
```

Atenção: normalize com **NFKD antes** de remover. Remover o byte acentuado
direto transforma `São Paulo` em `So Paulo`.

### 3.3 A forma essencial da linha

```
<logradouro> <número> <cidade> <UF> <CEP sem hífen> Brazil
```

Nada além disso. Em particular:

- **Descarte o bairro.** Ele não é pedido e colide com nome de cidade:
  `Av Lacerda Agostinho 300 Botafogo Macae RJ` ancora em Botafogo/Rio, não em
  Macaé. Medido: com bairro 70%, sem bairro 73%.
- **Descarte o raio.** Não é campo de endereço.
- **Descarte complemento, loja, piso, sala.** `LOJA 3004`, `PISO 2`, `SALA 15`
  não são endereçáveis — o geofence é um raio na rua.

### 3.4 Quando falta o logradouro: resolver pelo CEP

Base sem `formatted_address` é comum. O CEP resolve quase tudo:

```
CEP → { logradouro, complemento, bairro, localidade, uf, lat, lng }
```

Numa base de 1.358 CEPs distintos, **1.352 tiveram registro (99,6%)** e desses
só **0,2%** vieram sem logradouro.

Fontes: ViaCEP, BrasilAPI, OpenCEP. **Cacheie o resultado** — CEP não muda e a
mesma base é reprocessada várias vezes.

### 3.5 Quando falta o número de porta: injetar `100` (último recurso)

**O `100` não é o número da loja — é um número arbitrário.** A base não traz o
número de porta desses POIs e não há de onde extraí-lo; o que se sabe é a rua
(vinda do CEP) e o CEP. Exemplo real, aprovado pela DSP:

```
base  : loja "Macedo E Souza Comercio Varejista De Glp", CEP 06310320
          -> Rua Miguel Barbar, Carapicuíba/SP     (número: ausente)
sobe  : Rua Miguel Barbar 100 Carapicuiba SP 06310320 Brazil
ancora: no nº 100 dessa rua — a loja pode estar no 847
```

Este é o passo que mais move a taxa, e o resultado é contraintuitivo:

| Número usado | Taxa |
|---|---:|
| número real da loja | 80% |
| **`100` inventado** | **73%** |
| início da faixa do CEP (`de 2373 a 2819` → `2373`) | 61% |
| `1` inventado | 30% |
| nenhum | 0,1% |

**O `100` inventado bate o número real tirado da faixa do CEP.** A explicação:
um número baixo existe em praticamente toda rua, enquanto o início da faixa cai
num limite de trecho que o geocodificador não resolve. E o valor importa — `1`
rende menos da metade de `100`.

**O que isso custa.** O ponto não cai na porta da loja. Medindo a distância
entre a coordenada do CEP e a coordenada real da loja nas linhas aprovadas
com número inventado (426 após excluir 7 lojas de coordenada comprovadamente errada):

| | |
|---|---:|
| mediana | **170 m** |
| média | 500 m |

### O raio do geofence decide se isso serve

O `100` cumpre a **função sintática** do número de porta — faz a DSP aceitar a
linha. Não cumpre a **função de localização**: o ponto cai na rua certa, dentro
do CEP certo, mas não na porta da loja.

Logo, se o ponto sintético cobre ou não a loja depende do raio da campanha.
Medido nas 426 linhas aprovadas com número inventado (426 após excluir 7 lojas de coordenada comprovadamente errada):

| Raio do geofence | Loja dentro do próprio geofence |
|---:|---:|
| 100 m | **37%** |
| 200 m | 55% |
| 300 m | 68% |
| 500 m | **83%** |
| 1.000 m | 94% |

**Abaixo de 300 m de raio, o número inventado não substitui o real** — mais de
um terço das lojas fica fora da própria cerca. De 500 m para cima ele se
comporta perto do número verdadeiro.

> Ressalva de método: a distância medida é entre a coordenada do CEP e a
> coordenada da loja. Ela é um *proxy* de onde o geocodificador ancora o
> "número 100", não a medida direta. Serve para dimensionar a ordem de
> grandeza, não para auditar linha a linha.

**E é dado inventado** — deixe explícito: flag opt-in, coluna no relatório
marcando quais linhas receberam número sintético, e a decisão de usar ou não
fica com quem sobe a campanha.

### 3.6 Deduplicar pela linha final

Duas lojas no mesmo CEP sem número geram a mesma linha. Isso é correto — um
geofence por raio cobre o trecho inteiro — mas precisa ser deduplicado, senão
o arquivo estoura o limite sem necessidade. **Deduplique pela string final já
normalizada**, não pelo endereço de origem.

### 3.7 Trava dos aprovados

O retorno da DSP traz `successful` / `failed` por linha. **Reenvie as linhas
aprovadas byte a byte**, sem passar pelo pipeline de novo, e só reprocesse as
que falharam.

Isso é o que impede que uma melhoria no parser regrida o que já funcionava.
Medido em 3 uploads seguidos: **100% das linhas travadas voltaram aprovadas**
(44/44, depois 233/233).

### 3.8 Categorias isentas

Só **Airports, Arena/Stadiums e Universities/Colleges** podem ser enviados pelo
nome do POI. Para qualquer outra categoria, nome sem endereço rende **0,4%** —
não é alternativa, é desperdício de linha.

---

## 4. Regras de parsing que mudaram o resultado

Cada uma destas saiu de um erro real que derrubou endereços válidos.

| Caso | Regra |
|---|---|
| **Coluna `Nº` que é índice** | Se a coluna de número é a numeração da planilha (1..N densa), ignore. Senão você injeta `1`, `2`, `3`… como número de porta em toda a base |
| **Sigla de rodovia** | `Rodovia BR 101 5599` — o número da porta é `5599`, não o `101` da sigla. Não pegue o primeiro número da linha |
| **Número no nome da rua** | `Avenida 2 de Agosto 352` — porta é `352`. Exija que o número não seja seguido de conectivo (`de`, `da`, `do`) |
| **Ponto de milhar** | `Alameda Franca, 1.151` → `1151`, não `1 151` |
| **Float do Excel** | `Numero = 1842.0` → `1842`, não `1842 0` |
| **Vírgula decimal** | `km 83,5` não pode virar um segmento solto `5` |
| **`nº 2153`** | Vire `2153`, mas **exija o `º`/`°`** — um `n` solto pode ser nome de rua |
| **Nome do estabelecimento antes da rua** | Use o segmento só-número como âncora: o logradouro é o segmento anterior. Nunca corte se isso apagaria uma rua que tem número |
| **Bairro colado quando não há número** | Sem número de porta não dá para separar o bairro do fim do logradouro. Se o bairro vier em campo próprio, use o campo — não tente cortar da string |
| **Abreviações** | Expanda: `Av`→`Avenida`, `Rod`→`Rodovia`, `Dr.`→`Doutor`, `Pres.`→`Presidente`. A forma expandida geocodifica melhor |
| **Colunas repetidas no cabeçalho** | Entre duas colunas do mesmo papel, vença a **mais preenchida** (`name` vazio não pode bloquear `Nome Fantasia`) |

### O CEP arbitra a cidade

Nem a coluna `cidade` nem o texto do endereço são confiáveis sozinhos. No slot
de cidade costuma vir **bairro**. Use a faixa do CEP para decidir:

- `INTERLAGOS - SP` com CEP 04xxx → é bairro, a coluna vence
- `OSASCO - SP` com CEP 06020 → é município, o texto vence
- `ANANINDEUA` com CEP 67xxx → desmente a coluna que diz Belém

E abreviação não conta como divergência: `PRES. PRUDENTE` é `Presidente
Prudente`.

---

## 5. O que não funciona — não gaste tempo

| Tentativa | Resultado |
|---|---|
| Mandar latitude/longitude | 0 de 2.424 |
| Mandar planilha de colunas | 3 de 2.686 |
| Mandar nome do POI sem endereço | 0,4% |
| Reordenar os campos (CEP na frente, etc.) | 0% em todas as ordens testadas |
| CEP com hífen | 0%, e pior: a DSP nem parseia |
| Adicionar bairro para compensar a falta de número | 1,2% |
| Adicionar bairro em linhas que já falharam | 12% |

---

## 6. O que vocês podem fazer melhor que este trabalho

Três coisas foram limitadas pelo ambiente onde isto rodou, não pelo método:

1. **Número de porta real em vez de `100`.** A base tinha CNPJ das 1.606 lojas,
   e o cadastro da Receita traz logradouro e número exatos. Eu não consegui
   acesso de rede a nenhuma fonte de CNPJ. **A plataforma de vocês consegue** —
   e o número real vale **80% contra 73%**, sem nenhum dado inventado e sem os
   erro de posição mediano de 170 m.

2. **Exportar `formatted_address` com número na origem.** Nessa base, **919 das
   1.606 linhas tinham `Precisão da coordenada = "numero"`** — o sistema que
   gerou a base geocodificou até a porta, ou seja, **tinha o logradouro e não
   exportou**. Essa única coluna é a diferença entre ~230 e mais de 1.300
   aprovações. Se a plataforma gera esse campo internamente, persista e exporte.

3. **Geocodificação reversa pela coordenada.** Onde houver coordenada precisa e
   faltar endereço, o reverso (Nominatim, Google, HERE) devolve rua e número
   reais. Também estava bloqueado aqui.

**Ordem de preferência para o número de porta:**

```
número real da loja  >  número do reverso da coordenada  >  100 inventado  >>  nada
      80%                        (não medido)                   73%            0,1%
```

---

## 7. O ciclo de medição

O que fez a taxa subir não foi adivinhar o formato certo — foi **medir**.
Recomendo embutir isso na plataforma:

1. **Guarde o retorno da DSP** ligado linha a linha ao POI de origem. Sem isso
   não há como saber o que funcionou.

2. **Teste estratégias dentro do upload de produção.** Quando um grupo de linhas
   tem taxa conhecida ruim (as sem número valiam 0,1%), divida esse grupo em
   células com formatos diferentes. Cada linha continua sendo um POI real da
   audiência, então não se gasta um upload só para testar — e o retorno mede
   tudo de uma vez. Foi assim que `100` vs `1` vs bairro foi decidido, em uma
   rodada.

3. **Classifique risco antes de subir.** Dois sinais medidos:

   | Sinal | Efeito |
   |---|---|
   | endereço em rodovia | 57–67% de falha, contra 11–17% em rua normal |
   | CEP genérico (termina em `000`) | 2,4× mais falha |

4. **Rode sempre a mesma bateria de regressão.** Toda mudança no parser deve ser
   checada contra um conjunto de endereços que a DSP já aprovou. Duas vezes uma
   "melhoria" minha quebrou endereços que funcionavam, e só a bateria pegou.

---

## 8. Resumo para implementar

```
para cada POI:
    1. ler os campos (endereço, nome, cidade, UF, CEP, número, bairro)
    2. se não há logradouro e há CEP  -> buscar logradouro pelo CEP (com cache)
    3. escolher a cidade: o CEP arbitra entre a coluna e o texto
    4. extrair o número de porta (cuidado: sigla de rodovia, índice, milhar)
    5. se não há número:
         a) buscar o número real (CNPJ / reverso da coordenada)
         b) se não houver, injetar 100  [ÚLTIMO RECURSO: número arbitrário,
              não é o da loja. opt-in + marcar a linha como sintética]
    6. montar: <logradouro> <número> <cidade> <UF> <CEP> Brazil
    7. ascii_puro()  — NFKD primeiro, depois remover tudo fora de [A-Za-z0-9 ]
    8. deduplicar pela linha final
    9. reenviar byte a byte o que a DSP já aprovou
   10. dividir em arquivos de até 10.000 linhas, CRLF, sem cabeçalho
```

**Se for implementar uma só coisa:** garantir que todo POI saia com **logradouro
e número**. É isso que separa 0,1% de 80%.
