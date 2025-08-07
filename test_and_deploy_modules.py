#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar e fazer deploy dos módulos de contabilidade
"""

import os
import sys
import xml.etree.ElementTree as ET
import subprocess
import shutil
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def validate_xml_files(module_path):
    """Valida todos os arquivos XML de um módulo"""
    print(f"\n[INFO] Validando XMLs em {module_path}")
    errors = []
    
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.xml'):
                filepath = os.path.join(root, file)
                try:
                    ET.parse(filepath)
                    print(f"  [OK] {file}")
                except ET.ParseError as e:
                    print(f"  [ERRO] {file}: {e}")
                    errors.append((file, str(e)))
    
    return errors

def validate_python_files(module_path):
    """Valida todos os arquivos Python de um módulo"""
    print(f"\n[INFO] Validando Python em {module_path}")
    errors = []
    
    for root, dirs, files in os.walk(module_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, filepath, 'exec')
                    print(f"  [OK] {file}")
                except SyntaxError as e:
                    print(f"  [ERRO] {file}: {e}")
                    errors.append((file, str(e)))
    
    return errors

def check_manifest(module_path):
    """Verifica o arquivo __manifest__.py"""
    manifest_path = os.path.join(module_path, '__manifest__.py')
    
    if not os.path.exists(manifest_path):
        return False, "Manifest não encontrado"
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compilar para verificar sintaxe
        compile(content, manifest_path, 'exec')
        
        # Verificar dependências Enterprise
        if 'account_accountant' in content:
            print("  [AVISO] Dependência Enterprise encontrada: account_accountant")
            return False, "Contém dependência Enterprise"
        
        print("  [OK] Manifest válido")
        return True, "OK"
        
    except Exception as e:
        return False, str(e)

def clean_module(module_path):
    """Limpa cache e arquivos desnecessários"""
    print(f"\n[INFO] Limpando {module_path}")
    cleaned = 0
    
    for root, dirs, files in os.walk(module_path):
        # Remover __pycache__
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"  [OK] Removido: __pycache__")
            cleaned += 1
        
        # Remover .pyc
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                os.remove(pyc_path)
                print(f"  [OK] Removido: {file}")
                cleaned += 1
    
    if cleaned == 0:
        print("  [OK] Nada para limpar")
    
    return cleaned

def create_deployment_package(module_name):
    """Cria pacote ZIP para deploy"""
    module_path = f"custom-addons/ubuntu_server/{module_name}"
    
    if not os.path.exists(module_path):
        print(f"[ERRO] Módulo não encontrado: {module_path}")
        return None
    
    # Limpar antes de empacotar
    clean_module(module_path)
    
    # Criar ZIP
    zip_name = f"{module_name}.zip"
    shutil.make_archive(module_name, 'zip', module_path)
    print(f"[OK] Pacote criado: {zip_name}")
    
    return zip_name

def test_module(module_name):
    """Testa um módulo completamente"""
    print("\n" + "="*60)
    print(f"TESTANDO MÓDULO: {module_name}")
    print("="*60)
    
    module_path = f"custom-addons/ubuntu_server/{module_name}"
    
    if not os.path.exists(module_path):
        print(f"[ERRO] Módulo não encontrado: {module_path}")
        return False
    
    # 1. Verificar manifest
    print("\n1. Verificando __manifest__.py...")
    manifest_ok, manifest_msg = check_manifest(module_path)
    if not manifest_ok:
        print(f"   [ERRO] {manifest_msg}")
        return False
    
    # 2. Validar XMLs
    print("\n2. Validando XMLs...")
    xml_errors = validate_xml_files(module_path)
    if xml_errors:
        print(f"   [ERRO] {len(xml_errors)} erros encontrados")
        return False
    
    # 3. Validar Python
    print("\n3. Validando Python...")
    py_errors = validate_python_files(module_path)
    if py_errors:
        print(f"   [ERRO] {len(py_errors)} erros encontrados")
        return False
    
    # 4. Verificar estrutura
    print("\n4. Verificando estrutura...")
    required_files = [
        "__init__.py",
        "__manifest__.py",
        "security/ir.model.access.csv"
    ]
    
    missing = []
    for req_file in required_files:
        filepath = os.path.join(module_path, req_file)
        if not os.path.exists(filepath):
            print(f"   [ERRO] Arquivo obrigatório faltando: {req_file}")
            missing.append(req_file)
        else:
            print(f"   [OK] {req_file}")
    
    if missing:
        return False
    
    print(f"\n[SUCESSO] Módulo {module_name} está pronto para deploy!")
    return True

def main():
    """Função principal"""
    
    modules = [
        "mz_accounting_dashboard",  # Módulo simples
        "mozambique_accounting"      # Módulo completo
    ]
    
    print("="*60)
    print("TESTE E VALIDAÇÃO DOS MÓDULOS DE CONTABILIDADE")
    print("="*60)
    
    results = {}
    
    for module in modules:
        if test_module(module):
            results[module] = "PRONTO"
        else:
            results[module] = "COM ERROS"
    
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    for module, status in results.items():
        icon = "[OK]" if status == "PRONTO" else "[ERRO]"
        print(f"{icon} {module}: {status}")
    
    # Oferecer criação de pacotes
    ready_modules = [m for m, s in results.items() if s == "PRONTO"]
    
    if ready_modules:
        print("\n" + "="*60)
        print("MÓDULOS PRONTOS PARA DEPLOY")
        print("="*60)
        
        for module in ready_modules:
            print(f"\n[INFO] Criando pacote para {module}...")
            zip_file = create_deployment_package(module)
            if zip_file:
                print(f"[OK] Pacote criado: {zip_file}")
        
        print("\n" + "="*60)
        print("INSTRUÇÕES DE DEPLOY")
        print("="*60)
        
        print("\n1. MÓDULO SIMPLES (mz_accounting_dashboard):")
        print("   - Dashboard básica funcional")
        print("   - Instalar primeiro para testar")
        print("   - Menos chance de erros")
        
        print("\n2. MÓDULO COMPLETO (mozambique_accounting):")
        print("   - Todas as funcionalidades")
        print("   - Dashboard avançada")
        print("   - Instalar após testar o simples")
        
        print("\n3. COMANDO DE DEPLOY:")
        print("   python deploy_to_odoo_server.py IP_SERVIDOR")
        
        print("\n4. OU COPIAR MANUALMENTE:")
        print("   scp -r custom-addons/ubuntu_server/MODULE user@server:/opt/odoo/custom-addons/")

if __name__ == "__main__":
    main()