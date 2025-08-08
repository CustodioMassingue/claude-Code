{
    "name": "Invoicing: Accounting Menu Extras (MZ)",
    "version": "17.0.1.0.0",
    "summary": "Herda Invoicing e adiciona Analytic Items, Assets, Reconcile, Lock Dates, Secure Entries",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Tropigalia SA",
    "depends": ["account", "analytic"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_menu_ext.xml",
        "views/asset_views.xml"
    ],
    "installable": True
}
