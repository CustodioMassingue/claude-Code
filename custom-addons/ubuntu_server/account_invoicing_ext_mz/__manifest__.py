{
    "name": "Invoicing: Accounting Menu Extras (MZ)",
    "version": "17.0.1.0.4",
    "summary": "Herda Invoicing e adiciona Analytic Items, Assets, Reconcile, Lock Dates, Secure Entries, Balance Sheet",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Tropigalia SA",
    "depends": ["account", "analytic", "web"],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "data": [
        "security/ir.model.access.csv",
        "views/account_menu_ext.xml",
        "views/asset_views.xml",
        "views/balance_sheet_views.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "/account_invoicing_ext_mz/static/src/components/balance_sheet/balance_sheet.js",
            "/account_invoicing_ext_mz/static/src/components/balance_sheet/balance_sheet.xml",
            "/account_invoicing_ext_mz/static/src/components/profit_loss/profit_loss.js",
            "/account_invoicing_ext_mz/static/src/components/profit_loss/profit_loss.xml",
            "/account_invoicing_ext_mz/static/src/scss/balance_sheet.scss"
        ]
    },
    "installable": True
}
