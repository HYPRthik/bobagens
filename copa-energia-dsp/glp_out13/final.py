#!/usr/bin/env python3
"""
Monta o arquivo final da base GLP, combinando as duas fontes possiveis.

O teste de formato mostrou que nenhuma reordenacao salva uma linha sem
logradouro: 0% sem nome, 1,7% com nome, 0% com CEP hifenizado. Entao o ganho
real vem de arrumar logradouro de verdade para o maximo de linhas.

Fonte 1 — indice CEP: as bases ja processadas aqui tem 11.000 CEPs com
logradouro. Onde o CEP da Copa Energia bate E a cidade confere, o endereco sai
completo. O numero de porta e de outro estabelecimento no MESMO CEP, ou seja, no
mesmo trecho de rua — para um geofence por raio isso e irrelevante, e e o que
torna o endereco resolvivel pela DSP. Mesmo criterio que usei nos pontos de OOH.

Fonte 2 — o resto vai no formato "<nome> <cidade> <UF> <CEP>", unico que pontuou
no teste.

Uso:  python3 final.py
"""
import collections
import csv
import importlib.util
import io
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(BASE, "..", "..")
BASES = ["glp-dsp/origem_glp.csv", "farmacias-dsp/origem_farmacias.csv",
         "beleza-dsp/origem_beleza.csv", "cinemas-dsp/origem_cinemas.csv",
         "pois-jlr-dsp/origem_pois_completa.csv", "mercadolivre-ooh-dsp/origem_ml_ooh.csv",
         "campari-negroni-dsp/origem/pdvs_base_completa.csv"]
csv.field_size_limit(10 ** 7)

_spec = importlib.util.spec_from_file_location(
    "gf", os.path.join(RAIZ, "geofence-yahoo", "geofence.py"))
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv
sys.argv = ["gf", "x"]
try:
    _spec.loader.exec_module(_gf)
except SystemExit:
    pass
sys.argv = _sa


def norm(s):
    return re.sub(r"[^a-z]", "", _gf.sem_acento(s).lower())


idx = collections.defaultdict(list)
for b in BASES:
    p = os.path.join(RAIZ, b)
    if not os.path.exists(p):
        continue
    for r in csv.DictReader(io.StringIO(open(p, encoding="utf-8-sig").read())):
        a = (r.get("formatted_address") or "").strip()
        d = re.sub(r"\D", "", r.get("cep") or "")
        if a and len(d) == 8:
            idx[d].append((a, (r.get("city") or "").strip(), b.split("/")[0]))

alvo = list(csv.DictReader(io.StringIO(open(os.path.join(BASE, "origem.csv"),
                                            encoding="utf-8-sig").read())))
linhas, detalhe, vistos = [], [], set()
conta = collections.Counter()
for r in alvo:
    d = re.sub(r"\D", "", r["cep"])
    achado = next((a for a, cid, _f in idx.get(d, []) if norm(cid) == norm(r["city"])), None)
    if achado:
        # o gerador faz a forma essencial: logradouro, numero, cidade, UF, CEP
        miolo, cid_t, uf_t, cep_t, segs = _gf.partir_endereco(achado)
        cidade = r["city"] or cid_t
        rua, _bairro = _gf.partir_numero(_gf.limpar_ruido(_gf.expandir_tipo(miolo)))
        linha = _gf.ascii_puro(" ".join(x for x in (rua, cidade, r["uf"], d, "Brazil") if x))
        origem = "logradouro do indice de CEP"
    else:
        linha = _gf.ascii_puro(f"{r['name']} {r['city']} {r['uf']} {d} Brazil")
        origem = "nome do POI (sem logradouro)"
    if linha in vistos:
        continue
    vistos.add(linha)
    conta[origem] += 1
    linhas.append(linha)
    detalhe.append({"linha_dsp": linha, "origem": origem, "loja": r["name"],
                    "cnpj": r["CNPJ"], "cidade": r["city"], "uf": r["uf"], "cep": d,
                    "endereco_do_indice": achado or ""})

os.makedirs(os.path.join(BASE, "upload"), exist_ok=True)
p = os.path.join(BASE, "upload", "copa_glp_final")
with open(p + ".txt", "w", newline="", encoding="ascii") as f:
    f.write("\r\n".join(linhas) + "\r\n")
with open(p + ".csv", "w", newline="", encoding="ascii") as f:
    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
with open(p + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(detalhe[0]), delimiter=";")
    w.writeheader()
    w.writerows(detalhe)

print(f"origem: {len(alvo)} lojas -> {len(linhas)} linhas unicas")
for k, v in conta.most_common():
    print(f"   {v:5d}  {k}")
ruins = [x for x in linhas if re.search(r"[^A-Za-z0-9 ]", x)]
print(f"\nASCII limpo: {not ruins} | <=10.000: {len(linhas) <= 10000}")
