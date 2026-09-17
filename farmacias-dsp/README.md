# Farmácias SP-CE-MT-PA Set/26 — Yahoo DSP

```bash
python3 ../geofence-yahoo/geofence.py origem_farmacias.csv -o upload --nome farmacias --separar-por uf
```

**1.951 endereços** de 2.003 farmácias (52 duplicatas, zero descartes).
Um arquivo por UF, já que a campanha é regional:

| UF | Endereços |
|---|---:|
| SP | 1.478 |
| CE | 247 |
| MT | 139 |
| PA | 85 |
| AL | 1 |
| SC | 1 |

AL e SC estão fora do escopo do nome do arquivo. São duas linhas: uma em
Fortaleza com `uf` preenchido como AL, e uma farmácia de Itajaí/SC. Deixei nos
seus próprios arquivos para você decidir se entram.

## A coluna `city` estava errada em 65 linhas

O caso mais grave desta base. A coluna dizia "São Paulo" para farmácias que o
endereço e o CEP situam em **Osasco** e **Taboão da Serra**:

```
AV. DOS AUTONOMISTAS 755 - VILA YARA  OSASCO - SP  06020-000
   coluna city = "São Paulo"        <- erro
   ->  Avenida DOS AUTONOMISTAS 755 OSASCO SP 06020000 Brazil
```

Isso é o **oposto** da base de cinemas, onde o texto trazia bairro
(`INTERLAGOS - SP` é São Paulo) e a coluna é que estava certa. Nenhuma
precedência fixa serve, então quem arbitra agora é o CEP: a faixa da capital
paulista (01000–05999 e 08000–08499) diz qual dos dois está certo. Nas 73
divergências desta base o CEP confirmou o texto em 65 e a coluna em 7.

Corrigidas: 46 em Taboão da Serra, 5 em Osasco, e a farmácia de Itajaí, que a
coluna mandava para São Paulo com CEP de Santa Catarina.

## Nome da farmácia colado no logradouro

`FARMÁCIA - AV. FARIAS BRITO  160 - ...` — aqui o nome vem separado por hífen
**dentro** do mesmo campo, não por vírgula, então o corte por segmento não
alcançava. Agora corta até o tipo de logradouro, desde que não haja número antes
(a mesma trava que preserva `Boulevard Vinte e Oito de Setembro, 271`).

## Onde deve dar erro

183 ALTO: 104 sem número de porta, 84 endereço de rodovia, 9 logradouro sem
nome. Mais 451 MÉDIO, quase todos CEP genérico de cidade.
