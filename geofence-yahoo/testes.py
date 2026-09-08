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

print("\n=== T4d0 'LOGRADOURO - CIDADE, UF, CEP' não perde a rua ===")
p = entrada("hifen.csv", "endereco\n"
    '"R.FICA COMIGO - VÁRZEA DA PALMA, MG, 39260-000"\n'
    '"PRAÇA TEIXEIRA DE FREITAS - CACHOEIRA, BA, 44300-000"\n')
rc, out = run([p, "-o", f"{TMP}/t4j", "--nome", "hf"])
L = linhas(f"{TMP}/t4j/hf.txt") if rc == 0 else []
check("preserva 'R.FICA COMIGO' e a cidade",
      L[:1] == ["R FICA COMIGO VARZEA DA PALMA MG 39260000 Brazil"], L[:1] or out[-300:])
check("preserva 'PRACA TEIXEIRA DE FREITAS'",
      len(L) > 1 and L[1] == "PRACA TEIXEIRA DE FREITAS CACHOEIRA BA 44300000 Brazil", L[1:2])

print("\n=== T4d2 coluna cidade ganha do bairro que aparece no texto ===")
p = entrada("bairro_como_cidade.csv", "endereco,cidade,uf,cep\n"
    '"AV. INTERLAGOS  2255 - LOJA 157 A - VILA INGLESA  INTERLAGOS - SP  04661-100  BRASIL",São Paulo,SP,04661-100\n')
rc, out = run([p, "-o", f"{TMP}/t4i", "--nome", "bc"])
check("usa 'Sao Paulo' da coluna, não 'INTERLAGOS' do texto",
      rc == 0 and linhas(f"{TMP}/t4i/bc.txt") == ["Avenida INTERLAGOS 2255 Sao Paulo SP 04661100 Brazil"],
      linhas(f"{TMP}/t4i/bc.txt") if rc == 0 else out[-300:])

print("\n=== T4d formato de espaço duplo e loja dentro de shopping ===")
p = entrada("dupespaco.csv", "endereco,cidade,uf,cep\n"
    '"AV. PROF. CARLOS CUNHA  1000 - JARACATY  SÃO LUÍS - MA  65076-907  BRASIL",São Luís,MA,65076-907\n'
    '"PARK SHOPPING CANOAS  AV. FARROUPILHA  4545 - LOJA 3004 - MAL. RONDON  CANOAS - RS  92020-475  BRASIL",Canoas,RS,92020-475\n')
rc, out = run([p, "-o", f"{TMP}/t4h", "--nome", "de"])
L = linhas(f"{TMP}/t4h/de.txt") if rc == 0 else []
check("espaço duplo vira vírgula, bairro sai",
      L[:1] == ["Avenida PROF CARLOS CUNHA 1000 Sao Luis MA 65076907 Brazil"], L[:1] or out[-300:])
check("corta nome do shopping e 'LOJA 3004'",
      len(L) > 1 and L[1] == "Avenida FARROUPILHA 4545 Canoas RS 92020475 Brazil", L[1:2])

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

print("\n=== T9b --separar-por não perde linha em colisão de nome ===")
p = entrada("colisao.csv", "endereco;cidade;uf;cep;rede\n"
    "Rua A 1 Centro;Santos;SP;11010000;Cinépolis\n"
    "Rua B 2 Centro;Santos;SP;11010001;Cinepolis\n"
    "Rua C 3 Centro;Santos;SP;11010002;UCI\n")
rc, out = run([p, "-o", f"{TMP}/t9b", "--nome", "cl", "--separar-por", "rede"])
check("validação passa (sem sobrescrita)", rc == 0 and "TUDO OK" in out, out[-400:])
check("Cinépolis + Cinepolis unidos em 1 arquivo com 2 linhas",
      os.path.exists(f"{TMP}/t9b/cl_cinepolis.txt") and len(linhas(f"{TMP}/t9b/cl_cinepolis.txt")) == 2,
      linhas(f"{TMP}/t9b/cl_cinepolis.txt") if os.path.exists(f"{TMP}/t9b/cl_cinepolis.txt") else "ausente")
check("avisa que uniu", "unidos por normalizacao" in out)
soma = sum(len(linhas(f"{TMP}/t9b/cl_{x}.txt")) for x in ("cinepolis", "uci"))
check("soma das partes = total", soma == len(linhas(f"{TMP}/t9b/cl.txt")), soma)

print("\n=== T9c coluna alternativa de logradouro e de número ===")
p = entrada("alt.csv", 'endereco,cidade,uf,cep,Endereço,Nº\n'
    '"Shopping Jardim Guadalupe, Guadalupe, Rio de Janeiro - RJ, 21515-001, Brasil",Rio de Janeiro,RJ,21515-001,Av. Brasil,22155\n'
    '"Praia do Flamengo, 402, Flamengo, Rio de Janeiro - RJ, 22210-065, Brasil",Rio de Janeiro,RJ,22210-065,AV OSWALDO CRUZ OPOSTO AO No 400,\n')
rc, out = run([p, "-o", f"{TMP}/t9c", "--nome", "al"])
L = linhas(f"{TMP}/t9c/al.txt") if rc == 0 else []
check("sem logradouro na principal, usa a coluna Endereço + Nº",
      L[:1] == ["Avenida Brasil 22155 Rio de Janeiro RJ 21515001 Brazil"], L[:1] or out[-300:])
check("principal boa NÃO é trocada pela alternativa",
      len(L) > 1 and L[1] == "Praia do Flamengo 402 Rio de Janeiro RJ 22210065 Brazil", L[1:2])

print("\n=== T9c1 segmento só-número como âncora do logradouro ===")
p = entrada("ancora.csv", 'endereco,cidade,uf,cep,Nº\n'
    '"Shopping Nova Iguaçu, Avendia Abílio Augusto Távora, 1111, Luz, Nova Iguaçu - RJ, 26260-045",Nova Iguaçu,RJ,26260-045,\n'
    '"Evs - Espaço Vida Saudável, Avenida Pastor Martin Luther King Júnior, Del Castilho, Rio de Janeiro - RJ, 20765-000",Rio de Janeiro,RJ,20765-000,126\n')
rc, out = run([p, "-o", f"{TMP}/t9c1", "--nome", "an"])
L = linhas(f"{TMP}/t9c1/an.txt") if rc == 0 else []
check("corta o shopping mesmo com 'Avendia' errado",
      L[:1] == ["Avendia Abilio Augusto Tavora 1111 Nova Iguacu RJ 26260045 Brazil"], L[:1] or out[-300:])
check("número de coluna entra após a rua, bairro ainda sai",
      len(L) > 1 and L[1] == "Avenida Pastor Martin Luther King Junior 126 Rio de Janeiro RJ 20765000 Brazil", L[1:2])

print("\n=== T9c2 coluna alternativa de inventário OOH ===")
p = entrada("ooh.csv", 'endereco,cidade,uf,cep,Endereço\n'
    '"MetrôRio-Vicente de Carvalho, Vicente de Carvalho, Rio de Janeiro - RJ, 21220-300",Rio de Janeiro,RJ,21220-300,AV AUTOMOVEL CLUBE EM FRENTE AO SUPERMERCADO CARREFOUR\n'
    '"SuperVia-São Cristóvão, São Cristóvão, Rio de Janeiro - RJ, 20940-200",Rio de Janeiro,RJ,20940-200,AV RADIAL OESTE ENTRONCAMENTO COM AV OSWALDO ARANHA\n'
    '"Ponto X, Centro, Rio de Janeiro - RJ, 20040-002",Rio de Janeiro,RJ,20040-002,"RUA BARÃO DA TORRE, E/F Nº 623, ESQUINA COM RUA X"\n')
rc, out = run([p, "-o", f"{TMP}/t9c2", "--nome", "oh"])
L = linhas(f"{TMP}/t9c2/oh.txt") if rc == 0 else []
check("corta 'EM FRENTE AO SUPERMERCADO'",
      L[:1] == ["Avenida AUTOMOVEL CLUBE Rio de Janeiro RJ 21220300 Brazil"], L[:1] or out[-300:])
check("corta 'ENTRONCAMENTO COM'",
      len(L) > 1 and L[1] == "Avenida RADIAL OESTE Rio de Janeiro RJ 20940200 Brazil", L[1:2])
check("extrai o número de 'E/F Nº 623'",
      len(L) > 2 and L[2] == "RUA BARAO DA TORRE 623 Rio de Janeiro RJ 20040002 Brazil", L[2:3])

print("\n=== T9d 'Torre'/'Loja' em nome de rua não é apagado ===")
p = entrada("torre.csv", "endereco,cidade,uf,cep\n"
    '"Rua Barão da Torre, 623, Ipanema, Rio de Janeiro - RJ, 22411-002",Rio de Janeiro,RJ,22411-002\n'
    '"Av. Farroupilha, 4545, Loja 3004, Mal. Rondon, Canoas - RS, 92020-475",Canoas,RS,92020-475\n')
rc, out = run([p, "-o", f"{TMP}/t9d", "--nome", "tr"])
L = linhas(f"{TMP}/t9d/tr.txt") if rc == 0 else []
check("'Barao da Torre 623' preservado",
      L[:1] == ["Rua Barao da Torre 623 Rio de Janeiro RJ 22411002 Brazil"], L[:1] or out[-300:])
check("'Loja 3004' ainda removido",
      len(L) > 1 and L[1] == "Avenida Farroupilha 4545 Canoas RS 92020475 Brazil", L[1:2])

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
