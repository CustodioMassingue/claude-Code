# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def pre_init_hook(cr):
    """
    Clean up any conflicting records before module installation/update
    """
    try:
        # Use direct SQL to avoid ORM issues - clean up old external IDs
        cr.execute("""
            DELETE FROM ir_model_data 
            WHERE module = 'account_invoicing_ext_mz' 
            AND name IN ('act_mz_balance_sheet', 'act_mz_profit_loss', 
                        'menu_mz_balance_sheet', 'menu_mz_profit_loss')
        """)
        cr.commit()
    except Exception:
        cr.rollback()
        # Continue even if cleanup fails
        pass

def post_init_hook(cr, registry):
    """
    Clean up any conflicting records after module installation/update
    """
    try:
        # Use direct SQL to avoid ORM issues
        cr.execute("""
            DELETE FROM ir_model_data 
            WHERE module = 'account_invoicing_ext_mz' 
            AND name IN ('act_mz_balance_sheet', 'act_mz_profit_loss', 
                        'menu_mz_balance_sheet', 'menu_mz_profit_loss')
            AND model = 'ir.actions.act_window'
        """)
        cr.commit()
    except Exception:
        cr.rollback()
        # Continue even if cleanup fails
        pass