#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script FINAL para corrigir o módulo MZ Accounting Dashboard
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
    
    print("=" * 70)
    print("SOLUÇÃO FINAL - MZ ACCOUNTING DASHBOARD")
    print("=" * 70)
    
    print("\n[PROBLEMA IDENTIFICADO]")
    print("O erro 'Cannot find key mz_account_dashboard_kanban' ocorre porque:")
    print("1. Há referências antigas em cache")
    print("2. O banco de dados tem registros antigos")
    print("3. Conflito entre diferentes versões do código")
    
    print("\n" + "=" * 70)
    print("SOLUÇÃO COMPLETA - PASSO A PASSO")
    print("=" * 70)
    
    print("\n### PASSO 1: DESINSTALAR COMPLETAMENTE ###")
    print("\n1.1. No Odoo:")
    print("   - Apps → Procurar 'MZ Accounting Dashboard'")
    print("   - Clique em 'Uninstall'")
    print("   - Confirme a desinstalação")
    
    print("\n1.2. Aguarde a desinstalação completa")
    
    print("\n### PASSO 2: LIMPAR O BANCO DE DADOS ###")
    print("\n2.1. Conecte ao PostgreSQL:")
    print("   sudo -u postgres psql SEU_DATABASE")
    
    print("\n2.2. Execute os comandos SQL:")
    print("""
   -- Remover todas as referências antigas
   DELETE FROM ir_act_window WHERE name LIKE '%MZ%Dashboard%';
   DELETE FROM ir_ui_view WHERE name LIKE '%mz%dashboard%';
   DELETE FROM ir_ui_menu WHERE name LIKE '%MZ Accounting%';
   DELETE FROM ir_model_data WHERE module = 'mz_accounting_dashboard';
   
   -- Limpar cache
   DELETE FROM ir_attachment WHERE name LIKE '%mz_account%';
   """)
    
    print("\n### PASSO 3: LIMPAR ARQUIVOS DO SERVIDOR ###")
    print("\n3.1. Remover cache de assets:")
    print("   sudo rm -rf /var/lib/odoo/.local/share/Odoo/filestore/*/web/assets/*")
    
    print("\n3.2. Remover arquivos temporários:")
    print("   sudo find /tmp -name 'odo*' -delete")
    
    print("\n### PASSO 4: REINICIAR ODOO ###")
    print("\n4.1. Parar o serviço:")
    print("   sudo systemctl stop odoo")
    
    print("\n4.2. Iniciar o serviço:")
    print("   sudo systemctl start odoo")
    
    print("\n4.3. Verificar status:")
    print("   sudo systemctl status odoo")
    
    print("\n### PASSO 5: REINSTALAR O MÓDULO ###")
    print("\n5.1. Copiar módulo atualizado:")
    print("   sudo cp -r mz_accounting_dashboard /opt/odoo/custom-addons/")
    print("   sudo chown -R odoo:odoo /opt/odoo/custom-addons/mz_accounting_dashboard")
    
    print("\n5.2. No Odoo (use modo incógnito):")
    print("   - Apps → Update Apps List")
    print("   - Procurar 'MZ Accounting Dashboard'")
    print("   - Clique em 'Install'")
    
    print("\n### PASSO 6: VERIFICAR ###")
    print("\n6.1. Acesse o menu:")
    print("   - MZ Accounting → Dashboard")
    
    print("\n6.2. Verifique o dashboard:")
    print("   - Deve mostrar cards kanban para journals")
    print("   - Sem erros de JavaScript")
    
    print("\n" + "=" * 70)
    print("CONFIGURAÇÃO ATUAL DO MÓDULO")
    print("=" * 70)
    
    print("\n✓ Usando kanban PADRÃO do Odoo (sem js_class customizado)")
    print("✓ JavaScript customizado DESABILITADO")
    print("✓ Apenas CSS para estilização")
    print("✓ Action renomeada para 'action_mz_dashboard_simple'")
    print("✓ Menus renomeados para evitar conflitos")
    
    print("\n" + "=" * 70)
    print("SE AINDA HOUVER PROBLEMAS")
    print("=" * 70)
    
    print("\n1. Verifique os logs:")
    print("   sudo tail -f /var/log/odoo/odoo.log")
    
    print("\n2. Tente modo de debug:")
    print("   sudo -u odoo /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf \\")
    print("     -d SEU_DATABASE --dev=all --log-level=debug")
    
    print("\n3. Verifique dependências:")
    print("   - Módulo 'account' deve estar instalado")
    print("   - Usuário deve ter permissões de contabilidade")
    
    print("\n" + "=" * 70)
    print("IMPORTANTE")
    print("=" * 70)
    
    print("\n⚠️ SEMPRE use modo incógnito ou limpe o cache do navegador!")
    print("⚠️ O erro persiste em cache mesmo após correções!")
    print("⚠️ A desinstalação e reinstalação COMPLETA é necessária!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())