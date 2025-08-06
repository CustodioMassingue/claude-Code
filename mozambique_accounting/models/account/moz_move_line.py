# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional, Set
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class MozMoveLine(models.Model):
    """Journal Items (Move Lines) for Mozambican accounting"""
    
    _name = 'moz.move.line'
    _description = 'Mozambican Journal Item'
    _order = 'date desc, move_name desc, id'
    _rec_name = 'display_name'
    
    # Basic Fields
    name = fields.Char(
        string='Label',
        help='Description of the journal item'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    move_id = fields.Many2one(
        'moz.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    move_name = fields.Char(
        string='Entry Number',
        related='move_id.name',
        store=True,
        index=True
    )
    
    date = fields.Date(
        string='Date',
        related='move_id.date',
        store=True,
        index=True
    )
    
    ref = fields.Char(
        string='Reference',
        help='Reference of the document that generated this entry'
    )
    
    parent_state = fields.Selection(
        related='move_id.state',
        string='Entry State',
        store=True
    )
    
    # Account
    account_id = fields.Many2one(
        'moz.account',
        string='Account',
        required=True,
        index=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    
    account_type = fields.Selection(
        related='account_id.account_type',
        string='Account Type',
        store=True
    )
    
    account_internal_group = fields.Selection(
        related='account_id.internal_group',
        string='Internal Group',
        store=True
    )
    
    # Company and Currency
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='move_id.company_id',
        store=True,
        readonly=True
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True,
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='The currency of the amount'
    )
    
    # Amounts - Using Monetary fields for precision
    debit = fields.Monetary(
        string='Debit',
        default=0.0,
        currency_field='company_currency_id',
        help='Debit amount in company currency'
    )
    
    credit = fields.Monetary(
        string='Credit',
        default=0.0,
        currency_field='company_currency_id',
        help='Credit amount in company currency'
    )
    
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance',
        store=True,
        currency_field='company_currency_id',
        help='Technical field: debit - credit'
    )
    
    amount_currency = fields.Monetary(
        string='Amount in Currency',
        currency_field='currency_id',
        help='Amount in foreign currency'
    )
    
    # Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        index=True
    )
    
    # Journal
    journal_id = fields.Many2one(
        'moz.journal',
        string='Journal',
        related='move_id.journal_id',
        store=True,
        index=True
    )
    
    # Tax
    tax_ids = fields.Many2many(
        'moz.tax',
        'moz_move_line_tax_rel',
        'line_id',
        'tax_id',
        string='Taxes Applied',
        help='Taxes applied on this line'
    )
    
    tax_line_id = fields.Many2one(
        'moz.tax',
        string='Tax Line',
        help='Indicates this line is a tax line'
    )
    
    tax_base_amount = fields.Monetary(
        string='Tax Base',
        currency_field='company_currency_id',
        help='Base amount for tax calculation'
    )
    
    # Reconciliation
    reconciled = fields.Boolean(
        string='Reconciled',
        compute='_compute_reconciled',
        store=True
    )
    
    full_reconcile_id = fields.Many2one(
        'moz.full.reconcile',
        string='Full Reconcile',
        copy=False,
        index=True
    )
    
    matched_debit_ids = fields.One2many(
        'moz.partial.reconcile',
        'debit_move_id',
        string='Matched Debits'
    )
    
    matched_credit_ids = fields.One2many(
        'moz.partial.reconcile',
        'credit_move_id',
        string='Matched Credits'
    )
    
    amount_residual = fields.Monetary(
        string='Residual Amount',
        compute='_compute_amount_residual',
        store=True,
        currency_field='company_currency_id',
        help='Remaining amount to be reconciled'
    )
    
    amount_residual_currency = fields.Monetary(
        string='Residual Amount in Currency',
        compute='_compute_amount_residual',
        store=True,
        currency_field='currency_id',
        help='Remaining amount in foreign currency'
    )
    
    # Analytics
    analytic_account_id = fields.Many2one(
        'moz.analytic.account',
        string='Analytic Account',
        index=True
    )
    
    analytic_tag_ids = fields.Many2many(
        'moz.analytic.tag',
        'moz_move_line_analytic_tag_rel',
        'line_id',
        'tag_id',
        string='Analytic Tags'
    )
    
    # Payment
    payment_id = fields.Many2one(
        'moz.payment',
        string='Payment',
        copy=False,
        index=True
    )
    
    statement_line_id = fields.Many2one(
        'moz.bank.statement.line',
        string='Bank Statement Line',
        copy=False,
        index=True
    )
    
    statement_id = fields.Many2one(
        related='statement_line_id.statement_id',
        string='Bank Statement',
        store=True,
        index=True
    )
    
    # Maturity
    date_maturity = fields.Date(
        string='Due Date',
        index=True,
        help='Due date for receivables and payables'
    )
    
    # Blocking
    blocked = fields.Boolean(
        string='Blocked',
        default=False,
        help='Block this line from automatic reconciliation'
    )
    
    # Mozambican Specific Fields
    nuit = fields.Char(
        string='NUIT',
        related='partner_id.vat',
        store=True,
        help='Tax Identification Number (NUIT)'
    )
    
    province_id = fields.Many2one(
        'res.country.state',
        string='Province',
        related='partner_id.state_id',
        store=True
    )
    
    cost_center_id = fields.Many2one(
        'moz.cost.center',
        string='Cost Center',
        index=True
    )
    
    budget_line_id = fields.Many2one(
        'moz.budget.line',
        string='Budget Line'
    )
    
    # Computed Fields
    @api.depends('name', 'ref', 'move_name')
    def _compute_display_name(self):
        for line in self:
            parts = []
            if line.move_name:
                parts.append(line.move_name)
            if line.ref:
                parts.append(line.ref)
            if line.name:
                parts.append(line.name)
            
            line.display_name = ' - '.join(parts) if parts else '/'
    
    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit
    
    @api.depends('full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_reconciled(self):
        for line in self:
            line.reconciled = bool(line.full_reconcile_id)
    
    @api.depends('balance', 'amount_currency', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        for line in self:
            if line.reconciled:
                line.amount_residual = 0
                line.amount_residual_currency = 0
            else:
                # Calculate reconciled amount
                reconciled_amount = 0
                reconciled_amount_currency = 0
                
                if line.debit > 0:
                    for partial in line.matched_debit_ids:
                        reconciled_amount += partial.amount
                        if partial.currency_id:
                            reconciled_amount_currency += partial.amount_currency
                else:
                    for partial in line.matched_credit_ids:
                        reconciled_amount += partial.amount
                        if partial.currency_id:
                            reconciled_amount_currency += partial.amount_currency
                
                # Calculate residual
                line.amount_residual = abs(line.balance) - reconciled_amount
                
                if line.currency_id and line.amount_currency:
                    line.amount_residual_currency = abs(line.amount_currency) - reconciled_amount_currency
                else:
                    line.amount_residual_currency = 0
    
    # Constraints
    @api.constrains('debit', 'credit')
    def _check_amount(self):
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError(
                    _("Debit and Credit amounts must be positive!")
                )
            
            if line.debit > 0 and line.credit > 0:
                raise ValidationError(
                    _("A journal item cannot have both debit and credit amounts!")
                )
            
            if line.debit == 0 and line.credit == 0:
                raise ValidationError(
                    _("A journal item must have either a debit or credit amount!")
                )
    
    @api.constrains('account_id', 'partner_id')
    def _check_partner_required(self):
        for line in self:
            if line.account_id.require_partner and not line.partner_id:
                raise ValidationError(
                    _("Account %s requires a partner!") % line.account_id.display_name
                )
    
    @api.constrains('account_id', 'analytic_account_id')
    def _check_analytic_required(self):
        for line in self:
            if line.account_id.require_analytic and not line.analytic_account_id:
                raise ValidationError(
                    _("Account %s requires an analytic account!") % line.account_id.display_name
                )
    
    @api.constrains('currency_id', 'amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.currency_id:
                if not line.amount_currency:
                    raise ValidationError(
                        _("Amount in currency is required when a currency is set!")
                    )
            elif line.amount_currency:
                raise ValidationError(
                    _("Cannot set amount in currency without specifying a currency!")
                )
    
    # CRUD Methods
    @api.model
    def create(self, vals):
        # Check if move is not in draft state
        if vals.get('move_id'):
            move = self.env['moz.move'].browse(vals['move_id'])
            if move.state != 'draft':
                raise UserError(
                    _("Cannot add lines to a posted or cancelled entry!")
                )
        
        # Set default values
        if not vals.get('name'):
            if vals.get('ref'):
                vals['name'] = vals['ref']
        
        return super().create(vals)
    
    def write(self, vals):
        # Check if trying to modify posted lines
        posted_lines = self.filtered(lambda l: l.parent_state == 'posted')
        if posted_lines and not self.env.context.get('force_write'):
            restricted_fields = set(vals.keys()) - {'blocked', 'reconciled'}
            if restricted_fields:
                raise UserError(
                    _("Cannot modify posted journal items!")
                )
        
        return super().write(vals)
    
    def unlink(self):
        for line in self:
            if line.parent_state == 'posted':
                raise UserError(
                    _("Cannot delete posted journal items!")
                )
            if line.reconciled:
                raise UserError(
                    _("Cannot delete reconciled journal items!")
                )
        
        return super().unlink()
    
    # Business Methods
    def reconcile(self):
        """Reconcile journal items"""
        # Check if all lines are from the same account
        accounts = self.mapped('account_id')
        if len(accounts) > 1:
            raise UserError(
                _("Can only reconcile items from the same account!")
            )
        
        # Check if account allows reconciliation
        if not accounts.reconcile:
            raise UserError(
                _("Account %s does not allow reconciliation!") % accounts.display_name
            )
        
        # Check if all moves are posted
        if any(line.parent_state != 'posted' for line in self):
            raise UserError(
                _("Can only reconcile posted journal items!")
            )
        
        # Calculate total balance
        total_balance = sum(self.mapped('balance'))
        
        # Use Decimal for precision
        balance_decimal = Decimal(str(total_balance))
        
        if abs(balance_decimal) < Decimal('0.01'):
            # Full reconciliation
            reconcile = self.env['moz.full.reconcile'].create({
                'reconciled_line_ids': [(6, 0, self.ids)]
            })
            self.write({'full_reconcile_id': reconcile.id})
            
            _logger.info("Full reconciliation created: %s", reconcile.name)
        else:
            # Partial reconciliation
            self._create_partial_reconcile()
    
    def _create_partial_reconcile(self):
        """Create partial reconciliation"""
        debit_lines = self.filtered(lambda l: l.balance > 0).sorted(
            key=lambda l: (l.date_maturity or l.date, l.id)
        )
        credit_lines = self.filtered(lambda l: l.balance < 0).sorted(
            key=lambda l: (l.date_maturity or l.date, l.id)
        )
        
        for debit_line in debit_lines:
            for credit_line in credit_lines:
                if debit_line.amount_residual <= 0 or credit_line.amount_residual <= 0:
                    continue
                
                # Calculate amount to reconcile
                amount_to_reconcile = min(
                    debit_line.amount_residual,
                    abs(credit_line.amount_residual)
                )
                
                if amount_to_reconcile > 0:
                    partial = self.env['moz.partial.reconcile'].create({
                        'debit_move_id': debit_line.id,
                        'credit_move_id': credit_line.id,
                        'amount': amount_to_reconcile,
                        'currency_id': debit_line.currency_id.id if debit_line.currency_id else False,
                    })
                    
                    _logger.info("Partial reconciliation created: %s", partial.id)
    
    def remove_reconcile(self):
        """Remove reconciliation"""
        for line in self:
            if line.full_reconcile_id:
                reconcile = line.full_reconcile_id
                reconcile.reconciled_line_ids.write({'full_reconcile_id': False})
                reconcile.unlink()
            
            # Remove partial reconciliations
            (line.matched_debit_ids | line.matched_credit_ids).unlink()
    
    def action_open_reconcile_wizard(self):
        """Open reconciliation wizard"""
        return {
            'name': _('Reconcile'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.reconcile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'moz.move.line'
            }
        }
    
    @api.model
    def get_reconciliation_data(self, partner_id: Optional[int] = None,
                               account_id: Optional[int] = None) -> List[Dict]:
        """Get data for reconciliation widget"""
        domain = [
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('account_id.reconcile', '=', True)
        ]
        
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if account_id:
            domain.append(('account_id', '=', account_id))
        
        lines = self.search(domain, order='date, id')
        
        data = []
        for line in lines:
            data.append({
                'id': line.id,
                'name': line.display_name,
                'date': str(line.date),
                'partner': line.partner_id.name if line.partner_id else '',
                'ref': line.ref or '',
                'debit': float(line.debit),
                'credit': float(line.credit),
                'balance': float(line.balance),
                'residual': float(line.amount_residual),
                'currency': line.currency_id.name if line.currency_id else '',
                'amount_currency': float(line.amount_currency) if line.amount_currency else 0,
            })
        
        return data
    
    def copy_data(self, default=None):
        """Override to handle copy of journal items"""
        default = dict(default or {})
        default.update({
            'reconciled': False,
            'full_reconcile_id': False,
            'matched_debit_ids': False,
            'matched_credit_ids': False,
            'payment_id': False,
            'statement_line_id': False,
        })
        return super().copy_data(default)
    
    @api.model
    def get_aged_partner_balance(self, date_to: str, partner_ids: List[int] = None) -> Dict:
        """Calculate aged partner balance"""
        domain = [
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('date', '<=', date_to)
        ]
        
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        
        lines = self.search(domain)
        
        today = fields.Date.from_string(date_to)
        periods = {
            'current': (0, 30),
            '1-30': (31, 60),
            '31-60': (61, 90),
            '61-90': (91, 120),
            'over_120': (121, None)
        }
        
        result = {}
        for line in lines:
            partner_id = line.partner_id.id if line.partner_id else 0
            
            if partner_id not in result:
                result[partner_id] = {
                    'partner': line.partner_id.name if line.partner_id else _('Unknown'),
                    'current': 0,
                    '1-30': 0,
                    '31-60': 0,
                    '61-90': 0,
                    'over_120': 0,
                    'total': 0
                }
            
            # Calculate age
            due_date = line.date_maturity or line.date
            days_overdue = (today - due_date).days
            
            # Categorize by period
            amount = line.amount_residual
            for period_name, (min_days, max_days) in periods.items():
                if max_days is None:
                    if days_overdue > min_days:
                        result[partner_id][period_name] += amount
                        break
                elif min_days <= days_overdue <= max_days:
                    result[partner_id][period_name] += amount
                    break
            
            result[partner_id]['total'] += amount
        
        return result