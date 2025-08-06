# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MozAssetCategory(models.Model):
    _name = 'moz.asset.category'
    _description = 'Asset Category'
    _order = 'name'
    
    name = fields.Char(
        string='Category Name',
        required=True
    )
    
    code = fields.Char(
        string='Category Code'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    asset_type = fields.Selection([
        ('tangible', 'Tangible Assets'),
        ('intangible', 'Intangible Assets'),
        ('land', 'Land'),
        ('building', 'Buildings'),
        ('equipment', 'Equipment'),
        ('vehicle', 'Vehicles'),
        ('computer', 'Computer Equipment'),
        ('furniture', 'Furniture'),
        ('other', 'Other'),
    ], string='Asset Type', default='tangible', required=True)
    
    # Depreciation
    method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive'),
        ('degressive_then_linear', 'Degressive then Linear'),
    ], string='Depreciation Method', default='linear', required=True)
    
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
    
    # Accounting
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        required=True,
        domain="[('account_type', '=', 'asset_fixed')]"
    )
    
    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Depreciation Account',
        required=True,
        domain="[('account_type', '=', 'asset_fixed')]"
    )
    
    account_depreciation_expense_id = fields.Many2one(
        'account.account',
        string='Depreciation Expense Account',
        required=True,
        domain="[('account_type', '=', 'expense_depreciation')]"
    )
    
    account_gains_id = fields.Many2one(
        'account.account',
        string='Capital Gains Account',
        domain="[('account_type', '=', 'income_other')]"
    )
    
    account_losses_id = fields.Many2one(
        'account.account',
        string='Capital Losses Account',
        domain="[('account_type', '=', 'expense')]"
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
    
    # Statistics
    asset_ids = fields.One2many(
        'moz.asset',
        'category_id',
        string='Assets'
    )
    
    asset_count = fields.Integer(
        string='Asset Count',
        compute='_compute_asset_count'
    )
    
    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for category in self:
            category.asset_count = len(category.asset_ids)
    
    def action_view_assets(self):
        """View assets in this category"""
        self.ensure_one()
        return {
            'name': _('Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.asset',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id}
        }