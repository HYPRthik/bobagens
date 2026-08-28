#!/usr/bin/env python3
"""Suite de testes do geofence.py. Rode: python3 testes.py"""
import csv, io, os, pathlib, subprocess, sys, glob, re, shutil

G = str(pathlib.Path(__file__).parent / "geofence.py")
NISSAN = str(pathlib.Path(__file__).parent.parent / "nissan-dsp-geofencing" / "origem_nissan.csv")
RETORNO = "/root/.claude/uploads/e923556c-8433-5d80-a1ca-cd6fec5764b5/169284a4-line4354015geofencingaddresslist.csv"
TMP = "/tmp/gf_testes"
falhas = []


def run(args):
    r = subprocess.run([sys.executable, G] + args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def linhas(p):
    return [l.decode("ascii") for l in open(p, "rb").read().split(b"\r\n") if l.strip()]


def check(nome, cond, detalhe=""):
    print(("  OK   " if cond else "  FALHA") + f" {nome}" + ("" if cond else f"  <- {detalhe}"))
    if not cond:
        falhas.append(nome)


def entrada(nome, conteudo, enc="utf-8"):
    p = os.path.join(TMP, "in", nome)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(conteudo.encode(enc))
    return p


shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)

print("=== T1 Nissan: 202 endereços, ASCII, cidade e CEP preservados ===")
rc, out = run([NISSAN, "-o", f"{TMP}/t1", "--nome", "nissan"])
L = linhas(f"{TMP}/t1/nissan.txt") if rc == 0 else []
check("202 endereços", len(L) == 202, len(L) or out[-300:])
check("todos terminam em Brazil", all(x.endswith("Brazil") for x in L))
check("todos têm CEP de 8 dígitos", all(re.search(r"\b\d{8}\b", x) for x in L))
check("todos têm UF válida", all(re.search(r"\b[A-Z]{2}\b \d{8} Brazil$", x) for x in L))
check("bairro removido de Macaé", any(x == "Avenida Lacerda Agostinho 300 Macae RJ 27947287 Brazil" for x in L),
      [x for x in L if "Macae" in x])
check("São Conrado sem repetição", any(x == "Praca Sao Conrado 20 Rio de Janeiro RJ 22610230 Brazil" for x in L),
      [x for x in L if "Conrado" in x])

print("\n=== T2 só coordenadas -> recusa com exit 2, sem arquivo de upload ===")
POIS = str(pathlib.Path(__file__).parent.parent / "yahoo-dsp-pois" / "origem_pois_unificados.csv")
if os.path.exists(POIS):
    rc, out = run([POIS, "-o", f"{TMP}/t2", "--nome", "pois"])
    check("exit code 2", rc == 2, rc)
    check("não gerou .txt", not os.path.exists(f"{TMP}/t2/pois.txt"))
    check("explica o motivo", "UM ENDERECO POR LINHA" in out)

print("\n=== T3 --aprovados não reescreve o que a DSP já aceitou ===")
if os.path.exists(RETORNO):
    r = [x for x in csv.reader(io.StringIO(open(RETORNO, encoding="utf-8").read())) if x]
    okset = {" ".join(x[0].split()) for x in r if x[1] == "successful"}
    badset = {" ".join(x[0].split()) for x in r if x[1] != "successful"}
    rc, out = run([NISSAN, "-o", f"{TMP}/t3", "--nome", "ap", "--aprovados", RETORNO])
    L = linhas(f"{TMP}/t3/ap.txt") if rc == 0 else []
    check("preserva os 162 aprovados", sum(1 for x in L if x in okset) == 162, sum(1 for x in L if x in okset))
    risco = {x["endereco_dsp"]: x["severidade"] for x in csv.DictReader(
        io.StringIO(open(f"{TMP}/t3/ap_risco.csv", encoding="utf-8-sig").read()), delimiter=";")}
    iguais = [x for x in L if x in badset]
    check("rejeitado reenviado igual está marcado ALTO",
          all(risco.get(x) == "ALTO" for x in iguais), [(x, risco.get(x)) for x in iguais])
    check("reescreve >=36 dos 40 que falharam",
          sum(1 for x in L if x not in okset and x not in badset) >= 36,
          sum(1 for x in L if x not in okset and x not in badset))

print("\n=== T4 bairro só sai quando a cidade é identificável ===")
p = entrada("colunas.csv", "nome,logradouro,numero,bairro,cidade,uf,cep\n"
                           "Banco Y,Rua da Quitanda,50,Centro,Rio de Janeiro,RJ,20011-030\n")
rc, out = run([p, "-o", f"{TMP}/t4a", "--nome", "c"])
check("com coluna cidade, bairro sai",
      rc == 0 and linhas(f"{TMP}/t4a/c.txt") == ["Rua da Quitanda 50 Rio de Janeiro RJ 20011030 Brazil"],
      linhas(f"{TMP}/t4a/c.txt") if rc == 0 else out[-300:])

p = entrada("google.csv", 'endereco\n'
            '"Av. Paulista, 1578 - Bela Vista, São Paulo - SP, 01310-200, Brasil"\n')
rc, out = run([p, "-o", f"{TMP}/t4b", "--nome", "g"])
check("formato Google (vírgulas, com aspas), bairro sai",
      rc == 0 and linhas(f"{TMP}/t4b/g.txt") == ["Avenida Paulista 1578 Sao Paulo SP 01310200 Brazil"],
      linhas(f"{TMP}/t4b/g.txt") if rc == 0 else out[-300:])

p = entrada("google_sem_aspas.csv", "endereco\n"
            "Av. Paulista, 1578 - Bela Vista, São Paulo - SP, 01310-200, Brasil\n")
rc, out = run([p, "-o", f"{TMP}/t4d", "--nome", "gs"])
check("formato Google SEM aspas é recuperado",
      rc == 0 and linhas(f"{TMP}/t4d/gs.txt") == ["Avenida Paulista 1578 Sao Paulo SP 01310200 Brazil"],
      linhas(f"{TMP}/t4d/gs.txt") if rc == 0 else out[-300:])

p = entrada("flat.csv", "endereco\nAv Lacerda Agostinho 300 Botafogo Macae RJ 27947287\n")
rc, out = run([p, "-o", f"{TMP}/t4c", "--nome", "f"])
L = linhas(f"{TMP}/t4c/f.txt") if rc == 0 else []
check("cidade ambígua: NÃO apaga a cidade", L and "Macae" in L[0], L)
check("cidade ambígua: avisa no risco", "cidade nao identificada" in out, out[-300:])

print("\n=== T4b nome do estabelecimento antes do logradouro ===")
p = entrada("venue.csv", 'endereco\n'
    '"Churrascaria Ponteio Mogi das Cruzes, Avenida Francisco Ferreira Lopes, 460, Centro, Mogi das Cruzes - SP, 08710-000, Brasil"\n'
    '"AUDI, Rua Padre Germano Mayer, 1629, Hugo Lange, Curitiba - PR, 80040-170, Brasil"\n'
    '"Terminal Asa Sul, Asa Sul, Brasília - DF, 70610-200, Brasil"\n')
rc, out = run([p, "-o", f"{TMP}/t4e", "--nome", "v"])
L = linhas(f"{TMP}/t4e/v.txt") if rc == 0 else []
check("corta 'Churrascaria Ponteio Mogi das Cruzes'",
      L[:1] == ["Avenida Francisco Ferreira Lopes 460 Mogi das Cruzes SP 08710000 Brazil"], L[:1] or out[-300:])
check("corta 'AUDI'",
      len(L) > 1 and L[1] == "Rua Padre Germano Mayer 1629 Curitiba PR 80040170 Brazil", L[1:2])
check("sem tipo de logradouro: mantém o nome",
      len(L) > 2 and "Terminal Asa Sul" in L[2], L[2:3])

print("\n=== T4b2 corte de nome NUNCA apaga rua com número ===")
p = entrada("blvd.csv", 'endereco\n'
    '"Boulevard Vinte e Oito de Setembro, 271, Vila Isabel, Rio de Janeiro - RJ, 20551-030, Brasil"\n'
    '"Loja X, Rua das Flores, 88, Vila Nova, Curitiba - PR, 80000-000, Brasil"\n')
rc, out = run([p, "-o", f"{TMP}/t4g", "--nome", "bv"])
L = linhas(f"{TMP}/t4g/bv.txt") if rc == 0 else []
check("preserva 'Boulevard ... 271'",
      L[:1] == ["Boulevard Vinte e Oito de Setembro 271 Rio de Janeiro RJ 20551030 Brazil"],
      L[:1] or out[-300:])
check("ainda corta nome quando é seguro",
      len(L) > 1 and L[1] == "Rua das Flores 88 Curitiba PR 80000000 Brazil", L[1:2])

print("\n=== T4c número da porta com letra e bairro iniciado por conectivo ===")
p = entrada("numalpha.csv", 'endereco\n'
    '"Rua Olegario Mariano, 40A, Centro, São João de Meriti - RJ, 25510-350, Brasil"\n'
    '"Avenida do Estado, 1155, Dos Pioneiros, Balneário Camboriú - SC, 88331-110, Brasil"\n')
rc, out = run([p, "-o", f"{TMP}/t4f", "--nome", "na"])
L = linhas(f"{TMP}/t4f/na.txt") if rc == 0 else []
check("'40A' é número de porta",
      L[:1] == ["Rua Olegario Mariano 40A Sao Joao de Meriti RJ 25510350 Brazil"], L[:1] or out[-300:])
check("'Dos Pioneiros' é bairro, não conectivo",
      len(L) > 1 and L[1] == "Avenida do Estado 1155 Balneario Camboriu SC 88331110 Brazil", L[1:2])

print("\n=== T5 número da porta não confunde com número no nome da rua ===")
p = entrada("num.csv", "endereco;cidade;uf;cep\n"
            "Avenida 2 de Agosto 352 Asa Norte;Irece;BA;44864130\n"
            "Rodovia BR 470 7150 Canta Galo;Rio do Sul;SC;89163020\n")
rc, out = run([p, "-o", f"{TMP}/t5", "--nome", "n"])
L = linhas(f"{TMP}/t5/n.txt") if rc == 0 else []
check("mantém '2 de Agosto', corta 'Asa Norte'",
      L[:1] == ["Avenida 2 de Agosto 352 Irece BA 44864130 Brazil"], L[:1] or out[-300:])
check("'BR 470' não vira número de porta",
      len(L) > 1 and L[1] == "Rodovia BR 470 7150 Rio do Sul SC 89163020 Brazil", L[1:2])
check("rodovia marcada ALTO", "rodovia" in out and "ALTO" in out)

print("\n=== T6 abreviação expandida e ruído removido ===")
p = entrada("abrev.csv", "endereco;cidade;uf;cep\n"
            "Rod BR 471 KM 56 3510 SCHULZ;Santa Cruz do Sul;RS;96845545\n")
rc, out = run([p, "-o", f"{TMP}/t6", "--nome", "a"])
check("Rod->Rodovia e 'KM 56' removido",
      rc == 0 and linhas(f"{TMP}/t6/a.txt") == ["Rodovia BR 471 3510 Santa Cruz do Sul RS 96845545 Brazil"],
      linhas(f"{TMP}/t6/a.txt") if rc == 0 else out[-300:])

print("\n=== T7 encoding, separador e ausência de cabeçalho ===")
p = entrada("lat1.csv", "nome\tendereco\nLoja Açaí\tRua José Bonifácio 45 Centro Niterói RJ 24020-000\n", "cp1252")
rc, out = run([p, "-o", f"{TMP}/t7a", "--nome", "l"])
check("cp1252 + tab, acento e hífen removidos",
      rc == 0 and linhas(f"{TMP}/t7a/l.txt") == ["Rua Jose Bonifacio 45 Centro Niteroi RJ 24020000 Brazil"],
      linhas(f"{TMP}/t7a/l.txt") if rc == 0 else out[-300:])

p = entrada("nohdr.csv", "Rua Augusta 1500 Consolacao Sao Paulo SP 01305100\n"
                         "Av Paulista 900 Bela Vista Sao Paulo SP 01310100\n")
rc, out = run([p, "-o", f"{TMP}/t7b", "--nome", "nh"])
check("sem cabeçalho: não come a 1a linha",
      rc == 0 and len(linhas(f"{TMP}/t7b/nh.txt")) == 2, out[-300:])

print("\n=== T8 categoria isenta usa só o nome ===")
p = entrada("isenta.csv", "nome;categoria;endereco\nAeroporto de Congonhas;Airports;\n"
            "Joalheria X;Joalherias;Rua Oscar Freire 200 Jardins SP Sao Paulo 01426000\n")
rc, out = run([p, "-o", f"{TMP}/t8", "--nome", "i"])
L = linhas(f"{TMP}/t8/i.txt") if rc == 0 else []
check("aeroporto pelo nome", "Aeroporto de Congonhas" in L, L)
check("joalheria pelo endereço", any("Oscar Freire" in x for x in L), L)

print("\n=== T9 limite de 10.000 e duplicatas ===")
p = entrada("big.csv", "endereco;cidade;uf;cep\n" + "".join(
    f"Rua Teste {i} Centro;Campinas;SP;13010{i%900:03d}\n" for i in range(10500)))
rc, out = run([p, "-o", f"{TMP}/t9", "--nome", "b"])
check("dividiu em 2 partes", os.path.exists(f"{TMP}/t9/b_parte1.txt") and os.path.exists(f"{TMP}/t9/b_parte2.txt"), out[-300:])
if os.path.exists(f"{TMP}/t9/b_parte1.txt"):
    check("parte1 = 10.000", len(linhas(f"{TMP}/t9/b_parte1.txt")) == 10000, len(linhas(f"{TMP}/t9/b_parte1.txt")))

p = entrada("dup.csv", "endereco;cidade;uf;cep\nRua A 1 Centro;Santos;SP;11010000\n"
            "Rua A 1 Centro;Santos;SP;11010000\nRua B 2 Centro;Santos;SP;11010001\n")
rc, out = run([p, "-o", f"{TMP}/t9d", "--nome", "d"])
check("dedupe para 2", rc == 0 and len(linhas(f"{TMP}/t9d/d.txt")) == 2, out[-300:])

print("\n=== T10 nenhum caractere proibido em nenhuma saída de upload ===")
ruins = []
for q in glob.glob(f"{TMP}/**/*.txt", recursive=True) + glob.glob(f"{TMP}/**/*.csv", recursive=True):
    if any(k in q for k in ("conferencia", "descartados", "risco", "/in/")):
        continue
    for l in linhas(q):
        if re.search(r"[^A-Za-z0-9 ]", l.replace('"', "")):
            ruins.append((q, l))
            break
check("saídas 100% ASCII limpo", not ruins, ruins[:2])

print("\n" + ("TODOS OS TESTES PASSARAM" if not falhas else f"{len(falhas)} FALHAS: {falhas}"))
sys.exit(1 if falhas else 0)
