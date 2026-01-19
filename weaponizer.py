import subprocess
import re
import os
import sys
import time
import urllib.request
from shutil import which

# --- PALETA DE CORES MODERNA ---
RED = "\33[91m"
DARK_RED = "\33[31m"
WHITE = "\33[97m"
BOLD = "\33[1m"
RESET = "\33[0m"
YELLOW = "\33[93m"

def log(msg, level="info"):
    p = {"info": f"{WHITE}[*]{RESET}", "success": f"{RED}[+]{RESET}", "warn": f"{YELLOW}[!]{RESET}", "error": f"{BOLD}{RED}[-]{RESET}"}
    print(f"{p.get(level, '[*]')} {msg}")

def exibir_banner():
    os.system('clear' if os.name == 'posix' else 'cls')
    # O 'fr' antes das aspas garante que o banner não desconfigure
    banner = fr"""
{RED} ██╗    ██╗███████╗ █████╗ ██████╗  ██████╗ ███╗   ██╗██╗███████╗███████╗██████╗ 
{RED} ██║    ██║██╔════╝██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██║╚══███╔╝██╔════╝██╔══██╗
{DARK_RED} ██║ █╗ ██║█████╗  ███████║██████╔╝██║   ██║██╔██╗ ██║██║  ███╔╝ █████╗  ██████╔╝
{DARK_RED} ██║███╗██║██╔══╝  ██╔══██║██╔═══╝ ██║   ██║██║╚██╗██║██║ ███╔╝  ██╔══╝  ██╔══██╗
{RED} ╚███╔███╔╝███████╗██║  ██║██║     ╚██████╔╝██║ ╚████║██║███████╗███████╗██║  ██║
{RED}  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
{RESET}
 {WHITE}{BOLD}WEAPONIZER PRO{RESET} | {WHITE}Dev: Romildo (thuf){RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def bootstrap():
    exibir_banner()
    log("Iniciando rotina de conformidade do sistema...", "info")
    time.sleep(1)
    if not which("java"): install_package("openjdk-17-jdk")
    if not which("apktool"):
        if not install_package("apktool"): download_apktool_manual()
    if not which("zipalign") or not which("apksigner"): install_package("apksigner zipalign")

def install_package(pkg_name):
    managers = ["apt-get", "dnf", "pacman", "brew"]
    for mgr in managers:
        if which(mgr):
            prefix = ["sudo"] if os.getuid() != 0 and mgr != "brew" else []
            cmd = prefix + [mgr, "install", "-y", pkg_name] if "pacman" not in mgr else prefix + ["pacman", "-S", "--noconfirm", pkg_name]
            try:
                subprocess.run(cmd, capture_output=True)
                return True
            except: continue
    return False

def download_apktool_manual():
    urls = {"wrapper": "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool", "jar": "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar"}
    target_bin = "/usr/local/bin"
    try:
        if not os.access(target_bin, os.W_OK):
            target_bin = os.path.expanduser("~/.local/bin")
            os.makedirs(target_bin, exist_ok=True)
        urllib.request.urlretrieve(urls["wrapper"], os.path.join(target_bin, "apktool"))
        urllib.request.urlretrieve(urls["jar"], os.path.join(target_bin, "apktool.jar"))
        subprocess.run(["chmod", "+x", os.path.join(target_bin, "apktool")])
    except Exception as e: log(f"Falha no download: {e}", "error"); sys.exit(1)

def build_e_assinar(out):
    signer = which("apksigner") or which("jarsigner")
    if not signer: return
    log(f"Recompilando {out}...", "info")
    subprocess.run(["apktool", "b", out, "-o", "tmp.apk"], capture_output=True)
    if not os.path.exists("debug.keystore"):
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", "debug.keystore", "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)
    if "apksigner" in signer: subprocess.run(["apksigner", "sign", "--ks", "debug.keystore", "--ks-pass", "pass:android", "--out", f"{out}_fixed.apk", "tmp.apk"])
    else: os.rename("tmp.apk", f"{out}_fixed.apk")
    log(f"Concluído!", "success"); time.sleep(2)

def main():
    bootstrap()
    while True:
        exibir_banner()
        print(f" {BOLD}OPERATIONAL MENU:{RESET}")
        print(f" [{RED}1{RESET}] Engenharia Reversa (Decompile & Scan)")
        print(f" [{RED}2{RESET}] Injetar Payload (Build & Sign)")
        print(f" [{RED}3{RESET}] Terminar sessão")
        
        # Obter login do sistema com fallback
        try: login = os.getlogin()
        except: login = "user"

        op = input(f"\n {BOLD}{RED}WEAPONIZER@{login}:~# {RESET}").strip()
        
        # --- LÓGICA DE COMANDOS DE TERMINAL ---
        if op.lower() == "ls":
            print(f"\n{BOLD}{WHITE}Listagem de diretório:{RESET}")
            # Roda o comando ls com cores
            subprocess.run(["ls", "-F", "--color=auto"])
            input(f"\n{YELLOW}Pressione Enter para voltar ao menu...{RESET}")
            continue

        elif op.lower() == "clear":
            exibir_banner()
            continue
        
        # --- LÓGICA DO MENU ---
        if op == "1":
            path = input(f" {RED}»{RESET} Alvo (.apk): ").strip()
            if os.path.exists(path):
                out = os.path.splitext(os.path.basename(path))[0]
                log(f"Extraindo dados de {path}...", "info")
                subprocess.run(["apktool", "d", path, "-o", out, "-f"], capture_output=True)
                log(f"Pasta de trabalho criada: {out}", "success")
                input("\nPresione Enter para continuar...")
            else: log("Arquivo não encontrado.", "error"); time.sleep(2)
            
        elif op == "2":
            out = input(f" {RED}»{RESET} Pasta do projeto: ").strip()
            if os.path.isdir(out): build_e_assinar(out)
            else: log("Diretório inexistente.", "error"); time.sleep(2)
            
        elif op == "3":
            log("Encerrando...", "info")
            break
        
        elif op == "": # Ignorar enter vazio
            continue
            
        else:
            if op.lower() != "ls": # Se não for nenhum dos acima, avisa comando inválido
                log(f"Opção ou comando '{op}' inválido.", "error")
                time.sleep(1.5)

if __name__ == "__main__":
    main()
