#!/usr/bin/env python3
"""
Script to test and validate MZ Accounting Dashboard module menus in Odoo 18.
"""

import xmlrpc.client
import sys
from datetime import datetime

# Odoo connection parameters
url = 'http://localhost:8069'
db = 'teste'
username = 'admin'
password = 'admin'

def connect_odoo():
    """Establish connection to Odoo."""
    try:
        # Authentication
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Failed to authenticate with Odoo")
            return None, None
        
        # Get the object proxy
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print(f"✅ Connected to Odoo at {url}")
        print(f"   Database: {db}")
        print(f"   User ID: {uid}")
        
        return uid, models
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, None

def check_module_status(uid, models):
    """Check if the module is installed and its status."""
    try:
        # Search for the module
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', 'mz_accounting_dashboard']]]
        )
        
        if not module_ids:
            print("❌ Module 'mz_accounting_dashboard' not found")
            return False
        
        # Get module details
        module = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'read',
            [module_ids, ['state', 'installed_version', 'latest_version']]
        )[0]
        
        print(f"\n📦 Module Status:")
        print(f"   State: {module['state']}")
        print(f"   Installed Version: {module.get('installed_version', 'N/A')}")
        print(f"   Latest Version: {module.get('latest_version', 'N/A')}")
        
        if module['state'] != 'installed':
            print("⚠️  Module is not installed. Installing now...")
            # Install the module
            models.execute_kw(
                db, uid, password,
                'ir.module.module', 'button_immediate_install',
                [module_ids]
            )
            print("✅ Module installation initiated")
            return True
        else:
            print("✅ Module is installed")
            return True
            
    except Exception as e:
        print(f"❌ Error checking module status: {e}")
        return False

def upgrade_module(uid, models):
    """Force upgrade the module to apply changes."""
    try:
        # Search for the module
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', 'mz_accounting_dashboard']]]
        )
        
        if module_ids:
            # Upgrade the module
            models.execute_kw(
                db, uid, password,
                'ir.module.module', 'button_immediate_upgrade',
                [module_ids]
            )
            print("✅ Module upgrade initiated")
            return True
        else:
            print("❌ Module not found for upgrade")
            return False
            
    except Exception as e:
        print(f"❌ Error upgrading module: {e}")
        return False

def check_menus(uid, models):
    """Check if menus are created and accessible."""
    try:
        print("\n🔍 Checking Menus:")
        
        # List of menu IDs to check
        menu_xmlids = [
            'mz_accounting_dashboard.menu_mz_accounting_root',
            'mz_accounting_dashboard.menu_mz_dashboard_main',
            'mz_accounting_dashboard.menu_mz_customers',
            'mz_accounting_dashboard.menu_mz_vendors',
            'mz_accounting_dashboard.menu_mz_accounting',
            'mz_accounting_dashboard.menu_mz_banks_cash',
            'mz_accounting_dashboard.menu_mz_reporting',
            'mz_accounting_dashboard.menu_mz_configuration',
        ]
        
        found_menus = []
        missing_menus = []
        
        for xmlid in menu_xmlids:
            try:
                # Get menu by XML ID
                menu_id = models.execute_kw(
                    db, uid, password,
                    'ir.model.data', 'xmlid_to_res_id',
                    [xmlid]
                )
                
                if menu_id:
                    # Get menu details
                    menu = models.execute_kw(
                        db, uid, password,
                        'ir.ui.menu', 'read',
                        [[menu_id], ['name', 'parent_id', 'action', 'sequence', 'groups_id']]
                    )[0]
                    
                    found_menus.append(xmlid)
                    print(f"   ✅ {xmlid.split('.')[-1]}: {menu['name']}")
                    print(f"      Parent: {menu.get('parent_id', 'Root')}")
                    print(f"      Sequence: {menu.get('sequence', 'N/A')}")
                    
                    # Check if menu has groups
                    if menu.get('groups_id'):
                        groups = models.execute_kw(
                            db, uid, password,
                            'res.groups', 'read',
                            [menu['groups_id'], ['name']]
                        )
                        group_names = [g['name'] for g in groups]
                        print(f"      Groups: {', '.join(group_names)}")
                else:
                    missing_menus.append(xmlid)
                    print(f"   ❌ {xmlid.split('.')[-1]}: Not found")
                    
            except Exception as e:
                missing_menus.append(xmlid)
                print(f"   ❌ {xmlid.split('.')[-1]}: Error - {e}")
        
        print(f"\n📊 Menu Summary:")
        print(f"   Found: {len(found_menus)}/{len(menu_xmlids)}")
        print(f"   Missing: {len(missing_menus)}/{len(menu_xmlids)}")
        
        return len(found_menus) > 0
        
    except Exception as e:
        print(f"❌ Error checking menus: {e}")
        return False

def check_actions(uid, models):
    """Check if actions are created."""
    try:
        print("\n🎯 Checking Actions:")
        
        # List of action IDs to check
        action_xmlids = [
            'mz_accounting_dashboard.action_mz_dashboard_professional',
            'mz_accounting_dashboard.action_mz_customer_invoices',
            'mz_accounting_dashboard.action_mz_vendor_bills',
            'mz_accounting_dashboard.action_mz_journal_entries',
            'mz_accounting_dashboard.action_mz_chart_of_accounts',
        ]
        
        found_actions = []
        
        for xmlid in action_xmlids:
            try:
                # Get action by XML ID
                action_id = models.execute_kw(
                    db, uid, password,
                    'ir.model.data', 'xmlid_to_res_id',
                    [xmlid]
                )
                
                if action_id:
                    # Get action details
                    action = models.execute_kw(
                        db, uid, password,
                        'ir.actions.act_window', 'read',
                        [[action_id], ['name', 'res_model', 'view_mode', 'domain']]
                    )[0]
                    
                    found_actions.append(xmlid)
                    print(f"   ✅ {xmlid.split('.')[-1]}: {action['name']}")
                    print(f"      Model: {action.get('res_model', 'N/A')}")
                    print(f"      Views: {action.get('view_mode', 'N/A')}")
                else:
                    print(f"   ❌ {xmlid.split('.')[-1]}: Not found")
                    
            except Exception as e:
                print(f"   ❌ {xmlid.split('.')[-1]}: Error - {e}")
        
        print(f"\n📊 Action Summary:")
        print(f"   Found: {len(found_actions)}/{len(action_xmlids)}")
        
        return len(found_actions) > 0
        
    except Exception as e:
        print(f"❌ Error checking actions: {e}")
        return False

def check_user_access(uid, models):
    """Check if current user has access to the menus."""
    try:
        print("\n👤 Checking User Access:")
        
        # Get current user groups
        user = models.execute_kw(
            db, uid, password,
            'res.users', 'read',
            [[uid], ['name', 'groups_id']]
        )[0]
        
        print(f"   User: {user['name']}")
        
        # Get user groups
        if user.get('groups_id'):
            groups = models.execute_kw(
                db, uid, password,
                'res.groups', 'read',
                [user['groups_id'], ['name', 'full_name']]
            )
            
            print("   Groups:")
            for group in groups:
                print(f"      - {group['full_name'] or group['name']}")
            
            # Check if user has base.group_user
            group_names = [g['name'] for g in groups]
            if 'Internal User' in group_names or 'Employee' in group_names:
                print("   ✅ User has access to internal menus")
                return True
            else:
                print("   ⚠️  User may not have access to all menus")
                return False
        else:
            print("   ❌ No groups found for user")
            return False
            
    except Exception as e:
        print(f"❌ Error checking user access: {e}")
        return False

def main():
    """Main function to run all tests."""
    print("=" * 60)
    print("MZ Accounting Dashboard Menu Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to Odoo
    uid, models = connect_odoo()
    if not uid:
        sys.exit(1)
    
    # Check module status
    if not check_module_status(uid, models):
        print("\n⚠️  Module issues detected. Attempting to fix...")
        upgrade_module(uid, models)
    
    # Check menus
    menus_ok = check_menus(uid, models)
    
    # Check actions
    actions_ok = check_actions(uid, models)
    
    # Check user access
    access_ok = check_user_access(uid, models)
    
    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if menus_ok and actions_ok and access_ok:
        print("✅ All checks passed! Menus should be visible in Odoo.")
        print("\n📝 Next steps:")
        print("1. Refresh your browser (F5 or Ctrl+F5)")
        print("2. Clear browser cache if needed")
        print("3. Log out and log back in to Odoo")
        print("4. Look for 'MZ Accounting' in the main menu")
    else:
        print("⚠️  Some issues detected. Please review the output above.")
        print("\n📝 Troubleshooting steps:")
        print("1. Run: python3 test_mz_dashboard_menus.py")
        print("2. Upgrade the module in Odoo Apps")
        print("3. Check Odoo logs for errors")
        print("4. Ensure you're logged in as admin")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()