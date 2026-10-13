#!/usr/bin/env python3
"""
Monta um teste de formato para a base GLP da Copa Energia.

A base nao tem logradouro, e o formato "<nome> <cidade> <UF> <CEP>" rendeu 5
enderecos reconhecidos em 3.149 no upload anterior. Antes de gastar outro upload
com 1.606 linhas do mesmo jeito, este script gera UM arquivo de teste com quatro
formatos sobre as MESMAS 60 lojas. O retorno da DSP diz qual deles, se algum,
ela aceita sem logradouro.

As variantes saem embaralhadas de proposito: se a DSP processa em ordem, um
bloco inteiro no comeco poderia se beneficiar disso.

Uso:  python3 variantes.py origem.csv
"""
import csv
import importlib.util
import io
import os
import random
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

N = 60
rows = list(csv.DictReader(io.StringIO(open(sys.argv[1], encoding="utf-8-sig").read())))


def cep8(r):
    return re.sub(r"\D", "", r["cep"])


def cep_hifen(r):
    d = cep8(r)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else d


# so lojas com CEP especifico e coordenada no numero: se nem essas passarem,
# nenhuma passa
bons = [r for r in rows
        if len(cep8(r)) == 8 and not cep8(r).endswith("000")
        and r["Precisão da coordenada"].strip().lower() == "numero"]
random.seed(13)
amostra = random.sample(bons, min(N, len(bons)))
print(f"lojas elegiveis: {len(bons)}   na amostra: {len(amostra)}")

VARIANTES = {
    # A: endereco puro, CEP no fim — a posicao que o CEP ocupa no formato que
    #    funcionou no Nissan ("rua numero cidade UF CEP Brazil")
    "A_cidade_uf_cep":  lambda r: _gf.ascii_puro(f"{r['city']} {r['uf']} {cep8(r)} Brazil"),
    # B: CEP na frente, como o correio escreve
    "B_cep_cidade_uf":  lambda r: _gf.ascii_puro(f"{cep8(r)} {r['city']} {r['uf']} Brazil"),
    # C: o formato do upload anterior, de controle (rendeu 5 em 3.149)
    "C_nome_cidade_cep": lambda r: _gf.ascii_puro(f"{r['name']} {r['city']} {r['uf']} {cep8(r)} Brazil"),
    # D: CEP com hifen. A regra da DSP desaconselha "-", mas e como o CEP e
    #    escrito no Brasil, e no Nissan o hifen so foi testado COM logradouro
    "D_cep_com_hifen":  lambda r: (_gf.ascii_puro(f"{r['city']} {r['uf']}") + f" {cep_hifen(r)} Brazil"),
}

linhas, mapa = [], []
for nome, fn in VARIANTES.items():
    for r in amostra:
        t = fn(r)
        linhas.append(t)
        mapa.append({"variante": nome, "linha_dsp": t, "cnpj": r["CNPJ"],
                     "nome_loja": r["name"], "cidade": r["city"], "uf": r["uf"],
                     "cep": cep8(r)})
random.shuffle(linhas)

os.makedirs(os.path.join(BASE, "teste"), exist_ok=True)
p = os.path.join(BASE, "teste", "teste_formatos.txt")
with open(p, "w", newline="", encoding="ascii") as f:
    f.write("\r\n".join(linhas) + "\r\n")
with open(os.path.join(BASE, "teste", "teste_formatos.csv"), "w",
          newline="", encoding="ascii") as f:
    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
with open(os.path.join(BASE, "teste", "teste_de_para.csv"), "w",
          newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(mapa[0]), delimiter=";")
    w.writeheader()
    w.writerows(mapa)

print(f"\n{len(linhas)} linhas: {len(VARIANTES)} formatos x {len(amostra)} lojas")
for nome, fn in VARIANTES.items():
    print(f"   {nome:20} {fn(amostra[0])}")
print(f"\ngerado teste/teste_formatos.txt")
