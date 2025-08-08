# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountConsolidationAccount(models.Model):
    _name = 'account.consolidation.account'
    _description = 'Consolidation Account'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'code'
    
    name = fields.Char(
        string='Account Name',
        required=True,
        index=True
    )
    
    code = fields.Char(
        string='Account Code',
        required=True,
        index=True
    )
    
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    company_id = fields.Many2one(
        related='chart_id.company_id',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='chart_id.currency_id',
        store=True
    )
    
    # ==================== Account Type ====================
    
    account_type = fields.Selection([
        # Assets
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        # Liabilities
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        # Equity
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        # Income
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        # Expense
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_direct_cost', 'Cost of Revenue'),
        # Off Balance
        ('off_balance', 'Off-Balance Sheet'),
    ], string='Type', required=True, index=True)
    
    # ==================== Hierarchy ====================
    
    parent_id = fields.Many2one(
        'account.consolidation.account',
        string='Parent Account',
        index=True,
        ondelete='cascade',
        domain="[('chart_id', '=', chart_id)]"
    )
    
    parent_path = fields.Char(index=True, unaccent=False)
    
    child_ids = fields.One2many(
        'account.consolidation.account',
        'parent_id',
        string='Child Accounts'
    )
    
    # ==================== Currency Mode ====================
    
    currency_mode = fields.Selection([
        ('end', 'End Rate'),
        ('avg', 'Average Rate'),
        ('hist', 'Historical Rate')
    ], string='Currency Translation', default='end', required=True,
       help='Method for currency translation in consolidation')
    
    # ==================== Balances ====================
    
    balance = fields.Monetary(
        string='Balance',
        currency_field='currency_id',
        compute='_compute_balance',
        store=True
    )
    
    debit = fields.Monetary(
        string='Debit',
        currency_field='currency_id',
        compute='_compute_balance',
        store=True
    )
    
    credit = fields.Monetary(
        string='Credit',
        currency_field='currency_id',
        compute='_compute_balance',
        store=True
    )
    
    # ==================== Consolidation Settings ====================
    
    exclude_from_consolidation = fields.Boolean(
        string='Exclude from Consolidation',
        default=False
    )
    
    use_historical_rates = fields.Boolean(
        string='Use Historical Rates',
        default=False
    )
    
    mapped_account_ids = fields.One2many(
        'account.consolidation.mapping',
        'consolidation_account_id',
        string='Mapped Subsidiary Accounts'
    )
    
    # ==================== Analytics ====================
    
    analytic_distribution = fields.Json(
        string='Analytic Distribution'
    )
    
    tag_ids = fields.Many2many(
        'account.consolidation.tag',
        'account_consolidation_account_tag_rel',
        'account_id',
        'tag_id',
        string='Tags'
    )
    
    # ==================== Methods ====================
    
    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for account in self:
            account.complete_name = f"[{account.code}] {account.name}"
    
    @api.depends('mapped_account_ids', 'child_ids')
    def _compute_balance(self):
        """Compute consolidated balance from mapped accounts"""
        for account in self:
            # Get all consolidation move lines for this account
            lines = self.env['account.consolidation.move.line'].search([
                ('account_id', '=', account.id)
            ])
            
            account.debit = sum(lines.mapped('debit'))
            account.credit = sum(lines.mapped('credit'))
            account.balance = account.debit - account.credit
            
            # Add child account balances if hierarchical
            if account.child_ids:
                for child in account.child_ids:
                    account.balance += child.balance
                    account.debit += child.debit
                    account.credit += child.credit
    
    @api.constrains('code', 'chart_id')
    def _check_code_unique(self):
        for account in self:
            if self.search_count([
                ('code', '=', account.code),
                ('chart_id', '=', account.chart_id.id),
                ('id', '!=', account.id)
            ]) > 0:
                raise ValidationError(
                    _('Account code %s already exists in this chart!') % account.code
                )
    
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive accounts.'))
    
    def name_get(self):
        result = []
        for account in self:
            name = f"[{account.code}] {account.name}"
            result.append((account.id, name))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()


class AccountConsolidationMapping(models.Model):
    _name = 'account.consolidation.mapping'
    _description = 'Account Consolidation Mapping'
    _rec_name = 'consolidation_account_id'
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    consolidation_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Consolidation Account',
        required=True,
        domain="[('chart_id', '=', chart_id)]"
    )
    
    subsidiary_account_id = fields.Many2one(
        'account.account',
        string='Subsidiary Account',
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )
    
    active = fields.Boolean(
        default=True
    )
    
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='consolidation_account_id.currency_id'
    )
    
    @api.depends('subsidiary_account_id')
    def _compute_balance(self):
        for mapping in self:
            # Get balance from subsidiary account
            if mapping.subsidiary_account_id:
                mapping.balance = mapping.subsidiary_account_id.current_balance
            else:
                mapping.balance = 0.0
    
    @api.constrains('subsidiary_account_id', 'company_id', 'chart_id')
    def _check_unique_mapping(self):
        for mapping in self:
            if self.search_count([
                ('subsidiary_account_id', '=', mapping.subsidiary_account_id.id),
                ('company_id', '=', mapping.company_id.id),
                ('chart_id', '=', mapping.chart_id.id),
                ('id', '!=', mapping.id)
            ]) > 0:
                raise ValidationError(
                    _('This subsidiary account is already mapped in this chart!')
                )


class AccountConsolidationTag(models.Model):
    _name = 'account.consolidation.tag'
    _description = 'Consolidation Account Tag'
    
    name = fields.Char(
        string='Tag Name',
        required=True
    )
    
    color = fields.Integer(
        string='Color Index'
    )
    
    active = fields.Boolean(
        default=True
    )
    
    applicability = fields.Selection([
        ('accounts', 'Accounts'),
        ('taxes', 'Taxes'),
        ('products', 'Products'),
        ('all', 'All')
    ], string='Applicability', default='accounts', required=True)