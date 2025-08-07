#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Deploy Automático do Módulo Mozambique Accounting para Servidor Odoo
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Configuração
MODULE_NAME = "mozambique_accounting"
LOCAL_MODULE_PATH = f"custom-addons/ubuntu_server/{MODULE_NAME}"
REMOTE_MODULE_PATH = f"/opt/odoo/custom-addons/{MODULE_NAME}"

def run_command(cmd, description=""):
    """Executa um comando e mostra o resultado"""
    if description:
        print(f"\n[INFO] {description}")
    print(f"[CMD] {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"[OK] Comando executado com sucesso")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"[ERRO] Falha ao executar comando")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True

def create_deployment_package():
    """Cria um pacote ZIP para deploy"""
    print("\n[INFO] Criando pacote de deployment...")
    
    # Limpar cache antes de criar o pacote
    os.system("python clean_and_fix_mozambique_module.py")
    
    # Criar ZIP
    zip_name = f"{MODULE_NAME}.zip"
    shutil.make_archive(MODULE_NAME, 'zip', LOCAL_MODULE_PATH)
    print(f"[OK] Pacote criado: {zip_name}")
    
    return zip_name

def deploy_to_server(server_ip, username="odoo"):
    """Deploy do módulo para o servidor"""
    
    print("=" * 60)
    print("DEPLOY DO MÓDULO MOZAMBIQUE ACCOUNTING")
    print("=" * 60)
    
    # 1. Criar pacote
    zip_file = create_deployment_package()
    
    # 2. Copiar para servidor
    print(f"\n[INFO] Copiando módulo para servidor {server_ip}...")
    scp_cmd = f"scp {zip_file} {username}@{server_ip}:/tmp/"
    
    if not run_command(scp_cmd, "Transferindo arquivo"):
        print("[ERRO] Falha ao copiar arquivo para servidor")
        return False
    
    # 3. Script de instalação remota
    install_script = f'''
#!/bin/bash
set -e

echo "[INFO] Instalando módulo no servidor..."

# Backup do módulo existente se houver
if [ -d "{REMOTE_MODULE_PATH}" ]; then
    echo "[INFO] Fazendo backup do módulo existente..."
    sudo mv {REMOTE_MODULE_PATH} {REMOTE_MODULE_PATH}.bak.$(date +%Y%m%d_%H%M%S)
fi

# Extrair novo módulo
echo "[INFO] Extraindo módulo..."
sudo unzip -o /tmp/{MODULE_NAME}.zip -d /opt/odoo/custom-addons/
sudo chown -R odoo:odoo {REMOTE_MODULE_PATH}
sudo chmod -R 755 {REMOTE_MODULE_PATH}

# Limpar cache Odoo
echo "[INFO] Limpando cache do Odoo..."
sudo rm -rf /var/lib/odoo/.local/share/Odoo/filestore/*/web/assets/*

# Reiniciar Odoo
echo "[INFO] Reiniciando serviço Odoo..."
sudo systemctl restart odoo

# Aguardar Odoo iniciar
echo "[INFO] Aguardando Odoo iniciar..."
sleep 10

# Verificar status
if sudo systemctl is-active --quiet odoo; then
    echo "[OK] Odoo reiniciado com sucesso!"
else
    echo "[ERRO] Falha ao reiniciar Odoo. Verificar logs:"
    echo "sudo journalctl -u odoo -n 50"
    exit 1
fi

# Limpar arquivo temporário
rm /tmp/{MODULE_NAME}.zip

echo "[SUCESSO] Módulo instalado com sucesso!"
echo ""
echo "Próximos passos:"
echo "1. Acesse o Odoo: http://{server_ip}:8069"
echo "2. Ative o modo desenvolvedor (Settings > Developer Tools)"
echo "3. Vá para Apps > Update Apps List"
echo "4. Procure 'Mozambique Accounting'"
echo "5. Clique em Install"
'''
    
    # 4. Executar script de instalação
    ssh_cmd = f"ssh {username}@{server_ip} 'bash -s' << 'EOF'\n{install_script}\nEOF"
    
    if not run_command(ssh_cmd, "Executando instalação remota"):
        print("[ERRO] Falha na instalação remota")
        return False
    
    # 5. Limpar arquivo local
    os.remove(zip_file)
    
    print("\n" + "=" * 60)
    print("[SUCESSO] DEPLOY CONCLUÍDO!")
    print("=" * 60)
    
    return True

def main():
    """Função principal"""
    
    if len(sys.argv) < 2:
        print("Uso: python deploy_to_odoo_server.py <IP_DO_SERVIDOR> [username]")
        print("Exemplo: python deploy_to_odoo_server.py 192.168.1.100")
        print("Exemplo: python deploy_to_odoo_server.py 192.168.1.100 ubuntu")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "odoo"
    
    # Verificar se o módulo existe localmente
    if not os.path.exists(LOCAL_MODULE_PATH):
        print(f"[ERRO] Módulo não encontrado em: {LOCAL_MODULE_PATH}")
        sys.exit(1)
    
    # Executar deploy
    if deploy_to_server(server_ip, username):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()