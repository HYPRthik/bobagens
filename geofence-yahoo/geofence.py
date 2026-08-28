#!/usr/bin/env python3
"""
geofence.py — prepara qualquer lista de POIs para o upload de geofencing da Yahoo DSP.

    python3 geofence.py entrada.csv
    python3 geofence.py entrada.csv -o saida/ --nome campanha_x --raio 0.19

Regras da DSP implementadas aqui
--------------------------------
  * TXT/CSV com UM ENDERECO POR LINHA. A DSP le a linha inteira como endereco de
    texto livre — nao e uma planilha de colunas. Mandar coordenada nao funciona.
  * Maximo 10.000 enderecos por line item e por arquivo (a saida se divide sozinha).
  * Caracteres especiais podem dar erro (e, a, c, #, -). A saida e ASCII puro:
    apenas letras, digitos e espaco.
  * So Airports, Arena/Stadiums e Universities/Colleges podem ir com o NOME do POI
    em vez do endereco. Qualquer outra categoria exige endereco completo.
  * O raio e em MILHAS (radiusUnit: MILES). 0.3 milha = 483 m; 300 m = 0.19 milha.

O que o script resolve sozinho
------------------------------
  * Encoding (UTF-8 com/sem BOM, cp1252, latin-1) e separador (, ; tab |).
  * Descobre as colunas pelo cabecalho (endereco, nome, cidade, UF, CEP, lat, lon)
    em portugues ou ingles; se nao houver cabecalho util, inspeciona o conteudo.
  * Remonta o endereco em ordem convencional quando ele vem quebrado em colunas.
  * Conserta coordenada destruida por locale de virgula decimal
    (-229.753.965 -> -22.9753965), validando contra a bounding box da UF.
  * Remove duplicatas e reporta tudo que ficou de fora e por que.
"""
import argparse
import collections
import csv
import io
import os
import re
import sys
import unicodedata

LIMITE_DSP = 10000
CATEGORIAS_SEM_ENDERECO = {
    "airport", "airports", "aeroporto", "aeroportos",
    "arena", "arenas", "stadium", "stadiums", "estadio", "estadios",
    "university", "universities", "college", "colleges",
    "universidade", "universidades", "faculdade", "faculdades",
}

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
BR = (-33.9, 5.4, -74.1, -34.7)
CEPFX = [("SP",1000,19999),("RJ",20000,28999),("ES",29000,29999),("MG",30000,39999),
 ("BA",40000,48999),("SE",49000,49999),("PE",50000,56999),("AL",57000,57999),
 ("PB",58000,58999),("RN",59000,59999),("CE",60000,63999),("PI",64000,64999),
 ("MA",65000,65999),("PA",66000,68899),("AP",68900,68999),("AM",69000,69299),
 ("RR",69300,69389),("AM",69400,69899),("AC",69900,69999),("DF",70000,72799),
 ("GO",72800,72999),("DF",73000,73699),("GO",73700,76799),("RO",76800,76999),
 ("TO",77000,77999),("MT",78000,78899),("MS",79000,79999),("PR",80000,87999),
 ("SC",88000,89999),("RS",90000,99999)]

# papel -> palavras que aparecem no cabecalho (comparadas sem acento, minusculas)
PISTAS = {
 "endereco": ["endereco", "address", "logradouro", "rua", "street", "formatted address",
              "formatted_address", "vicinity", "local", "location"],
 "numero":   ["numero", "number", "num", "nro"],
 "bairro":   ["bairro", "neighborhood", "neighbourhood", "district"],
 "cidade":   ["cidade", "city", "municipio", "town", "localidade"],
 "uf":       ["uf", "estado", "state", "provincia"],
 "cep":      ["cep", "zip", "postal", "postcode", "zipcode", "postal code"],
 "lat":      ["lat", "latitude"],
 "lon":      ["lon", "lng", "long", "longitude"],
 "nome":     ["nome", "name", "poi", "title", "estabelecimento", "razao social"],
 "categoria":["categoria", "category", "tipo", "type", "segmento"],
}


def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()


def ascii_puro(s):
    """Deixa so letras, digitos e espaco — o que a DSP aceita sem risco."""
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", sem_acento(s))).strip()


def uf_do_cep(c):
    for uf, a, b in CEPFX:
        if a <= c <= b:
            return uf
    return None


def ler(path):
    """Descobre encoding e separador."""
    bruto = open(path, "rb").read()
    texto = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            texto = bruto.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    amostra = "\n".join(texto.splitlines()[:20])
    melhor, placar = ",", -1
    for d in (";", ",", "\t", "|"):
        linhas = [l for l in amostra.splitlines() if l.strip()]
        if not linhas:
            continue
        cont = [l.count(d) for l in linhas]
        # bom separador: aparece sempre e sempre a mesma quantidade de vezes
        if min(cont) > 0 and len(set(cont)) == 1 and min(cont) > placar:
            melhor, placar = d, min(cont)
    return list(csv.reader(io.StringIO(texto), delimiter=melhor)), melhor, enc


def parece_cabecalho(row):
    """Decide se a linha 0 e titulo de coluna ou ja e dado.
    Sem isso, o casamento parcial acha 'rua' DENTRO de um endereco e conclui,
    errado, que aquela linha e cabecalho — perdendo o primeiro registro."""
    cels = [str(c).strip() for c in row]
    if not any(cels):
        return False
    conhecidas = {p for ps in PISTAS.values() for p in ps}
    norm = [sem_acento(c).lower().strip() for c in cels]
    if any(n in conhecidas for n in norm):        # bate exato com um nome conhecido
        return True
    for n in norm:
        if not n:
            continue
        if len(n) > 30:                            # longa demais para ser titulo
            return False
        if re.fullmatch(r"-?[\d.,]+", n):          # numero puro e dado
            return False
        if len(n.split()) >= 4 and re.search(r"\d", n):   # cheira a endereco
            return False
    return True


def mapear(header, linhas):
    """Casa cada papel com um indice de coluna, pelo cabecalho e depois pelo conteudo.
    Devolve (cols, tem_cabecalho) — tem_cabecalho e False quando nenhum papel foi
    reconhecido pelo NOME da coluna, sinal de que a linha 0 e dado, nao cabecalho."""
    cols, usados = {}, set()
    norm = [sem_acento(h).lower().strip() for h in header]
    for papel, pistas in PISTAS.items():
        for i, h in enumerate(norm):
            if i in usados or not h:
                continue
            if h in pistas or any(re.fullmatch(rf"{re.escape(p)}s?", h) for p in pistas):
                cols[papel] = i
                usados.add(i)
                break
    for papel, pistas in PISTAS.items():           # 2a passada, casamento parcial
        if papel in cols:
            continue
        for i, h in enumerate(norm):
            if i in usados or not h:
                continue
            if any(p in h for p in pistas):
                cols[papel] = i
                usados.add(i)
                break
    if "endereco" not in cols:                     # sem cabecalho util: olha o conteudo
        for i in range(len(header)):
            if i in usados:
                continue
            vals = [l[i] for l in linhas[:40] if len(l) > i and l[i].strip()]
            if not vals:
                continue
            # endereco: texto longo, com numero de porta e varias palavras
            if (sum(len(v) for v in vals) / len(vals) > 18
                    and sum(1 for v in vals if re.search(r"\d", v)) > len(vals) * 0.5
                    and sum(v.count(" ") for v in vals) / len(vals) >= 2):
                cols["endereco"] = i
                usados.add(i)
                break
    return cols


def candidatos(tok, faixa):
    """Conserta numero destruido por locale de virgula decimal, dentro da faixa dada."""
    lo, hi = faixa
    tok = str(tok).strip()
    if not tok:
        return []
    try:
        v = float(tok.replace(",", "."))   # <=1 separador: nunca virou milhar
        if tok.count(".") <= 1 and lo <= v <= hi:
            return [v]
    except ValueError:
        pass
    neg = tok.startswith("-")
    d = re.sub(r"\D", "", tok)
    out = []
    for k in (1, 2):
        if len(d) <= k:
            continue
        v = float(d[:k] + "." + d[k:])
        v = -v if neg else v
        if lo <= v <= hi and v not in out:
            out.append(v)
    return out


def partir_endereco(txt):
    """Separa CEP / miolo / UF / cidade de um endereco brasileiro em texto corrido."""
    t = " ".join(str(txt).split())
    cep = uf = cidade = None
    m = re.search(r"\b(\d{5})-?(\d{3})\b", t)
    if m:
        cep = m.group(1) + m.group(2)
        t = (t[:m.start()] + " " + t[m.end():]).strip()
    ufs = [x for x in re.finditer(r"\b([A-Z]{2})\b", t) if x.group(1) in UFBOX]
    if ufs:
        u = ufs[-1]
        uf = u.group(1)
        depois = t[u.end():].strip(" ,-")
        antes = t[:u.start()].strip(" ,-")
        if depois and len(depois.split()) <= 6:
            cidade, t = depois, antes
        else:
            t = (antes + " " + depois).strip()
    return t.strip(" ,-"), cidade, uf, cep


def main():
    ap = argparse.ArgumentParser(description="Prepara CSV de POIs para o geofencing da Yahoo DSP.")
    ap.add_argument("entrada")
    ap.add_argument("-o", "--saida", default="saida_dsp", help="diretorio de saida")
    ap.add_argument("--nome", default=None, help="nome base dos arquivos gerados")
    ap.add_argument("--pais", default="Brazil", help="pais anexado ao fim do endereco (vazio para omitir)")
    ap.add_argument("--raio", default=None, help="raio EM MILHAS, so para registro na conferencia (0.19 = ~300 m)")
    ap.add_argument("--split", type=int, default=LIMITE_DSP, help=f"maximo de enderecos por arquivo (padrao {LIMITE_DSP})")
    a = ap.parse_args()

    linhas, delim, enc = ler(a.entrada)
    linhas = [l for l in linhas if any(str(c).strip() for c in l)]
    if not linhas:
        sys.exit("arquivo vazio")
    if parece_cabecalho(linhas[0]):
        header, corpo = linhas[0], linhas[1:]
        cols = mapear(header, corpo)
    else:
        # linha 0 e dado. O inverso disso — tratar dado como cabecalho — foi
        # exatamente o que a DSP fez ao geocodificar "Latitude,Longitude,..."
        header = [f"col{i+1}" for i in range(len(linhas[0]))]
        corpo = linhas
        cols = mapear([""] * len(linhas[0]), linhas)

    base = a.nome or re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(a.entrada))[0]).strip("_").lower()
    os.makedirs(a.saida, exist_ok=True)

    def campo(row, papel):
        i = cols.get(papel)
        return str(row[i]).strip() if i is not None and len(row) > i else ""

    saidas, descartes, confer = [], [], []
    for n, row in enumerate(corpo, start=2):
        nome = campo(row, "nome")
        categoria = campo(row, "categoria")
        isenta = sem_acento(categoria).lower().strip() in CATEGORIAS_SEM_ENDERECO

        bruto = campo(row, "endereco")
        miolo, cidade, uf, cep = partir_endereco(bruto) if bruto else ("", None, None, None)
        cidade = cidade or campo(row, "cidade") or None
        uf = uf or (campo(row, "uf").upper() if campo(row, "uf").upper() in UFBOX else None)
        cep = cep or (re.sub(r"\D", "", campo(row, "cep")) or None)
        if campo(row, "numero") and campo(row, "numero") not in miolo:
            miolo = f"{miolo} {campo(row, 'numero')}".strip()
        if campo(row, "bairro") and sem_acento(campo(row, "bairro")).lower() not in sem_acento(miolo).lower():
            miolo = f"{miolo} {campo(row, 'bairro')}".strip()

        if uf is None and cep and len(cep) >= 5:
            uf = uf_do_cep(int(cep[:5]))

        faixa_lat = (UFBOX[uf][0], UFBOX[uf][1]) if uf else (BR[0], BR[1])
        faixa_lon = (UFBOX[uf][2], UFBOX[uf][3]) if uf else (BR[2], BR[3])
        cla = candidatos(campo(row, "lat"), faixa_lat)
        clo = candidatos(campo(row, "lon"), faixa_lon)
        lat = cla[0] if len(cla) == 1 else None
        lon = clo[0] if len(clo) == 1 else None

        if isenta and nome:
            linha = ascii_puro(nome)
            origem = "nome (categoria isenta)"
        else:
            partes = [p for p in (miolo, cidade, uf, cep, a.pais) if p]
            linha = ascii_puro(" ".join(partes))
            origem = "endereco"
            # endereco util precisa de rua e de pelo menos cidade ou CEP
            if not miolo or not (cidade or cep):
                motivo = ("so tem coordenada, sem endereco" if (cla or clo) and not bruto
                          else "endereco incompleto")
                descartes.append((n, nome or f"linha {n}", motivo, bruto or "(vazio)"))
                continue
        if len(linha) < 8:
            descartes.append((n, nome or f"linha {n}", "endereco curto demais", bruto or "(vazio)"))
            continue
        saidas.append(linha)
        confer.append({"linha": n, "nome": nome, "categoria": categoria, "origem": origem,
                       "endereco_original": bruto, "endereco_dsp": linha,
                       "cidade": cidade or "", "uf": uf or "", "cep": cep or "",
                       "lat_original": campo(row, "lat"), "lon_original": campo(row, "lon"),
                       "lat_corrigida": "" if lat is None else f"{lat:.6f}".rstrip("0").rstrip("."),
                       "lon_corrigida": "" if lon is None else f"{lon:.6f}".rstrip("0").rstrip("."),
                       "raio_milhas": a.raio or ""})

    vistos, unicos, dup = set(), [], 0
    for s in saidas:
        if s in vistos:
            dup += 1
            continue
        vistos.add(s)
        unicos.append(s)

    if not unicos:
        print(f"entrada       : {os.path.basename(a.entrada)}  (encoding {enc}, separador {delim!r})")
        print(f"colunas lidas : " + (", ".join(f"{k}={header[v] if v < len(header) else v!r}"
                                               for k, v in sorted(cols.items())) or "(nenhuma reconhecida)"))
        print(f"registros     : {len(corpo)}")
        print(f"\nNENHUM endereco aproveitavel — nada foi gerado.")
        for m, c in collections.Counter(d[2] for d in descartes).most_common():
            print(f"  {c:6d}  {m}")
        if any("so tem coordenada" in d[2] for d in descartes):
            print("\nA Yahoo DSP nao aceita coordenada: o geofencing le UM ENDERECO POR LINHA,")
            print("em texto livre. Junte a coluna de endereco a esta lista e rode de novo.")
            print("Excecao: POIs de Airports, Arena/Stadiums e Universities/Colleges podem ir")
            print("so com o nome — nesse caso inclua uma coluna 'categoria' com esse valor.")
        pdesc = os.path.join(a.saida, f"{base}_descartados.csv")
        with open(pdesc, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["linha", "nome", "motivo", "endereco_original"])
            w.writerows(descartes)
        print(f"\ndetalhe linha a linha em {pdesc}")
        return 2

    lotes = [unicos[i:i + a.split] for i in range(0, len(unicos), a.split)]
    gerados = []
    for k, lote in enumerate(lotes, 1):
        sufixo = "" if len(lotes) == 1 else f"_parte{k}"
        for ext in ("txt", "csv"):
            p = os.path.join(a.saida, f"{base}{sufixo}.{ext}")
            with open(p, "w", newline="", encoding="ascii") as f:
                if ext == "txt":
                    f.write("\r\n".join(lote) + ("\r\n" if lote else ""))
                else:
                    csv.writer(f, lineterminator="\r\n").writerows([[x] for x in lote])
            gerados.append((p, len(lote)))

    pconf = os.path.join(a.saida, f"{base}_conferencia.csv")
    campos = ["linha", "nome", "categoria", "origem", "endereco_original", "endereco_dsp",
              "cidade", "uf", "cep", "lat_original", "lon_original",
              "lat_corrigida", "lon_corrigida", "raio_milhas"]
    with open(pconf, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(confer)
    if descartes:
        pdesc = os.path.join(a.saida, f"{base}_descartados.csv")
        with open(pdesc, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["linha", "nome", "motivo", "endereco_original"])
            w.writerows(descartes)

    falhas = []
    for p, n in gerados:
        if not p.endswith(".txt"):
            continue
        b = open(p, "rb").read()
        ls = [l for l in b.split(b"\r\n") if l.strip()]
        if len(ls) != n:
            falhas.append(f"{os.path.basename(p)}: contagem de linhas nao bate")
        if len(ls) > LIMITE_DSP:
            falhas.append(f"{os.path.basename(p)}: passa de {LIMITE_DSP} enderecos")
        for l in ls:
            s = l.decode("ascii")
            if re.search(r"[^A-Za-z0-9 ]", s):
                falhas.append(f"{os.path.basename(p)}: caractere proibido em {s!r}")
                break
            if "  " in s or s != s.strip():
                falhas.append(f"{os.path.basename(p)}: espacamento irregular em {s!r}")
                break

    print(f"entrada       : {os.path.basename(a.entrada)}  (encoding {enc}, separador {delim!r})")
    print(f"colunas lidas : " + (", ".join(f"{k}={header[v] if v < len(header) else v!r}"
                                           for k, v in sorted(cols.items())) or "(nenhuma reconhecida)"))
    print(f"registros     : {len(corpo)}")
    print(f"enderecos     : {len(unicos)}  (duplicatas removidas: {dup})")
    print(f"descartados   : {len(descartes)}")
    if descartes:
        for m, c in collections.Counter(d[2] for d in descartes).most_common():
            print(f"                {c:5d}  {m}")
    print(f"\narquivos gerados em {a.saida}/:")
    for p, n in gerados:
        print(f"  {os.path.basename(p):42} {n:6d} enderecos")
    print(f"  {os.path.basename(pconf):42}   conferencia")
    if descartes:
        print(f"  {base}_descartados.csv{'':<{max(0, 42-len(base)-18)}}   o que ficou de fora e por que")
    if a.raio:
        try:
            print(f"\nraio informado: {a.raio} milha(s) = {float(a.raio)*1609.34:.0f} m")
        except ValueError:
            pass
    print("\nvalidacao     : " + ("TUDO OK" if not falhas else "FALHAS:\n  " + "\n  ".join(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
