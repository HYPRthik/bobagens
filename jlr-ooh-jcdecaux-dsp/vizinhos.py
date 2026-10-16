#!/usr/bin/env python3
"""Indice de enderecos reais da cidade de SP (bases ja processadas no repo) e
busca, para cada face de OOH, do endereco real mais proximo NA MESMA RUA."""
import csv, difflib, io, math, os, re, sys, importlib.util, unicodedata

RAIZ = "/home/user/bobagens/"
csv.field_size_limit(10 ** 7)
_s = importlib.util.spec_from_file_location("gf", RAIZ + "geofence-yahoo/geofence.py")
gf = importlib.util.module_from_spec(_s); _a = sys.argv; sys.argv = ["gf", "x"]
try: _s.loader.exec_module(gf)
except SystemExit: pass
sys.argv = _a

NUMS = {"9": "nove", "23": "vinte tres", "25": "vinte cinco", "7": "sete", "1": "primeiro"}
TIPOS = r"^(rua|r|avenida|av|alameda|al|praca|pca|travessa|largo|viaduto|complexo viario|estrada|rodovia)\b"
FILLER = {"de", "da", "do", "dos", "das", "e", "presidente", "pres", "doutor", "dr", "engenheiro",
          "eng", "professor", "prof", "brigadeiro", "brig", "general", "gen"}


def chave(rua):
    s = unicodedata.normalize("NFKD", rua or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s).strip()
    s = re.sub(TIPOS, "", s).strip()
    t = []
    for w in s.split():
        w = NUMS.get(w, w)
        t += [x for x in w.split() if x not in FILLER]
    return " ".join(t)


def mesma_rua(a, b):
    ka, kb = chave(a), chave(b)
    if not ka or not kb:
        return False
    if ka == kb or ka in kb or kb in ka:
        return True
    return difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.85


def km(a, b, c, d):
    p = math.pi / 180
    return 12742 * math.asin(math.sqrt(.5 - math.cos((c - a) * p) / 2 +
                                       math.cos(a * p) * math.cos(c * p) * (1 - math.cos((d - b) * p)) / 2))


def indice():
    out = []
    for dp, _dn, fn in os.walk(RAIZ):
        if ".git" in dp or "cache" in dp or "cepdata" in dp or "jlr-ooh-jcdecaux" in dp:
            continue
        for f in fn:
            if not (f.endswith(".csv") and ("origem" in f or "base" in f)):
                continue
            try:
                rr = list(csv.DictReader(io.StringIO(open(os.path.join(dp, f), encoding="utf-8-sig",
                                                          errors="replace").read())))
            except Exception:
                continue
            if not rr or "formatted_address" not in rr[0]:
                continue
            for r in rr:
                a = (r.get("formatted_address") or "").strip()
                try:
                    la, lo = float(r.get("lat") or 0), float(r.get("lng") or 0)
                except ValueError:
                    continue
                if not a or not (-23.75 < la < -23.40 and -46.85 < lo < -46.35):
                    continue
                miolo, cid, uf, cep, _seg = gf.partir_endereco(a)
                rua_num, _b = gf.partir_numero(gf.limpar_ruido(gf.expandir_tipo(miolo)))
                m = re.match(r"^(.*?)\s+(\d{1,5}[A-Za-z]?)$", rua_num.strip())
                if not m or not cep or len(re.sub(r"\D", "", cep)) != 8:
                    continue
                out.append({"lat": la, "lng": lo, "rua": m.group(1), "num": m.group(2),
                            "cep": re.sub(r"\D", "", cep), "end": a, "cidade": cid or ""})
    return out
