#!/usr/bin/env python3
"""
Prepara a lista de concessionarias Nissan para o upload de geofencing da Yahoo DSP.

Regras da DSP aplicadas aqui:
  - TXT ou CSV, UM ENDERECO POR LINHA/CELULA (a DSP le a linha inteira como
    um endereco de texto livre — nao e uma planilha de colunas).
  - Maximo 10.000 enderecos por line item e por arquivo.
  - Caracteres especiais podem dar erro (e, a, c, #, -). A saida e ASCII puro:
    somente letras, digitos e espaco.
  - Concessionaria nao esta na lista de categorias que aceitam so o nome
    (Airports, Arena/Stadiums, Universities/Colleges), entao vai endereco completo.

Alem disso reconstroi as coordenadas do arquivo de origem, que vieram destruidas
por um locale de virgula decimal (-229.753.965 era -22.9753965). Cada valor e
validado contra a bounding box da UF do proprio endereco.

Uso:  python3 build_nissan.py origem.csv
"""
import collections
import csv
import io
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "origem_nissan.csv")
PAIS = "Brazil"

# bounding box por UF (lat_min, lat_max, lon_min, lon_max), com folga
UFBOX = {
 "AC": (-11.2, -7.0, -74.1, -66.5), "AL": (-10.6, -8.7, -38.3, -35.1),
 "AM": (-9.9, 2.3, -73.9, -56.0),   "AP": (-1.3, 4.5, -55.0, -49.8),
 "BA": (-18.5, -8.4, -46.7, -37.2), "CE": (-7.9, -2.7, -41.5, -37.2),
 "DF": (-16.1, -15.4, -48.4, -47.2),"ES": (-21.4, -17.8, -42.0, -39.6),
 "GO": (-19.6, -12.3, -53.3, -45.8),"MA": (-10.4, -0.9, -48.9, -41.7),
 "MG": (-23.0, -14.1, -51.2, -39.8),"MS": (-24.2, -17.1, -58.3, -50.8),
 "MT": (-18.2, -7.2, -61.8, -50.1), "PA": (-9.9, 2.7, -59.0, -45.9),
 "PB": (-8.4, -5.9, -38.9, -34.7),  "PE": (-9.6, -7.2, -41.5, -34.7),
 "PI": (-11.0, -2.6, -46.1, -40.2), "PR": (-26.8, -22.4, -54.7, -47.9),
 "RJ": (-23.5, -20.7, -45.0, -40.9),"RN": (-7.1, -4.7, -38.7, -34.9),
 "RO": (-13.8, -7.9, -66.9, -59.7), "RR": (-1.7, 5.4, -64.9, -58.8),
 "RS": (-33.9, -27.0, -57.8, -49.6),"SC": (-29.5, -25.9, -54.0, -48.2),
 "SE": (-11.7, -9.4, -38.3, -36.3), "SP": (-25.4, -19.7, -53.2, -44.1),
 "TO": (-13.6, -5.1, -50.9, -45.6),
}
# faixas de CEP por UF, para conferir a UF lida do texto
CEPFX = [("SP",1000,19999),("RJ",20000,28999),("ES",29000,29999),("MG",30000,39999),
 ("BA",40000,48999),("SE",49000,49999),("PE",50000,56999),("AL",57000,57999),
 ("PB",58000,58999),("RN",59000,59999),("CE",60000,63999),("PI",64000,64999),
 ("MA",65000,65999),("PA",66000,68899),("AP",68900,68999),("AM",69000,69299),
 ("RR",69300,69389),("AM",69400,69899),("AC",69900,69999),("DF",70000,72799),
 ("GO",72800,72999),("DF",73000,73699),("GO",73700,76799),("RO",76800,76999),
 ("TO",77000,77999),("MT",78000,78899),("MS",79000,79999),("PR",80000,87999),
 ("SC",88000,89999),("RS",90000,99999)]


def uf_do_cep(c):
    for uf, a, b in CEPFX:
        if a <= c <= b:
            return uf
    return None


def ascii_puro(s):
    """Remove acentos e tudo que nao seja letra, digito ou espaco."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", s)).strip()


def candidatos(tok, faixa):
    """Reconstroi um numero destruido por locale de virgula decimal.
    Devolve so os candidatos que caem dentro da faixa da UF."""
    lo, hi = faixa
    out = []
    try:
        v = float(tok)                     # <=1 ponto: nunca passou pelo separador
        if lo <= v <= hi:                  # de milhar, entao e o valor original
            return [v]
    except ValueError:
        pass
    neg = tok.strip().startswith("-")
    d = re.sub(r"\D", "", tok)
    for k in (1, 2):                       # 1 ou 2 digitos na parte inteira
        if len(d) <= k:
            continue
        v = float(d[:k] + "." + d[k:])
        v = -v if neg else v
        if lo <= v <= hi and v not in out:
            out.append(v)
    return out


def fmt(v, d=6):
    if v is None:
        return ""
    return f"{round(v, d):.{d}f}".rstrip("0").rstrip(".") or "0"


# ------------------------------------------------------------------ leitura
rows = list(csv.reader(io.StringIO(open(SRC, encoding="utf-8-sig").read()), delimiter=";"))
header, body = rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]
assert header[:4] == ["name", "address", "lat", "lng"], header

regs, avisos = [], []
for i, r in enumerate(body, start=2):
    nome, ender = r[0].strip(), r[1].strip()

    m = re.match(r"^\s*(\d{5})-?(\d{3})\s+(.*)$", ender)
    if not m:
        avisos.append(f"L{i} {nome}: sem CEP reconhecivel"); continue
    cep, resto = m.group(1) + m.group(2), m.group(3)

    ufs = [x for x in re.finditer(r"\b([A-Z]{2})\b", resto) if x.group(1) in UFBOX]
    if not ufs:
        avisos.append(f"L{i} {nome}: sem UF reconhecivel"); continue
    ult = ufs[-1]
    logradouro, uf, cidade = resto[:ult.start()].strip(), ult.group(1), resto[ult.end():].strip()
    if not logradouro or not cidade:
        avisos.append(f"L{i} {nome}: logradouro ou cidade vazio"); continue

    uf_cep = uf_do_cep(int(cep[:5]))
    if uf_cep and uf_cep != uf:
        avisos.append(f"L{i} {nome}: endereco diz {uf} mas o CEP {cep} indica {uf_cep}")

    la0, la1, lo0, lo1 = UFBOX[uf]
    cla, clo = candidatos(r[2], (la0, la1)), candidatos(r[3], (lo0, lo1))
    if len(cla) != 1 or len(clo) != 1:
        # o upload da DSP usa so o endereco, entao o registro continua valendo;
        # a coordenada fica vazia na conferencia para ser conferida a mao
        avisos.append(f"L{i} {nome}: coordenada ambigua lat={cla} lon={clo} "
                      f"— endereco mantido, coordenada em branco")
        cla, clo = (cla[:1] or [None]), (clo[:1] or [None])
        if len(candidatos(r[2], (la0, la1))) > 1:
            cla = [None]
        if len(candidatos(r[3], (lo0, lo1))) > 1:
            clo = [None]

    # endereco em ordem convencional brasileira, ASCII puro, sem hifen
    linha = ascii_puro(f"{logradouro} {cidade} {uf} {cep} {PAIS}")
    regs.append({"linha_origem": i, "nome": nome, "endereco_original": ender,
                 "endereco_dsp": linha, "cep": cep, "uf": uf, "cidade": cidade,
                 "lat": cla[0], "lon": clo[0]})

# ------------------------------------------------------------------ saida
vistos, unicos = set(), []
for g in regs:
    if g["endereco_dsp"] in vistos:
        continue
    vistos.add(g["endereco_dsp"]); unicos.append(g)

os.makedirs(os.path.join(BASE, "upload"), exist_ok=True)
txt = os.path.join(BASE, "upload", "nissan_varejo_enderecos.txt")
with open(txt, "w", newline="\r\n", encoding="ascii") as f:
    f.write("\n".join(g["endereco_dsp"] for g in unicos) + "\n")

csv_um = os.path.join(BASE, "upload", "nissan_varejo_enderecos.csv")
with open(csv_um, "w", newline="", encoding="ascii") as f:
    w = csv.writer(f, lineterminator="\r\n")
    for g in unicos:
        w.writerow([g["endereco_dsp"]])

# arquivo de conferencia (nao e o upload)
conf = os.path.join(BASE, "conferencia_nissan.csv")
with open(conf, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["linha_origem", "name", "endereco_original", "lat_original", "lng_original",
                "lat_corrigida", "lng_corrigida", "cidade", "uf", "cep", "endereco_para_dsp"])
    orig = {i: (r[2], r[3]) for i, r in enumerate(body, start=2)}
    for g in regs:
        o = orig[g["linha_origem"]]
        w.writerow([g["linha_origem"], g["nome"], g["endereco_original"], o[0], o[1],
                    fmt(g["lat"]), fmt(g["lon"]), g["cidade"], g["uf"], g["cep"], g["endereco_dsp"]])

# ------------------------------------------------------------------ validacao
falhas = []
b = open(txt, "rb").read()
linhas = [l for l in b.split(b"\r\n") if l.strip()]
if len(linhas) != len(unicos):
    falhas.append("txt: contagem de linhas nao bate")
if len(linhas) > 10000:
    falhas.append("txt: passa do limite de 10.000 enderecos")
for l in linhas:
    s = l.decode("ascii")
    if re.search(r"[^A-Za-z0-9 ]", s):
        falhas.append(f"txt: caractere proibido em {s!r}"); break
    if "  " in s or s != s.strip():
        falhas.append(f"txt: espacamento irregular em {s!r}"); break
    if not re.search(r"\b\d{8}\b", s):
        falhas.append(f"txt: sem CEP em {s!r}"); break
    if not s.endswith(PAIS):
        falhas.append(f"txt: sem pais em {s!r}"); break
for g in regs:
    la0, la1, lo0, lo1 = UFBOX[g["uf"]]
    if g["lat"] is None or g["lon"] is None:
        continue
    if not (la0 <= g["lat"] <= la1 and lo0 <= g["lon"] <= lo1):
        falhas.append(f"{g['nome']}: coordenada fora da UF {g['uf']}")

print(f"origem            : {len(body)} concessionarias")
print(f"processadas       : {len(regs)}")
print(f"enderecos no TXT  : {len(unicos)}  (duplicatas removidas: {len(regs)-len(unicos)})")
print(f"UFs               : {len(collections.Counter(g['uf'] for g in regs))}")
print(f"coordenadas recon.: {sum(1 for g in regs if g['lat'] is not None)} de {len(regs)}")
if avisos:
    print(f"\navisos ({len(avisos)}):")
    for a in avisos:
        print("  -", a)
print("\nvalidacao         : " + ("TUDO OK" if not falhas else "FALHAS:\n  " + "\n  ".join(falhas)))
sys.exit(1 if falhas else 0)
