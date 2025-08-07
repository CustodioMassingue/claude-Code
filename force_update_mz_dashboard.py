#!/usr/bin/env python3
"""
Script para forçar atualização completa do módulo mz_accounting_dashboard no Odoo via Docker
Executa todas as operações necessárias para garantir que os menus apareçam
"""

import subprocess
import sys
import time
import os

class OdooModuleUpdater:
    def __init__(self):
        self.module_name = "mz_accounting_dashboard"
        self.container_name = "web"  # Nome padrão do container Odoo no docker-compose
        self.database = "teste"
        
    def run_command(self, command, description=""):
        """Executa um comando e mostra o resultado"""
        if description:
            print(f"\n{'='*60}")
            print(f"✅ {description}")
            print(f"{'='*60}")
        
        print(f"Executando: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.stdout:
                print(f"Saída: {result.stdout}")
            if result.stderr:
                print(f"Avisos/Erros: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Erro ao executar comando: {e}")
            return False
    
    def docker_exec(self, command):
        """Executa comando dentro do container Docker"""
        full_command = f'docker-compose exec -T {self.container_name} {command}'
        return self.run_command(full_command)
    
    def update_module(self):
        """Processo completo de atualização do módulo"""
        
        print("\n" + "="*80)
        print("🚀 INICIANDO ATUALIZAÇÃO FORÇADA DO MÓDULO MZ ACCOUNTING DASHBOARD")
        print("="*80)
        
        # 1. Limpar cache do Odoo
        print("\n📦 PASSO 1: Limpando cache do Odoo...")
        self.docker_exec('rm -rf /var/lib/odoo/.local/share/Odoo/filestore/teste/*.cache')
        self.docker_exec('find /mnt/extra-addons -name "*.pyc" -delete')
        self.docker_exec('find /mnt/extra-addons -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true')
        
        # 2. Verificar se o módulo existe no container
        print("\n📂 PASSO 2: Verificando presença do módulo no container...")
        self.docker_exec(f'ls -la /mnt/extra-addons/ubuntu_server/{self.module_name}/')
        
        # 3. Reiniciar o Odoo com modo de atualização
        print("\n🔄 PASSO 3: Reiniciando Odoo com atualização do módulo...")
        print("Parando container...")
        self.run_command('docker-compose stop web')
        time.sleep(2)
        
        print("Iniciando container com comando de atualização...")
        update_command = f'''docker-compose run --rm -e ODOO_RC="/etc/odoo/odoo.conf" web \
            odoo --database={self.database} \
            --update={self.module_name} \
            --stop-after-init \
            --log-level=info'''
        
        success = self.run_command(update_command, "Executando atualização do módulo")
        
        # 4. Iniciar container normalmente
        print("\n🚀 PASSO 4: Iniciando container normalmente...")
        self.run_command('docker-compose start web')
        time.sleep(5)
        
        # 5. Verificar logs
        print("\n📋 PASSO 5: Verificando logs do container...")
        self.run_command('docker-compose logs --tail=50 web | grep -i "mz_accounting"')
        
        # 6. Executar script Python dentro do Odoo para forçar visibilidade dos menus
        print("\n🔧 PASSO 6: Forçando visibilidade dos menus via script Python...")
        python_script = '''
import xmlrpc.client

# Conectar ao Odoo
url = "http://localhost:8069"
db = "teste"
username = "admin"
password = "admin"

# Conectar
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print("Conectado ao Odoo!")

# Buscar o módulo
module_ids = models.execute_kw(db, uid, password,
    "ir.module.module", "search",
    [[["name", "=", "mz_accounting_dashboard"]]])

if module_ids:
    print(f"Módulo encontrado: {module_ids}")
    
    # Verificar estado do módulo
    module = models.execute_kw(db, uid, password,
        "ir.module.module", "read",
        [module_ids, ["state", "latest_version"]])
    print(f"Estado do módulo: {module}")
    
    # Forçar instalação se não estiver instalado
    if module[0]["state"] != "installed":
        print("Instalando módulo...")
        models.execute_kw(db, uid, password,
            "ir.module.module", "button_immediate_install", [module_ids])
    else:
        print("Atualizando módulo...")
        models.execute_kw(db, uid, password,
            "ir.module.module", "button_immediate_upgrade", [module_ids])
    
    # Buscar e ativar menus
    print("\\nVerificando menus...")
    menu_ids = models.execute_kw(db, uid, password,
        "ir.ui.menu", "search",
        [["|", ["name", "ilike", "MZ Accounting"], ["name", "=", "Dashboard"]]])
    
    if menu_ids:
        menus = models.execute_kw(db, uid, password,
            "ir.ui.menu", "read",
            [menu_ids, ["name", "sequence", "parent_id", "action", "active"]])
        
        for menu in menus:
            print(f"Menu encontrado: {menu['name']} (ID: {menu['id']}, Ativo: {menu['active']})")
            
            # Ativar menu se estiver inativo
            if not menu["active"]:
                print(f"Ativando menu {menu['name']}...")
                models.execute_kw(db, uid, password,
                    "ir.ui.menu", "write",
                    [[menu["id"]], {"active": True}])
    
    # Limpar cache
    print("\\nLimpando cache de menus...")
    models.execute_kw(db, uid, password,
        "ir.ui.menu", "clear_caches", [])
    
    print("\\n✅ Processo concluído com sucesso!")
else:
    print("❌ Módulo não encontrado!")
'''
        
        # Salvar script temporário
        script_path = "temp_update_menus.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_script)
        
        # Executar script
        self.run_command(f'python "{script_path}"')
        
        # Remover script temporário
        if os.path.exists(script_path):
            os.remove(script_path)
        
        print("\n" + "="*80)
        print("✅ ATUALIZAÇÃO CONCLUÍDA!")
        print("="*80)
        print("\n📌 PRÓXIMOS PASSOS:")
        print("1. Acesse http://localhost:8069")
        print("2. Faça login como admin/admin")
        print("3. Pressione F5 para atualizar a página")
        print("4. O menu 'MZ Accounting' deve aparecer na barra superior")
        print("\n💡 Se o menu ainda não aparecer:")
        print("   - Vá em Configurações > Técnico > Menu Items")
        print("   - Procure por 'MZ Accounting'")
        print("   - Verifique se está ativo e visível")

def main():
    updater = OdooModuleUpdater()
    
    # Verificar se docker-compose está rodando
    print("Verificando se Docker está rodando...")
    result = subprocess.run("docker ps", shell=True, capture_output=True)
    if result.returncode != 0:
        print("❌ Docker não está rodando! Inicie o Docker Desktop primeiro.")
        sys.exit(1)
    
    # Executar atualização
    updater.update_module()

if __name__ == "__main__":
    main()