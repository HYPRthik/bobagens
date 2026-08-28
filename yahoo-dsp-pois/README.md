# POIs Unificados HYPR/JLR — status: BLOQUEADO, faltam os endereços

> **Correção.** A primeira versão deste diretório dizia para subir os CSVs de
> coordenadas no "campo de latitude/longitude" da DSP. **Esse campo não existe.**
> Os arquivos em `upload/`, `por_estado/` e `por_poi/` **não funcionam** no
> geofencing da Yahoo DSP e estão mantidos aqui só como base de dados limpa.

## O formato real do geofencing da Yahoo DSP

- Arquivo **TXT ou CSV**, com **um endereço por linha ou célula**. A DSP lê a
  linha inteira como um endereço de texto livre — não é uma planilha de colunas.
- Máximo de **10.000 endereços** por line item e por arquivo.
- **Caracteres especiais podem dar erro**: `é`, `à`, `ç`, `#`, `-`.
- Só estas categorias de POI podem ser enviadas **pelo nome, sem endereço**:
  Airports, Arena / Stadiums, Universities / Colleges. Todas as outras exigem
  **endereço completo**.
- O raio é medido em **MILHAS** (`radiusUnit: MILES` na API). O valor 0,3 que
  estava na planilha equivale a **483 m**, não a 300 m.

## Por que os dois uploads falharam

| Upload | Resultado | Motivo |
|---|---|---|
| Planilha original (5 colunas) | 3 de 2.686 | Cada linha virou uma string de endereço. As que continham `SP` — UF válida — davam `Incomplete address`; com `Demais Praças`, nem estado era reconhecido, daí `Unknown error`. Os 3 "successful" foram coincidência de geocodificação. |
| CSV de coordenadas (3 colunas) | 0 de 2.424 | Sem nenhum texto de endereço, a string `-23.568083,-46.673556,0.3` não geocodifica em nada. Daí `All 2424 addresses failed`. |

A linha de **cabeçalho** do arquivo original voltou marcada como `successful` —
a DSP geocodificou o texto `Latitude,Longitude,Radius Distance,Estado,POI` como
se fosse um endereço. É a prova mais direta de que o campo é de texto livre.

## O que falta

As 2.424 coordenadas estão corretas e validadas, mas **coordenada não é endereço**.
Nenhuma das 11 categorias da lista (Bancos, Concessionárias, Joalherias, Marinas,
Restaurantes, Shoppings, Clubes, Helipontos, Decor, Resorts, Golf Clubs) está na
lista de exceções que aceitam só o nome.

Dois caminhos:

1. **Recuperar o export original dos POIs com endereço.** É o caminho limpo — a
   lista veio de alguma fonte (Google Places ou similar) que quase certamente
   trazia `formatted_address`. Com isso o arquivo sai pronto na hora.
2. **Geocodificação reversa das 2.424 coordenadas.** Funciona, mas é aproximada:
   devolve o endereço mais próximo, que nem sempre é o do estabelecimento.

## Conteúdo

- `HYPR_JLR_POIs_Unificados_LIMPO.xlsx` — base limpa: 2.686 → 2.424 coordenadas
  distintas, validadas dentro do Brasil, com Estado e categoria. Serve como
  insumo para qualquer um dos dois caminhos acima.
- `upload/`, `por_estado/`, `por_poi/` — CSVs de coordenadas. **Não são
  uploadáveis** no formato atual da DSP.
- `build.py` — regenera tudo a partir de `origem_pois_unificados.csv`.

Veja `../nissan-dsp-geofencing/` para um exemplo já no formato correto.
