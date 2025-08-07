# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Entry Line"
    _order = "date desc, move_name desc, id"
    _check_company_auto = True
    _rec_name = 'display_name'

    @api.depends('name', 'account_id', 'partner_id', 'date')
    def _compute_display_name(self):
        for line in self:
            name = line.name or '/'
            if line.ref:
                name = f"{name} ({line.ref})"
            line.display_name = name

    # Link to Move
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade',
        index=True
    )
    move_name = fields.Char(
        string='Number',
        related='move_id.name',
        store=True,
        index=True
    )
    
    # Basic Fields
    name = fields.Text(string='Label', required=True, default='/')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    sequence = fields.Integer(default=10)
    ref = fields.Char(string='Reference')
    date = fields.Date(
        related='move_id.date',
        store=True,
        index=True,
        copy=False
    )
    parent_state = fields.Selection(
        related='move_id.state',
        store=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        related='move_id.journal_id',
        store=True,
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        related='move_id.company_id',
        store=True,
        index=True
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        store=True
    )
    
    # Account
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        index=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    account_internal_group = fields.Selection(
        related='account_id.internal_group'
    )
    account_type = fields.Selection(
        related='account_id.account_type'
    )
    
    # Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        index=True
    )
    
    # Amounts
    debit = fields.Monetary(
        string='Debit',
        default=0.0,
        currency_field='company_currency_id'
    )
    credit = fields.Monetary(
        string='Credit',
        default=0.0,
        currency_field='company_currency_id'
    )
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance',
        store=True,
        currency_field='company_currency_id'
    )
    amount_currency = fields.Monetary(
        string='Amount in Currency',
        help="The amount expressed in an optional other currency if it is a multi-currency entry."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Invoice Fields
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        default=1.0
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price'
    )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    
    # Subtotals for Invoice Lines
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )
    
    # Tax
    tax_ids = fields.Many2many(
        'account.tax',
        'account_move_line_account_tax_rel',
        'line_id', 'tax_id',
        string='Taxes'
    )
    tax_line_id = fields.Many2one(
        'account.tax',
        string='Tax Line',
        help="Indicates that this line is a tax line"
    )
    tax_group_id = fields.Many2one(
        'account.tax.group',
        related='tax_line_id.tax_group_id',
        store=True
    )
    tax_base_amount = fields.Monetary(
        string='Tax Base Amount',
        currency_field='company_currency_id'
    )
    tax_tag_ids = fields.Many2many(
        'account.account.tag',
        string='Tax Tags'
    )
    
    # Reconciliation
    reconciled = fields.Boolean(
        string='Reconciled',
        compute='_compute_reconciled',
        store=True
    )
    full_reconcile_id = fields.Many2one(
        'account.full.reconcile',
        string='Full Reconcile',
        index=True,
        copy=False
    )
    partial_reconcile_ids = fields.One2many(
        'account.partial.reconcile',
        'debit_move_id',
        string='Partial Reconciles'
    )
    matched_debit_ids = fields.One2many(
        'account.partial.reconcile',
        'credit_move_id',
        string='Matched Debits'
    )
    
    # Maturity
    date_maturity = fields.Date(
        string='Due Date',
        index=True
    )
    
    # Analytic
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        index=True
    )
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags'
    )
    analytic_line_ids = fields.One2many(
        'account.analytic.line',
        'move_line_id',
        string='Analytic Lines'
    )
    analytic_distribution = fields.Json(
        string='Analytic Distribution'
    )
    
    # Display Type (for invoice lines)
    display_type = fields.Selection([
        ('product', 'Product'),
        ('line_section', 'Section'),
        ('line_note', 'Note'),
        ('payment_term', 'Payment Term'),
        ('rounding', 'Rounding'),
        ('tax', 'Tax'),
    ], default='product')
    
    # Residual
    amount_residual = fields.Monetary(
        string='Residual Amount',
        compute='_compute_residual',
        store=True,
        currency_field='company_currency_id'
    )
    amount_residual_currency = fields.Monetary(
        string='Residual Amount in Currency',
        compute='_compute_residual',
        store=True,
        currency_field='currency_id'
    )
    
    # Payment
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        index=True
    )
    statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Statement Line',
        index=True
    )
    statement_id = fields.Many2one(
        'account.bank.statement',
        related='statement_line_id.statement_id',
        store=True
    )
    
    # Misc
    blocked = fields.Boolean(
        string='Blocked',
        default=False,
        help="You can block the reconciliation of this line"
    )
    is_rounding_line = fields.Boolean(
        string='Is Rounding Line',
        help="This line is a rounding difference line"
    )
    exclude_from_invoice_tab = fields.Boolean(
        string='Exclude from Invoice Tab',
        help="Technical field to exclude lines from invoice tab"
    )
    
    _sql_constraints = [
        ('check_credit_debit',
         'CHECK(credit + debit >= 0 AND credit * debit = 0)',
         'Wrong credit or debit value!'),
    ]

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids')
    def _compute_subtotal(self):
        for line in self:
            if line.display_type == 'product':
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                line.price_subtotal = price * line.quantity
                
                # Compute taxes
                if line.tax_ids:
                    taxes = line.tax_ids.compute_all(
                        price,
                        currency=line.currency_id,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=line.partner_id
                    )
                    line.price_total = taxes['total_included']
                else:
                    line.price_total = line.price_subtotal
            else:
                line.price_subtotal = 0
                line.price_total = 0

    @api.depends('full_reconcile_id', 'partial_reconcile_ids', 'matched_debit_ids')
    def _compute_reconciled(self):
        for line in self:
            line.reconciled = bool(line.full_reconcile_id)

    @api.depends('balance', 'amount_currency', 'partial_reconcile_ids', 'matched_debit_ids')
    def _compute_residual(self):
        for line in self:
            if line.account_id.reconcile:
                reconciled = 0
                reconciled_currency = 0
                
                for partial in line.partial_reconcile_ids + line.matched_debit_ids:
                    if partial.debit_move_id == line:
                        reconciled += partial.amount
                        reconciled_currency += partial.debit_amount_currency
                    else:
                        reconciled += partial.amount
                        reconciled_currency += partial.credit_amount_currency
                
                line.amount_residual = abs(line.balance) - reconciled
                line.amount_residual_currency = abs(line.amount_currency or 0) - reconciled_currency
            else:
                line.amount_residual = 0
                line.amount_residual_currency = 0

    @api.constrains('account_id', 'partner_id')
    def _check_partner_required(self):
        for line in self:
            if line.account_id.account_type in ['asset_receivable', 'liability_payable'] and not line.partner_id:
                raise ValidationError(_('A partner is required for receivable/payable accounts.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_id
            
            # Set default accounts
            if self.move_id.move_type in ['out_invoice', 'out_refund']:
                self.account_id = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id
            elif self.move_id.move_type in ['in_invoice', 'in_refund']:
                self.account_id = self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id
            
            # Set taxes
            if self.move_id.move_type in ['out_invoice', 'out_refund']:
                self.tax_ids = self.product_id.taxes_id
            elif self.move_id.move_type in ['in_invoice', 'in_refund']:
                self.tax_ids = self.product_id.supplier_taxes_id

    @api.onchange('amount_currency', 'currency_id')
    def _onchange_amount_currency(self):
        if self.currency_id and self.currency_id != self.company_currency_id:
            # Convert amount_currency to debit/credit
            amount = self.currency_id._convert(
                self.amount_currency,
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.today()
            )
            if amount > 0:
                self.debit = amount
                self.credit = 0
            else:
                self.debit = 0
                self.credit = -amount

    def reconcile(self):
        """Reconcile the lines together."""
        # Group by account and partner
        accounts = {}
        for line in self:
            if not line.account_id.reconcile:
                raise UserError(_('Account %s is not marked as reconcilable.') % line.account_id.display_name)
            key = (line.account_id.id, line.partner_id.id or False)
            if key not in accounts:
                accounts[key] = self.env['account.move.line']
            accounts[key] |= line
        
        # Reconcile each group
        for (account_id, partner_id), lines in accounts.items():
            if len(lines) < 2:
                continue
                
            # Check if can be fully reconciled
            if float_is_zero(sum(lines.mapped('balance')), precision_rounding=0.01):
                # Full reconciliation
                self.env['account.full.reconcile'].create({
                    'reconciled_line_ids': [(6, 0, lines.ids)]
                })
            else:
                # Partial reconciliation
                debit_lines = lines.filtered(lambda l: l.balance > 0)
                credit_lines = lines.filtered(lambda l: l.balance < 0)
                
                for debit_line in debit_lines:
                    for credit_line in credit_lines:
                        amount = min(abs(debit_line.amount_residual), abs(credit_line.amount_residual))
                        if amount > 0:
                            self.env['account.partial.reconcile'].create({
                                'debit_move_id': debit_line.id,
                                'credit_move_id': credit_line.id,
                                'amount': amount,
                            })

    def remove_move_reconcile(self):
        """Remove reconciliation."""
        self.partial_reconcile_ids.unlink()
        self.matched_debit_ids.unlink()
        self.full_reconcile_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set balance from debit/credit
            if 'debit' in vals and 'credit' not in vals:
                vals['credit'] = 0
            elif 'credit' in vals and 'debit' not in vals:
                vals['debit'] = 0
        
        return super().create(vals_list)

    def write(self, vals):
        # Prevent editing reconciled lines
        if any(line.reconciled for line in self):
            raise UserError(_('You cannot modify a reconciled line.'))
        
        return super().write(vals)