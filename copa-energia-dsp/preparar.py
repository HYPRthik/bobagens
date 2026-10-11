#!/usr/bin/env python3
"""
Separa a base Copa Energia por CNAE e monta as duas audiencias.

A base NAO tem logradouro: so nome, CNPJ, cidade, UF, CEP e coordenada. A linha
de endereco fica "<nome> <cidade> <UF> <CEP>", e o CEP de 8 digitos e o que
aponta a rua — 87.779 das 96.038 linhas do grupo maior tem CEP especifico.

Grupo GLP (CNAE 47.84-9/00): 3.169 locais, cabe numa audiencia so.
Demais CNAEs: 96.038 locais em 73 cidades, nao cabe. Reduz para 10.000 com cota
igual por cidade, decidido com o usuario.

A cota usa reparticao por agua: cidade com menos que a cota entra inteira e sua
sobra volta para o bolo das demais. Curitiba tem 10.211 locais sozinha — sem
isso, uma cidade levaria a audiencia inteira.

Dentro da cidade, entra quem tem melhor sinal de geocodificacao:
CEP especifico > coordenada no numero > estabelecimento fisico mais alto.

Uso:  python3 preparar.py <base.csv>
"""
import collections
import csv
import os
import re
import sys
import importlib.util
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
CNAE_GLP = "47.84-9/00"
# usa a MESMA normalizacao do gerador: deduplicar com chave diferente da dele
# deixaria o total abaixo do teto depois que ele deduplicasse de novo
_spec = importlib.util.spec_from_file_location(
    "gf", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "geofence-yahoo", "geofence.py"))
_gf = importlib.util.module_from_spec(_spec)
_sa = sys.argv
sys.argv = ["gf", "x"]
try:
    _spec.loader.exec_module(_gf)
except SystemExit:
    pass
sys.argv = _sa


def linha_dsp(r):
    """A linha exata que a DSP vai ver."""
    return _gf.ascii_puro(" ".join(x for x in (r["nome"], r["cidade"], r["uf"],
                                               r["cep"], "Brazil") if x))
TETO = 10000
csv.field_size_limit(10 ** 7)


def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()


def cep_especifico(cep):
    d = re.sub(r"\D", "", str(cep))
    return len(d) == 8 and not d.endswith("000")


def qualidade(r):
    """Maior e melhor. Sinais que a propria base traz sobre a precisao do ponto."""
    try:
        fisico = int(re.sub(r"\D", "", r["fisico"]) or 0)
    except ValueError:
        fisico = 0
    return (1 if cep_especifico(r["cep"]) else 0,
            1 if r["precisao"].strip().lower() == "numero" else 0,
            fisico)


def cota_por_cidade(por_cidade, teto):
    """Reparticao por agua: distribui o teto o mais igualmente possivel entre as
    cidades. Quem tem menos que a cota entra inteiro e devolve a sobra."""
    restante, cidades = teto, dict(por_cidade)
    fechadas = {}
    while cidades:
        justo = restante // len(cidades)
        if justo == 0:
            break
        pequenas = {c: n for c, n in cidades.items() if n <= justo}
        if not pequenas:
            for c in cidades:
                fechadas[c] = justo
                restante -= justo
            # o que sobrou da divisao inteira vai para as maiores, 1 a 1
            for c in sorted(cidades, key=lambda x: -cidades[x]):
                if restante <= 0:
                    break
                if fechadas[c] < cidades[c]:
                    fechadas[c] += 1
                    restante -= 1
            cidades = {}
            break
        for c, n in pequenas.items():
            fechadas[c] = n
            restante -= n
            del cidades[c]
    return fechadas


# ------------------------------------------------------------------ leitura
fonte = sys.argv[1]
grupos = {"glp": [], "demais": []}
with open(fonte, encoding="utf-8-sig", errors="replace", newline="") as f:
    rd = csv.reader(f)
    hdr = next(rd)
    i = {h: n for n, h in enumerate(hdr)}
    for r in rd:
        if not any(x.strip() for x in r):
            continue
        reg = {"nome": r[i["name"]].strip(), "cidade": r[i["city"]].strip(),
               "uf": r[i["uf"]].strip(), "cep": r[i["cep"]].strip(),
               "lat": r[i["lat"]].strip(), "lng": r[i["lng"]].strip(),
               "cnpj": r[i["CNPJ"]].strip(), "cnae": r[i["CNAE"]].strip(),
               "porte": r[i["Porte"]].strip(),
               "fisico": r[i["Estabelecimento físico (0–100)"]].strip(),
               "precisao": r[i["Precisão da coordenada"]].strip()}
        grupos["glp" if CNAE_GLP in reg["cnae"] else "demais"].append(reg)

print(f"separacao por CNAE: GLP {len(grupos['glp'])}  |  demais {len(grupos['demais'])}")

# so o necessario: uma coluna de texto longo a mais (CNAE) e farejada como
# endereco pelo gerador, e a descricao da CNAE vira o endereco inteiro
CAMPOS = ["nome", "cidade", "uf", "cep", "lat", "lng"]
CAMPOS_REF = CAMPOS + ["cnpj", "cnae", "porte", "fisico", "precisao"]
os.makedirs(os.path.join(BASE, "preparado"), exist_ok=True)

for nome_g, regs in grupos.items():
    # dedup pela linha que a DSP vai ver; o resto do registro nao a distingue
    vistos, unicos = set(), []
    for r in sorted(regs, key=qualidade, reverse=True):
        chave = linha_dsp(r)
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(r)
    dup = len(regs) - len(unicos)

    por_cidade = collections.Counter(f"{r['cidade']}/{r['uf']}" for r in unicos)
    if len(unicos) <= TETO:
        escolhidos, nota = unicos, "cabe inteiro no teto"
    else:
        cotas = cota_por_cidade(por_cidade, TETO)
        usado = collections.Counter()
        escolhidos = []
        for r in sorted(unicos, key=qualidade, reverse=True):
            c = f"{r['cidade']}/{r['uf']}"
            if usado[c] < cotas.get(c, 0):
                usado[c] += 1
                escolhidos.append(r)
        faixa = sorted(cotas.values())
        nota = (f"cota por cidade: {faixa[0]} a {faixa[-1]} locais "
                f"({sum(1 for v in cotas.values() if v == faixa[-1])} cidades no teto da cota)")

    p = os.path.join(BASE, "preparado", f"{nome_g}.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        w.writerows(escolhidos)
    with open(os.path.join(BASE, "preparado", f"{nome_g}_referencia.csv"), "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_REF, delimiter=";")
        w.writeheader()
        w.writerows(escolhidos)
    print(f"\n{nome_g}: {len(regs)} linhas -> {len(unicos)} unicas (dup {dup}) "
          f"-> {len(escolhidos)} escolhidas")
    print(f"   {nota}")
    cidades_rep = {f"{r['cidade']}/{r['uf']}" for r in escolhidos}
    print(f"   cidades representadas: {len(cidades_rep)}")
    cep_ok = sum(1 for r in escolhidos if cep_especifico(r["cep"]))
    print(f"   com CEP especifico: {cep_ok}/{len(escolhidos)}")
