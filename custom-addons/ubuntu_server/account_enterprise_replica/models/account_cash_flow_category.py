# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountCashFlowCategory(models.Model):
    _name = 'account.cash.flow.category'
    _description = 'Cash Flow Category'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Category Name',
        required=True
    )
    
    code = fields.Char(
        string='Code',
        required=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    category_type = fields.Selection([
        ('operating', 'Operating Activities'),
        ('investing', 'Investing Activities'),
        ('financing', 'Financing Activities')
    ], string='Category Type', required=True, default='operating')
    
    sign = fields.Selection([
        ('positive', 'Positive (Inflow)'),
        ('negative', 'Negative (Outflow)')
    ], string='Sign', required=True, default='positive')
    
    parent_id = fields.Many2one(
        'account.cash.flow.category',
        string='Parent Category'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )