# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountConsolidationEliminationRule(models.Model):
    _name = 'account.consolidation.elimination.rule'
    _description = 'Consolidation Elimination Rule'
    _order = 'sequence, id'
    
    name = fields.Char(
        string='Rule Name',
        required=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    rule_type = fields.Selection([
        ('intercompany_revenue', 'Intercompany Revenue'),
        ('intercompany_expense', 'Intercompany Expense'),
        ('intercompany_payable', 'Intercompany Payable'),
        ('intercompany_receivable', 'Intercompany Receivable'),
        ('intercompany_investment', 'Intercompany Investment'),
        ('intercompany_dividend', 'Intercompany Dividend'),
        ('custom', 'Custom Rule')
    ], string='Rule Type', required=True)
    
    debit_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Debit Account',
        required=True
    )
    
    credit_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Credit Account',
        required=True
    )
    
    elimination_percentage = fields.Float(
        string='Elimination %',
        digits=(5, 2),
        default=100.0
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_from_id = fields.Many2one(
        'res.company',
        string='From Company'
    )
    
    company_to_id = fields.Many2one(
        'res.company',
        string='To Company'
    )
    
    notes = fields.Text(
        string='Notes'
    )