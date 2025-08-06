# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountClosePeriodWizard(models.TransientModel):
    _name = 'moz.account.close.period.wizard'
    _description = 'Close Accounting Period'
    
    period_id = fields.Many2one(
        'moz.fiscal.period',
        string='Fiscal Period',
        required=True,
        domain="[('state', '=', 'open')]"
    )
    
    date_from = fields.Date(
        related='period_id.date_from',
        string='Start Date',
        readonly=True
    )
    
    date_to = fields.Date(
        related='period_id.date_to',
        string='End Date',
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Closing Journal',
        required=True,
        domain="[('type', '=', 'general')]"
    )
    
    closing_date = fields.Date(
        string='Closing Date',
        required=True,
        default=fields.Date.today
    )
    
    # Options
    close_revenue_accounts = fields.Boolean(
        string='Close Revenue Accounts',
        default=True
    )
    
    close_expense_accounts = fields.Boolean(
        string='Close Expense Accounts',
        default=True
    )
    
    create_opening_entries = fields.Boolean(
        string='Create Opening Entries for Next Period',
        default=True
    )
    
    # Result accounts
    profit_account_id = fields.Many2one(
        'account.account',
        string='Profit Account',
        domain="[('account_type', '=', 'equity')]"
    )
    
    loss_account_id = fields.Many2one(
        'account.account',
        string='Loss Account',
        domain="[('account_type', '=', 'equity')]"
    )
    
    interim_account_id = fields.Many2one(
        'account.account',
        string='Interim Results Account',
        domain="[('account_type', '=', 'equity')]"
    )
    
    def action_close_period(self):
        """Close the accounting period"""
        self.ensure_one()
        
        if self.period_id.state != 'open':
            raise UserError(_('Period is not open.'))
        
        # Check if all entries are posted
        unposted_moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'draft')
        ])
        
        if unposted_moves:
            raise UserError(_('There are %s unposted entries in this period. Please post them before closing.') % len(unposted_moves))
        
        # Create closing entries
        closing_move = self._create_closing_entries()
        
        # Close the period
        self.period_id.state = 'closed'
        
        # Create opening entries for next period if requested
        if self.create_opening_entries:
            self._create_opening_entries()
        
        # Return action to view the closing move
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': closing_move.id,
            'view_mode': 'form',
        }
    
    def _create_closing_entries(self):
        """Create closing journal entries"""
        # Get accounts to close
        revenue_accounts = []
        expense_accounts = []
        
        if self.close_revenue_accounts:
            revenue_accounts = self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                ('account_type', 'in', ['income', 'income_other'])
            ])
        
        if self.close_expense_accounts:
            expense_accounts = self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                ('account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation'])
            ])
        
        # Calculate balances
        move_lines = []
        total_revenue = 0
        total_expense = 0
        
        # Close revenue accounts
        for account in revenue_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                total_revenue += abs(balance)
                move_lines.append((0, 0, {
                    'account_id': account.id,
                    'name': f'Closing {account.name}',
                    'debit': abs(balance) if balance < 0 else 0,
                    'credit': balance if balance > 0 else 0,
                }))
        
        # Close expense accounts
        for account in expense_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                total_expense += balance
                move_lines.append((0, 0, {
                    'account_id': account.id,
                    'name': f'Closing {account.name}',
                    'debit': 0 if balance > 0 else abs(balance),
                    'credit': balance if balance > 0 else 0,
                }))
        
        # Add result line
        result = total_revenue - total_expense
        result_account = self.profit_account_id if result > 0 else self.loss_account_id
        
        if not result_account:
            result_account = self.interim_account_id
        
        if result != 0 and result_account:
            move_lines.append((0, 0, {
                'account_id': result_account.id,
                'name': f'Period Result',
                'debit': 0 if result > 0 else abs(result),
                'credit': result if result > 0 else 0,
            }))
        
        # Create closing move
        if move_lines:
            move = self.env['account.move'].create({
                'journal_id': self.journal_id.id,
                'date': self.closing_date,
                'ref': f'Closing Period {self.period_id.name}',
                'line_ids': move_lines,
            })
            move.action_post()
            return move
        
        return self.env['account.move']
    
    def _get_account_balance(self, account):
        """Get account balance for the period"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        debit = sum(move_lines.mapped('debit'))
        credit = sum(move_lines.mapped('credit'))
        
        # For revenue accounts, credit is positive
        if account.account_type in ['income', 'income_other']:
            return credit - debit
        # For expense accounts, debit is positive
        else:
            return debit - credit
    
    def _create_opening_entries(self):
        """Create opening entries for the next period"""
        # Find next period
        next_period = self.env['moz.fiscal.period'].search([
            ('date_from', '>', self.date_to),
            ('company_id', '=', self.company_id.id)
        ], order='date_from', limit=1)
        
        if not next_period:
            return
        
        # Get balance sheet accounts
        bs_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', 'in', ['asset_cash', 'asset_current', 'asset_fixed', 
                                   'asset_receivable', 'liability_current', 
                                   'liability_payable', 'equity'])
        ])
        
        move_lines = []
        
        for account in bs_accounts:
            balance = self._get_account_total_balance(account)
            if balance != 0:
                move_lines.append((0, 0, {
                    'account_id': account.id,
                    'name': f'Opening Balance {account.name}',
                    'debit': balance if balance > 0 else 0,
                    'credit': abs(balance) if balance < 0 else 0,
                }))
        
        # Create opening move
        if move_lines:
            move = self.env['account.move'].create({
                'journal_id': self.journal_id.id,
                'date': next_period.date_from,
                'ref': f'Opening Balances {next_period.name}',
                'line_ids': move_lines,
            })
            move.action_post()
            return move
        
        return self.env['account.move']
    
    def _get_account_total_balance(self, account):
        """Get total account balance up to period end"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        debit = sum(move_lines.mapped('debit'))
        credit = sum(move_lines.mapped('credit'))
        
        return debit - credit