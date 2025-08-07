#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir conflitos e validar o módulo MZ Accounting Dashboard
"""

import os
import sys
import re
import json

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def check_js_conflicts(js_file):
    """Verifica conflitos em arquivos JavaScript"""
    print(f"\n[INFO] Verificando conflitos em {js_file}")
    
    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Padrões que podem causar conflitos
    patterns = {
        'views': r'registry\.category\("views"\)\.add\("([^"]+)"',
        'fields': r'registry\.category\("fields"\)\.add\("([^"]+)"',
        'widgets': r'registry\.category\("widgets"\)\.add\("([^"]+)"',
    }
    
    found = {}
    for category, pattern in patterns.items():
        matches = re.findall(pattern, content)
        if matches:
            found[category] = matches
            for match in matches:
                print(f"  [OK] Registrado em '{category}': {match}")
    
    return found

def check_xml_references(module_path):
    """Verifica referências em arquivos XML"""
    print(f"\n[INFO] Verificando referências XML")
    
    xml_files = []
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    references = {}
    for xml_file in xml_files:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Procurar por js_class
        js_class_matches = re.findall(r'js_class="([^"]+)"', content)
        if js_class_matches:
            references[xml_file] = js_class_matches
            for match in js_class_matches:
                print(f"  [OK] js_class em {os.path.basename(xml_file)}: {match}")
        
        # Procurar por widget
        widget_matches = re.findall(r'widget="([^"]+)"', content)
        if widget_matches:
            if xml_file not in references:
                references[xml_file] = []
            references[xml_file].extend(widget_matches)
            for match in widget_matches:
                if 'dashboard' in match.lower() or 'mz' in match.lower():
                    print(f"  [OK] widget em {os.path.basename(xml_file)}: {match}")
    
    return references

def validate_manifest(manifest_path):
    """Valida o arquivo __manifest__.py"""
    print(f"\n[INFO] Validando manifest")
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar assets
    if "'assets':" in content or '"assets":' in content:
        print("  [OK] Assets definidos no manifest")
        
        # Verificar se os arquivos JS estão incluídos
        if 'account_dashboard.js' in content:
            print("  [OK] account_dashboard.js incluído nos assets")
        else:
            print("  [AVISO] account_dashboard.js não encontrado nos assets")
    else:
        print("  [AVISO] Seção 'assets' não encontrada no manifest")
    
    return True

def main():
    """Função principal"""
    module_path = "custom-addons/ubuntu_server/mz_accounting_dashboard"
    
    print("=" * 60)
    print("VALIDAÇÃO DE CONFLITOS - MZ ACCOUNTING DASHBOARD")
    print("=" * 60)
    
    # 1. Verificar JavaScript
    js_file = os.path.join(module_path, "static/src/js/account_dashboard.js")
    if os.path.exists(js_file):
        js_registrations = check_js_conflicts(js_file)
    else:
        print(f"[ERRO] Arquivo JavaScript não encontrado: {js_file}")
        return 1
    
    # 2. Verificar XML
    xml_references = check_xml_references(module_path)
    
    # 3. Validar manifest
    manifest_path = os.path.join(module_path, "__manifest__.py")
    if os.path.exists(manifest_path):
        validate_manifest(manifest_path)
    
    # 4. Verificar consistência
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO DE CONSISTÊNCIA")
    print("=" * 60)
    
    issues = []
    
    # Verificar se js_class nas views XML corresponde ao registro JS
    if 'views' in js_registrations:
        registered_views = js_registrations['views']
        for xml_file, refs in xml_references.items():
            for ref in refs:
                if ref.endswith('_kanban') and ref not in registered_views:
                    if 'view' in xml_file.lower():
                        print(f"[AVISO] js_class '{ref}' em XML não corresponde ao registro JS")
                        print(f"        Registrado: {registered_views}")
                        issues.append(f"js_class mismatch: {ref}")
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 60)
    
    if not issues:
        print("[SUCESSO] Nenhum conflito detectado!")
        print("\nPróximos passos:")
        print("1. Limpar cache do navegador (Ctrl+Shift+Delete)")
        print("2. No servidor Odoo:")
        print("   sudo rm -rf /var/lib/odoo/.local/share/Odoo/filestore/*/web/assets/*")
        print("   sudo systemctl restart odoo")
        print("3. No Odoo: Settings > Developer > Clear assets and reload")
    else:
        print(f"[AVISO] {len(issues)} possíveis problemas encontrados:")
        for issue in issues:
            print(f"  - {issue}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())