# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

_logger = logging.getLogger(__name__)

class MozAsset(models.Model):
    _name = 'moz.asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fixed Asset'
    _order = 'acquisition_date desc, id desc'
    
    name = fields.Char(
        string='Asset Name',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Asset Code',
        readonly=True,
        copy=False,
        index=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Closed'),
        ('sold', 'Sold'),
    ], string='State', default='draft', tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Asset Information
    category_id = fields.Many2one(
        'moz.asset.category',
        string='Category',
        required=True,
        tracking=True
    )
    
    asset_type = fields.Selection(
        related='category_id.asset_type',
        string='Asset Type',
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
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Acquisition
    acquisition_date = fields.Date(
        string='Acquisition Date',
        required=True,
        tracking=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Purchase Invoice',
        domain="[('move_type', '=', 'in_invoice')]"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        tracking=True
    )
    
    # Values
    purchase_value = fields.Monetary(
        string='Purchase Value',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    
    salvage_value = fields.Monetary(
        string='Salvage Value',
        currency_field='currency_id',
        tracking=True
    )
    
    book_value = fields.Monetary(
        string='Book Value',
        compute='_compute_book_value',
        store=True,
        currency_field='currency_id'
    )
    
    value_residual = fields.Monetary(
        string='Residual Value',
        compute='_compute_value_residual',
        store=True,
        currency_field='currency_id'
    )
    
    # Depreciation
    method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive'),
        ('degressive_then_linear', 'Degressive then Linear'),
    ], string='Depreciation Method', required=True, default='linear', tracking=True)
    
    method_number = fields.Integer(
        string='Number of Years',
        default=5,
        help='Number of years for depreciation'
    )
    
    method_period = fields.Selection([
        ('1', 'Monthly'),
        ('3', 'Quarterly'),
        ('12', 'Yearly'),
    ], string='Period', default='12', required=True)
    
    method_progress_factor = fields.Float(
        string='Degressive Factor',
        default=0.3
    )
    
    depreciation_line_ids = fields.One2many(
        'moz.asset.depreciation.line',
        'asset_id',
        string='Depreciation Lines'
    )
    
    # Accounting
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
        tracking=True
    )
    
    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Depreciation Account',
        required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
        tracking=True
    )
    
    account_depreciation_expense_id = fields.Many2one(
        'account.account',
        string='Depreciation Expense Account',
        required=True,
        domain="[('account_type', '=', 'expense_depreciation')]",
        tracking=True
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'general')]"
    )
    
    # Analytics
    analytic_account_id = fields.Many2one(
        'moz.analytic.account',
        string='Analytic Account'
    )
    
    analytic_tag_ids = fields.Many2many(
        'moz.analytic.tag',
        string='Analytic Tags'
    )
    
    # Disposal
    disposal_date = fields.Date(
        string='Disposal Date'
    )
    
    disposal_move_id = fields.Many2one(
        'account.move',
        string='Disposal Entry',
        readonly=True
    )
    
    sale_value = fields.Monetary(
        string='Sale Value',
        currency_field='currency_id'
    )
    
    # Computed totals
    depreciated_value = fields.Monetary(
        string='Depreciated Value',
        compute='_compute_depreciation_values',
        store=True,
        currency_field='currency_id'
    )
    
    total_depreciation = fields.Monetary(
        string='Total Depreciation',
        compute='_compute_depreciation_values',
        store=True,
        currency_field='currency_id'
    )
    
    # Additional info
    note = fields.Text(
        string='Notes'
    )
    
    serial_number = fields.Char(
        string='Serial Number'
    )
    
    model = fields.Char(
        string='Model'
    )
    
    location = fields.Char(
        string='Location'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Responsible Employee'
    )
    
    @api.depends('purchase_value', 'salvage_value', 'depreciation_line_ids.depreciation_value')
    def _compute_book_value(self):
        for asset in self:
            depreciated = sum(line.depreciation_value for line in asset.depreciation_line_ids if line.move_id)
            asset.book_value = asset.purchase_value - depreciated
    
    @api.depends('book_value', 'salvage_value')
    def _compute_value_residual(self):
        for asset in self:
            asset.value_residual = asset.book_value - asset.salvage_value
    
    @api.depends('depreciation_line_ids.depreciation_value', 'depreciation_line_ids.move_id')
    def _compute_depreciation_values(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered('move_id')
            asset.depreciated_value = sum(posted_lines.mapped('depreciation_value'))
            asset.total_depreciation = sum(asset.depreciation_line_ids.mapped('depreciation_value'))
    
    @api.model
    def create(self, vals):
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('moz.asset') or 'New'
        
        # Set accounting fields from category if not provided
        if 'category_id' in vals and vals['category_id']:
            category = self.env['moz.asset.category'].browse(vals['category_id'])
            if not vals.get('account_asset_id'):
                vals['account_asset_id'] = category.account_asset_id.id
            if not vals.get('account_depreciation_id'):
                vals['account_depreciation_id'] = category.account_depreciation_id.id
            if not vals.get('account_depreciation_expense_id'):
                vals['account_depreciation_expense_id'] = category.account_depreciation_expense_id.id
            if not vals.get('journal_id'):
                vals['journal_id'] = category.journal_id.id
            if not vals.get('method'):
                vals['method'] = category.method
            if not vals.get('method_number'):
                vals['method_number'] = category.method_number
            if not vals.get('method_period'):
                vals['method_period'] = category.method_period
        
        return super().create(vals)
    
    def action_validate(self):
        """Validate asset and create depreciation lines"""
        for asset in self:
            if asset.state != 'draft':
                raise UserError(_('Only draft assets can be validated.'))
            
            # Create depreciation lines
            asset._compute_depreciation_lines()
            
            asset.state = 'open'
        
        return True
    
    def action_set_to_close(self):
        """Close the asset"""
        for asset in self:
            if asset.state != 'open':
                raise UserError(_('Only running assets can be closed.'))
            
            # Cancel remaining depreciation lines
            remaining_lines = asset.depreciation_line_ids.filtered(lambda l: not l.move_id)
            remaining_lines.unlink()
            
            asset.state = 'close'
        
        return True
    
    def action_sell(self):
        """Sell the asset"""
        self.ensure_one()
        
        if self.state != 'open':
            raise UserError(_('Only running assets can be sold.'))
        
        return {
            'name': _('Sell Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.asset.sell.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_sale_value': self.book_value,
            }
        }
    
    def _compute_depreciation_lines(self):
        """Compute depreciation lines"""
        self.ensure_one()
        
        # Clear existing unposted lines
        self.depreciation_line_ids.filtered(lambda l: not l.move_id).unlink()
        
        if self.value_residual == 0:
            return
        
        amount_to_depreciate = self.purchase_value - self.salvage_value
        depreciation_date = self.acquisition_date
        
        # Already depreciated amount
        already_depreciated = sum(
            line.depreciation_value 
            for line in self.depreciation_line_ids.filtered('move_id')
        )
        
        amount_to_depreciate -= already_depreciated
        
        if self.method == 'linear':
            amount = amount_to_depreciate / self.method_number
            
            for i in range(self.method_number):
                if int(self.method_period) == 1:
                    depreciation_date = depreciation_date + relativedelta(months=1)
                elif int(self.method_period) == 3:
                    depreciation_date = depreciation_date + relativedelta(months=3)
                else:
                    depreciation_date = depreciation_date + relativedelta(years=1)
                
                remaining_value = amount_to_depreciate - (amount * (i + 1))
                
                self.env['moz.asset.depreciation.line'].create({
                    'asset_id': self.id,
                    'sequence': i + 1,
                    'depreciation_date': depreciation_date,
                    'depreciation_value': amount,
                    'remaining_value': remaining_value,
                })
        
        elif self.method == 'degressive':
            amount = amount_to_depreciate * self.method_progress_factor
            
            for i in range(self.method_number):
                if int(self.method_period) == 1:
                    depreciation_date = depreciation_date + relativedelta(months=1)
                elif int(self.method_period) == 3:
                    depreciation_date = depreciation_date + relativedelta(months=3)
                else:
                    depreciation_date = depreciation_date + relativedelta(years=1)
                
                if i == self.method_number - 1:
                    amount = amount_to_depreciate
                
                amount_to_depreciate -= amount
                
                self.env['moz.asset.depreciation.line'].create({
                    'asset_id': self.id,
                    'sequence': i + 1,
                    'depreciation_date': depreciation_date,
                    'depreciation_value': amount,
                    'remaining_value': amount_to_depreciate,
                })
                
                amount = amount_to_depreciate * self.method_progress_factor
    
    @api.model
    def _cron_generate_entries(self):
        """Cron job to generate depreciation entries"""
        # Find assets with depreciation lines to post
        assets = self.search([('state', '=', 'open')])
        
        for asset in assets:
            lines_to_post = asset.depreciation_line_ids.filtered(
                lambda l: not l.move_id and l.depreciation_date <= fields.Date.today()
            )
            
            for line in lines_to_post:
                try:
                    line.create_move()
                except Exception as e:
                    _logger.error(f"Failed to create depreciation entry for asset {asset.name}: {e}")
    
    def action_view_depreciation_lines(self):
        """View depreciation lines"""
        self.ensure_one()
        return {
            'name': _('Depreciation Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.asset.depreciation.line',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }