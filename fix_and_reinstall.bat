@echo off
echo ============================================================
echo CORRIGINDO E REINSTALANDO MZ ACCOUNTING DASHBOARD
echo ============================================================

echo.
echo [1] Copiando modulo para pasta de addons...
if not exist "C:\mnt\extra-addons" mkdir "C:\mnt\extra-addons"
xcopy /E /I /Y "C:\Users\custodio.massingue\Documents\GitHub\claude-Code\custom-addons\ubuntu_server\mz_accounting_dashboard" "C:\mnt\extra-addons\mz_accounting_dashboard"

echo.
echo [2] Modulo copiado com sucesso!
echo.
echo ============================================================
echo PROXIMOS PASSOS:
echo ============================================================
echo.
echo 1. REINICIE O SERVICO ODOO:
echo    - Abra o PowerShell como Administrador
echo    - Execute: Restart-Service odoo-server-18.0
echo    - Ou reinicie pelo Gerenciador de Servicos (services.msc)
echo.
echo 2. LIMPE O CACHE DO NAVEGADOR:
echo    - Pressione Ctrl+Shift+F5
echo    - Ou abra em modo incognito
echo.
echo 3. ATUALIZE/INSTALE O MODULO:
echo    - Acesse: http://localhost:8069
echo    - Va em: Apps
echo    - Clique: Update Apps List
echo    - Procure: MZ Accounting Dashboard
echo    - Se ja instalado: Clique nos 3 pontos e selecione Upgrade
echo    - Se nao instalado: Clique em Install
echo.
echo 4. ACESSE O DASHBOARD:
echo    - Menu: Accounting (deve funcionar sem erros agora)
echo    - Ou: MZ Accounting -^> Dashboard
echo.
echo ============================================================
echo CORRECOES APLICADAS:
echo ============================================================
echo - Removido js_class="account_dashboard" que causava o erro
echo - Corrigido widget para "mz_dashboard_graph"
echo - Modulo pronto para uso sem erros JavaScript
echo ============================================================
echo.
pause