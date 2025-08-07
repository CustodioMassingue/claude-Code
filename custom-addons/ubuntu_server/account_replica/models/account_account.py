# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class AccountAccount(models.Model):
    _name = "account.account"
    _description = "Account"
    _order = "code, name"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _check_company_auto = True

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for account in self:
            name = account.name
            if account.code:
                name = f"{account.code} - {account.name}"
            account.display_name = name

    @api.depends('move_line_ids', 'move_line_ids.amount_currency', 'move_line_ids.debit', 'move_line_ids.credit')
    def _compute_balance(self):
        for account in self:
            balance = 0.0
            for line in account.move_line_ids:
                balance += line.debit - line.credit
            account.balance = balance

    # Basic Fields
    name = fields.Char(
        string="Account Name",
        required=True,
        index=True,
        tracking=True
    )
    code = fields.Char(
        string="Code",
        size=64,
        required=True,
        index=True,
        tracking=True
    )
    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Account Currency',
        help="Forces all journal items in this account to have a specific currency."
    )
    
    # Type and Classification
    account_type = fields.Selection([
        # Balance Sheet
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        
        # Profit & Loss
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_direct_cost', 'Cost of Revenue'),
        
        # Off Balance
        ('off_balance', 'Off-Balance Sheet'),
    ], string="Account Type", required=True, tracking=True,
        help="Account Type determines the nature of the account and is used in reports.")
    
    internal_group = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('off_balance', 'Off Balance'),
    ], string="Internal Group", compute='_compute_internal_group', store=True)
    
    # Legacy fields for compatibility (will be computed from account_type)
    user_type_id = fields.Many2one(
        'account.account.type',
        string='Account Type',
        compute='_compute_user_type_id',
        store=True,
        help='Compatibility field - computed from account_type selection'
    )
    internal_type = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'), 
        ('liquidity', 'Liquidity'),
        ('other', 'Regular'),
    ], string='Internal Type', compute='_compute_internal_type', store=True)
    
    # Root account field for hierarchy  
    root_id = fields.Many2one(
        'account.account', 
        string='Root Account',
        compute='_compute_root_id',
        store=True
    )
    
    # Configuration
    reconcile = fields.Boolean(
        string='Allow Reconciliation',
        default=False,
        tracking=True,
        help="Check this box if this account allows invoices & payments matching of journal items."
    )
    deprecated = fields.Boolean(
        string='Deprecated',
        default=False,
        tracking=True,
        help="Check this to deprecate the account and prevent its use in transactions."
    )
    tax_ids = fields.Many2many(
        'account.tax',
        'account_account_tax_default_rel',
        'account_id', 'tax_id',
        string='Default Taxes'
    )
    note = fields.Text('Internal Notes')
    
    # Group and Tags
    group_id = fields.Many2one(
        'account.group',
        string='Group',
        index=True
    )
    tag_ids = fields.Many2many(
        'account.account.tag',
        'account_account_tag_rel',
        'account_id', 'tag_id',
        string='Tags'
    )
    
    # Allowed Journals
    allowed_journal_ids = fields.Many2many(
        'account.journal',
        'account_journal_account_rel',
        'account_id', 'journal_id',
        string='Allowed Journals'
    )
    
    # Opening Balance
    opening_debit = fields.Monetary(
        string="Opening Debit",
        compute='_compute_opening_balance',
        inverse='_set_opening_balance',
        currency_field='company_currency_id'
    )
    opening_credit = fields.Monetary(
        string="Opening Credit",
        compute='_compute_opening_balance',
        inverse='_set_opening_balance',
        currency_field='company_currency_id'
    )
    opening_balance = fields.Monetary(
        string="Opening Balance",
        compute='_compute_opening_balance',
        inverse='_set_opening_balance',
        currency_field='company_currency_id'
    )
    
    # Computed Balance
    balance = fields.Monetary(
        string="Balance",
        compute='_compute_balance',
        currency_field='company_currency_id'
    )
    
    # Related Fields
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string="Company Currency",
        readonly=True
    )
    move_line_ids = fields.One2many(
        'account.move.line',
        'account_id',
        string='Journal Items'
    )
    move_line_count = fields.Integer(
        'Journal Items Count',
        compute='_compute_move_lines_count'
    )
    
    # Hierarchy
    parent_id = fields.Many2one(
        'account.account',
        string='Parent Account',
        ondelete='cascade'
    )
    child_ids = fields.One2many(
        'account.account',
        'parent_id',
        string='Child Accounts'
    )
    
    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'The account code must be unique per company!'),
    ]

    @api.depends('account_type')
    def _compute_internal_group(self):
        for account in self:
            if account.account_type:
                if account.account_type in ['asset_receivable', 'asset_cash', 'asset_current', 
                                           'asset_non_current', 'asset_prepayments', 'asset_fixed']:
                    account.internal_group = 'asset'
                elif account.account_type in ['liability_payable', 'liability_credit_card', 
                                             'liability_current', 'liability_non_current']:
                    account.internal_group = 'liability'
                elif account.account_type in ['equity', 'equity_unaffected']:
                    account.internal_group = 'equity'
                elif account.account_type in ['income', 'income_other']:
                    account.internal_group = 'income'
                elif account.account_type in ['expense', 'expense_depreciation', 'expense_direct_cost']:
                    account.internal_group = 'expense'
                else:
                    account.internal_group = 'off_balance'

    @api.depends('account_type')
    def _compute_user_type_id(self):
        """Compute compatibility field user_type_id from account_type selection."""
        for account in self:
            # Try to find existing account type or create/find default
            if account.account_type:
                account_type = self.env['account.account.type'].search([
                    ('type', '=', account.account_type)
                ], limit=1)
                if not account_type:
                    # Create default account type if it doesn't exist
                    account_type = self.env['account.account.type'].create({
                        'name': dict(account._fields['account_type'].selection)[account.account_type],
                        'type': account.account_type,
                        'internal_group': account.internal_group or 'other',
                    })
                account.user_type_id = account_type
            else:
                account.user_type_id = False

    @api.depends('account_type')
    def _compute_internal_type(self):
        """Compute internal_type from account_type for compatibility."""
        for account in self:
            if account.account_type == 'asset_receivable':
                account.internal_type = 'receivable'
            elif account.account_type == 'liability_payable':
                account.internal_type = 'payable'
            elif account.account_type in ['asset_cash', 'liability_credit_card']:
                account.internal_type = 'liquidity'
            else:
                account.internal_type = 'other'

    @api.depends('parent_id')
    def _compute_root_id(self):
        """Compute the root account in hierarchy."""
        for account in self:
            current = account
            while current.parent_id:
                current = current.parent_id
            account.root_id = current if current != account else False

    @api.depends('move_line_ids')
    def _compute_move_lines_count(self):
        for account in self:
            account.move_line_count = len(account.move_line_ids)

    @api.depends('move_line_ids', 'move_line_ids.debit', 'move_line_ids.credit')
    def _compute_opening_balance(self):
        for account in self:
            opening_lines = account.move_line_ids.filtered(lambda l: l.move_id.is_opening)
            account.opening_debit = sum(opening_lines.mapped('debit'))
            account.opening_credit = sum(opening_lines.mapped('credit'))
            account.opening_balance = account.opening_debit - account.opening_credit

    def _set_opening_balance(self):
        """Create or update opening journal entries."""
        for account in self:
            if account.opening_balance:
                # Implementation to create opening entries
                pass

    @api.constrains('account_type', 'reconcile')
    def _check_reconcile(self):
        for account in self:
            if account.account_type in ['asset_cash', 'liability_credit_card'] and not account.reconcile:
                raise ValidationError(_('Bank and credit card accounts must allow reconciliation.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'code' in vals:
                vals['code'] = vals['code'].strip()
        return super().create(vals_list)

    def write(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].strip()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_check(self):
        if self.move_line_ids:
            raise UserError(_('You cannot delete an account that has journal items.'))

    def action_open_journal_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items'),
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def mark_as_reconciled(self):
        return self.write({'reconcile': True})

    def mark_as_unreconciled(self):
        return self.write({'reconcile': False})


class AccountGroup(models.Model):
    _name = "account.group"
    _description = "Account Group"
    _order = "code_prefix_start"
    _rec_name = 'display_name'

    @api.depends('name', 'code_prefix_start', 'code_prefix_end')
    def _compute_display_name(self):
        for group in self:
            prefix = group.code_prefix_start
            if group.code_prefix_end:
                prefix = f"{group.code_prefix_start} - {group.code_prefix_end}"
            group.display_name = f"{prefix} {group.name}"

    name = fields.Char(required=True)
    code_prefix_start = fields.Char(string='Prefix From', required=True)
    code_prefix_end = fields.Char(string='Prefix To')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    parent_id = fields.Many2one('account.group', string='Parent Group', ondelete='cascade')
    child_ids = fields.One2many('account.group', 'parent_id', string='Child Groups')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    account_ids = fields.One2many('account.account', 'group_id', string='Accounts')

    _sql_constraints = [
        ('code_prefix_company_uniq', 
         'unique (code_prefix_start, code_prefix_end, company_id)',
         'The code prefix must be unique per company!')
    ]


class AccountAccountTag(models.Model):
    _name = "account.account.tag"
    _description = "Account Tag"

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer('Color Index', default=0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company')
    country_id = fields.Many2one('res.country', string='Country')
    applicability = fields.Selection([
        ('accounts', 'Accounts'),
        ('taxes', 'Taxes'),
        ('products', 'Products'),
    ], string='Applicability', default='accounts', required=True)
    tax_negate = fields.Boolean(
        string="Negate Tax Balance",
        help="Check this box to negate the balance of the tax report lines associated with this tag."
    )