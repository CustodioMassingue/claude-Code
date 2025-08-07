# MZ Accounting Dashboard - Menu Fix Instructions

## Problem
The menus for MZ Accounting Dashboard are not appearing in Odoo 18.

## Solution Applied

### 1. Fixed Issues in menuitems.xml
- **Removed references to non-existent views** (account.view_account_invoice_filter, etc.)
- **Added proper security groups** (base.group_user instead of account groups)
- **Fixed duplicate IDs** by prefixing all IDs with "mz_"
- **Created simplified menu structure** in menuitems_simple.xml

### 2. Updated __manifest__.py
- Changed menu file reference to use menuitems_simple.xml
- Ensured proper file loading order

### 3. Fixed Security Access
- Updated ir.model.access.csv to use base.group_user and base.group_system

## Installation Steps

### Method 1: Via Odoo Interface
1. Go to Apps menu in Odoo
2. Remove "Apps" filter to see all modules
3. Search for "MZ Accounting Dashboard"
4. Click "Upgrade" or "Install"
5. Refresh browser (Ctrl+F5)

### Method 2: Via Command Line (Recommended)
```bash
# On Windows (PowerShell)
cd C:\Users\custodio.massingue\Documents\GitHub\claude-Code
python test_mz_dashboard_menus.py

# On Linux/Mac
cd /path/to/claude-Code
python3 test_mz_dashboard_menus.py
```

### Method 3: Force Reinstall
```bash
# Run the reinstall script
sh reinstall_mz_dashboard.sh
```

### Method 4: Manual Database Update
1. Stop Odoo server
2. Run Odoo with update flag:
```bash
python odoo-bin -c odoo.conf -d odoo18 -u mz_accounting_dashboard
```
3. Restart Odoo normally

## Verification

After installation, you should see:
1. **Main Menu**: "MZ Accounting" with icon in the app menu
2. **Submenus**:
   - Dashboard
   - Customers (Invoices, Credit Notes, Payments)
   - Vendors (Bills, Refunds, Payments)
   - Accounting (Journal Entries, Journal Items, Chart of Accounts)
   - Banks and Cash (Bank Statements, Cash Registers)
   - Reporting (Partner Ledger, General Ledger, Aged Reports)
   - Configuration (for administrators)

## Troubleshooting

### If menus still don't appear:

1. **Clear Browser Cache**
   - Chrome: Ctrl+Shift+Delete → Clear browsing data
   - Firefox: Ctrl+Shift+Delete → Clear recent history

2. **Check User Permissions**
   - Go to Settings → Users & Companies → Users
   - Edit your user
   - Ensure "Internal User" is checked
   - Add "Accounting / Billing" access rights

3. **Check Odoo Logs**
   Look for errors like:
   - "Field does not exist"
   - "Model not found"
   - "Access denied"

4. **Verify Module Dependencies**
   Ensure these modules are installed:
   - account (Accounting)
   - base (Base)
   - web (Web)

5. **Database Consistency**
   ```sql
   -- Check if menus exist in database
   SELECT name, action, parent_id 
   FROM ir_ui_menu 
   WHERE name LIKE '%MZ%';
   ```

## Files Modified

1. **views/menuitems_simple.xml** - New simplified menu structure
2. **__manifest__.py** - Updated to use new menu file
3. **security/ir.model.access.csv** - Fixed security groups
4. **test_mz_dashboard_menus.py** - Test script to verify installation
5. **reinstall_mz_dashboard.sh** - Automated reinstall script

## Common Errors and Solutions

| Error | Solution |
|-------|----------|
| "Field 'account.view_account_invoice_filter' does not exist" | Use menuitems_simple.xml instead |
| "Access Denied" | Check user groups and permissions |
| "Module not found" | Ensure module path is in odoo.conf |
| "Menus not visible" | Clear cache and refresh browser |

## Contact Support

If issues persist after following these instructions:
1. Check the Odoo logs for specific error messages
2. Run the test script: `python test_mz_dashboard_menus.py`
3. Verify all dependencies are installed
4. Ensure you're using Odoo 18 (not an earlier version)