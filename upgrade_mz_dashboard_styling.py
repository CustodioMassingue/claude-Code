#!/usr/bin/env python3
"""
Upgrade MZ Accounting Dashboard Module with Professional Styling
This script upgrades the module to apply the new professional styling
"""

import xmlrpc.client
import sys

# Odoo server configuration
URL = 'http://localhost:8069'
DB = 'postgres'  # Changed from 'odoo' to 'postgres'
USERNAME = 'admin'
PASSWORD = 'admin'

def upgrade_module():
    """Upgrade the MZ Accounting Dashboard module"""
    
    try:
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        
        if not uid:
            print("Authentication failed. Please check your credentials.")
            return False
        
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        print("Connected to Odoo successfully")
        
        # Find the module
        module_ids = models.execute_kw(DB, uid, PASSWORD,
            'ir.module.module', 'search',
            [[['name', '=', 'mz_accounting_dashboard']]])
        
        if not module_ids:
            print("Module 'mz_accounting_dashboard' not found!")
            return False
        
        module_id = module_ids[0]
        
        # Check module state
        module_data = models.execute_kw(DB, uid, PASSWORD,
            'ir.module.module', 'read',
            [module_id, ['state', 'name']])
        
        print(f"Module found: {module_data['name']} (State: {module_data['state']})")
        
        # Upgrade the module
        print("Upgrading module...")
        models.execute_kw(DB, uid, PASSWORD,
            'ir.module.module', 'button_immediate_upgrade',
            [[module_id]])
        
        print("Module upgraded successfully!")
        
        # Ensure journals are configured for dashboard
        print("Configuring journals for dashboard...")
        
        # Get all journals
        journal_ids = models.execute_kw(DB, uid, PASSWORD,
            'account.journal', 'search',
            [[]])
        
        if journal_ids:
            # Update all journals to show on dashboard
            models.execute_kw(DB, uid, PASSWORD,
                'account.journal', 'write',
                [journal_ids, {'show_on_dashboard': True}])
            
            print(f"Updated {len(journal_ids)} journals to show on dashboard")
        
        # Call the ensure_dashboard_journals method
        try:
            models.execute_kw(DB, uid, PASSWORD,
                'account.journal', 'ensure_dashboard_journals',
                [])
            print("Dashboard journals configured successfully")
        except Exception as e:
            print(f"Note: {e}")
        
        # Clear the browser cache reminder
        print("\n" + "="*60)
        print("IMPORTANT: Professional styling has been applied!")
        print("="*60)
        print("\nTo see the changes:")
        print("1. Clear your browser cache (Ctrl+F5 or Cmd+Shift+R)")
        print("2. Navigate to: MZ Accounting > Dashboard")
        print("3. Or go to: Accounting > MZ Dashboard")
        print("\nThe dashboard should now show:")
        print("- Purple gradient headers for Customer Invoices")
        print("- Blue gradients for Bank journals")
        print("- Green gradients for Cash journals")
        print("- Card shadows and rounded corners")
        print("- Professional stat boxes with gradients")
        print("- Modern buttons with hover effects")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("MZ Accounting Dashboard - Styling Upgrade")
    print("-" * 40)
    
    if upgrade_module():
        print("\n[OK] Upgrade completed successfully!")
        print("\nAccess the dashboard at:")
        print(f"  {URL}/web#action=mz_accounting_dashboard.action_mz_dashboard_simple")
    else:
        print("\n[ERROR] Upgrade failed. Please check the error messages above.")
        sys.exit(1)