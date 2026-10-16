#!/usr/bin/env python3
"""
Audiencia Yahoo DSP — JLR OOH Amplifier RRS, faces JCDecaux (Out/Nov 26).

As duas bases recebidas (CSV da plataforma e XLSX do roteiro) sao as mesmas 50
faces, campo a campo. O CSV tem `formatted_address` vazio, entao o endereco
vem do texto do roteiro: "AVENIDA X, [numero], RUA Y, CANTEIRO CENTRAL".

Em face de OOH a COORDENADA e a verdade (e onde o painel esta); o texto descreve
o cruzamento e o CEP da base frequentemente pertence a outra rua. Por isso cada
face passa por:

  1. rua + numero do texto, quando o texto traz numero (o numero pertence ao
     segmento imediatamente anterior a ele);
  2. senao, o endereco real mais proximo NA MESMA RUA (principal ou transversal)
     entre as bases ja processadas no repo, a ate 150 m da coordenada;
  3. senao, o inicio da faixa do CEP, se o CEP for da rua principal/transversal;
  4. senao, numero 100 (medido: 73% de aprovacao; numero inventado, rotulado).

O CEP e conferido contra o espelho aberto do OpenCEP: precisa ser da mesma rua
e, havendo faixa, conter o numero. Se o CEP da base nao serve, procura-se o CEP
certo (endereco real vizinho na mesma rua, ou CEPs vizinhos no dataset).

Toda linha final e conferida: a coordenada do CEP usado precisa cair perto da
coordenada da face. Se o texto aponta para longe, a face e marcada.
"""
import csv, io, json, math, os, re, sys, urllib.request, collections

BASE = "/home/user/bobagens/jlr-ooh-jcdecaux-dsp/"
sys.path.insert(0, BASE)
import vizinhos as V
gf = V.gf
U = "https://raw.githubusercontent.com/gpfconfea/banco-ceps/main/cep/%s.json"


def cep_info(c):
    c = re.sub(r"\D", "", c or "")
    if len(c) != 8:
        return None
    p = BASE + "cache_cep/%s.json" % c
    if os.path.exists(p + ".sem"):
        return None
    if not os.path.exists(p):
        try:
            b = urllib.request.urlopen(U % c, timeout=30).read()
            json.loads(b.decode()); open(p, "wb").write(b)
        except Exception:
            open(p + ".sem", "w").close(); return None
    try:
        j = json.load(open(p, encoding="utf-8"))
        return j if isinstance(j, dict) and j.get("logradouro") else None
    except Exception:
        return None


def faixa(compl):
    """(ini, fim, paridade) da faixa do complemento; None se nao houver."""
    c = (compl or "").lower()
    par = "par" if "lado par" in c else ("impar" if ("ímpar" in c or "impar" in c) else None)
    m = re.search(r"de\s+(\d+)(?:/\d+)?\s+a\s+(\d+)", c)
    if m: return int(m.group(1)), int(m.group(2)), par
    m = re.search(r"de\s+(\d+)(?:/\d+)?\s+ao\s+fim", c)
    if m: return int(m.group(1)), 10 ** 6, par
    m = re.search(r"at[eé]\s+(\d+)", c)
    if m: return 1, int(m.group(1)), par
    if par: return 1, 10 ** 6, par
    return None


def cep_serve(j, rua, num):
    if not j or not V.mesma_rua(j["logradouro"], rua):
        return False
    f = faixa(j.get("complemento"))
    if not f or not num:
        return True
    n = int(re.sub(r"\D", "", num) or 0)
    ok = f[0] <= n <= f[1]
    if ok and f[2]:
        ok = (n % 2 == 0) == (f[2] == "par")
    return ok


def procura_cep(prefixo5, rua, num, limite=60):
    """Varre o dataset no mesmo prefixo de 5 digitos atras do CEP que contem rua+numero."""
    for suf in range(0, 1000, 10):
        c = "%s%03d" % (prefixo5, suf)
        j = cep_info(c)
        if j and cep_serve(j, rua, num):
            return c, j
        limite -= 1 if j is None else 0
    return None, None


def melhor_cep_conhecido(rua, num, la, lo, viz, base_ceps):
    """Entre todos os CEPs conhecidos (os da propria base e os de enderecos reais
    a ate 1,5 km), o que e desta rua, contem este numero e fica mais perto do
    painel. Pega CEP trocado entre linhas da base."""
    pool = set(base_ceps) | {p["cep"] for d, p in viz if d <= 1.5 and V.mesma_rua(p["rua"], rua)}
    melhor = None
    for c in pool:
        j = cep_info(c)
        if not cep_serve(j, rua, num):
            continue
        d = dist_cep(j, la, lo)
        d = 99 if d is None else d
        if melhor is None or d < melhor[0]:
            melhor = (d, c)
    return melhor[1] if melhor and melhor[0] <= 3 else None


def dist_cep(j, la, lo):
    try:
        d = V.km(la, lo, float(j["latitude"]), float(j["longitude"]))
        return None if d > 50 else d          # >50 km = coordenada do dataset quebrada
    except Exception:
        return None


ROT = re.compile(r"(?i)^(av\b|av\.|avenida|rua|r\.|alameda|praca|praça|viaduto|complexo|estrada|largo|doutor)")
idx = [p for p in V.indice() if ROT.match(V.unicodedata.normalize("NFKD", p["rua"]).encode("ascii", "ignore").decode())]
faces = list(csv.DictReader(io.StringIO(open(BASE + "origem/base_completa.csv", encoding="utf-8-sig").read())))
base_ceps = {re.sub(r"\D", "", f["CEP"]) for f in faces}

ABREV = [(r"\bBRIG\b\.?|\bBRG\b\.?", "BRIGADEIRO"), (r"\bCAP\b\.?", "CAPITAO"),
         (r"\bDR\b\.?", "DOUTOR"), (r"\bPRES\b\.?", "PRESIDENTE"), (r"\bENG\b\.?", "ENGENHEIRO"),
         (r"\bPROF\b\.?", "PROFESSOR"), (r"\bGAL\b\.?|\bGEN\b\.?", "GENERAL"),
         (r"\bSTA\b\.?", "SANTA"), (r"\bSTO\b\.?", "SANTO"), (r"\bAV\b\.?", "AVENIDA"), (r"^R\b\.?", "RUA")]


def forma(rua):
    r = V.unicodedata.normalize("NFC", rua).upper()
    for a, b in ABREV:
        r = re.sub(a, b, r)
    return re.sub(r"\s+", " ", r).strip()


def acha_cep(rua, num, la, lo, viz, base_cep):
    """Devolve (cep, como) para rua+numero, ou (None, motivo)."""
    if cep_serve(cep_info(base_cep), rua, num):
        return base_cep, "base (confere com rua e numero)"
    hit = next((p for d, p in viz if d <= 0.5 and V.mesma_rua(p["rua"], rua)
                and cep_serve(cep_info(p["cep"]), rua, num)), None)
    if hit:
        return hit["cep"], "CORRIGIDO: endereco real vizinho na mesma rua"
    c = melhor_cep_conhecido(rua, num, la, lo, viz, base_ceps)
    if c:
        return c, "CORRIGIDO: CEP conhecido da mesma rua, perto do painel"
    # varre o dataset nos prefixos do proprio CEP e dos enderecos reais perto do painel
    prefixos = list(dict.fromkeys([base_cep[:5]] + [p["cep"][:5] for d, p in viz[:40] if d <= 0.6]))[:4]
    for pf in prefixos:
        c2, _j = procura_cep(pf, rua, num)
        if c2:
            return c2, "CORRIGIDO: CEP da rua achado no dataset (prefixo %s)" % pf
    return None, "nenhum CEP da rua encontrado"


def ancoras_do_roteiro(faces):
    """(rua, numero, lat, lng) de toda face cujo texto traz numero de porta."""
    out = []
    for f in faces:
        seg = [s.strip() for s in f["Endereço"].split(",")]
        for i, s_ in enumerate(seg[1:], 1):
            if re.fullmatch(r"\d{1,5}", s_):
                out.append((seg[i - 1], int(s_), float(f["Latitude"]), float(f["Longitude"])))
                break
    return out


def interpola(rua, la, lo, ancoras):
    """Numero estimado no ponto (la, lo) a partir de >=2 faces com numero na mesma
    rua: projeta o ponto no segmento entre as duas ancoras mais proximas."""
    a = [x for x in ancoras if V.mesma_rua(x[0], rua)]
    a = sorted({(n, y, z) for _r, n, y, z in a})
    if len(a) < 2:
        return None
    a.sort(key=lambda t: V.km(la, lo, t[1], t[2]))
    (n1, y1, x1), (n2, y2, x2) = a[0], a[1]
    if n1 == n2:
        return None
    k = math.cos(math.radians(la))
    vx, vy = (x2 - x1) * k, (y2 - y1)
    wx, wy = (lo - x1) * k, (la - y1)
    t = (wx * vx + wy * vy) / (vx * vx + vy * vy or 1e-12)
    if not -0.15 <= t <= 1.15:
        return None                      # fora do trecho entre as ancoras: nao extrapola
    metros = V.km(y1, x1, y2, x2) * 1000
    if not metros or not 0.4 <= abs(n2 - n1) / metros <= 2.5:
        return None                      # SP numera por metro; densidade fora disso = ancora errada
    return max(1, int(round(n1 + t * (n2 - n1))))


def coerente(p, rua, la, lo, ancoras, tol=700):
    """Endereco vizinho cujo numero contradiz as faces com numero na mesma rua e
    rejeitado: a coordenada dele na base de origem esta errada."""
    est = interpola(rua, la, lo, ancoras)
    try:
        return est is None or abs(int(re.sub(r"\D", "", p["num"])) - est) <= tol
    except ValueError:
        return True


def real_validado(p):
    return cep_serve(cep_info(p["cep"]), p["rua"], p["num"])


ANCORAS = ancoras_do_roteiro(faces)
saida, conf = [], []
for x in faces:
    la, lo = float(x["Latitude"]), float(x["Longitude"])
    seg = [s.strip() for s in x["Endereço"].split(",")]
    ruas = [s for s in seg if not re.fullmatch(r"\d+", s) and s.upper() not in ("-", "CC", "CANTEIRO CENTRAL")
            and not s.upper().startswith(("EM FRENTE", "ZONA ", "CANTEIRO", "COMPLEXO", "PONTE"))]
    princ = ruas[0]
    trans = ruas[1] if len(ruas) > 1 else ""
    rua_txt = num_txt = ""
    for i, s_ in enumerate(seg[1:], 1):
        if re.fullmatch(r"\d{1,5}", s_):
            rua_txt, num_txt = seg[i - 1], s_
            break
    base_cep = re.sub(r"\D", "", x["CEP"])
    viz = sorted(((V.km(la, lo, p["lat"], p["lng"]), p) for p in idx), key=lambda t: t[0])
    na_rua = lambda p: V.mesma_rua(p["rua"], princ) or (trans and V.mesma_rua(p["rua"], trans))
    risco = []

    # ---- 0. texto x coordenada -------------------------------------------
    # So conta como conflito acima de 5 km: o centroide de CEP de avenida longa
    # (Marginal) cai a 3-4 km do painel sem que nada esteja errado. O bairro do
    # roteiro (Conurbation) desempata.
    jb = cep_info(base_cep)
    texto_km = None
    if jb and any(r_ and V.mesma_rua(jb["logradouro"], r_) for r_ in (princ, trans)):
        texto_km = dist_cep(jb, la, lo)
    modo = "normal"
    if texto_km is not None and texto_km > 5:
        b_txt, b_rot = V.chave(jb.get("bairro", "")), V.chave(x["Conurbation"])
        if b_rot and b_txt and (b_rot in b_txt or b_txt in b_rot):
            modo = "texto"
            risco.append("roteiro inconsistente: coordenada a %.1f km do endereco; o bairro do roteiro "
                         "(%s) confirma o ENDERECO, entao a coordenada foi ignorada" % (texto_km, x["Conurbation"]))
        else:
            modo = "coordenada"
            risco.append("roteiro inconsistente: endereco a %.1f km da coordenada; o bairro do roteiro "
                         "(%s) nao confirma o endereco, entao vale a COORDENADA" % (texto_km, x["Conurbation"]))

    cep = None
    if modo == "coordenada":
        perto = next(((d, p) for d, p in viz if d <= 0.4 and real_validado(p)
                      and coerente(p, p["rua"], la, lo, ANCORAS)), None)
        if perto:
            d, p = perto
            rua, num, cep = p["rua"], p["num"], p["cep"]
            origem_num = "endereco real a %d m da coordenada do painel" % round(d * 1000)
            origem_cep = "do endereco real (conferido)"
        else:
            modo = "texto"
            risco.append("sem endereco real perto da coordenada; usado o texto do roteiro")

    # ---- 1. rua + numero ---------------------------------------------------
    if cep:
        pass
    elif num_txt:
        rua, num, origem_num = rua_txt, num_txt, "texto do roteiro"
    else:
        escolha = None
        if modo != "texto":
            ok_rua = lambda p: na_rua(p) and coerente(p, p["rua"], la, lo, ANCORAS)
            ok_qq = lambda p: coerente(p, p["rua"], la, lo, ANCORAS)
            etapas = [(0.15, ok_rua, "mesma rua"), (0.15, ok_qq, "rua vizinha"),
                      (0.40, ok_rua, "mesma rua"), ("interp", None, None), (0.30, ok_qq, "rua vizinha")]
        else:
            etapas = []                      # coordenada nao e confiavel: nada de vizinhanca
        for lim, filtro, rot in etapas:
            if lim == "interp":
                for r_ in (princ, trans):
                    n_est = interpola(r_, la, lo, ANCORAS) if r_ else None
                    if n_est:
                        rua, num, escolha = r_, str(n_est), True
                        origem_num = "interpolado entre faces do roteiro com numero na mesma rua"
                        break
                if escolha:
                    break
                continue
            escolha = next(((d, p) for d, p in viz if d <= lim and filtro(p) and real_validado(p)), None)
            if escolha:
                d, p = escolha
                rua, num, cep = p["rua"], p["num"], p["cep"]
                origem_num = "endereco real a %d m do painel (%s)" % (round(d * 1000), rot)
                origem_cep = "do endereco real (conferido)"
                break
        if not escolha:
            f = faixa(jb.get("complemento")) if jb else None
            if jb and f and f[0] > 1 and any(r_ and V.mesma_rua(jb["logradouro"], r_) for r_ in (princ, trans)):
                rua, num, cep = jb["logradouro"], str(f[0]), base_cep
                origem_num, origem_cep = "inicio da faixa do CEP", "base (confere com a rua)"
            else:
                rua, num, origem_num = princ, "100", "INVENTADO (100)"
                risco.append("numero inventado: em avenida longa o ponto pode cair longe do painel")

    # ---- 2. CEP ------------------------------------------------------------
    if not cep:
        cep, origem_cep = acha_cep(rua, num, la, lo, viz, base_cep)
        if not cep:
            cep = base_cep
            risco.append("CEP da base e de outra rua e o certo nao foi encontrado")
            origem_cep = "base — NAO confere com a rua"
    jc = cep_info(cep)
    d = dist_cep(jc, la, lo) if (jc and cep_serve(jc, rua, num)) else None

    linha = gf.ascii_puro(" ".join(z for z in (forma(rua), num, "Sao Paulo", "SP", cep, "Brazil") if z))
    saida.append(linha)
    conf.append({"face": x["Nome"], "linha_dsp": linha, "origem_numero": origem_num, "origem_cep": origem_cep,
                 "km_cep_x_painel": "" if d is None else "%.2f" % d, "risco": "; ".join(risco),
                 "endereco_roteiro": x["Endereço"], "cep_roteiro": x["CEP"], "bairro_roteiro": x["Conurbation"],
                 "lat": x["Latitude"], "lng": x["Longitude"]})

unicas = list(dict.fromkeys(saida))
os.makedirs(BASE + "upload", exist_ok=True)
nome = BASE + "upload/jlr_rrs_jcdecaux_nov26"
open(nome + ".txt", "w", newline="", encoding="ascii").write("\r\n".join(unicas) + "\r\n")
with open(nome + "_conferencia.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(conf[0]), delimiter=";"); w.writeheader(); w.writerows(conf)
print("%d faces -> %d linhas unicas" % (len(faces), len(unicas)))
print("\nnumero:", dict(collections.Counter(c["origem_numero"].split(" a ")[0] for c in conf)))
print("CEP   :", dict(collections.Counter(c["origem_cep"] for c in conf)))
print("\ncom risco:")
for c in conf:
    if c["risco"]: print("  %-20s %-62s | %s" % (c["face"], c["linha_dsp"][:62], c["risco"]))
