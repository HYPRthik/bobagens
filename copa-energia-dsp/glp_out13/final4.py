#!/usr/bin/env python3
"""
v4 da audiencia GLP. O retorno do v3 (684 de 1.381 = 49,5%) mediu as celulas:

    aprovadas antes .................. 233/233 = 100%
    N1  rua 100 cidade UF CEP ........ 183/250 =  73,2%   <- vence
    N4  rua 100 bairro cidade UF CEP . 176/249 =  70,7%
    N2  rua 1 cidade UF CEP ..........  74/250 =  29,6%
    F1  numero real da faixa + bairro   15/120 =  12,5%
    N3  rua bairro (sem numero) .......  3/250 =   1,2%

Tres coisas ficaram provadas:
  1. O numero de porta 100 INVENTADO (73%) bate o numero real da faixa do
     complemento (61% no v2). Um numero baixo existe em quase toda rua; o
     inicio da faixa cai em limite de trecho que o geocodificador nao resolve.
  2. O valor importa muito: 100 da 73%, 1 da 30%.
  3. O bairro atrapalha de leve (73,2 contra 70,7) e nao salva nada sozinho.

Entao o v4 leva a forma vencedora para tudo que falhou e ainda nao tentou o
100, e usa as 68 linhas que falharam COM 100 para testar outros valores.

Uso:  python3 final4.py
"""
import collections, csv, importlib.util, io, os, re, sys

BASE = "/home/user/bobagens/copa-energia-dsp/glp_out13"
csv.field_size_limit(10 ** 7)
_spec = importlib.util.spec_from_file_location("gf", "/home/user/bobagens/geofence-yahoo/geofence.py")
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv; sys.argv = ["gf", "x"]
try: _spec.loader.exec_module(_gf)
except SystemExit: pass
sys.argv = _sa

ret = {r[0].strip(): (r[1].strip() if len(r) > 1 else "")
       for r in csv.reader(io.StringIO(open(os.path.join(BASE, "retorno_v3", "retorno.csv"),
                                            encoding="utf-8-sig").read())) if r}
v3 = list(csv.DictReader(io.StringIO(open(os.path.join(BASE, "upload", "copa_glp_v3_conferencia.csv"),
                                          encoding="utf-8-sig").read()), delimiter=";"))

ok = [c for c in v3 if ret.get(c["linha_dsp"]) == "successful"]
ko = [c for c in v3 if ret.get(c["linha_dsp"]) != "successful"]
# quem ainda nao tentou o 100 na forma vencedora
nunca_100 = [c for c in ko if c["celula"][:2] in ("N2", "N3") or c["celula"].startswith("F1")]
# N4 falhou com 100 + bairro: tirar o bairro e uma tentativa nova
sem_bairro = [c for c in ko if c["celula"].startswith("N4")]
# N1 falhou com exatamente a forma vencedora: so resta variar o numero
duro = sorted([c for c in ko if c["celula"].startswith("N1")], key=lambda c: c["cep"])
sem_rua = [c for c in ko if c["celula"].startswith("nome do POI")]
OUTROS = ["50", "200", "500", "1000"]

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
                    "celula_anterior": c.get("celula", "")})


def vencedora(c, numero="100"):
    return _gf.ascii_puro(" ".join(x for x in (c["logradouro_do_cep"], numero,
                                               c["cidade"], c["uf"], c["cep"], "Brazil") if x))


for c in ok:                                      # trava: nada reescreve o aprovado
    põe(c["linha_dsp"], "aprovada pela DSP (mantida igual)", c, c["numero_inventado"] == "sim")

for c in nunca_100 + sem_bairro:
    põe(vencedora(c), "forma vencedora: rua 100 cidade UF CEP", c, True)

for i, c in enumerate(duro):                      # falhou com 100: testa outro numero
    n = OUTROS[i % len(OUTROS)]
    põe(vencedora(c, n), f"falhou com 100, tentando numero {n}", c, True)

for c in sem_rua:
    põe(c["linha_dsp"], "nome do POI (CEP sem registro)", c, False)

p = os.path.join(BASE, "upload", "copa_glp_v4")
open(p + ".txt", "w", newline="", encoding="ascii").write("\r\n".join(linhas) + "\r\n")
with open(p + ".csv", "w", newline="", encoding="ascii") as f:
    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in linhas])
with open(p + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(detalhe[0]), delimiter=";")
    w.writeheader(); w.writerows(detalhe)

print(f"{len(linhas)} linhas\n")
for k, v in sorted(conta.items(), key=lambda x: -x[1]):
    print(f"   {v:5d}  {k}")
inv = sum(1 for d in detalhe if d["numero_inventado"] == "sim")
print(f"\nlinhas com numero de porta inventado: {inv}")
ruins = [x for x in linhas if re.search(r"[^A-Za-z0-9 ]", x)]
print(f"ASCII limpo: {not ruins} | <=10.000: {len(linhas) <= 10000}")
