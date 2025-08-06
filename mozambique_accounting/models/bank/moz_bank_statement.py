# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from decimal import Decimal, ROUND_HALF_UP
import logging

_logger = logging.getLogger(__name__)

class MozBankStatement(models.Model):
    _name = 'moz.bank.statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bank Statement'
    _order = 'date desc, id desc'
    
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    date_from = fields.Date(
        string='From Date',
        tracking=True
    )
    
    date_to = fields.Date(
        string='To Date',
        tracking=True
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', '=', 'bank')]",
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('confirm', 'Confirmed'),
    ], string='State', default='draft', tracking=True)
    
    line_ids = fields.One2many(
        'moz.bank.statement.line',
        'statement_id',
        string='Statement Lines'
    )
    
    balance_start = fields.Monetary(
        string='Starting Balance',
        currency_field='currency_id',
        tracking=True
    )
    
    balance_end = fields.Monetary(
        string='Ending Balance',
        compute='_compute_balance_end',
        store=True,
        currency_field='currency_id'
    )
    
    balance_end_real = fields.Monetary(
        string='Real Ending Balance',
        currency_field='currency_id',
        tracking=True
    )
    
    total_entry_encoding = fields.Monetary(
        string='Total Transactions',
        compute='_compute_total_entry',
        store=True,
        currency_field='currency_id'
    )
    
    difference = fields.Monetary(
        string='Difference',
        compute='_compute_difference',
        store=True,
        currency_field='currency_id'
    )
    
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        compute='_compute_is_reconciled',
        store=True
    )
    
    @api.depends('balance_start', 'line_ids.amount')
    def _compute_balance_end(self):
        for statement in self:
            total = sum(line.amount for line in statement.line_ids)
            statement.balance_end = statement.balance_start + total
    
    @api.depends('line_ids.amount')
    def _compute_total_entry(self):
        for statement in self:
            statement.total_entry_encoding = sum(line.amount for line in statement.line_ids)
    
    @api.depends('balance_end', 'balance_end_real')
    def _compute_difference(self):
        for statement in self:
            statement.difference = statement.balance_end_real - statement.balance_end
    
    @api.depends('line_ids.is_reconciled')
    def _compute_is_reconciled(self):
        for statement in self:
            statement.is_reconciled = all(line.is_reconciled for line in statement.line_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('moz.bank.statement') or 'New'
        return super().create(vals)
    
    def action_open(self):
        """Open the statement for reconciliation"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft statements can be opened.'))
        self.state = 'open'
        return True
    
    def action_confirm(self):
        """Confirm the statement and create journal entries"""
        self.ensure_one()
        if self.state != 'open':
            raise UserError(_('Only open statements can be confirmed.'))
        
        if abs(self.difference) > 0.01:
            raise UserError(_('The statement is not balanced. Difference: %s') % self.difference)
        
        # Create journal entries for reconciled lines
        for line in self.line_ids.filtered(lambda l: l.is_reconciled):
            line._create_journal_entry()
        
        self.state = 'confirm'
        return True
    
    def action_reset(self):
        """Reset to draft"""
        self.ensure_one()
        if self.state == 'confirm':
            raise UserError(_('Confirmed statements cannot be reset to draft.'))
        
        # Unreconcile all lines
        for line in self.line_ids:
            line.action_undo_reconciliation()
        
        self.state = 'draft'
        return True
    
    def action_reconcile(self):
        """Open reconciliation wizard"""
        self.ensure_one()
        return {
            'name': _('Bank Reconciliation'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.bank.reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_statement_id': self.id,
            }
        }


class MozBankStatementLine(models.Model):
    _name = 'moz.bank.statement.line'
    _description = 'Bank Statement Line'
    _order = 'date desc, id desc'
    
    statement_id = fields.Many2one(
        'moz.bank.statement',
        string='Statement',
        required=True,
        ondelete='cascade'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    
    name = fields.Char(
        string='Description',
        required=True
    )
    
    ref = fields.Char(
        string='Reference'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='statement_id.currency_id',
        string='Currency'
    )
    
    company_id = fields.Many2one(
        related='statement_id.company_id',
        string='Company',
        store=True
    )
    
    journal_id = fields.Many2one(
        related='statement_id.journal_id',
        string='Journal',
        store=True
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True
    )
    
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        default=False
    )
    
    reconcile_model_id = fields.Many2one(
        'moz.bank.reconcile.model',
        string='Reconciliation Model'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Counterpart Account'
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes'
    )
    
    analytic_distribution = fields.Json(
        string='Analytic Distribution'
    )
    
    def action_reconcile(self):
        """Reconcile this line"""
        self.ensure_one()
        
        if self.is_reconciled:
            raise UserError(_('This line is already reconciled.'))
        
        # Try automatic reconciliation first
        if self._auto_reconcile():
            return True
        
        # Open manual reconciliation wizard
        return {
            'name': _('Manual Reconciliation'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.bank.reconciliation.line.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }
    
    def action_undo_reconciliation(self):
        """Undo reconciliation"""
        for line in self:
            if line.move_id:
                if line.move_id.state == 'posted':
                    line.move_id.button_cancel()
                line.move_id.unlink()
            line.is_reconciled = False
        return True
    
    def _auto_reconcile(self):
        """Try to automatically reconcile the line"""
        self.ensure_one()
        
        # Look for matching reconciliation model
        model = self.env['moz.bank.reconcile.model'].search([
            ('company_id', '=', self.company_id.id),
            '|',
            ('partner_id', '=', self.partner_id.id),
            ('partner_id', '=', False),
        ], limit=1)
        
        if model and model._match_statement_line(self):
            self.reconcile_model_id = model
            self.account_id = model.account_id
            self.tax_ids = model.tax_ids
            self.is_reconciled = True
            return True
        
        # Look for matching invoice
        if self.partner_id and self.amount != 0:
            domain = [
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('amount_residual', '!=', 0),
            ]
            
            if self.amount > 0:
                domain.append(('move_type', 'in', ['out_invoice', 'in_refund']))
            else:
                domain.append(('move_type', 'in', ['in_invoice', 'out_refund']))
            
            invoices = self.env['account.move'].search(domain)
            
            for invoice in invoices:
                if abs(invoice.amount_residual - abs(self.amount)) < 0.01:
                    # Found matching invoice
                    self.account_id = invoice.partner_id.property_account_receivable_id if self.amount > 0 else invoice.partner_id.property_account_payable_id
                    self.is_reconciled = True
                    return True
        
        return False
    
    def _create_journal_entry(self):
        """Create journal entry for reconciled line"""
        self.ensure_one()
        
        if not self.is_reconciled:
            raise UserError(_('Cannot create journal entry for unreconciled line.'))
        
        if self.move_id:
            return self.move_id
        
        # Prepare move values
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref or self.name,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'line_ids': [],
        }
        
        # Bank account line
        move_vals['line_ids'].append((0, 0, {
            'name': self.name,
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'debit': self.amount if self.amount > 0 else 0,
            'credit': -self.amount if self.amount < 0 else 0,
        }))
        
        # Counterpart line(s)
        if self.tax_ids:
            # With taxes
            base_amount = self.amount / (1 + sum(tax.amount / 100 for tax in self.tax_ids))
            tax_amount = self.amount - base_amount
            
            # Base line
            move_vals['line_ids'].append((0, 0, {
                'name': self.name,
                'account_id': self.account_id.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'debit': -base_amount if self.amount < 0 else 0,
                'credit': base_amount if self.amount > 0 else 0,
                'analytic_distribution': self.analytic_distribution,
            }))
            
            # Tax line(s)
            for tax in self.tax_ids:
                tax_line_amount = base_amount * (tax.amount / 100)
                move_vals['line_ids'].append((0, 0, {
                    'name': f"{tax.name} - {self.name}",
                    'account_id': tax.account_id.id,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'debit': -tax_line_amount if self.amount < 0 else 0,
                    'credit': tax_line_amount if self.amount > 0 else 0,
                    'tax_base_amount': base_amount,
                }))
        else:
            # Without taxes
            move_vals['line_ids'].append((0, 0, {
                'name': self.name,
                'account_id': self.account_id.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'debit': -self.amount if self.amount < 0 else 0,
                'credit': self.amount if self.amount > 0 else 0,
                'analytic_distribution': self.analytic_distribution,
            }))
        
        # Create and post move
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.move_id = move
        return move