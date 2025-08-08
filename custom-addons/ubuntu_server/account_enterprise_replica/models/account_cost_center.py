# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountCostCenter(models.Model):
    _name = 'account.cost.center'
    _description = 'Cost Center'
    _order = 'code, name'
    
    name = fields.Char(
        string='Cost Center Name',
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
        'account.cost.center',
        string='Parent Cost Center'
    )
    
    child_ids = fields.One2many(
        'account.cost.center',
        'parent_id',
        string='Child Cost Centers'
    )
    
    type = fields.Selection([
        ('production', 'Production'),
        ('service', 'Service'),
        ('administrative', 'Administrative'),
        ('distribution', 'Distribution'),
        ('research', 'Research & Development')
    ], string='Type', default='service')
    
    allocation_method = fields.Selection([
        ('direct', 'Direct'),
        ('percentage', 'Percentage'),
        ('quantity', 'Quantity Based')
    ], string='Allocation Method', default='direct')
    
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