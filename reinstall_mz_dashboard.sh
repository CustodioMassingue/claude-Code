#!/bin/bash
# Script to reinstall/upgrade MZ Accounting Dashboard module

echo "=========================================="
echo "MZ Accounting Dashboard - Reinstall Script"
echo "=========================================="

# Configuration
ODOO_URL="http://localhost:8069"
DB_NAME="odoo18"
ADMIN_USER="admin"
ADMIN_PASS="admin"
MODULE_NAME="mz_accounting_dashboard"

echo ""
echo "Configuration:"
echo "  Odoo URL: $ODOO_URL"
echo "  Database: $DB_NAME"
echo "  Module: $MODULE_NAME"
echo ""

# Using Python to interact with Odoo XML-RPC
python3 << EOF
import xmlrpc.client
import time

url = '$ODOO_URL'
db = '$DB_NAME'
username = '$ADMIN_USER'
password = '$ADMIN_PASS'
module_name = '$MODULE_NAME'

print("Connecting to Odoo...")
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

if not uid:
    print("❌ Failed to authenticate")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
print("✅ Connected successfully")

# Search for the module
print(f"\\nSearching for module '{module_name}'...")
module_ids = models.execute_kw(
    db, uid, password,
    'ir.module.module', 'search',
    [[['name', '=', module_name]]]
)

if not module_ids:
    print(f"❌ Module '{module_name}' not found")
    print("\\nPlease ensure the module is in the addons path")
    exit(1)

# Get module state
module = models.execute_kw(
    db, uid, password,
    'ir.module.module', 'read',
    [module_ids, ['state', 'name']]
)[0]

print(f"✅ Module found: {module['name']} (State: {module['state']})")

# Uninstall if installed
if module['state'] == 'installed':
    print("\\nUninstalling module...")
    try:
        models.execute_kw(
            db, uid, password,
            'ir.module.module', 'button_immediate_uninstall',
            [module_ids]
        )
        print("✅ Module uninstalled")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️  Could not uninstall: {e}")
        print("Trying upgrade instead...")
        models.execute_kw(
            db, uid, password,
            'ir.module.module', 'button_immediate_upgrade',
            [module_ids]
        )
        print("✅ Module upgraded")
        exit(0)

# Install the module
print("\\nInstalling module...")
models.execute_kw(
    db, uid, password,
    'ir.module.module', 'button_immediate_install',
    [module_ids]
)
print("✅ Module installed successfully")

print("\\n" + "="*40)
print("INSTALLATION COMPLETE")
print("="*40)
print("\\nNext steps:")
print("1. Refresh your browser (F5)")
print("2. Clear browser cache if needed")
print("3. Look for 'MZ Accounting' in the main menu")
EOF

echo ""
echo "=========================================="
echo "Script completed!"
echo "==========================================="