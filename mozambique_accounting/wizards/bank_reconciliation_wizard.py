# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class BankReconciliationWizard(models.TransientModel):
    _name = 'moz.bank.reconciliation.wizard'
    _description = 'Bank Reconciliation Wizard'
    
    statement_id = fields.Many2one(
        'moz.bank.statement',
        string='Bank Statement',
        required=True
    )
    
    line_ids = fields.One2many(
        'moz.bank.reconciliation.wizard.line',
        'wizard_id',
        string='Lines to Reconcile'
    )
    
    @api.onchange('statement_id')
    def _onchange_statement_id(self):
        if self.statement_id:
            # Load unreconciled lines
            lines = []
            for line in self.statement_id.line_ids.filtered(lambda l: not l.is_reconciled):
                lines.append((0, 0, {
                    'statement_line_id': line.id,
                    'date': line.date,
                    'name': line.name,
                    'amount': line.amount,
                    'partner_id': line.partner_id.id if line.partner_id else False,
                }))
            self.line_ids = lines
    
    def action_reconcile(self):
        """Reconcile selected lines"""
        for line in self.line_ids.filtered('to_reconcile'):
            if line.account_id:
                line.statement_line_id.account_id = line.account_id
                line.statement_line_id.is_reconciled = True
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_auto_reconcile(self):
        """Auto reconcile all lines"""
        for line in self.line_ids:
            line.statement_line_id._auto_reconcile()
        
        # Reload
        self._onchange_statement_id()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class BankReconciliationWizardLine(models.TransientModel):
    _name = 'moz.bank.reconciliation.wizard.line'
    _description = 'Bank Reconciliation Wizard Line'
    
    wizard_id = fields.Many2one(
        'moz.bank.reconciliation.wizard',
        string='Wizard'
    )
    
    statement_line_id = fields.Many2one(
        'moz.bank.statement.line',
        string='Statement Line'
    )
    
    date = fields.Date(
        string='Date'
    )
    
    name = fields.Char(
        string='Description'
    )
    
    amount = fields.Float(
        string='Amount'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Account'
    )
    
    to_reconcile = fields.Boolean(
        string='Reconcile'
    )