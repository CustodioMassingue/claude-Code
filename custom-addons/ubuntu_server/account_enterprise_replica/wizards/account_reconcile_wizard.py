# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountReconcileWizard(models.TransientModel):
    _name = 'account.reconcile.wizard'
    _description = 'Account Reconciliation Wizard'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        domain="[('reconcile', '=', True)]"
    )
    
    date_from = fields.Date(
        string='From Date'
    )
    
    date_to = fields.Date(
        string='To Date'
    )
    
    auto_reconcile = fields.Boolean(
        string='Auto Reconcile Matching Amounts',
        default=True
    )
    
    def action_reconcile(self):
        """Run reconciliation"""
        self.ensure_one()
        
        domain = [
            ('account_id', '=', self.account_id.id),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted')
        ]
        
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        
        move_lines = self.env['account.move.line'].search(domain)
        
        if not move_lines:
            raise UserError(_('No entries found to reconcile.'))
        
        # Auto reconcile if requested
        if self.auto_reconcile:
            move_lines.auto_reconcile_lines()
        
        # Return action to show reconciliation widget
        return {
            'type': 'ir.actions.client',
            'tag': 'account_reconciliation_widget',
            'context': {
                'move_line_ids': move_lines.ids,
                'mode': 'accounts',
            }
        }