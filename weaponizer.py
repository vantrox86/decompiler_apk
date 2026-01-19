import subprocess
import re
import os
import sys
import time
import urllib.request
from shutil import which

# Ativa o preenchimento automático com TAB
try:
    import readline
    readline.parse_and_bind("tab: complete")
except ImportError:
    pass

# --- PALETA DE CORES MODERNA ---
RED, DARK_RED, WHITE, BOLD, RESET, YELLOW = "\33[91m", "\33[31m", "\33[97m", "\33[1m", "\33[0m", "\33[93m"

def log(msg, level="info"):
    p = {"info": f"{WHITE}[*]{RESET}", "success": f"{RED}[+]{RESET}", "warn": f"{YELLOW}[!]{RESET}", "error": f"{BOLD}{RED}[-]{RESET}"}
    print(f"{p.get(level, '[*]')} {msg}")

def exibir_banner():
    os.system('clear' if os.name == 'posix' else 'cls')
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
    log("Verificando ferramentas de sistema...", "info")
    if not which("java"): install_package("openjdk-17-jdk")
    if not which("apktool"):
        if not install_package("apktool"): download_apktool_manual()
    # Verifica build-tools (zipalign/apksigner)
    if not which("apksigner"): install_package("apksigner")
    if not which("zipalign"): install_package("zipalign")

def install_package(pkg_name):
    for mgr in ["apt-get", "dnf", "pacman", "brew"]:
        if which(mgr):
            prefix = ["sudo"] if os.getuid() != 0 and mgr != "brew" else []
            try:
                subprocess.run(prefix + [mgr, "install", "-y", pkg_name], capture_output=True)
                return True
            except: continue
    return False

def download_apktool_manual():
    urls = {"wrapper": "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool", "jar": "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar"}
    target_bin = "/usr/local/bin"
    if not os.access(target_bin, os.W_OK): target_bin = os.path.expanduser("~/.local/bin")
    os.makedirs(target_bin, exist_ok=True)
    urllib.request.urlretrieve(urls["wrapper"], os.path.join(target_bin, "apktool"))
    urllib.request.urlretrieve(urls["jar"], os.path.join(target_bin, "apktool.jar"))
    subprocess.run(["chmod", "+x", os.path.join(target_bin, "apktool")])

def preparar_injecao(folder, silent=False):
    """Identifica o ponto de Hook e orienta a injeção."""
    manifest_path = os.path.join(folder, "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        log(f"Erro: AndroidManifest.xml não encontrado em {folder}", "error")
        return
        
    with open(manifest_path, "r") as f:
        content = f.read()
        main_activity = re.search(r'<activity [^>]*android:name="([^"]+)"', content)
        if main_activity:
            target = main_activity.group(1)
            print(f"\n{YELLOW}[!] ANÁLISE DE PONTO DE INJEÇÃO (HOOK):{RESET}")
            print(f"    » MainActivity: {BOLD}{target}{RESET}")
            print(f"    » Arquivo Smali: {BOLD}{folder}/smali/{target.replace('.', '/')}.smali{RESET}")
            print(f"\n{WHITE}[*] Instruções para o Pentester:{RESET}")
            print(f"    1. Abra o arquivo .smali acima.")
            print(f"    2. Localize o método 'onCreate' e insira a chamada para seu payload.")
            print(f"    3. Salve o arquivo e então proceda com o Build (Opção 2).")
        else:
            log("Não foi possível detectar o ponto de entrada automaticamente.", "warn")
    
    if not silent:
        input(f"\n{YELLOW}Pressione Enter para confirmar e continuar...{RESET}")

def build_e_assinar(out):
    """Executa a recompilação e assinatura, garantindo logs de erro."""
    signer = which("apksigner") or which("jarsigner")
    if not signer:
        log("Erro Crítico: Nenhum assinador (apksigner/jarsigner) encontrado!", "error")
        input(f"\n{YELLOW}Pressione Enter para voltar ao menu e corrigir as ferramentas...{RESET}")
        return

    final_apk = f"{out}_weaponized.apk"
    log(f"Weaponizing: Recompilando projeto '{out}'...", "info")
    
    # Roda o Build e captura erros reais
    res = subprocess.run(["apktool", "b", out, "-o", "tmp.apk"], capture_output=True, text=True)
    if res.returncode != 0:
        log("Falha na Recompilação! O código injetado pode conter erros de sintaxe.", "error")
        print(f"\n{RED}Logs do Apktool:{RESET}\n{res.stderr}")
        input(f"\n{YELLOW}Pressione Enter para voltar e revisar seu código...{RESET}")
        return
    
    # Assinatura
    ks = "debug.keystore"
    if not os.path.exists(ks):
        log("Gerando Keystore temporária para assinatura digital...", "info")
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", ks, "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)
    
    log(f"Signing: Aplicando assinatura via {os.path.basename(signer)}...", "info")
    if "apksigner" in signer:
        subprocess.run(["apksigner", "sign", "--ks", ks, "--ks-pass", "pass:android", "--out", final_apk, "tmp.apk"])
    else:
        subprocess.run(["jarsigner", "-keystore", ks, "-storepass", "android", "tmp.apk", "dev"])
        os.rename("tmp.apk", final_apk)
    
    if os.path.exists("tmp.apk"): os.remove("tmp.apk")
    log(f"SUCESSO! Artefato gerado: {BOLD}{final_apk}{RESET}", "success")
    input(f"\n{YELLOW}Pressione Enter para retornar ao HUD Principal...{RESET}")

def main():
    bootstrap()
    while True:
        exibir_banner()
        print(f" {BOLD}OPERATIONAL MENU:{RESET}")
        print(f" [{RED}1{RESET}] Reverse Engineering (Decompile & Scan)")
        print(f" [{RED}2{RESET}] Payload Injection (Build & Sign)")
        print(f" [{RED}3{RESET}] Terminar sessão")
        
        try: login = os.getlogin()
        except: login = "user"
        op = input(f"\n {BOLD}{RED}WEAPONIZER@{login}:~# {RESET}").strip()
        
        if op.lower() == "ls":
            print(f"\n{BOLD}{WHITE}Listagem de arquivos:{RESET}")
            subprocess.run(["ls", "-F", "--color=auto"])
            input(f"\n{YELLOW}Pressione Enter para voltar...{RESET}")
            continue

        if op == "1":
            path = os.path.abspath(os.path.expanduser(input(f" {RED}»{RESET} Alvo (.apk): ").strip()))
            if os.path.exists(path):
                out = os.path.splitext(os.path.basename(path))[0]
                log(f"Decompiling: {os.path.basename(path)}...", "info")
                subprocess.run(["apktool", "d", path, "-o", out, "-f"], capture_output=True)
                log("Sucesso! Analisando metas de injeção...", "success")
                preparar_injecao(out) # Mostra o guia de hook
            else: log("Arquivo não encontrado.", "error"); time.sleep(2)
            
        elif op == "2":
            out = input(f" {RED}»{RESET} Pasta do projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                # NOVO: Pergunta se quer ver as instruções de injeção antes de fechar o app
                ver_hook = input(f" {YELLOW}»{RESET} Visualizar instruções de Injeção/Hook novamente? (s/n): ").lower()
                if ver_hook == 's':
                    preparar_injecao(out)
                
                # Executa o build e assinatura com feedback total
                build_e_assinar(out)
            else:
                log(f"Diretório '{out}' não encontrado.", "error")
                input(f"\n{YELLOW}Pressione Enter para voltar...{RESET}")
        
        elif op == "3": break
        elif op.lower() == "clear": continue
        elif op == "": continue
        else: log(f"Comando '{op}' inválido.", "error"); time.sleep(1)

if __name__ == "__main__":
    main()
