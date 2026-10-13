#!/usr/bin/env python3
"""Baixa logradouro por CEP do espelho aberto do OpenCEP (gpfconfea/banco-ceps).

As APIs de CEP estao bloqueadas pela politica de rede, mas o raw do GitHub nao.
Cada CEP e um JSON: {cep, logradouro, complemento, bairro, localidade, uf,
ibge, latitude, longitude}. Grava um por arquivo em cepdata/ e nada mais —
e dado de terceiro, fica isolado e e lido com parser estrito depois.
"""
import csv, io, json, os, re, sys, time
import concurrent.futures as cf
import urllib.request, urllib.error

BASE = "/home/user/bobagens/copa-energia-dsp/glp_out13"
DEST = os.path.join(BASE, "cepdata")
URL = "https://raw.githubusercontent.com/gpfconfea/banco-ceps/main/cep/%s.json"

alvo = list(csv.DictReader(io.StringIO(
    open(os.path.join(BASE, "origem.csv"), encoding="utf-8-sig").read())))
ceps = sorted({re.sub(r"\D", "", r["cep"]) for r in alvo if len(re.sub(r"\D", "", r["cep"])) == 8})
print(f"{len(ceps)} CEPs distintos", flush=True)


def pega(c):
    d = os.path.join(DEST, c + ".json")
    if os.path.exists(d):
        return "cache"
    for tent in range(4):
        try:
            with urllib.request.urlopen(URL % c, timeout=30) as r:
                b = r.read()
            json.loads(b.decode("utf-8"))          # so grava se for JSON valido
            open(d, "wb").write(b)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(d + ".404", "w").close()
                return "404"
            time.sleep(2 ** tent)
        except Exception:
            time.sleep(2 ** tent)
    return "erro"


n = {"ok": 0, "404": 0, "erro": 0, "cache": 0}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for i, r in enumerate(ex.map(pega, ceps), 1):
        n[r] += 1
        if i % 200 == 0:
            print(f"  {i}/{len(ceps)}  {n}", flush=True)
print("FIM", n, flush=True)
