# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountConsolidationRate(models.Model):
    _name = 'account.consolidation.rate'
    _description = 'Consolidation Currency Rate'
    _order = 'date desc'
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )
    
    rate_type = fields.Selection([
        ('closing', 'Closing Rate'),
        ('average', 'Average Rate'),
        ('historical', 'Historical Rate')
    ], string='Rate Type', required=True, default='closing')
    
    rate = fields.Float(
        string='Rate',
        digits=(16, 6),
        required=True,
        default=1.0
    )
    
    inverse_rate = fields.Float(
        string='Inverse Rate',
        digits=(16, 6),
        compute='_compute_inverse_rate',
        store=True
    )
    
    @api.depends('rate')
    def _compute_inverse_rate(self):
        for record in self:
            if record.rate:
                record.inverse_rate = 1.0 / record.rate
            else:
                record.inverse_rate = 0.0