#!/usr/bin/env python3
"""
Prepara a base JLR Q3: marca a camada e escolhe UM bloco de endereco.

As 4 camadas nao estao em coluna nenhuma: a planilha e uma pilha de 4 blocos, e
o unico sinal e a coluna "Nº" reiniciar a contagem no inicio de cada um. O nome
da camada vem das subcategorias que predominam no bloco.

Uso:  python3 preparar.py
"""
import collections
import csv
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(BASE, "origem", "base_completa.csv")
SAIDA = os.path.join(BASE, "origem", "com_camada.csv")

# termo que aparece na subcategoria -> nome da camada
TEMAS = [
    ("condominio",   "Condominios de alto padrao"),
    ("equestre",     "Lifestyle equestre"),
    ("hipic",        "Lifestyle equestre"),
    ("haras",        "Lifestyle equestre"),
    ("equitacao",    "Lifestyle equestre"),
    ("jockey",       "Lifestyle equestre"),
    ("polo",         None),            # ambiguo: "polo tecnologico" x "clube de polo"
    ("tech",         "Tech e capital"),
    ("venture",      "Tech e capital"),
    ("private equity", "Tech e capital"),
    ("consultoria",  "Tech e capital"),
    ("inovacao",     "Tech e capital"),
    ("banco",        "Tech e capital"),
    ("fintech",      "Tech e capital"),
    ("revestimento", "Design e arte"),
    ("galeria",      "Design e arte"),
    ("marcenaria",   "Design e arte"),
    ("iluminacao",   "Design e arte"),
    ("metais",       "Design e arte"),
    ("design",       "Design e arte"),
    ("pedras",       "Design e arte"),
    ("arte",         "Design e arte"),
]


def sem_acento(s):
    import unicodedata
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()


rows = list(csv.reader(io.StringIO(open(ORIG, encoding="utf-8-sig").read())))
hdr = rows[0]
body = [r for r in rows[1:] if any(c.strip() for c in r)]
iNUM = hdr.index("Nº")
iSUB = hdr.index("Subcategoria")
SEM_RUA = re.compile(r"logradouro\s+n[ao]o\s+informado", re.I)


def tem_logradouro(a):
    a = (a or "").strip()
    return bool(a) and not SEM_RUA.search(sem_acento(a))


def bloco_curado(r):
    return (r[hdr.index("Endereço completo")], r[hdr.index("Cidade")],
            r[hdr.index("UF")], r[hdr.index("CEP")])


def bloco_geo(r):
    return (r[hdr.index("formatted_address")], r[hdr.index("city")],
            r[hdr.index("uf")], r[hdr.index("cep")])

# os blocos comecam onde o contador cai
quebras = [0] + [n for n in range(1, len(body))
                 if body[n][iNUM].strip().isdigit() and body[n - 1][iNUM].strip().isdigit()
                 and int(body[n][iNUM]) < int(body[n - 1][iNUM])] + [len(body)]
print(f"blocos detectados: {len(quebras) - 1}  (limites {quebras})")
if len(quebras) - 1 != 4:
    sys.exit("esperava 4 camadas; confira a planilha antes de seguir")


def nomear(bloco):
    """Nomeia a camada pelo tema que mais aparece nas subcategorias do bloco."""
    votos = collections.Counter()
    for r in bloco:
        sub = sem_acento(r[iSUB]).lower()
        for termo, nome in TEMAS:
            if nome and termo in sub:
                votos[nome] += 1
                break
    return votos.most_common(1)[0][0] if votos else "Sem tema"


origem_conta = collections.Counter()
with open(SAIDA, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["nome", "endereco", "cidade", "uf", "cep", "lat", "lng",
                "subcategoria", "camada", "origem_endereco"])
    for b in range(len(quebras) - 1):
        bloco = body[quebras[b]:quebras[b + 1]]
        nome = nomear(bloco)
        cob = sum(1 for r in bloco
                  if any(nome == n and termo in sem_acento(r[iSUB]).lower()
                         for termo, n in TEMAS if n))
        print(f"  camada {b + 1}: {len(bloco):3d} linhas  {nome!r}"
              f"   ({cob}/{len(bloco)} subcategorias batem com o tema)")
        for r in bloco:
            cur, geo = bloco_curado(r), bloco_geo(r)
            # bloco inteiro, nunca misturado
            usa, marca = (cur, "curado") if tem_logradouro(cur[0]) else (geo, "geocodificador")
            ender, cid, uf, cep = usa
            if (cep or "").strip().lower() in ("n/d", "nd", "-"):
                cep = ""
            origem_conta[marca] += 1
            w.writerow([r[hdr.index("name")], ender, cid, uf, cep,
                        r[hdr.index("lat")], r[hdr.index("lng")],
                        r[iSUB], nome, marca])
print(f"\nbloco de endereco usado: {dict(origem_conta)}")
print(f"gerado {os.path.relpath(SAIDA, BASE)}")
