@echo off
REM Script para atualizar o módulo mz_accounting_dashboard no Odoo Docker
REM Execute este arquivo como Administrador se necessário

echo ========================================
echo ATUALIZACAO FORCADA DO MODULO MZ DASHBOARD
echo ========================================

echo.
echo [1] Limpando cache do Odoo...
docker-compose exec -T web rm -rf /var/lib/odoo/.local/share/Odoo/filestore/teste/*.cache
docker-compose exec -T web find /mnt/extra-addons -name "*.pyc" -delete
docker-compose exec -T web find /mnt/extra-addons -name "__pycache__" -type d -exec rm -rf {} + 2>nul

echo.
echo [2] Verificando presenca do modulo...
docker-compose exec -T web ls -la /mnt/extra-addons/ubuntu_server/mz_accounting_dashboard/

echo.
echo [3] Parando container Odoo...
docker-compose stop web

echo.
echo [4] Atualizando modulo com --update flag...
docker-compose run --rm web odoo --database=teste --update=mz_accounting_dashboard --stop-after-init --log-level=info

echo.
echo [5] Iniciando container normalmente...
docker-compose start web

echo.
echo [6] Aguardando 10 segundos para o Odoo iniciar...
timeout /t 10 /nobreak

echo.
echo [7] Verificando logs do container...
docker-compose logs --tail=30 web

echo.
echo ========================================
echo PROCESSO CONCLUIDO!
echo ========================================
echo.
echo Acesse http://localhost:8069
echo Login: admin / Senha: admin
echo.
echo O menu 'MZ Accounting' deve aparecer agora!
echo.
echo Se nao aparecer, pressione Ctrl+F5 no navegador
echo.
pause