# geofence.py — template de audiências de geofencing para a Yahoo DSP

Você manda um CSV com os POIs, o script devolve o arquivo pronto para subir.

```bash
python3 geofence.py minha_lista.csv
python3 geofence.py minha_lista.csv -o saida/ --nome campanha_x --raio 0.19
```

## As regras da DSP que isso implementa

- Arquivo **TXT ou CSV com um endereço por linha**. A DSP lê a linha inteira como
  um endereço de texto livre — **não é uma planilha de colunas, e coordenada não
  funciona**.
- Máximo de **10.000 endereços** por line item e por arquivo. Acima disso a saída
  se divide em `_parte1`, `_parte2`, ...
- **Caracteres especiais podem dar erro** (`é`, `à`, `ç`, `#`, `-`). A saída é
  ASCII puro: só letras, dígitos e espaço.
- Só **Airports, Arena / Stadiums e Universities / Colleges** podem ser enviados
  pelo nome do POI. Qualquer outra categoria exige endereço completo.
- O raio é em **MILHAS** (`radiusUnit: MILES`). `0.3` = 483 m; para ~300 m use `0.19`.

## O que ele resolve sozinho

| | |
|---|---|
| Encoding | UTF-8 com/sem BOM, cp1252, latin-1 |
| Separador | `,` `;` tab `\|` |
| Colunas | Acha `endereco`, `nome`, `cidade`, `uf`, `cep`, `lat`, `lon`, `categoria` pelo cabeçalho, em português ou inglês |
| Sem cabeçalho | Detecta e não come a primeira linha |
| Endereço em colunas | Remonta na ordem convencional: logradouro, número, bairro, cidade, UF, CEP, país |
| Coordenada corrompida | Conserta o estrago de locale de vírgula decimal (`-229.753.965` → `-22.9753965`), validando contra a bounding box da UF |
| Categoria isenta | Usa só o nome quando a categoria permite |
| Duplicatas | Remove |

## O que ele devolve

- `<nome>.txt` e `<nome>.csv` — os arquivos de upload, um endereço por linha.
- `<nome>_conferencia.csv` — cada registro com endereço original, endereço final,
  e as coordenadas antes/depois. Para conferir antes de subir.
- `<nome>_descartados.csv` — só aparece se algo ficou de fora, com o motivo.

Se **nenhum** endereço for aproveitável, o script sai com código 2 e não gera
arquivo de upload nenhum — em vez de entregar um arquivo vazio que a DSP
rejeitaria. Foi o que aconteceu com a lista de POIs unificados, que só tinha
coordenadas.

## Opções

| Opção | Padrão | Para quê |
|---|---|---|
| `-o`, `--saida` | `saida_dsp` | Diretório de saída |
| `--nome` | nome do arquivo de entrada | Nome base dos arquivos gerados |
| `--pais` | `Brazil` | País anexado ao fim do endereço. Vazio para omitir |
| `--raio` | — | Raio em milhas, só registrado na conferência. Converte para metros no relatório |
| `--split` | `10000` | Máximo de endereços por arquivo |

## Testes

```bash
python3 testes.py
```

Cobre: paridade com o build dedicado do Nissan, recusa de arquivo só com
coordenadas, arquivo sem cabeçalho, cp1252 com tab, categoria isenta, endereço
quebrado em colunas, divisão acima de 10.000, duplicatas e ausência de
caractere proibido em toda a saída.
