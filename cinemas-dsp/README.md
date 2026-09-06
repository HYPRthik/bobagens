# Cinemas no Brasil — arquivos de geofencing para a Yahoo DSP

```bash
python3 ../geofence-yahoo/geofence.py origem_cinemas.csv -o upload --nome cinemas_brasil
```

**2.511 endereços** de 2.620 linhas de origem: 70 duplicatas removidas, 39 descartados
por não terem endereço utilizável. Um arquivo só — cabe no limite de 10.000 por line item.

Cinema **não** está entre as categorias que a DSP aceita pelo nome do POI
(só Airports, Arena / Stadiums e Universities / Colleges), então vai endereço completo.

## O formato desta base

Diferente do export do Google: os componentes vêm separados por **espaço duplo**,
não por vírgula.

```
AV. PROF. CARLOS CUNHA  1000 - JARACATY  SÃO LUÍS - MA  65076-907  BRASIL
   ->  Avenida PROF CARLOS CUNHA 1000 Sao Luis MA 65076907 Brazil
```

Como muitos cinemas ficam em shopping, a base traz o nome do shopping e a loja:

```
PARK SHOPPING CANOAS  AV. FARROUPILHA  4545 - LOJA 3004 - MAL. RONDON  CANOAS - RS  92020-475
   ->  Avenida FARROUPILHA 4545 Canoas RS 92020475 Brazil
```

O nome do shopping e o `LOJA 3004` saem: para um geofence por raio o que importa
é o endereço na rua, não a posição dentro do prédio.

## Transformações

| | |
|---|---:|
| Bairro descartado | 1.863 |
| Duplicatas removidas | 70 |
| Descartados sem endereço | 39 |

Em 34 linhas o slot de cidade do endereço trazia na verdade um **bairro**
(`BELA VISTA - SP`, `PIRITUBA - SP`, `INTERLAGOS - SP` são todos São Paulo).
A coluna `city` tem precedência sobre o texto justamente por isso.

## Onde deve dar erro

`cinemas_brasil_risco.csv` marca 709 ALTO e 473 MÉDIO.

| Motivo | Qtd | Observação |
|---|---:|---|
| Sem número de porta | 641 | **A origem não tem o número.** Conferido linha a linha: 640 dos 641 já vinham sem número |
| CEP genérico de cidade | 266 | Termina em `000`; 2,4x mais falha |
| Endereço de rodovia | 105 | 57–67% falharam no teste do Nissan |
| Logradouro sem nome | 74 | Origem só tem bairro + cidade, ex.: `CENTRO, PAINS - MG, 35582-000` |

206 endereços saíram sem CEP porque a origem não tinha.

Depois do upload, passe o arquivo de retorno da DSP em `--aprovados` para reenviar
sem alteração tudo o que passou e reescrever só o que falhou.
