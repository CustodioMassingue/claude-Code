#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar correções do módulo MZ Accounting Dashboard para Odoo 18
"""

import os
import sys
import re

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def validate_js_file(filepath):
    """Valida o arquivo JavaScript para Odoo 18"""
    print(f"\n[INFO] Validando JavaScript: {os.path.basename(filepath)}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    fixes = []
    
    # Verificar problemas conhecidos do Odoo 18
    odoo18_issues = {
        'useService("rpc")': 'Use useService("orm") em vez de rpc',
        'this.rpc(': 'Use this.orm.call() em vez de this.rpc()',
        'useService("user")': 'Serviço user pode não estar disponível em todos os contextos',
        '/web/dataset/call_kw': 'Use orm.call() diretamente',
    }
    
    for issue, fix in odoo18_issues.items():
        if issue in content:
            issues.append(f"  [AVISO] Encontrado: {issue}")
            fixes.append(f"    -> {fix}")
    
    # Verificar imports corretos
    required_imports = [
        '@web/core/registry',
        '@web/views/kanban/kanban_controller',
        '@odoo/owl',
    ]
    
    for import_str in required_imports:
        if import_str in content:
            print(f"  [OK] Import encontrado: {import_str}")
    
    # Verificar registro da view
    if 'registry.category("views").add(' in content:
        matches = re.findall(r'registry\.category\("views"\)\.add\("([^"]+)"', content)
        for match in matches:
            print(f"  [OK] View registrada: {match}")
    
    if issues:
        print("\n  [PROBLEMAS ENCONTRADOS]:")
        for issue, fix in zip(issues, fixes):
            print(issue)
            print(fix)
    else:
        print("  [OK] Nenhum problema de compatibilidade detectado")
    
    return len(issues) == 0

def check_manifest(module_path):
    """Verifica qual arquivo JS está ativo no manifest"""
    print("\n[INFO] Verificando __manifest__.py")
    
    manifest_path = os.path.join(module_path, "__manifest__.py")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar qual JS está ativo
    if 'account_dashboard_simple.js' in content and '# ' not in content.split('account_dashboard_simple.js')[0].split('\n')[-1]:
        print("  [OK] Usando versão SIMPLIFICADA (account_dashboard_simple.js)")
        active_js = 'simple'
    elif 'account_dashboard.js' in content and '# ' not in content.split('account_dashboard.js')[0].split('\n')[-1]:
        print("  [OK] Usando versão COMPLETA (account_dashboard.js)")
        active_js = 'complex'
    else:
        print("  [ERRO] Nenhum arquivo JS está ativo!")
        active_js = None
    
    return active_js

def check_view_xml(module_path):
    """Verifica a configuração da view XML"""
    print("\n[INFO] Verificando view XML")
    
    view_file = os.path.join(module_path, "views/account_journal_dashboard_view.xml")
    with open(view_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar js_class
    matches = re.findall(r'js_class="([^"]+)"', content)
    if matches:
        print(f"  [OK] js_class configurado: {matches[0]}")
        return matches[0]
    else:
        print("  [ERRO] js_class não encontrado!")
        return None

def main():
    """Função principal"""
    module_path = "custom-addons/ubuntu_server/mz_accounting_dashboard"
    
    print("=" * 60)
    print("VALIDAÇÃO ODOO 18 - MZ ACCOUNTING DASHBOARD")
    print("=" * 60)
    
    # 1. Verificar qual JS está ativo
    active_js = check_manifest(module_path)
    
    # 2. Verificar arquivo JS
    if active_js == 'simple':
        js_file = os.path.join(module_path, "static/src/js/account_dashboard_simple.js")
    elif active_js == 'complex':
        js_file = os.path.join(module_path, "static/src/js/account_dashboard.js")
    else:
        js_file = None
    
    if js_file and os.path.exists(js_file):
        js_valid = validate_js_file(js_file)
    else:
        js_valid = False
        print(f"\n[ERRO] Arquivo JS não encontrado!")
    
    # 3. Verificar view XML
    js_class = check_view_xml(module_path)
    
    # 4. Verificar consistência
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO DE CONSISTÊNCIA")
    print("=" * 60)
    
    if active_js == 'simple' and js_class == 'mz_account_dashboard_kanban_simple':
        print("[OK] Configuração consistente - Usando versão SIMPLIFICADA")
        consistent = True
    elif active_js == 'complex' and js_class == 'mz_account_dashboard_kanban':
        print("[OK] Configuração consistente - Usando versão COMPLETA")
        consistent = True
    else:
        print(f"[ERRO] Inconsistência detectada!")
        print(f"  - JS ativo: {active_js}")
        print(f"  - js_class: {js_class}")
        consistent = False
    
    # Resumo e recomendações
    print("\n" + "=" * 60)
    print("RESUMO E RECOMENDAÇÕES")
    print("=" * 60)
    
    if js_valid and consistent:
        print("\n[SUCESSO] Módulo configurado corretamente para Odoo 18!")
        print("\nPróximos passos:")
        print("1. Limpar cache do navegador")
        print("2. Reiniciar Odoo:")
        print("   sudo systemctl restart odoo")
        print("3. Atualizar o módulo em Apps")
    else:
        print("\n[ATENÇÃO] Problemas detectados!")
        print("\nRecomendações:")
        print("1. USE A VERSÃO SIMPLIFICADA para testar primeiro")
        print("2. Certifique-se de que js_class no XML corresponde ao JS registrado")
        print("3. Evite usar serviços não disponíveis (rpc, user)")
        print("4. Use apenas: orm, action, notification")
    
    print("\n" + "=" * 60)
    print("SOLUÇÃO RÁPIDA")
    print("=" * 60)
    print("\nPara usar a versão SIMPLIFICADA (recomendado):")
    print("1. Mantenha account_dashboard_simple.js no manifest")
    print("2. Use js_class='mz_account_dashboard_kanban_simple' na view")
    print("3. Esta versão não tem customizações complexas mas funciona")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())