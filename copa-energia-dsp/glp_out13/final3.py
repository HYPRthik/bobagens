#!/usr/bin/env python3
"""
v3 da audiencia GLP. O retorno do v2 mediu o numero de porta em mil linhas:

    rua + numero ............ 188/308 = 61%
    rua SEM numero ...........  1/1026 = 0,1%
    ja aprovadas antes ....... 44/44  = 100%

Sem numero de porta a linha nao vale nada. E 949 das 1.026 linhas sem numero
tem CEP sem complemento — ou seja, a rua inteira cabe num CEP so, entao nao ha
CEP vizinho de onde emprestar a faixa (testei 40 casos: 0 de 40).

Como essas 1.025 linhas hoje valem 0,1%, qualquer coisa que se tente nelas e
ganho. Entao o v3 divide as que falharam em celulas de estrategia e o proprio
retorno mede qual funciona — sem gastar um teste a parte, porque toda linha
continua sendo uma loja real da audiencia.

    N1  rua 100 cidade UF CEP            numero inventado
    N2  rua 1 cidade UF CEP              numero inventado
    N3  rua bairro cidade UF CEP         bairro em vez de numero
    N4  rua 100 bairro cidade UF CEP     os dois
    F1  rua numero bairro cidade UF CEP  as 123 que ja tinham numero e falharam

ATENCAO: em N1, N2 e N4 o numero de porta e INVENTADO. A loja esta naquela rua,
e o CEP cobre a rua inteira, entao o ponto cai dentro do trecho certo — mas nao
e o numero da loja. A conferencia marca isso em `numero_inventado`.

As 233 linhas que a DSP aprovou vao byte a byte como foram.

Uso:  python3 final3.py
"""
import collections, csv, importlib.util, io, json, os, re, sys

BASE = "/home/user/bobagens/copa-energia-dsp/glp_out13"
csv.field_size_limit(10 ** 7)
_spec = importlib.util.spec_from_file_location("gf", "/home/user/bobagens/geofence-yahoo/geofence.py")
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv; sys.argv = ["gf", "x"]
try: _spec.loader.exec_module(_gf)
except SystemExit: pass
sys.argv = _sa

ret = {r[0].strip(): (r[1].strip() if len(r) > 1 else "")
       for r in csv.reader(io.StringIO(open(os.path.join(BASE, "retorno_v2", "retorno.csv"),
                                            encoding="utf-8-sig").read())) if r}
conf = list(csv.DictReader(io.StringIO(open(os.path.join(BASE, "upload", "copa_glp_v2_conferencia.csv"),
                                            encoding="utf-8-sig").read()), delimiter=";"))

aprov = [c for c in conf if ret.get(c["linha_dsp"]) == "successful"]
falhou = [c for c in conf if ret.get(c["linha_dsp"]) != "successful"]
sem_num = sorted([c for c in falhou if c["tem_numero"] != "sim" and c["logradouro_do_cep"]],
                 key=lambda c: c["cep"])
com_num = [c for c in falhou if c["tem_numero"] == "sim"]
sem_rua = [c for c in falhou if not c["logradouro_do_cep"]]

CELULAS = [("N1 rua + numero 100", lambda c: [c["logradouro_do_cep"], "100"], True),
           ("N2 rua + numero 1", lambda c: [c["logradouro_do_cep"], "1"], True),
           ("N3 rua + bairro", lambda c: [c["logradouro_do_cep"], c["bairro_do_cep"]], False),
           ("N4 rua + numero 100 + bairro",
            lambda c: [c["logradouro_do_cep"], "100", c["bairro_do_cep"]], True)]

linhas, detalhe, vistos = [], [], set()
conta = collections.Counter()


def põe(linha, celula, c, inventado):
    if not linha or linha in vistos:
        return
    vistos.add(linha); linhas.append(linha); conta[celula] += 1
    detalhe.append({"linha_dsp": linha, "celula": celula,
                    "numero_inventado": "sim" if inventado else "nao",
                    "loja": c.get("loja", ""), "cnpj": c.get("cnpj", ""),
                    "cidade": c.get("cidade", ""), "uf": c.get("uf", ""), "cep": c.get("cep", ""),
                    "logradouro_do_cep": c.get("logradouro_do_cep", ""),
                    "bairro_do_cep": c.get("bairro_do_cep", "")})


for c in aprov:                                   # trava: nada reescreve o aprovado
    põe(c["linha_dsp"], "aprovada pela DSP (mantida igual)", c, False)

for i, c in enumerate(sem_num):                   # round-robin pelo CEP: celulas comparaveis
    nome, monta, inv = CELULAS[i % len(CELULAS)]
    partes = monta(c) + [c["cidade"], c["uf"], c["cep"], "Brazil"]
    põe(_gf.ascii_puro(" ".join(x for x in partes if x)), nome, c, inv)

for c in com_num:
    # Nao remontar: a linha v2 ja tem a rua e o numero certos. Remontar foi o que
    # transformou "Rodovia BR 101 5599" em "Rodovia BR 101 101" — o primeiro
    # numero da linha e a sigla da rodovia, nao a porta. Aqui so se insere o
    # bairro antes do sufixo conhecido <cidade> <UF> <CEP> Brazil.
    sufixo = _gf.ascii_puro(" ".join(x for x in (c["cidade"], c["uf"], c["cep"], "Brazil") if x))
    if not c["linha_dsp"].endswith(sufixo) or not c["bairro_do_cep"]:
        continue
    rua_num = c["linha_dsp"][: -len(sufixo)].strip()
    linha = _gf.ascii_puro(" ".join((rua_num, c["bairro_do_cep"], sufixo)))
    põe(linha, "F1 tinha numero, falhou: + bairro", c, False)

for c in sem_rua:                                 # CEP sem registro: so resta o nome
    põe(c["linha_dsp"], "nome do POI (CEP sem registro)", c, False)

p = os.path.join(BASE, "upload", "copa_glp_v3")
open(p + ".txt", "w", newline="", encoding="ascii").write("\r\n".join(linhas) + "\r\n")
with open(p + ".csv", "w", newline="", encoding="ascii") as f:
    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
with open(p + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(detalhe[0]), delimiter=";")
    w.writeheader(); w.writerows(detalhe)

print(f"{len(linhas)} linhas\n")
for k, v in sorted(conta.items()):
    print(f"   {v:5d}  {k}")
inv = sum(1 for d in detalhe if d["numero_inventado"] == "sim")
print(f"\nlinhas com numero de porta INVENTADO: {inv}")
ruins = [x for x in linhas if re.search(r"[^A-Za-z0-9 ]", x)]
print(f"ASCII limpo: {not ruins} | <=10.000: {len(linhas) <= 10000}")
