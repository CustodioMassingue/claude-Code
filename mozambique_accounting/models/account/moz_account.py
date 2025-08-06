# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional, Tuple
import re


class MozAccount(models.Model):
    """Mozambican Chart of Accounts - PGC-NIRF/PE Compliant"""
    
    _name = 'moz.account'
    _description = 'Mozambican Account'
    _order = 'code, name'
    _rec_name = 'display_name'
    _parent_store = True
    
    # Basic Fields
    name = fields.Char(
        string='Account Name',
        required=True,
        index=True,
        translate=True
    )
    
    code = fields.Char(
        string='Account Code',
        size=20,
        required=True,
        index=True,
        help='Account code according to PGC-NIRF'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Account Type and Classification
    account_type = fields.Selection([
        ('asset_fixed', 'Fixed Assets'),
        ('asset_current', 'Current Assets'),
        ('asset_cash', 'Cash and Bank'),
        ('asset_receivable', 'Receivable'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        ('liability_payable', 'Payable'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_other', 'Other Expenses'),
        ('off_balance', 'Off Balance'),
    ], string='Account Type', required=True, index=True)
    
    internal_group = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('off_balance', 'Off Balance'),
    ], string='Internal Group', compute='_compute_internal_group', store=True)
    
    # PGC-NIRF Classification
    pgc_class = fields.Selection([
        ('1', 'Class 1 - Fixed Assets and Investments'),
        ('2', 'Class 2 - Inventory'),
        ('3', 'Class 3 - Accounts Receivable and Payable'),
        ('4', 'Class 4 - Cash and Cash Equivalents'),
        ('5', 'Class 5 - Equity'),
        ('6', 'Class 6 - Costs and Losses'),
        ('7', 'Class 7 - Revenue and Gains'),
        ('8', 'Class 8 - Results'),
        ('9', 'Class 9 - Cost Accounting'),
    ], string='PGC Class', compute='_compute_pgc_class', store=True)
    
    # Hierarchy
    parent_id = fields.Many2one(
        'moz.account',
        string='Parent Account',
        index=True,
        ondelete='cascade'
    )
    
    parent_path = fields.Char(index=True)
    
    child_ids = fields.One2many(
        'moz.account',
        'parent_id',
        string='Child Accounts'
    )
    
    # Configuration
    currency_id = fields.Many2one(
        'res.currency',
        string='Account Currency',
        help='Forces all moves for this account to have this currency'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    reconcile = fields.Boolean(
        string='Allow Reconciliation',
        help='Check this if you want to allow reconciliation of journal items'
    )
    
    deprecated = fields.Boolean(
        string='Deprecated',
        default=False,
        help='Deprecated accounts cannot be used in transactions'
    )
    
    # Tax Configuration
    tax_ids = fields.Many2many(
        'moz.tax',
        'account_tax_rel',
        'account_id',
        'tax_id',
        string='Default Taxes'
    )
    
    # Balance and Activity
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance',
        currency_field='company_currency_id'
    )
    
    debit = fields.Monetary(
        string='Debit',
        compute='_compute_balance',
        currency_field='company_currency_id'
    )
    
    credit = fields.Monetary(
        string='Credit',
        compute='_compute_balance',
        currency_field='company_currency_id'
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )
    
    # Mozambican Specific Fields
    require_partner = fields.Boolean(
        string='Require Partner',
        help='Forces to set a partner on journal items'
    )
    
    require_analytic = fields.Boolean(
        string='Require Analytic Account',
        help='Forces to set an analytic account on journal items'
    )
    
    saft_account_type = fields.Selection([
        ('GA', 'General Accounts'),
        ('AR', 'Accounts Receivable'),
        ('AP', 'Accounts Payable'),
        ('FA', 'Fixed Assets'),
        ('OA', 'Other Assets'),
        ('CA', 'Current Assets'),
        ('CL', 'Current Liabilities'),
        ('EQ', 'Equity'),
        ('REV', 'Revenue'),
        ('EXP', 'Expenses'),
    ], string='SAF-T Account Type', help='Account type for SAF-T(MZ) reporting')
    
    at_classification = fields.Char(
        string='AT Classification',
        help='Tax Authority classification code'
    )
    
    # Computed Fields
    @api.depends('name', 'code')
    def _compute_display_name(self):
        for account in self:
            account.display_name = f"{account.code} - {account.name}"
    
    @api.depends('account_type')
    def _compute_internal_group(self):
        type_mapping = {
            'asset_fixed': 'asset',
            'asset_current': 'asset',
            'asset_cash': 'asset',
            'asset_receivable': 'asset',
            'liability_current': 'liability',
            'liability_non_current': 'liability',
            'liability_payable': 'liability',
            'equity': 'equity',
            'income': 'income',
            'income_other': 'income',
            'expense': 'expense',
            'expense_depreciation': 'expense',
            'expense_other': 'expense',
            'off_balance': 'off_balance',
        }
        for account in self:
            account.internal_group = type_mapping.get(account.account_type, False)
    
    @api.depends('code')
    def _compute_pgc_class(self):
        for account in self:
            if account.code:
                first_digit = account.code[0] if account.code else ''
                if first_digit in '123456789':
                    account.pgc_class = first_digit
                else:
                    account.pgc_class = False
            else:
                account.pgc_class = False
    
    def _compute_balance(self):
        """Compute account balance from journal items"""
        for account in self:
            domain = [
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted')
            ]
            
            move_lines = self.env['moz.move.line'].search(domain)
            
            account.debit = sum(move_lines.mapped('debit'))
            account.credit = sum(move_lines.mapped('credit'))
            account.balance = account.debit - account.credit
    
    # Constraints
    @api.constrains('code')
    def _check_code_unique(self):
        for account in self:
            if self.search_count([
                ('code', '=', account.code),
                ('company_id', '=', account.company_id.id),
                ('id', '!=', account.id)
            ]) > 0:
                raise ValidationError(
                    _("Account code '%s' already exists!") % account.code
                )
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate account code format according to PGC-NIRF"""
        for account in self:
            if not re.match(r'^[1-9]\d{0,9}$', account.code):
                raise ValidationError(
                    _("Invalid account code format. Must start with 1-9 and contain only digits.")
                )
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(
                _("You cannot create recursive account hierarchies.")
            )
    
    @api.constrains('deprecated')
    def _check_deprecated_has_no_moves(self):
        for account in self:
            if account.deprecated:
                move_count = self.env['moz.move.line'].search_count([
                    ('account_id', '=', account.id)
                ])
                if move_count > 0:
                    raise ValidationError(
                        _("Cannot deprecate account %s as it has existing journal entries.") % account.display_name
                    )
    
    # Business Methods
    def validate_for_transaction(self) -> bool:
        """Validate if account can be used in transactions"""
        self.ensure_one()
        
        if self.deprecated:
            raise UserError(
                _("Cannot use deprecated account %s") % self.display_name
            )
        
        if self.child_ids:
            raise UserError(
                _("Cannot post to parent account %s. Use a child account instead.") % self.display_name
            )
        
        return True
    
    def get_balance_at_date(self, date: str) -> float:
        """Get account balance at specific date"""
        self.ensure_one()
        
        domain = [
            ('account_id', '=', self.id),
            ('date', '<=', date),
            ('parent_state', '=', 'posted')
        ]
        
        move_lines = self.env['moz.move.line'].search(domain)
        
        total_debit = sum(move_lines.mapped('debit'))
        total_credit = sum(move_lines.mapped('credit'))
        
        return total_debit - total_credit
    
    def get_journal_items(self, date_from: Optional[str] = None, 
                         date_to: Optional[str] = None) -> models.Model:
        """Get journal items for this account within date range"""
        self.ensure_one()
        
        domain = [('account_id', '=', self.id)]
        
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        return self.env['moz.move.line'].search(domain, order='date, id')
    
    @api.model
    def create_pgc_nirf_accounts(self) -> None:
        """Create standard PGC-NIRF chart of accounts for Mozambique"""
        
        # This method would be called during module installation
        # to create the standard chart of accounts
        # Implementation would read from data files
        pass
    
    def action_open_journal_items(self):
        """Open journal items for this account"""
        self.ensure_one()
        
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id}
        }