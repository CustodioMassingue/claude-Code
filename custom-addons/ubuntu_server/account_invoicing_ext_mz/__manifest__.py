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
            "/account_invoicing_ext_mz/static/src/components/cash_flow/cash_flow.js",
            "/account_invoicing_ext_mz/static/src/components/cash_flow/cash_flow.xml",
            "/account_invoicing_ext_mz/static/src/components/executive_summary/executive_summary.js",
            "/account_invoicing_ext_mz/static/src/components/executive_summary/executive_summary.xml",
            "/account_invoicing_ext_mz/static/src/components/tax_return/tax_return.js",
            "/account_invoicing_ext_mz/static/src/components/tax_return/tax_return.xml",
            "/account_invoicing_ext_mz/static/src/components/general_ledger/general_ledger.js",
            "/account_invoicing_ext_mz/static/src/components/general_ledger/general_ledger.xml",
            "/account_invoicing_ext_mz/static/src/components/trial_balance/trial_balance.js",
            "/account_invoicing_ext_mz/static/src/components/trial_balance/trial_balance.xml",
            "/account_invoicing_ext_mz/static/src/components/journal_audit/journal_audit.js",
            "/account_invoicing_ext_mz/static/src/components/journal_audit/journal_audit.xml",
            "/account_invoicing_ext_mz/static/src/components/partner_ledger/partner_ledger.js",
            "/account_invoicing_ext_mz/static/src/components/partner_ledger/partner_ledger.xml",
            "/account_invoicing_ext_mz/static/src/components/aged_receivable/aged_receivable.js",
            "/account_invoicing_ext_mz/static/src/components/aged_receivable/aged_receivable.xml",
            "/account_invoicing_ext_mz/static/src/components/aged_payable/aged_payable.js",
            "/account_invoicing_ext_mz/static/src/components/aged_payable/aged_payable.xml",
            "/account_invoicing_ext_mz/static/src/scss/financial_reports.scss"
        ]
    },
    "installable": True
}
