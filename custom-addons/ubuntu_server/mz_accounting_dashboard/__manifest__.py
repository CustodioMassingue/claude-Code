# -*- coding: utf-8 -*-
{
    'name': 'MZ Accounting Dashboard',
    'version': '18.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Professional Accounting Dashboard for Odoo 18 Community',
    'description': """
MZ Professional Accounting Dashboard
====================================

A complete accounting dashboard for Odoo 18 Community Edition that replicates 
Enterprise functionality with enhanced features.

Key Features:
-------------
* **Real-time Dashboard**: Live financial KPIs and metrics
* **Journal Cards**: Interactive cards for each accounting journal
* **Sales Dashboard**: Draft invoices, overdue amounts, pending approvals
* **Purchase Dashboard**: Vendor bills, payment tracking, late payments
* **Bank & Cash**: Balance tracking, reconciliation status, outstanding items
* **Visual Analytics**: Mini graphs showing trends for each journal
* **Quick Actions**: Create invoices, bills, payments directly from dashboard
* **Auto-refresh**: Dashboard updates automatically every 60 seconds
* **Mobile Responsive**: Optimized for all device sizes
* **Multi-company**: Support for multi-company environments

Technical Features:
------------------
* Built with OWL 2.0 Framework for Odoo 18
* ES6 JavaScript modules
* Real-time data computation
* Optimized PostgreSQL queries
* Decimal precision for all monetary calculations
* Full accounting compliance

Dashboard Components:
--------------------
1. **Customer Invoices Card**:
   - Draft invoices count and total
   - Invoices to send
   - Overdue invoices with amounts
   - Invoices to check/approve
   - Monthly comparison

2. **Vendor Bills Card**:
   - Draft bills tracking
   - Bills to pay with amounts
   - Late/overdue bills
   - Bills pending approval
   - Document upload support

3. **Bank Account Card**:
   - Current balance display
   - Last synchronization date
   - Items to reconcile
   - Outstanding payments/receipts
   - Quick reconciliation access

4. **Cash Journal Card**:
   - Cash balance
   - Today's cash in/out
   - Pending transactions
   - Daily transaction count

5. **General Journal Card**:
   - Draft entries
   - Posted entries this month
   - Entries to review

Performance:
-----------
* Optimized for large datasets
* Efficient caching mechanisms
* Minimal database queries
* Fast load times

Security:
--------
* Respects Odoo access rights
* Journal-level permissions
* Company isolation
* Audit trail compliance
    """,
    'author': 'MZ Solutions',
    'website': 'https://www.mzsolutions.com',
    'depends': [
        'base',
        'account',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/dashboard_security.xml',
        'data/account_journal_data.xml',
        'views/account_journal_dashboard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mz_accounting_dashboard/static/src/scss/account_dashboard.scss',
            # 'mz_accounting_dashboard/static/src/js/account_dashboard_simple.js',  # Disabled to use standard kanban
            # 'mz_accounting_dashboard/static/src/js/account_dashboard.js',  # Complex version - disabled for now
            # 'mz_accounting_dashboard/static/src/xml/account_dashboard_templates.xml',  # Disabled for now
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'external_dependencies': {
        'python': [],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}