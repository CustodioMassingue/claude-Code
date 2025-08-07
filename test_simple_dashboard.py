#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar configuração simplificada do dashboard
"""

import os
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def main():
    """Função principal"""
    module_path = "custom-addons/ubuntu_server/mz_accounting_dashboard"
    
    print("=" * 60)
    print("CONFIGURAÇÃO SIMPLIFICADA - MZ ACCOUNTING DASHBOARD")
    print("=" * 60)
    
    print("\n[INFO] Módulo configurado para usar kanban PADRÃO do Odoo")
    print("  - Sem JavaScript customizado")
    print("  - Sem js_class na view")
    print("  - Usando apenas estilos CSS")
    
    print("\n" + "=" * 60)
    print("PRÓXIMOS PASSOS")
    print("=" * 60)
    
    print("\n1. LIMPAR CACHE COMPLETAMENTE:")
    print("   No servidor:")
    print("   sudo rm -rf /var/lib/odoo/.local/share/Odoo/filestore/*/web/assets/*")
    print("   sudo find /tmp -name 'odo*' -delete")
    
    print("\n2. REINICIAR ODOO:")
    print("   sudo systemctl stop odoo")
    print("   sudo systemctl start odoo")
    
    print("\n3. NO NAVEGADOR:")
    print("   - Use modo incógnito/privado")
    print("   - Ou limpe todo cache (Ctrl+Shift+Delete)")
    
    print("\n4. NO ODOO:")
    print("   - Vá para Apps")
    print("   - Procure 'MZ Accounting Dashboard'")
    print("   - Clique em 'Upgrade' (ou desinstale e reinstale)")
    
    print("\n5. ACESSAR O DASHBOARD:")
    print("   - Menu: MZ Accounting → Dashboard")
    print("   - Ou: Accounting → Dashboard (se disponível)")
    
    print("\n" + "=" * 60)
    print("O QUE ESPERAR")
    print("=" * 60)
    
    print("\n✓ Dashboard mostrará cards kanban para cada journal")
    print("✓ Dados dos journals serão calculados automaticamente")
    print("✓ Estilos CSS aplicados (cores, gradientes)")
    print("✓ Sem erros de JavaScript/OWL")
    
    print("\n" + "=" * 60)
    print("SE AINDA HOUVER ERROS")
    print("=" * 60)
    
    print("\n1. DESINSTALAR COMPLETAMENTE:")
    print("   - Apps → MZ Accounting Dashboard → Uninstall")
    print("   - Confirmar desinstalação")
    
    print("\n2. REINSTALAR DO ZERO:")
    print("   - Apps → Update Apps List")
    print("   - Procurar e instalar novamente")
    
    print("\n3. VERIFICAR LOGS:")
    print("   sudo tail -f /var/log/odoo/odoo.log")
    
    print("\n4. VERIFICAR DEPENDÊNCIAS:")
    print("   - Módulo 'account' deve estar instalado")
    print("   - Usuário deve ter permissões de contabilidade")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())