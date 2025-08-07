# DIAGNÓSTICO - MZ ACCOUNTING DASHBOARD NÃO APARECE

## PROBLEMA
O módulo MZ Accounting Dashboard não está visível na lista de Apps do Odoo.

## POSSÍVEIS CAUSAS E SOLUÇÕES

### 1. MÓDULO NÃO ESTÁ NO CAMINHO CORRETO

**Verificar onde o Odoo procura por módulos:**
1. Acesse o Odoo
2. Ative o modo desenvolvedor: Settings → Developer Tools → Activate Developer Mode
3. Vá em: Settings → Technical → System Parameters
4. Procure por: `addons_path`

**O módulo deve estar em um destes locais:**
- `/mnt/extra-addons/mz_accounting_dashboard`
- `C:\mnt\extra-addons\mz_accounting_dashboard`
- Ou no caminho configurado no seu `odoo.conf`

### 2. COPIAR O MÓDULO PARA O LOCAL CORRETO

**No Windows (PowerShell como Admin):**
```powershell
# Crie a pasta extra-addons se não existir
New-Item -ItemType Directory -Force -Path "C:\mnt\extra-addons"

# Copie o módulo
Copy-Item -Path "C:\Users\custodio.massingue\Documents\GitHub\claude-Code\custom-addons\ubuntu_server\mz_accounting_dashboard" -Destination "C:\mnt\extra-addons\" -Recurse -Force
```

**No Linux/Ubuntu:**
```bash
# Crie a pasta se não existir
sudo mkdir -p /mnt/extra-addons

# Copie o módulo
sudo cp -r /path/to/custom-addons/ubuntu_server/mz_accounting_dashboard /mnt/extra-addons/

# Ajuste permissões
sudo chown -R odoo:odoo /mnt/extra-addons/mz_accounting_dashboard
sudo chmod -R 755 /mnt/extra-addons/mz_accounting_dashboard
```

### 3. CONFIGURAR O ODOO.CONF

Localize e edite o arquivo `odoo.conf`:

**Windows:** 
- `C:\Program Files\Odoo 18.0\server\odoo.conf`
- ou `%PROGRAMDATA%\Odoo\odoo.conf`

**Linux:**
- `/etc/odoo/odoo.conf`
- ou `/opt/odoo/odoo.conf`

**Adicione ou edite a linha addons_path:**
```ini
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

### 4. REINICIAR O ODOO

**Windows (PowerShell como Admin):**
```powershell
Restart-Service odoo-server-18.0
```

**Linux:**
```bash
sudo systemctl restart odoo
# ou
sudo service odoo restart
```

### 5. ATUALIZAR LISTA DE APPS

1. Acesse o Odoo: http://localhost:8069
2. Vá em: **Apps**
3. Clique: **Update Apps List**
4. Procure: **MZ Accounting Dashboard**

### 6. SE AINDA NÃO APARECER

**Verifique logs de erro:**

**Windows:**
```powershell
Get-Content "C:\Program Files\Odoo 18.0\server\odoo.log" -Tail 50
```

**Linux:**
```bash
sudo tail -f /var/log/odoo/odoo.log
```

**Procure por erros como:**
- "Unable to load module mz_accounting_dashboard"
- "Module not found"
- Erros de Python no __manifest__.py

### 7. MODO DESENVOLVEDOR E DEBUG

1. Ative o modo desenvolvedor
2. Vá em: Settings → Technical → Database Structure → Modules
3. Clique em "Update Apps List"
4. Procure por "mz_accounting"

### 8. VERIFICAR ESTRUTURA DO MÓDULO

O módulo DEVE ter esta estrutura:
```
mz_accounting_dashboard/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── account_journal_dashboard.py
├── views/
│   ├── account_dashboard_views.xml
│   ├── account_journal_dashboard_view.xml
│   └── menuitems.xml
├── security/
│   └── ir.model.access.csv
├── static/
│   └── src/
│       ├── js/
│       ├── scss/
│       └── xml/
└── data/
    └── default_journals.xml
```

### 9. COMANDO DIRETO PARA FORÇAR INSTALAÇÃO

**Se você tem acesso SSH/Terminal ao servidor:**
```bash
# Força a instalação do módulo
python3 odoo-bin -d seu_banco -i mz_accounting_dashboard --stop-after-init

# Ou com caminho específico
python3 odoo-bin -d seu_banco -i mz_accounting_dashboard --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --stop-after-init
```

### 10. ÚLTIMO RECURSO - INSTALAÇÃO MANUAL

1. Comprima o módulo em ZIP
2. No Odoo, vá em: Apps
3. Clique em: Import Module (pode precisar do modo desenvolvedor)
4. Faça upload do ZIP
5. Instale

## CHECKLIST DE VERIFICAÇÃO

- [ ] Módulo está no caminho correto (/mnt/extra-addons)
- [ ] odoo.conf tem o addons_path configurado
- [ ] Serviço Odoo foi reiniciado
- [ ] Update Apps List foi executado
- [ ] Modo desenvolvedor está ativo
- [ ] Não há erros nos logs
- [ ] Estrutura do módulo está correta
- [ ] Permissões de arquivo estão corretas (Linux)

## SOLUÇÃO RÁPIDA

Execute estes comandos em sequência:

```bash
# 1. Copiar módulo (ajuste os caminhos)
cp -r /seu/caminho/mz_accounting_dashboard /mnt/extra-addons/

# 2. Reiniciar Odoo
sudo service odoo restart

# 3. Forçar update
curl -X POST http://localhost:8069/web/database/manager \
  -d "master_pwd=admin&name=seu_banco&update=mz_accounting_dashboard"
```

Após seguir estes passos, o módulo deve aparecer na lista de Apps!