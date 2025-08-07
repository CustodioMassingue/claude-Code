#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar e validar o menu do MZ Accounting Dashboard
"""

import os
import sys
import xml.etree.ElementTree as ET

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def check_menu_structure(module_path):
    """Verifica a estrutura de menus do módulo"""
    print("\n[INFO] Verificando estrutura de menus")
    
    view_file = os.path.join(module_path, "views/account_journal_dashboard_view.xml")
    
    if not os.path.exists(view_file):
        print(f"[ERRO] Arquivo de view não encontrado: {view_file}")
        return False
    
    try:
        tree = ET.parse(view_file)
        root = tree.getroot()
        
        # Procurar por menuitems
        menuitems = root.findall(".//menuitem")
        
        print(f"\n[INFO] Encontrados {len(menuitems)} menus:")
        for menu in menuitems:
            menu_id = menu.get('id', 'sem_id')
            menu_name = menu.get('name', 'sem_nome')
            parent = menu.get('parent', 'raiz')
            action = menu.get('action', 'sem_action')
            groups = menu.get('groups', 'todos')
            
            print(f"\n  Menu ID: {menu_id}")
            print(f"    Nome: {menu_name}")
            print(f"    Parent: {parent}")
            print(f"    Action: {action}")
            print(f"    Groups: {groups}")
        
        # Verificar se há menu raiz
        root_menus = [m for m in menuitems if not m.get('parent') or 'root' in m.get('id', '')]
        if root_menus:
            print(f"\n[OK] Menu raiz encontrado: {root_menus[0].get('name')}")
        else:
            print("\n[AVISO] Nenhum menu raiz encontrado")
        
        return True
        
    except ET.ParseError as e:
        print(f"[ERRO] Erro ao analisar XML: {e}")
        return False

def check_manifest(module_path):
    """Verifica as configurações do manifest"""
    print("\n[INFO] Verificando __manifest__.py")
    
    manifest_path = os.path.join(module_path, "__manifest__.py")
    
    if not os.path.exists(manifest_path):
        print(f"[ERRO] Manifest não encontrado: {manifest_path}")
        return False
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificações importantes
    checks = {
        "'application': True": "Módulo configurado como aplicação",
        "'installable': True": "Módulo instalável",
        "'account'": "Dependência do módulo account",
        "account_journal_dashboard_view.xml": "View incluída nos data files"
    }
    
    for check, description in checks.items():
        if check in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [ERRO] {description} não encontrado")
    
    return True

def check_action(module_path):
    """Verifica se a action está configurada corretamente"""
    print("\n[INFO] Verificando Action do Dashboard")
    
    view_file = os.path.join(module_path, "views/account_journal_dashboard_view.xml")
    
    try:
        tree = ET.parse(view_file)
        root = tree.getroot()
        
        # Procurar por actions
        actions = root.findall(".//record[@model='ir.actions.act_window']")
        
        print(f"\n[INFO] Encontradas {len(actions)} actions:")
        for action in actions:
            action_id = action.get('id', 'sem_id')
            
            # Pegar campos da action
            fields = {}
            for field in action.findall('field'):
                fields[field.get('name')] = field.text or field.get('ref', '')
            
            print(f"\n  Action ID: {action_id}")
            print(f"    Nome: {fields.get('name', 'N/A')}")
            print(f"    Model: {fields.get('res_model', 'N/A')}")
            print(f"    View Mode: {fields.get('view_mode', 'N/A')}")
            print(f"    Domain: {fields.get('domain', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"[ERRO] Erro ao verificar actions: {e}")
        return False

def main():
    """Função principal"""
    module_path = "custom-addons/ubuntu_server/mz_accounting_dashboard"
    
    print("=" * 60)
    print("TESTE DE MENU - MZ ACCOUNTING DASHBOARD")
    print("=" * 60)
    
    if not os.path.exists(module_path):
        print(f"[ERRO] Módulo não encontrado em: {module_path}")
        return 1
    
    # Executar verificações
    check_manifest(module_path)
    check_menu_structure(module_path)
    check_action(module_path)
    
    # Instruções finais
    print("\n" + "=" * 60)
    print("INSTRUÇÕES PARA RESOLVER PROBLEMA DE MENU")
    print("=" * 60)
    
    print("\n1. ATUALIZAR O MÓDULO:")
    print("   - No Odoo, vá para Apps")
    print("   - Procure 'MZ Accounting Dashboard'")
    print("   - Clique em 'Upgrade' ou desinstale e reinstale")
    
    print("\n2. LIMPAR CACHE:")
    print("   - Settings > Developer > Clear assets and reload")
    print("   - Ou pressione Ctrl+Shift+R no navegador")
    
    print("\n3. VERIFICAR PERMISSÕES:")
    print("   - Certifique-se de que seu usuário tem permissões de contabilidade")
    print("   - Settings > Users > Seu usuário > Access Rights")
    print("   - Marque: Accounting / Billing")
    
    print("\n4. MENU ESPERADO:")
    print("   - Menu principal: 'MZ Accounting'")
    print("   - Submenu: 'Dashboard'")
    print("   - Também em: Accounting > Dashboard (se módulo account instalado)")
    
    print("\n5. SE AINDA NÃO APARECER:")
    print("   - Faça logout e login novamente")
    print("   - Verifique se há erros no log do servidor")
    print("   - sudo tail -f /var/log/odoo/odoo.log")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())