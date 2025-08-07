{
    'name': 'MZ Accounting Dashboard',
    'version': '18.0.2.0.0',
    'category': 'Accounting',
    'summary': 'Professional Accounting Dashboard like Odoo Enterprise',
    'description': """
        Professional Accounting Dashboard for Odoo 18 Community
        ========================================================
        
        Replica of Odoo Enterprise Accounting Dashboard with:
        - Customer Invoices card with statistics
        - Vendor Bills card with upload functionality
        - Bank reconciliation card
        - Cash management card
        - Miscellaneous Operations card
        - Point of Sale integration
    """,
    'author': 'MZ Solutions',
    'website': 'https://www.mzsolutions.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/default_journals.xml',
        'views/account_journal_dashboard_view.xml',
        'views/dashboard_professional_view.xml',
        'views/account_dashboard_views.xml',
        'views/menuitems.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # SCSS Files
            'mz_accounting_dashboard/static/src/scss/dashboard.scss',
            'mz_accounting_dashboard/static/src/scss/dashboard_professional.scss',
            
            # JavaScript Files
            'mz_accounting_dashboard/static/src/js/dashboard_graph_field.js',
            
            # XML Templates
            'mz_accounting_dashboard/static/src/xml/dashboard_graph_field.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}