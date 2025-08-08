# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountCashFlowForecastLine(models.Model):
    _name = 'account.cash.flow.forecast.line'
    _description = 'Cash Flow Forecast Line'
    _order = 'date, sequence'
    
    forecast_id = fields.Many2one(
        'account.cash.flow.forecast',
        string='Forecast',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    name = fields.Char(
        string='Description',
        required=True
    )
    
    date = fields.Date(
        string='Date',
        required=True
    )
    
    category_id = fields.Many2one(
        'account.cash.flow.category',
        string='Category',
        required=True
    )
    
    flow_type = fields.Selection([
        ('inflow', 'Cash Inflow'),
        ('outflow', 'Cash Outflow')
    ], string='Flow Type', required=True)
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='forecast_id.currency_id',
        store=True
    )
    
    probability = fields.Float(
        string='Probability %',
        digits=(5, 2),
        default=100.0
    )
    
    weighted_amount = fields.Monetary(
        string='Weighted Amount',
        compute='_compute_weighted_amount',
        store=True,
        currency_field='currency_id'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Account'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Related Entry'
    )
    
    payment_id = fields.Many2one(
        'account.payment',
        string='Related Payment'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    @api.depends('amount', 'probability')
    def _compute_weighted_amount(self):
        for line in self:
            line.weighted_amount = line.amount * (line.probability / 100.0)