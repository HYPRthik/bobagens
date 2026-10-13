#!/usr/bin/env python3
"""
Gera o arquivo completo da base GLP no formato sem nome do estabelecimento.

Sem logradouro e sem nome, a granularidade real do dado e o CEP: cada CEP
distinto e um trecho de rua, e um geofence por raio cobre o trecho inteiro.
1.606 lojas em 1.358 CEPs distintos viram 1.358 geofences, nao 1.606 — as
repetidas estao no mesmo trecho de rua.

Uso:  python3 completo.py origem.csv
"""
import collections
import csv
import importlib.util
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "gf", os.path.join(BASE, "..", "..", "geofence-yahoo", "geofence.py"))
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv
sys.argv = ["gf", "x"]
try:
    _spec.loader.exec_module(_gf)
except SystemExit:
    pass
sys.argv = _sa

rows = list(csv.DictReader(io.StringIO(open(sys.argv[1], encoding="utf-8-sig").read())))
os.makedirs(os.path.join(BASE, "upload"), exist_ok=True)


def cep8(r):
    return re.sub(r"\D", "", r["cep"])


def escrever(nome, linhas, detalhe):
    p = os.path.join(BASE, "upload", nome)
    with open(p + ".txt", "w", newline="", encoding="ascii") as f:
        f.write("\r\n".join(linhas) + "\r\n")
    with open(p + ".csv", "w", newline="", encoding="ascii") as f:
        csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
    with open(p + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(detalhe[0]), delimiter=";")
        w.writeheader()
        w.writerows(detalhe)
    print(f"  {nome:28} {len(linhas):5d} linhas")


for rotulo, fn in (("copa_glp_sem_nome", lambda r: f"{r['city']} {r['uf']} {cep8(r)} Brazil"),
                   ("copa_glp_com_nome", lambda r: f"{r['name']} {r['city']} {r['uf']} {cep8(r)} Brazil")):
    vistos, linhas, detalhe = set(), [], []
    agrupadas = collections.defaultdict(list)
    for r in rows:
        if len(cep8(r)) != 8:
            continue
        t = _gf.ascii_puro(fn(r))
        agrupadas[t].append(r)
        if t in vistos:
            continue
        vistos.add(t)
        linhas.append(t)
    for t in linhas:
        g = agrupadas[t]
        detalhe.append({"linha_dsp": t, "lojas_no_mesmo_ponto": len(g),
                        "cep": cep8(g[0]), "cidade": g[0]["city"], "uf": g[0]["uf"],
                        "lojas": " | ".join(x["name"] for x in g[:6]),
                        "cnpjs": " | ".join(x["CNPJ"] for x in g[:6])})
    escrever(rotulo, linhas, detalhe)

print(f"\norigem: {len(rows)} lojas | CEPs distintos: {len({cep8(r) for r in rows})}")
