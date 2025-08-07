#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para forçar atualização completa do módulo MZ Accounting Dashboard
"""

import os
import sys
import subprocess
import shutil

def clear_cache():
    """Limpa todos os caches do Odoo"""
    cache_paths = [
        "/var/lib/odoo/.local/share/Odoo/filestore/*/web/assets/*",
        "/tmp/odoosessions*",
        "~/.cache/odoo*"
    ]
    
    print("\n[LIMPEZA] Limpando caches do Odoo...")
    for path in cache_paths:
        try:
            expanded_path = os.path.expanduser(path)
            if '*' in expanded_path:
                # Use shell to handle wildcards
                os.system(f"rm -rf {expanded_path} 2>/dev/null")
            elif os.path.exists(expanded_path):
                if os.path.isdir(expanded_path):
                    shutil.rmtree(expanded_path)
                else:
                    os.remove(expanded_path)
            print(f"   [OK] Limpo: {path}")
        except Exception as e:
            print(f"   [AVISO] Nao foi possivel limpar {path}: {e}")

def update_module_windows():
    """Instruções específicas para Windows"""
    print("\n" + "="*60)
    print("INSTRUCOES PARA WINDOWS")
    print("="*60)
    
    print("\n1. Via Interface Web do Odoo (RECOMENDADO):")
    print("   a) Acesse: http://localhost:8069")
    print("   b) Va em: Apps -> Update Apps List")
    print("   c) Procure por 'MZ Accounting Dashboard'")
    print("   d) Clique nos 3 pontos -> Upgrade")
    print("   e) Confirme a atualizacao")
    
    print("\n2. Via PowerShell/CMD:")
    print("   # Navegue ate a pasta do Odoo")
    print("   cd C:\\Program Files\\Odoo 18.0\\server")
    print("   # ou onde seu Odoo esta instalado")
    print("")
    print("   # Execute o update")
    print("   python odoo-bin -u mz_accounting_dashboard --stop-after-init")
    
    print("\n3. Reinicie o servico Odoo:")
    print("   # No PowerShell como Administrador:")
    print("   Restart-Service odoo-server-18.0")
    print("   # ou reinicie manualmente pelo Gerenciador de Servicos")

def print_instructions():
    """Imprime instruções para atualização manual"""
    print("\n" + "="*60)
    print("INSTRUCOES PARA ATUALIZACAO COMPLETA")
    print("="*60)
    
    print("\n[PASSO 1] Atualize o modulo:")
    print("   -> Acesse: Apps -> Update Apps List")
    print("   -> Procure: MZ Accounting Dashboard")
    print("   -> Clique: Menu (3 pontos) -> Upgrade")
    print("   -> Confirme a atualizacao")
    
    print("\n[PASSO 2] Limpe o cache do navegador:")
    print("   -> Chrome/Edge: Ctrl+Shift+F5")
    print("   -> Firefox: Ctrl+F5")
    print("   -> Ou abra em modo incognito/privado")
    
    print("\n[PASSO 3] Acesse o Dashboard:")
    print("   -> Menu: MZ Accounting -> Dashboard")
    print("   -> Ou: Accounting -> MZ Dashboard")
    
    print("\n[VISUAL ESPERADO]")
    print("   O dashboard deve mostrar:")
    print("   -> Headers com gradiente roxo")
    print("   -> Cards com sombras e bordas arredondadas")
    print("   -> Graficos interativos")
    print("   -> Design profissional estilo Enterprise")
    
    print("\n[TROUBLESHOOTING]")
    print("   Se ainda nao mudou:")
    print("   1. Confirme que o modulo esta instalado")
    print("   2. Verifique a versao: deve ser 18.0.2.0.0")
    print("   3. Teste em outro navegador")
    print("   4. Reinicie o servidor Odoo completamente")
    print("   5. Delete a pasta filestore/cache:")
    print("      Windows: %APPDATA%\\Odoo\\filestore\\<db>\\web")
    print("      Linux: ~/.local/share/Odoo/filestore/<db>/web")
    
    print("\n[COMANDO DIRETO]")
    print("   Para forcar update via comando:")
    print("   python odoo-bin -u mz_accounting_dashboard -d seu_banco --stop-after-init")
    
    print("\n" + "="*60)

def main():
    print("\n" + "="*60)
    print("FORCANDO ATUALIZACAO DO MZ ACCOUNTING DASHBOARD")
    print("="*60)
    
    # Detecta o sistema operacional
    if sys.platform == "win32":
        print("\n[INFO] Sistema Windows detectado")
        update_module_windows()
    else:
        print("\n[INFO] Sistema Unix/Linux detectado")
        clear_cache()
    
    # Mostra instruções gerais
    print_instructions()
    
    print("\n[CONCLUIDO] Siga as instrucoes acima para completar a atualizacao!")
    print("="*60)

if __name__ == "__main__":
    main()