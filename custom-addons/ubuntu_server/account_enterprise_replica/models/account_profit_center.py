# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountProfitCenter(models.Model):
    _name = 'account.profit.center'
    _description = 'Profit Center'
    _order = 'code, name'
    
    name = fields.Char(
        string='Profit Center Name',
        required=True
    )
    
    code = fields.Char(
        string='Code',
        required=True
    )
    
    description = fields.Text(
        string='Description'
    )
    
    manager_id = fields.Many2one(
        'res.users',
        string='Manager'
    )
    
    parent_id = fields.Many2one(
        'account.profit.center',
        string='Parent Profit Center'
    )
    
    child_ids = fields.One2many(
        'account.profit.center',
        'parent_id',
        string='Child Profit Centers'
    )
    
    target_revenue = fields.Monetary(
        string='Target Revenue',
        currency_field='currency_id'
    )
    
    target_profit = fields.Monetary(
        string='Target Profit',
        currency_field='currency_id'
    )
    
    actual_revenue = fields.Monetary(
        string='Actual Revenue',
        currency_field='currency_id',
        compute='_compute_actuals'
    )
    
    actual_profit = fields.Monetary(
        string='Actual Profit',
        currency_field='currency_id',
        compute='_compute_actuals'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    def _compute_actuals(self):
        for center in self:
            center.actual_revenue = 0.0
            center.actual_profit = 0.0