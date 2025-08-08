# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountBusinessSegment(models.Model):
    _name = 'account.business.segment'
    _description = 'Business Segment'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Segment Name',
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
    
    description = fields.Text(
        string='Description'
    )
    
    segment_type = fields.Selection([
        ('geographic', 'Geographic'),
        ('product', 'Product Line'),
        ('customer', 'Customer Type'),
        ('channel', 'Distribution Channel'),
        ('other', 'Other')
    ], string='Segment Type', default='product')
    
    parent_id = fields.Many2one(
        'account.business.segment',
        string='Parent Segment'
    )
    
    child_ids = fields.One2many(
        'account.business.segment',
        'parent_id',
        string='Child Segments'
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