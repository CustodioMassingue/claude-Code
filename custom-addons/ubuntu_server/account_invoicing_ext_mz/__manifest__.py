{
    "name": "Invoicing: Accounting Menu Extras (MZ)",
    "version": "17.0.1.0.0",
    "summary": "Herda Invoicing e adiciona Analytic Items, Assets, Reconcile, Lock Dates, Secure Entries, Balance Sheet",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Tropigalia SA",
    "depends": ["account", "analytic", "web"],
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
            "/account_invoicing_ext_mz/static/src/scss/balance_sheet.scss"
        ]
    },
    "installable": True
}
