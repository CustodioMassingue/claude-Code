# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FiscalYearWizard(models.TransientModel):
    _name = 'fiscal.year.wizard'
    _description = 'Fiscal Year Closing Wizard'
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    fiscal_year = fields.Selection(
        selection='_get_fiscal_years',
        string='Fiscal Year',
        required=True
    )
    
    closing_date = fields.Date(
        string='Closing Date',
        required=True,
        default=fields.Date.today
    )
    
    closing_journal_id = fields.Many2one(
        'account.journal',
        string='Closing Journal',
        required=True,
        domain="[('type', '=', 'general')]"
    )
    
    profit_account_id = fields.Many2one(
        'account.account',
        string='Profit Account',
        required=True
    )
    
    loss_account_id = fields.Many2one(
        'account.account',
        string='Loss Account',
        required=True
    )
    
    @api.model
    def _get_fiscal_years(self):
        """Get available fiscal years"""
        current_year = fields.Date.today().year
        years = []
        for i in range(5):
            year = current_year - i
            years.append((str(year), str(year)))
        return years
    
    def action_close_fiscal_year(self):
        """Close the fiscal year"""
        self.ensure_one()
        
        # Get all P&L accounts
        pl_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', 'in', ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost'])
        ])
        
        if not pl_accounts:
            raise UserError(_('No P&L accounts found to close.'))
        
        # Create closing entry
        move_vals = {
            'journal_id': self.closing_journal_id.id,
            'date': self.closing_date,
            'ref': _('Fiscal Year Closing %s') % self.fiscal_year,
            'company_id': self.company_id.id,
            'line_ids': []
        }
        
        total_profit = 0
        total_loss = 0
        
        for account in pl_accounts:
            balance = account.current_balance
            if balance != 0:
                # Create closing line
                line_vals = {
                    'account_id': account.id,
                    'name': _('Closing %s') % account.name,
                    'debit': -balance if balance < 0 else 0,
                    'credit': balance if balance > 0 else 0,
                }
                move_vals['line_ids'].append((0, 0, line_vals))
                
                if account.account_type in ['income', 'income_other']:
                    total_profit += balance
                else:
                    total_loss += abs(balance)
        
        # Add profit/loss line
        net_result = total_profit - total_loss
        if net_result > 0:
            # Profit
            move_vals['line_ids'].append((0, 0, {
                'account_id': self.profit_account_id.id,
                'name': _('Net Profit for %s') % self.fiscal_year,
                'debit': 0,
                'credit': net_result,
            }))
        else:
            # Loss
            move_vals['line_ids'].append((0, 0, {
                'account_id': self.loss_account_id.id,
                'name': _('Net Loss for %s') % self.fiscal_year,
                'debit': abs(net_result),
                'credit': 0,
            }))
        
        # Create and post the move
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }