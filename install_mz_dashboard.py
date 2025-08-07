#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para instalar e configurar o módulo MZ Accounting Dashboard no Odoo
"""

import os
import sys
import shutil

def check_odoo_paths():
    """Verifica possíveis caminhos do Odoo"""
    possible_paths = [
        r"C:\Program Files\Odoo 18.0",
        r"C:\Program Files\Odoo 18",
        r"C:\Program Files\Odoo",
        r"C:\Program Files (x86)\Odoo 18.0",
        r"C:\odoo",
        r"C:\odoo18",
        os.path.expanduser(r"~\odoo"),
        r"D:\odoo",
    ]
    
    print("\n[VERIFICACAO] Procurando instalacao do Odoo...")
    odoo_path = None
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"   [ENCONTRADO] Odoo em: {path}")
            odoo_path = path
            break
    
    if not odoo_path:
        print("   [AVISO] Nao foi possivel encontrar o Odoo automaticamente")
        print("\n   Digite o caminho do Odoo manualmente")
        print("   (ex: C:\\Program Files\\Odoo 18.0):")
        odoo_path = input("   > ").strip()
    
    return odoo_path

def find_addons_path(odoo_path):
    """Encontra o diretório de addons do Odoo"""
    possible_addons = [
        os.path.join(odoo_path, "server", "odoo", "addons"),
        os.path.join(odoo_path, "server", "addons"),
        os.path.join(odoo_path, "addons"),
        r"C:\mnt\extra-addons",
        r"/mnt/extra-addons",
        os.path.expanduser(r"~\extra-addons"),
    ]
    
    print("\n[VERIFICACAO] Procurando pasta de addons...")
    
    for path in possible_addons:
        if os.path.exists(path):
            print(f"   [ENCONTRADO] Addons em: {path}")
            return path
    
    print("   [AVISO] Pasta de addons nao encontrada")
    print("\n   Digite o caminho dos addons manualmente")
    print("   (ex: C:\\mnt\\extra-addons):")
    return input("   > ").strip()

def copy_module_to_addons(source_path, addons_path):
    """Copia o módulo para a pasta de addons"""
    module_name = "mz_accounting_dashboard"
    source = source_path
    destination = os.path.join(addons_path, module_name)
    
    print(f"\n[COPIA] Copiando modulo para pasta de addons...")
    print(f"   De: {source}")
    print(f"   Para: {destination}")
    
    try:
        # Remove destino se já existe
        if os.path.exists(destination):
            print("   [INFO] Removendo versao antiga...")
            shutil.rmtree(destination)
        
        # Copia o módulo
        shutil.copytree(source, destination)
        print("   [OK] Modulo copiado com sucesso!")
        return True
    except Exception as e:
        print(f"   [ERRO] Falha ao copiar: {e}")
        return False

def create_odoo_conf():
    """Cria arquivo de configuração com o caminho dos addons"""
    conf_content = """[options]
; Adicione este caminho aos seus addons_path no odoo.conf
; addons_path = C:\\Program Files\\Odoo 18.0\\server\\odoo\\addons,C:\\mnt\\extra-addons

; Para Windows, o arquivo odoo.conf geralmente esta em:
; C:\\Program Files\\Odoo 18.0\\server\\odoo.conf
; ou
; %PROGRAMDATA%\\Odoo\\odoo.conf

; Adicione a linha do addons_path incluindo o caminho do modulo
"""
    
    print("\n[CONFIG] Instrucoes para configurar odoo.conf:")
    print(conf_content)

def print_final_instructions():
    """Imprime instruções finais"""
    print("\n" + "="*60)
    print("INSTRUCOES FINAIS PARA INSTALACAO")
    print("="*60)
    
    print("\n[1] CONFIGURE O ODOO.CONF:")
    print("   Localize o arquivo odoo.conf:")
    print("   - Windows: C:\\Program Files\\Odoo 18.0\\server\\odoo.conf")
    print("   - ou: %PROGRAMDATA%\\Odoo\\odoo.conf")
    print("")
    print("   Adicione/edite a linha addons_path para incluir:")
    print("   addons_path = ...,C:\\mnt\\extra-addons")
    
    print("\n[2] REINICIE O SERVICO ODOO:")
    print("   PowerShell (como Admin):")
    print("   > Restart-Service odoo-server-18.0")
    print("")
    print("   Ou pelo Gerenciador de Servicos:")
    print("   > services.msc")
    print("   > Procure 'Odoo' e reinicie")
    
    print("\n[3] ATUALIZE A LISTA DE APPS:")
    print("   - Acesse: http://localhost:8069")
    print("   - Va em: Apps")
    print("   - Clique: Update Apps List")
    print("   - Procure: MZ Accounting Dashboard")
    print("   - Instale o modulo")
    
    print("\n[4] ATIVE O MODO DESENVOLVEDOR (se necessario):")
    print("   - Settings -> Developer Tools")
    print("   - Activate Developer Mode")
    
    print("\n[5] ACESSE O DASHBOARD:")
    print("   - Menu: MZ Accounting -> Dashboard")
    print("   - Ou crie um menu em: Settings -> Technical -> Menu Items")
    
    print("\n[IMPORTANTE]")
    print("   Se o modulo nao aparecer:")
    print("   1. Verifique se o addons_path esta correto no odoo.conf")
    print("   2. Certifique-se que o servico foi reiniciado")
    print("   3. Limpe o cache: --clear-cache ao iniciar o Odoo")
    print("   4. Use modo desenvolvedor para ver erros")
    
    print("\n" + "="*60)

def main():
    print("\n" + "="*60)
    print("INSTALADOR DO MZ ACCOUNTING DASHBOARD")
    print("="*60)
    
    # Caminho do módulo fonte
    module_source = r"C:\Users\custodio.massingue\Documents\GitHub\claude-Code\custom-addons\ubuntu_server\mz_accounting_dashboard"
    
    if not os.path.exists(module_source):
        print(f"\n[ERRO] Modulo nao encontrado em: {module_source}")
        return
    
    print(f"\n[INFO] Modulo encontrado em: {module_source}")
    
    # Verifica instalação do Odoo
    odoo_path = check_odoo_paths()
    
    if odoo_path and os.path.exists(odoo_path):
        # Encontra pasta de addons
        addons_path = find_addons_path(odoo_path)
        
        if addons_path:
            # Pergunta se deve copiar
            print("\n[PERGUNTA] Deseja copiar o modulo para a pasta de addons?")
            print("   (s/n): ", end="")
            response = input().strip().lower()
            
            if response == 's':
                copy_module_to_addons(module_source, addons_path)
    
    # Mostra configuração necessária
    create_odoo_conf()
    
    # Instruções finais
    print_final_instructions()
    
    print("\n[CONCLUIDO] Siga as instrucoes acima para completar a instalacao!")

if __name__ == "__main__":
    main()