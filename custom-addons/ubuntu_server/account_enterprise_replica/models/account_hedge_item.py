# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountHedgeItem(models.Model):
    _name = 'account.hedge.item'
    _description = 'Hedge Item'
    _order = 'name'
    
    name = fields.Char(
        string='Hedge Item',
        required=True
    )
    
    hedge_type = fields.Selection([
        ('fair_value', 'Fair Value Hedge'),
        ('cash_flow', 'Cash Flow Hedge'),
        ('net_investment', 'Net Investment Hedge')
    ], string='Hedge Type', required=True)
    
    hedged_item = fields.Text(
        string='Hedged Item Description'
    )
    
    hedge_instrument = fields.Text(
        string='Hedge Instrument'
    )
    
    inception_date = fields.Date(
        string='Inception Date',
        required=True
    )
    
    maturity_date = fields.Date(
        string='Maturity Date'
    )
    
    notional_amount = fields.Monetary(
        string='Notional Amount',
        currency_field='currency_id'
    )
    
    fair_value = fields.Monetary(
        string='Fair Value',
        currency_field='currency_id'
    )
    
    effectiveness = fields.Float(
        string='Effectiveness %',
        digits=(5, 2)
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
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ], string='Status', default='draft')
    
    active = fields.Boolean(
        string='Active',
        default=True
    )