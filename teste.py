import xmlrpc.client

URL = "http://localhost:8069"
DB = "teste"
USER = "teste"
PWD = "123"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PWD, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

# 1) Todos os xmlids do módulo 'account' que apontam para menus
imd_ids = models.execute_kw(DB, uid, PWD, 'ir.model.data', 'search', [[
    ('model', '=', 'ir.ui.menu'),
    ('module', '=', 'account'),
]])
imd = models.execute_kw(DB, uid, PWD, 'ir.model.data', 'read', [imd_ids], {'fields': ['id','module','name','res_id']})

# 2) Ler os menus correspondentes
menu_map = {}
if imd:
    menu_ids = [r['res_id'] for r in imd]
    menus = models.execute_kw(DB, uid, PWD, 'ir.ui.menu', 'read', [menu_ids], {'fields': ['id','name','complete_name','parent_id']})
    menu_map = {m['id']: m for m in menus}

# 3) Mostrar apenas menus de TOPO (sem parent) do módulo 'account'
print("Top-level menus do módulo 'account':")
candidates = []
for r in imd:
    m = menu_map.get(r['res_id'])
    if not m:
        continue
    parent = m['parent_id']
    if not parent:  # top-level
        xmlid = f"{r['module']}.{r['name']}"
        candidates.append((xmlid, m['id'], m['name'], m.get('complete_name')))
        print(f"- XMLID: {xmlid} | id: {m['id']} | name: {m['name']} | complete_name: {m.get('complete_name')}")

# 4) (Opcional) testar alguns candidatos conhecidos
known = ['account.menu_finance', 'account.menu_finance_root', 'account.menu_finance_accounting']
print("\nExistem estes XMLIDs conhecidos?")
for k in known:
    exists = models.execute_kw(DB, uid, PWD, 'ir.model.data', 'search_count', [[('model','=','ir.ui.menu'), ('module','=', k.split('.')[0]), ('name','=', k.split('.')[1])]])
    print(f"- {k}: {'SIM' if exists else 'não encontrado'}")
