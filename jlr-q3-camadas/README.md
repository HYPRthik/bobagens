# JLR Q3 Out/26 — 4 camadas · Yahoo DSP

```bash
python3 preparar.py                                  # marca a camada e escolhe o endereço
python3 ../geofence-yahoo/geofence.py origem/com_camada.csv \
        -o upload --nome jlr_q3 --separar-por camada
```

**222 endereços** de 232 pontos, zero descartes. Quatro audiências:

| Camada | Endereços |
|---|---:|
| Lifestyle equestre | 62 |
| Condomínios de alto padrão | 60 |
| Design e arte | 54 |
| Tech e capital | 49 |

A soma dá 225 contra 222 do arquivo único: três endereços entram em duas camadas
(um condomínio com centro equestre, por exemplo). Correto — são listas de
targeting independentes.

## As camadas não estão em nenhuma coluna

A planilha é uma pilha de 4 blocos, e o único sinal é a coluna `Nº` reiniciar a
contagem. `preparar.py` detecta as quebras (posições 60, 115, 170) e nomeia cada
camada pelas subcategorias que predominam nela — 60/60, 50/55, 54/55 e 57/62 das
subcategorias batem com o tema atribuído.

## Dois endereços concorrentes por linha

Cada linha traz o endereço do geocodificador (`formatted_address` + `city`/`cep`)
**e** um curado à mão (`Endereço completo` + `Cidade`/`UF`/`CEP`). O curado ganha:

| | com logradouro | com número |
|---|---:|---:|
| geocodificador | 206/232 | 172 |
| curado | 221/232 | 202 |

E onde divergem, é o curado que acerta. `Centro Hípico de Itu` aparece como
**Via W3 Norte, Asa Norte, Brasília - DF** no geocodificador.

O `preparar.py` escolhe **um bloco inteiro** por linha, nunca mistura. Misturar
produzia endereço que não existe em lugar nenhum — rua de uma cidade com CEP de
outra:

```
antes:  Via W3 Norte Asa Norte Itu SP 70760545     <- Brasília + Itu
agora:  Estrada do Varejao City Castello Itu SP
```

231 das 232 linhas usaram o bloco curado.

## Onde deve dar erro

72 ALTO: 48 sem número de porta e 47 endereço de rodovia — esperado numa base de
condomínios de campo e haras, que ficam em rodovia e raramente têm número.
Zero divergência de cidade.
