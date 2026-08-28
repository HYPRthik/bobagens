# geofence.py — template de audiências de geofencing para a Yahoo DSP

Você manda um CSV com os POIs, o script devolve o arquivo pronto para subir.

```bash
python3 geofence.py minha_lista.csv
python3 geofence.py minha_lista.csv --aprovados retorno_anterior.csv
```

## A forma essencial

A própria mensagem de erro da DSP diz o que ela procura: *"Check street address,
city & postal code are correct"*. São esses três campos, mais UF e país. Todo o
resto é ruído, então a saída é:

```
<logradouro> <número> <cidade> <UF> <CEP> Brazil
```

**O bairro sai.** Ele não é pedido pela DSP e colide com nome de cidade:
`Av Lacerda Agostinho 300 Botafogo Macae RJ` faz o geocodificador ancorar em
Botafogo/Rio em vez de Macaé; `Praca Sao Conrado 20 Sao Conrado Rio de Janeiro`
repete o mesmo termo duas vezes. Nos 202 endereços Nissan que a DSP processou,
20% falharam, e o bairro colidente aparece em boa parte deles.

O bairro só é descartado quando a cidade é identificável com segurança — por uma
coluna `cidade`, por um endereço com vírgulas, ou por a cidade vir depois da UF.
Quando não dá para separar, o script **mantém tudo** em vez de arriscar apagar a
cidade, e avisa no relatório de risco.

## `--aprovados`: não reescreve o que já funciona

Passe o arquivo de retorno de um upload anterior. Todo endereço que voltou
`successful` é reenviado com a string **exata** que funcionou; a forma essencial
só é aplicada ao que falhou.

```
aprovados     : 162 enderecos ja validados pela DSP serao reenviados sem alteracao
reenviados sem alteracao (ja aprovados): 162
reescritos na forma essencial          : 40
```

Sem isso, reescrever os 162 que já passavam seria arriscar uma regressão para
tentar consertar 40.

## Relatório de risco

Marca o que a DSP historicamente rejeita, com percentuais medidos no retorno real:

| Severidade | Sinal | Taxa de falha medida |
|---|---|---|
| ALTO | Endereço de rodovia (`Rodovia`, `BR 470`, `RS 020`) | 57–67%, contra 11–17% de rua normal |
| ALTO | Sem número de porta | 5% das falhas |
| ALTO | Logradouro sem nome (`477 Ararangua SC`) | — |
| MÉDIO | CEP genérico de cidade (termina em `000`) | 2,4x mais falha |

`ALTO` vale conferência manual antes de subir. `MÉDIO` sozinho é sinal fraco.

## Regras da DSP implementadas

- Arquivo **TXT ou CSV com um endereço por linha**. A DSP lê a linha inteira como
  endereço de texto livre — **não é planilha de colunas, e coordenada não funciona**.
- Máximo **10.000 endereços** por line item e por arquivo. Acima disso a saída se
  divide em `_parte1`, `_parte2`, ...
- **Caracteres especiais podem dar erro** (`é`, `à`, `ç`, `#`, `-`). A saída é
  ASCII puro: só letras, dígitos e espaço.
- Só **Airports, Arena / Stadiums e Universities / Colleges** podem ser enviados
  pelo nome do POI. Qualquer outra categoria exige endereço completo.

## O que ele resolve sozinho

| | |
|---|---|
| Encoding | UTF-8 com/sem BOM, cp1252, latin-1 |
| Separador | `,` `;` tab `\|` |
| Colunas | Acha `endereco`, `nome`, `cidade`, `uf`, `cep`, `lat`, `lon`, `categoria`, em português ou inglês |
| Sem cabeçalho | Detecta e não come a primeira linha |
| Formato Google | `Av. Paulista, 1578 - Bela Vista, São Paulo - SP, 01310-200` — com ou sem aspas |
| Nome do estabelecimento | `Churrascaria Ponteio, Avenida Francisco Ferreira Lopes, 460, ...` → corta o nome. Nunca corta se o trecho anterior tiver número (`Boulevard Vinte e Oito de Setembro, 271`) |
| Número com letra | `40A`, `1029D` são número de porta |
| Abreviações | `Av` → `Avenida`, `Rod` → `Rodovia` |
| Ruído | Remove `Km 56`, `S N` — não são endereçáveis |
| Número da porta | Não confunde com número no nome (`Avenida 2 de Agosto 352`) nem com sigla de rodovia (`Rodovia BR 470 7150`) |
| Coordenada corrompida | Conserta o estrago de locale de vírgula decimal (`-229.753.965` → `-22.9753965`), validando contra a bounding box da UF |
| Duplicatas | Remove |

## O que ele devolve

- `<nome>.txt` e `<nome>.csv` — os arquivos de upload.
- `<nome>_conferencia.csv` — cada registro com endereço original, endereço final,
  bairro descartado, severidade e coordenadas antes/depois.
- `<nome>_risco.csv` — só se houver, ordenado por severidade.
- `<nome>_descartados.csv` — só se algo ficou de fora, com o motivo.

Se **nenhum** endereço for aproveitável, sai com código 2 e não gera arquivo de
upload — em vez de entregar um arquivo vazio que a DSP rejeitaria.

## Opções

| Opção | Padrão | Para quê |
|---|---|---|
| `-o`, `--saida` | `saida_dsp` | Diretório de saída |
| `--nome` | nome do arquivo de entrada | Nome base dos arquivos gerados |
| `--pais` | `Brazil` | País no fim do endereço. Vazio para omitir |
| `--aprovados` | — | Retorno da DSP de um upload anterior |
| `--manter-bairro` | — | Não descarta o bairro |
| `--separar-por` | — | Gera um arquivo por valor da coluna (ex: `POI`, `Estado`) — cada line item recebe uma lista |
| `--split` | `10000` | Máximo de endereços por arquivo |

## Testes

```bash
python3 testes.py
```

31 checagens: paridade com o retorno real da DSP, preservação dos aprovados,
recusa de lista só com coordenadas, remoção do bairro nas três formas em que a
cidade é identificável, proteção contra apagar a cidade quando não é, número da
porta, expansão de abreviação, encoding, sem cabeçalho, categoria isenta,
limite de 10.000, duplicatas, corte de nome de estabelecimento com a trava que
impede apagar rua com número, e ASCII em toda a saída.
