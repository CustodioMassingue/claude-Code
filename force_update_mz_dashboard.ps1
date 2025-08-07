# PowerShell Script para forçar atualização do módulo MZ Accounting Dashboard
# Execute este script com PowerShell como Administrador se necessário

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ATUALIZAÇÃO FORÇADA DO MÓDULO MZ DASHBOARD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Configurações
$moduleName = "mz_accounting_dashboard"
$database = "teste"

Write-Host "`n[1] Verificando se Docker está rodando..." -ForegroundColor Yellow
$dockerStatus = docker ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Docker não está rodando! Inicie o Docker Desktop primeiro." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit
}

Write-Host "[OK] Docker está rodando" -ForegroundColor Green

Write-Host "`n[2] Limpando cache e arquivos compilados..." -ForegroundColor Yellow
docker-compose exec -T web bash -c "rm -rf /var/lib/odoo/.local/share/Odoo/filestore/$database/*.cache" 2>$null
docker-compose exec -T web bash -c "find /mnt/extra-addons -name '*.pyc' -delete" 2>$null
docker-compose exec -T web bash -c "find /mnt/extra-addons -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true" 2>$null
docker-compose exec -T web bash -c "rm -rf /var/lib/odoo/.local/share/Odoo/sessions/*" 2>$null
Write-Host "[OK] Cache limpo" -ForegroundColor Green

Write-Host "`n[3] Verificando presença do módulo no container..." -ForegroundColor Yellow
$moduleCheck = docker-compose exec -T web ls /mnt/extra-addons/ubuntu_server/$moduleName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Módulo não encontrado no container!" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit
}
Write-Host "[OK] Módulo encontrado" -ForegroundColor Green

Write-Host "`n[4] Parando container Odoo..." -ForegroundColor Yellow
docker-compose stop web
Start-Sleep -Seconds 2
Write-Host "[OK] Container parado" -ForegroundColor Green

Write-Host "`n[5] Atualizando módulo com --update flag..." -ForegroundColor Yellow
docker-compose run --rm web odoo `
    --database=$database `
    --update=$moduleName `
    --stop-after-init `
    --log-level=info `
    --no-http

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Módulo atualizado com sucesso" -ForegroundColor Green
} else {
    Write-Host "[AVISO] Possível erro na atualização, continuando..." -ForegroundColor Yellow
}

Write-Host "`n[6] Iniciando container normalmente..." -ForegroundColor Yellow
docker-compose start web
Write-Host "Aguardando 10 segundos para o Odoo iniciar..." -ForegroundColor Cyan
Start-Sleep -Seconds 10
Write-Host "[OK] Container iniciado" -ForegroundColor Green

Write-Host "`n[7] Executando script Python para ativar menus..." -ForegroundColor Yellow

$pythonScript = @'
import xmlrpc.client
import sys

# Configurações de conexão
url = "http://localhost:8069"
db = "teste"
username = "admin"
password = "admin"

try:
    # Conectar ao Odoo
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("ERRO: Não foi possível autenticar. Verifique as credenciais.")
        sys.exit(1)
        
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    print("Conectado ao Odoo com sucesso!")
    
    # Buscar o módulo
    module_ids = models.execute_kw(db, uid, password,
        "ir.module.module", "search",
        [[["name", "=", "mz_accounting_dashboard"]]])
    
    if module_ids:
        module = models.execute_kw(db, uid, password,
            "ir.module.module", "read",
            [module_ids[0], ["state", "latest_version"]])
        print(f"Módulo encontrado - Estado: {module['state']}")
        
        # Forçar upgrade se instalado
        if module["state"] == "installed":
            print("Forçando upgrade do módulo...")
            try:
                models.execute_kw(db, uid, password,
                    "ir.module.module", "button_immediate_upgrade", [[module_ids[0]]])
                print("Upgrade executado!")
            except:
                print("Módulo já está atualizado")
        elif module["state"] == "to install":
            print("Instalando módulo...")
            models.execute_kw(db, uid, password,
                "ir.module.module", "button_immediate_install", [[module_ids[0]]])
        
        # Buscar e ativar todos os menus do módulo
        print("\nVerificando menus do módulo...")
        menu_ids = models.execute_kw(db, uid, password,
            "ir.ui.menu", "search",
            [["&", "|", 
              ["name", "ilike", "MZ Accounting"],
              ["id", "in", [
                  "mz_accounting_dashboard.menu_mz_accounting_root",
                  "mz_accounting_dashboard.menu_mz_dashboard_main",
                  "mz_accounting_dashboard.menu_mz_customers",
                  "mz_accounting_dashboard.menu_mz_vendors",
                  "mz_accounting_dashboard.menu_mz_accounting",
                  "mz_accounting_dashboard.menu_mz_banks_cash",
                  "mz_accounting_dashboard.menu_mz_reporting",
                  "mz_accounting_dashboard.menu_mz_configuration"
              ]],
              ["active", "in", [True, False]]
            ]])
        
        if menu_ids:
            print(f"Encontrados {len(menu_ids)} menus")
            
            # Ativar todos os menus
            for menu_id in menu_ids:
                models.execute_kw(db, uid, password,
                    "ir.ui.menu", "write",
                    [[menu_id], {"active": True, "sequence": 10}])
            
            print(f"Todos os {len(menu_ids)} menus foram ativados!")
        else:
            print("AVISO: Nenhum menu encontrado. Eles serão criados na próxima atualização.")
        
        # Limpar todos os caches
        print("\nLimpando caches...")
        try:
            models.execute_kw(db, uid, password, "ir.ui.menu", "clear_caches", [])
            models.execute_kw(db, uid, password, "ir.model.access", "clear_caches", [])
        except:
            pass
        
        print("\n✅ Processo concluído com sucesso!")
        print("Os menus devem estar visíveis agora.")
        
    else:
        print("ERRO: Módulo mz_accounting_dashboard não encontrado!")
        sys.exit(1)
        
except Exception as e:
    print(f"ERRO: {e}")
    sys.exit(1)
'@

# Salvar e executar script Python
$pythonScript | Out-File -FilePath "temp_activate_menus.py" -Encoding UTF8
python temp_activate_menus.py
Remove-Item "temp_activate_menus.py" -ErrorAction SilentlyContinue

Write-Host "`n[8] Verificando logs recentes..." -ForegroundColor Yellow
docker-compose logs --tail=20 web | Select-String -Pattern "mz_accounting" -Context 2,2

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✅ PROCESSO CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n📌 INSTRUÇÕES FINAIS:" -ForegroundColor Cyan
Write-Host "1. Abra o navegador em: http://localhost:8069" -ForegroundColor White
Write-Host "2. Faça login com: admin / admin" -ForegroundColor White
Write-Host "3. Pressione Ctrl+F5 para limpar o cache do navegador" -ForegroundColor White
Write-Host "4. O menu 'MZ Accounting' deve aparecer na barra superior" -ForegroundColor White

Write-Host "`n💡 VERIFICAÇÃO ADICIONAL:" -ForegroundColor Yellow
Write-Host "Se o menu ainda não aparecer:" -ForegroundColor White
Write-Host "1. Vá em: Configurações > Técnico > Menu Items" -ForegroundColor White
Write-Host "2. Procure por: 'MZ Accounting'" -ForegroundColor White
Write-Host "3. Verifique se está marcado como 'Ativo'" -ForegroundColor White
Write-Host "4. Se necessário, marque 'Ativo' e salve" -ForegroundColor White

Write-Host "`n"
Read-Host "Pressione Enter para sair"