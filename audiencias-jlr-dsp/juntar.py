#!/usr/bin/env python3
"""
Resolve as audiencias de coordenada do JLR em enderecos.

As 11 planilhas em origem/ trazem so lat,lon,raio — formato que o geofencing da
Yahoo DSP nao aceita, porque ele le UM ENDERECO POR LINHA em texto livre. Este
script cruza cada coordenada com a base de enderecos
(../pois-jlr-dsp/origem_pois_completa.csv) e escreve um CSV enriquecido por
categoria, pronto para o geofence.py.

O que nao casa vai para <categoria>_sem_endereco.csv, para conferencia.

Uso:  python3 juntar.py
"""
import csv
import io
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
ENDERECOS = os.path.join(BASE, "..", "pois-jlr-dsp", "origem_pois_completa.csv")
PRECISAO = 5          # ~1 m; casa as duas colunas de coordenada da base
BR = (-33.9, 5.4, -74.1, -34.7)      # lat_min, lat_max, lon_min, lon_max


def no_brasil(la, lo):
    return BR[0] <= la <= BR[1] and BR[2] <= lo <= BR[3]


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def candidatos(tok):
    """Uma coordenada pode vir destruida por locale de virgula decimal
    ("-23.531.969" era "-23.531969"). Devolve as leituras possiveis, em ordem;
    quem chama escolhe a que existe na base de enderecos."""
    tok = str(tok).strip()
    out = []
    try:
        v = float(tok)
        if tok.count(".") <= 1:        # <=1 ponto: nunca virou separador de milhar
            return [v]
        out.append(v)
    except ValueError:
        pass
    neg = tok.startswith("-")
    d = re.sub(r"\D", "", tok)
    for k in (1, 2):
        if len(d) <= k:
            continue
        v = float(d[:k] + "." + d[k:])
        v = -v if neg else v
        if v not in out:
            out.append(v)
    return out


def ler_coords(caminho):
    """Le lat,lon,raio tolerando separador , ou ; e lixo de ';;;' no fim de linha
    (o export de Helipontos vem assim). Nao ha cabecalho: a linha 1 ja e dado."""
    linhas = open(caminho, encoding="utf-8-sig", errors="replace").read().splitlines()
    out, ruins = [], 0
    for ln in linhas:
        ln = ln.strip().strip(";").strip()
        if not ln:
            continue
        p = [x.strip() for x in re.split(r"[;,]", ln) if x.strip()]
        if len(p) < 2:
            ruins += 1
            continue
        cla, clo = candidatos(p[0]), candidatos(p[1])
        if cla and clo:
            out.append((cla, clo))
        else:
            ruins += 1
    return out, ruins


def chave(la, lo):
    return (round(float(la), PRECISAO), round(float(lo), PRECISAO))


base = list(csv.DictReader(io.StringIO(open(ENDERECOS, encoding="utf-8-sig").read())))
idx = {}
for r in base:
    # a base tem duas colunas de coordenada; indexa as duas
    for la, lo in ((r.get("lat"), r.get("lng")), (r.get("Latitude"), r.get("Longitude"))):
        if not la or not lo:
            continue
        try:
            idx.setdefault(chave(la, lo), r)
        except (ValueError, TypeError):
            pass

os.makedirs(os.path.join(BASE, "enriquecido"), exist_ok=True)
CAMPOS = ["lat", "lng", "formatted_address", "city", "uf", "cep"]
tot = casou = 0
print(f"{'audiencia':26}{'pontos':>8}{'com endereco':>14}{'cobertura':>11}")
print("-" * 60)
for f in sorted(os.listdir(os.path.join(BASE, "origem"))):
    if not f.endswith(".csv"):
        continue
    nome = slug(f.replace("HYPR_JLR_", "").replace(".csv", "").replace("_StackAdapt", ""))
    coords, ruins = ler_coords(os.path.join(BASE, "origem", f))
    vistos, achados, faltam = set(), [], []
    # ponto de referencia da audiencia: mediana das coordenadas sem ambiguidade.
    # Serve para desempatar leituras corrompidas — "-23.531.969" pode ser lido
    # como -2.35 ou -23.53, e ambos caem no Brasil; vence o que fica perto dos
    # demais pontos do mesmo arquivo.
    certos = [(a[0], b[0]) for a, b in coords if len(a) == 1 and len(b) == 1]
    if certos:
        ref = (sorted(x for x, _ in certos)[len(certos) // 2],
               sorted(y for _, y in certos)[len(certos) // 2])
    else:
        ref = None

    for cla, clo in coords:
        pares = [(a, b) for a in cla for b in clo]
        # 1) a leitura que existe na base de enderecos
        k = next((chave(a, b) for a, b in pares if chave(a, b) in idx), None)
        if k is None:
            # 2) entre as que caem no Brasil, a mais proxima do resto da audiencia
            dentro = [(a, b) for a, b in pares if no_brasil(a, b)] or pares
            if ref:
                dentro.sort(key=lambda ab: (ab[0] - ref[0]) ** 2 + (ab[1] - ref[1]) ** 2)
            k = chave(*dentro[0])
        la, lo = k
        if k in vistos:
            continue
        vistos.add(k)
        r = idx.get(k)
        if r:
            achados.append({"lat": la, "lng": lo, "formatted_address": r["formatted_address"],
                            "city": r["city"], "uf": r["uf"], "cep": r["cep"]})
        else:
            faltam.append((la, lo))
    with open(os.path.join(BASE, "enriquecido", f"{nome}.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(achados)
    if faltam:
        with open(os.path.join(BASE, "enriquecido", f"{nome}_sem_endereco.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["lat", "lng"])
            w.writerows(faltam)
    tot += len(vistos)
    casou += len(achados)
    extra = f"  ({ruins} linhas ilegiveis)" if ruins else ""
    print(f"{nome:26}{len(vistos):8d}{len(achados):14d}{len(achados)/len(vistos):10.0%}{extra}")
print("-" * 60)
print(f"{'TOTAL':26}{tot:8d}{casou:14d}{casou/tot:10.0%}")
print(f"\nsem endereco: {tot - casou} coordenadas — ver enriquecido/*_sem_endereco.csv")
