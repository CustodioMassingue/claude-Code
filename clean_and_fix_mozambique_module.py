#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpar e corrigir o módulo Mozambique Accounting para Odoo 18
"""

import os
import sys
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def validate_xml_file(filepath):
    """Valida um arquivo XML"""
    try:
        ET.parse(filepath)
        print(f"[OK] XML válido: {filepath}")
        return True
    except ET.ParseError as e:
        print(f"[ERRO] XML em {filepath}: {e}")
        return False

def validate_python_file(filepath):
    """Valida sintaxe Python"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, filepath, 'exec')
        print(f"[OK] Python válido: {filepath}")
        return True
    except SyntaxError as e:
        print(f"[ERRO] Python em {filepath}: {e}")
        return False

def clean_pycache(module_path):
    """Remove __pycache__ e arquivos .pyc"""
    removed = 0
    for root, dirs, files in os.walk(module_path):
        # Remove __pycache__ directories
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"[OK] Removido: {pycache_path}")
            removed += 1
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                os.remove(pyc_path)
                print(f"[OK] Removido: {pyc_path}")
                removed += 1
    
    return removed

def fix_manifest(manifest_path):
    """Corrige o arquivo __manifest__.py"""
    if not os.path.exists(manifest_path):
        print(f"[ERRO] Manifest não encontrado: {manifest_path}")
        return False
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove dependência de account_accountant se existir
    if 'account_accountant' in content:
        content = content.replace("'account_accountant',", "")
        content = content.replace('"account_accountant",', "")
        content = content.replace("'account_accountant'", "")
        content = content.replace('"account_accountant"', "")
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Removida dependência Enterprise de {manifest_path}")
    
    return True

def validate_csv_file(filepath):
    """Valida arquivo CSV de segurança"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            print(f"[ERRO] CSV vazio: {filepath}")
            return False
        
        # Verifica header
        header = lines[0].strip()
        expected_header = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
        
        if not header.startswith("id,"):
            print(f"[ERRO] Header CSV inválido em {filepath}")
            return False
        
        print(f"[OK] CSV válido: {filepath}")
        return True
    except Exception as e:
        print(f"[ERRO] CSV em {filepath}: {e}")
        return False

def create_minimal_structure(module_path):
    """Cria estrutura mínima se não existir"""
    dirs = [
        'models',
        'views', 
        'security',
        'data',
        'static/src/js',
        'static/src/scss',
        'static/src/xml',
        'i18n'
    ]
    
    for dir_path in dirs:
        full_path = os.path.join(module_path, dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"[OK] Diretório garantido: {full_path}")

def main():
    """Função principal"""
    module_path = "custom-addons/ubuntu_server/mozambique_accounting"
    
    if not os.path.exists(module_path):
        print(f"[ERRO] Módulo não encontrado em: {module_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("LIMPEZA E VALIDAÇÃO DO MÓDULO MOZAMBIQUE ACCOUNTING")
    print("=" * 60)
    
    # 1. Limpar __pycache__
    print("\n1. Limpando cache Python...")
    removed = clean_pycache(module_path)
    print(f"   Removidos {removed} arquivos/diretórios de cache")
    
    # 2. Criar estrutura mínima
    print("\n2. Garantindo estrutura de diretórios...")
    create_minimal_structure(module_path)
    
    # 3. Corrigir manifest
    print("\n3. Verificando __manifest__.py...")
    manifest_path = os.path.join(module_path, "__manifest__.py")
    fix_manifest(manifest_path)
    
    # 4. Validar XMLs
    print("\n4. Validando arquivos XML...")
    xml_errors = 0
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.xml'):
                filepath = os.path.join(root, file)
                if not validate_xml_file(filepath):
                    xml_errors += 1
    
    # 5. Validar Python
    print("\n5. Validando arquivos Python...")
    py_errors = 0
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if not validate_python_file(filepath):
                    py_errors += 1
    
    # 6. Validar CSVs
    print("\n6. Validando arquivos CSV...")
    csv_errors = 0
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.csv'):
                filepath = os.path.join(root, file)
                if not validate_csv_file(filepath):
                    csv_errors += 1
    
    # 7. Verificar arquivos obrigatórios
    print("\n7. Verificando arquivos obrigatórios...")
    required_files = [
        "__init__.py",
        "__manifest__.py",
        "models/__init__.py",
        "security/ir.model.access.csv"
    ]
    
    missing_files = []
    for req_file in required_files:
        filepath = os.path.join(module_path, req_file)
        if os.path.exists(filepath):
            print(f"[OK] Encontrado: {req_file}")
        else:
            print(f"[ERRO] Faltando: {req_file}")
            missing_files.append(req_file)
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 60)
    
    total_errors = xml_errors + py_errors + csv_errors + len(missing_files)
    
    if total_errors == 0:
        print("[SUCESSO] MÓDULO PRONTO PARA INSTALAÇÃO!")
        print("\nPróximos passos:")
        print("1. Copie o módulo para o servidor:")
        print("   scp -r custom-addons/ubuntu_server/mozambique_accounting user@server:/opt/odoo/custom-addons/")
        print("\n2. No servidor, reinicie o Odoo:")
        print("   sudo systemctl restart odoo")
        print("\n3. Ative o modo desenvolvedor no Odoo")
        print("\n4. Vá para Apps > Atualizar Lista de Apps")
        print("\n5. Procure 'Mozambique Accounting' e instale")
    else:
        print(f"[AVISO] ENCONTRADOS {total_errors} PROBLEMAS!")
        print(f"   - Erros XML: {xml_errors}")
        print(f"   - Erros Python: {py_errors}")
        print(f"   - Erros CSV: {csv_errors}")
        print(f"   - Arquivos faltando: {len(missing_files)}")
        print("\nCorreia os problemas antes de instalar o módulo.")
    
    return 0 if total_errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())