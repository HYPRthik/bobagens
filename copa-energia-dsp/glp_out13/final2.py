#!/usr/bin/env python3
"""
Monta a audiencia GLP usando o logradouro real de cada CEP.

O retorno da DSP para o arquivo anterior mediu o que faltava saber:

    com rua + numero ....... 37/39 = 95%
    so com nome do POI ..... 6/1534 = 0,4%

Ou seja: o logradouro e tudo. O arquivo anterior so tinha rua em 44 linhas
porque o indice vinha das bases ja processadas aqui. Agora o logradouro vem do
espelho aberto do OpenCEP no GitHub (gpfconfea/banco-ceps), que o proxy alcanca
— as APIs de CEP continuam bloqueadas, o raw do GitHub nao e.

Numero de porta: o dataset nao traz, mas o campo `complemento` costuma trazer a
faixa do trecho ("de 2373 a 2819 - lado impar"). Onde ela existe, uso o inicio
da faixa — e um numero real daquele trecho de rua, mesma logica ja usada e
declarada para os pontos de OOH: o geofence e por raio sobre o trecho.

Conferencia cruzada: cada CEP do dataset tem coordenada, e a base da Copa tem a
coordenada da loja. A distancia entre as duas diz se o CEP confere.

Uso:  python3 final2.py
"""
import collections, csv, importlib.util, io, json, math, os, re, sys

BASE = "/home/user/bobagens/copa-energia-dsp/glp_out13"
RAIZ = "/home/user/bobagens"
CEPDATA = os.path.join(BASE, "cepdata")
csv.field_size_limit(10 ** 7)

_spec = importlib.util.spec_from_file_location("gf", RAIZ + "/geofence-yahoo/geofence.py")
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv; sys.argv = ["gf", "x"]
try: _spec.loader.exec_module(_gf)
except SystemExit: pass
sys.argv = _sa

norm = lambda s: re.sub(r"[^a-z]", "", _gf.sem_acento(s or "").lower())


def num_da_faixa(complemento):
    """Primeiro numero de porta citado na faixa do trecho, se houver."""
    c = complemento or ""
    if not re.search(r"\d", c):
        return ""
    m = re.search(r"\bde\s+(\d{1,6})", c) or re.search(r"\bat[eé]\s+(\d{1,6})", c)
    if not m:
        m = re.search(r"(\d{1,6})", c)
    return m.group(1) if m else ""


def dist_km(a, b, c, d):
    try:
        a, b, c, d = map(float, (a, b, c, d))
    except (TypeError, ValueError):
        return None
    p = math.pi / 180
    return 12742 * math.asin(math.sqrt(
        0.5 - math.cos((c - a) * p) / 2
        + math.cos(a * p) * math.cos(c * p) * (1 - math.cos((d - b) * p)) / 2))


# ---- dataset de CEP (dado de terceiro: parser estrito, nada executado) -------
cep_db = {}
for fn in os.listdir(CEPDATA):
    if not fn.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(CEPDATA, fn), encoding="utf-8"))
    except Exception:
        continue
    if isinstance(d, dict) and re.fullmatch(r"\d{8}", str(d.get("cep", "")).replace("-", "")):
        cep_db[str(d["cep"]).replace("-", "")] = d

# ---- indice proprio, so para emprestar numero de porta -----------------------
BASES = ["glp-dsp/origem_glp.csv", "farmacias-dsp/origem_farmacias.csv",
         "beleza-dsp/origem_beleza.csv", "cinemas-dsp/origem_cinemas.csv",
         "pois-jlr-dsp/origem_pois_completa.csv", "mercadolivre-ooh-dsp/origem_ml_ooh.csv",
         "campari-negroni-dsp/origem/pdvs_base_completa.csv"]
num_idx = {}
for b in BASES:
    p = os.path.join(RAIZ, b)
    if not os.path.exists(p):
        continue
    for r in csv.DictReader(io.StringIO(open(p, encoding="utf-8-sig").read())):
        a = (r.get("formatted_address") or "").strip()
        d = re.sub(r"\D", "", r.get("cep") or "")
        if a and len(d) == 8 and d not in num_idx:
            miolo, _c, _u, _p, _s = _gf.partir_endereco(a)
            _rua, _bai = _gf.partir_numero(_gf.limpar_ruido(_gf.expandir_tipo(miolo)))
            m = re.search(r"\b(\d{1,6})\b", _rua)
            if m:
                num_idx[d] = m.group(1)

alvo = list(csv.DictReader(io.StringIO(
    open(os.path.join(BASE, "origem.csv"), encoding="utf-8-sig").read())))

# ---- trava dos aprovados ----------------------------------------------------
# 44 linhas do upload anterior voltaram "successful". Elas nao sao reescritas:
# vao byte a byte como foram, e a loja correspondente nao gera linha nova. E o
# mesmo mecanismo do --aprovados do template — nenhuma troca de fonte de dados
# pode regredir o que a DSP ja aceitou.
aprovadas, loja_aprovada = [], {}
ret = os.path.join(BASE, "retorno_final", "retorno.csv")
conf_ant = os.path.join(BASE, "upload", "copa_glp_final_conferencia.csv")
if os.path.exists(ret) and os.path.exists(conf_ant):
    ok = {r[0].strip() for r in csv.reader(io.StringIO(open(ret, encoding="utf-8-sig").read()))
          if len(r) > 1 and r[1].strip() == "successful"}
    for c in csv.DictReader(io.StringIO(open(conf_ant, encoding="utf-8-sig").read()), delimiter=";"):
        if c["linha_dsp"] in ok:
            loja_aprovada[c["cnpj"]] = c["linha_dsp"]
    aprovadas = sorted(set(loja_aprovada.values()))

linhas, detalhe, vistos = [], [], set()
conta, fonte_num = collections.Counter(), collections.Counter()
for linha in aprovadas:
    vistos.add(linha); linhas.append(linha)
    conta["ja aprovada pela DSP (mantida igual)"] += 1
    detalhe.append({"linha_dsp": linha, "origem": "ja aprovada pela DSP (mantida igual)",
                    "tem_numero": "", "fonte_do_numero": "", "loja": "", "cnpj": "",
                    "cidade": "", "uf": "", "cep": "", "logradouro_do_cep": "",
                    "bairro_do_cep": "", "km_entre_cep_e_loja": ""})

for r in alvo:
    if r["CNPJ"] in loja_aprovada:
        continue
    d = re.sub(r"\D", "", r["cep"])
    rec = cep_db.get(d)
    log = (rec.get("logradouro") or "").strip() if rec else ""
    numero, de_onde = "", ""
    if log:
        numero = num_da_faixa(rec.get("complemento"))
        de_onde = "faixa do complemento" if numero else ""
        if not numero and d in num_idx:
            numero, de_onde = num_idx[d], "vizinho no mesmo CEP"
    # cidade: o CEP arbitra, como no resto do template
    cidade = (rec.get("localidade") or "").strip() if rec else ""
    cidade = cidade or r["city"]
    uf = ((rec.get("uf") or "").strip() if rec else "") or r["uf"]
    km = dist_km(r.get("lat") or r.get("latitude"), r.get("lng") or r.get("longitude"),
                 (rec or {}).get("latitude"), (rec or {}).get("longitude"))

    if log:
        partes = [log, numero, cidade, uf, d, "Brazil"]
        origem = "logradouro do CEP" + (" + numero" if numero else " (sem numero)")
    else:
        partes = [r["name"], cidade, uf, d, "Brazil"]
        origem = "nome do POI (CEP sem logradouro)"
    linha = _gf.ascii_puro(" ".join(x for x in partes if x))
    if linha in vistos:
        continue
    vistos.add(linha)
    conta[origem] += 1
    if de_onde:
        fonte_num[de_onde] += 1
    detalhe.append({"linha_dsp": linha, "origem": origem, "tem_numero": "sim" if numero else "nao",
                    "fonte_do_numero": de_onde, "loja": r["name"], "cnpj": r["CNPJ"],
                    "cidade": cidade, "uf": uf, "cep": d,
                    "logradouro_do_cep": log, "bairro_do_cep": (rec or {}).get("bairro", ""),
                    "km_entre_cep_e_loja": "" if km is None else f"{km:.2f}"})
    linhas.append(linha)

for x in detalhe:                       # conferencia sai na ordem do arquivo
    pass
p = os.path.join(BASE, "upload", "copa_glp_v2")
open(p + ".txt", "w", newline="", encoding="ascii").write("\r\n".join(linhas) + "\r\n")
with open(p + ".csv", "w", newline="", encoding="ascii") as f:
    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
with open(p + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(detalhe[0]), delimiter=";")
    w.writeheader(); w.writerows(detalhe)

print(f"CEPs no dataset: {len(cep_db)}")
print(f"origem: {len(alvo)} lojas -> {len(linhas)} linhas unicas\n")
for k, v in conta.most_common():
    print(f"   {v:5d}  {k}")
print("\nde onde veio o numero de porta:")
for k, v in fonte_num.most_common():
    print(f"   {v:5d}  {k}")
longe = [x for x in detalhe if x["km_entre_cep_e_loja"] and float(x["km_entre_cep_e_loja"]) > 5]
print(f"\nCEP a mais de 5 km da coordenada da loja: {len(longe)}")
ruins = [x for x in linhas if re.search(r"[^A-Za-z0-9 ]", x)]
print(f"ASCII limpo: {not ruins} | <=10.000: {len(linhas) <= 10000}")
