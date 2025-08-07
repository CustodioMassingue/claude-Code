-- Script SQL para limpar completamente referências ao módulo MZ Dashboard
-- Execute com cuidado no banco de dados Odoo

-- 1. Remover actions antigas
DELETE FROM ir_actions WHERE name LIKE '%MZ%Dashboard%' OR name LIKE '%Account%Dashboard%';
DELETE FROM ir_act_window WHERE name LIKE '%MZ%Dashboard%' OR name LIKE '%Account%Dashboard%';

-- 2. Remover views antigas  
DELETE FROM ir_ui_view WHERE name LIKE '%account.journal.dashboard%' OR name LIKE '%mz%dashboard%';

-- 3. Remover menuitems antigos
DELETE FROM ir_ui_menu WHERE name LIKE '%MZ%' OR name LIKE '%Dashboard%' AND name NOT IN (SELECT name FROM ir_ui_menu WHERE module = 'account');

-- 4. Limpar cache de assets
DELETE FROM ir_attachment WHERE name LIKE '%mz_account%' OR url LIKE '%mz_account%';

-- 5. Remover registros de modelos
DELETE FROM ir_model_data WHERE module = 'mz_accounting_dashboard';

-- 6. Verificar o que sobrou
SELECT 'Actions:', COUNT(*) FROM ir_act_window WHERE name LIKE '%Dashboard%';
SELECT 'Views:', COUNT(*) FROM ir_ui_view WHERE name LIKE '%dashboard%';
SELECT 'Menus:', COUNT(*) FROM ir_ui_menu WHERE name LIKE '%Dashboard%';
SELECT 'Model Data:', COUNT(*) FROM ir_model_data WHERE module = 'mz_accounting_dashboard';

-- NOTA: Após executar este script, você precisará:
-- 1. Reiniciar o Odoo
-- 2. Reinstalar o módulo do zero