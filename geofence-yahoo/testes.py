import subprocess, os, csv, io, sys, shutil, random
import pathlib
G=str(pathlib.Path(__file__).parent / "geofence.py")
def run(args):
    r=subprocess.run([sys.executable,G]+args,capture_output=True,text=True)
    return r.returncode, r.stdout+r.stderr
def linhas(p):
    return [l.decode('ascii') for l in open(p,'rb').read().split(b'\r\n') if l.strip()]
os.makedirs("/tmp/tc",exist_ok=True)
falhas=[]
def check(nome,cond,detalhe=""):
    print(("  OK   " if cond else "  FALHA")+f" {nome}"+("" if cond else f"  <- {detalhe}"))
    if not cond: falhas.append(nome)

print("\n=== T3 nissan genérico == dedicado ===")
rc,_=run(["/home/user/bobagens/nissan-dsp-geofencing/origem_nissan.csv","-o","/tmp/t1","--nome","nissan"])
a=set(linhas("/tmp/t1/nissan.txt")); b=set(linhas("/home/user/bobagens/nissan-dsp-geofencing/upload/nissan_varejo_enderecos.txt"))
check("saída idêntica ao build dedicado", a==b, f"{len(a)} vs {len(b)}; diff {list(a^b)[:2]}")
check("202 endereços", len(a)==202, len(a))

print("\n=== T4 só coordenadas -> exit 2, sem arquivo de upload ===")
rc,out=run(["/home/user/bobagens/yahoo-dsp-pois/origem_pois_unificados.csv","-o","/tmp/t2","--nome","pois"])
check("exit code 2", rc==2, rc)
check("não gerou .txt de upload", not os.path.exists("/tmp/t2/pois.txt"))
check("explica o motivo", "UM ENDERECO POR LINHA" in out)
check("gerou descartados.csv", os.path.exists("/tmp/t2/pois_descartados.csv"))

print("\n=== T5 sem cabeçalho ===")
open("/tmp/tc/nohdr.csv","w",encoding="utf-8").write(
"Rua Augusta 1500 Consolacao Sao Paulo SP 01305100\nAv Paulista 900 Bela Vista Sao Paulo SP 01310100\n")
rc,out=run(["/tmp/tc/nohdr.csv","-o","/tmp/t5","--nome","nh"])
check("2 endereços (não comeu a 1a linha)", rc==0 and len(linhas("/tmp/t5/nh.txt"))==2, out[-300:])

print("\n=== T6 encoding cp1252 + separador tab ===")
open("/tmp/tc/lat1.csv","wb").write("nome\tendereco\nLoja Açaí\tRua José Bonifácio 45 Centro Niterói RJ 24020-000\n".encode("cp1252"))
rc,out=run(["/tmp/tc/lat1.csv","-o","/tmp/t6","--nome","l1"])
ok = rc==0 and linhas("/tmp/t6/l1.txt")==["Rua Jose Bonifacio 45 Centro Niteroi RJ 24020000 Brazil"]
check("acento removido, hífen do CEP removido", ok, linhas("/tmp/t6/l1.txt") if rc==0 else out[-300:])

print("\n=== T7 categoria isenta usa só o nome ===")
open("/tmp/tc/isenta.csv","w",encoding="utf-8").write(
"nome;categoria;endereco\nAeroporto de Congonhas;Airports;\nJoalheria X;Joalherias;Rua Oscar Freire 200 Jardins Sao Paulo SP 01426000\n")
rc,out=run(["/tmp/tc/isenta.csv","-o","/tmp/t7","--nome","is"])
ls=linhas("/tmp/t7/is.txt") if rc==0 else []
check("aeroporto entra pelo nome", "Aeroporto de Congonhas" in ls, ls)
check("joalheria entra pelo endereço", any("Oscar Freire" in x for x in ls), ls)

print("\n=== T8 endereço quebrado em colunas ===")
open("/tmp/tc/cols.csv","w",encoding="utf-8").write(
"nome,logradouro,numero,bairro,cidade,uf,cep\nBanco Y,Rua da Quitanda,50,Centro,Rio de Janeiro,RJ,20011-030\n")
rc,out=run(["/tmp/tc/cols.csv","-o","/tmp/t8","--nome","cl"])
ok = rc==0 and linhas("/tmp/t8/cl.txt")==["Rua da Quitanda 50 Centro Rio de Janeiro RJ 20011030 Brazil"]
check("remonta na ordem convencional", ok, linhas("/tmp/t8/cl.txt") if rc==0 else out[-300:])

print("\n=== T9 mais de 10.000 -> divide em partes ===")
with open("/tmp/tc/big.csv","w",encoding="utf-8") as f:
    f.write("endereco\n")
    for i in range(10500): f.write(f"Rua Teste {i} Centro Campinas SP 13010{i%900:03d}\n")
rc,out=run(["/tmp/tc/big.csv","-o","/tmp/t9","--nome","bg"])
p1,p2="/tmp/t9/bg_parte1.txt","/tmp/t9/bg_parte2.txt"
check("dividiu em 2 partes", os.path.exists(p1) and os.path.exists(p2), out[-300:])
if os.path.exists(p1):
    check("parte1 = 10.000", len(linhas(p1))==10000, len(linhas(p1)))
    check("parte2 = 500", len(linhas(p2))==500, len(linhas(p2)))

print("\n=== T10 duplicatas ===")
open("/tmp/tc/dup.csv","w",encoding="utf-8").write(
"endereco\nRua A 1 Centro Santos SP 11010000\nRua A 1 Centro Santos SP 11010000\nRua B 2 Centro Santos SP 11010001\n")
rc,out=run(["/tmp/tc/dup.csv","-o","/tmp/t10","--nome","dp"])
check("dedupe para 2", rc==0 and len(linhas("/tmp/t10/dp.txt"))==2, out[-200:])

print("\n=== T11 nenhum caractere proibido em nenhuma saída ===")
import re, glob
bad=[]
for p in [q for q in glob.glob("/tmp/t[0-9]*/**/*.txt",recursive=True)+glob.glob("/tmp/t[0-9]*/**/*.csv",recursive=True)]:
    if "conferencia" in p or "descartados" in p: continue
    for l in linhas(p):
        if re.search(r"[^A-Za-z0-9 ]", l.replace('"','')): bad.append((p,l)); break
check("saídas 100% ASCII limpo", not bad, bad[:2])

print("\n"+("TODOS OS TESTES PASSARAM" if not falhas else f"FALHAS: {falhas}"))
sys.exit(1 if falhas else 0)
