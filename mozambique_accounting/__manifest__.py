# -*- coding: utf-8 -*-
{
    'name': 'Mozambique Advanced Accounting',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete accounting module for Mozambican legislation',
    'description': """
        Advanced Accounting Module for Mozambique
        ==========================================
        
        This module provides comprehensive accounting features tailored for
        Mozambican businesses, including:
        
        * PGC-NIRF/PE compliant chart of accounts
        * All Mozambican taxes (IVA, IRPC, IRPS, ICE)
        * e-Tributação integration
        * SAF-T(MZ) compliance
        * Certified invoicing with QR codes
        * Complete financial and fiscal reporting
        * Bank reconciliation
        * Asset management
        * Analytical accounting
        * Multi-company support
        
        Fully developed for Odoo Community Edition with enterprise-level features.
    """,
    'author': 'Mozambique Accounting Team',
    'website': 'https://github.com/mozambique-accounting',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'purchase',
        'stock',
        'contacts',
        'product',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/account_chart_template.xml',
        'data/account_tax_data.xml',
        # 'data/fiscal_positions.xml',  # To be implemented
        'data/sequences.xml',
        
        # Views
        'views/menu_views.xml',
        'views/moz_invoice_views.xml',
        'views/moz_asset_views.xml',
        
        # Reports (to be implemented)
        # 'reports/financial_reports.xml',
        # 'reports/fiscal_reports.xml',
        # 'reports/invoice_report.xml',
        
        # Wizards (to be implemented)
        # 'wizards/account_close_period.xml',
        # 'wizards/saft_export.xml',
        # 'wizards/fiscal_declaration.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_accounts.xml',
        'demo/demo_invoices.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mozambique_accounting/static/src/scss/accounting.scss',
            'mozambique_accounting/static/src/js/reconciliation_widget.js',
            'mozambique_accounting/static/src/js/dashboard.js',
            'mozambique_accounting/static/src/xml/templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}