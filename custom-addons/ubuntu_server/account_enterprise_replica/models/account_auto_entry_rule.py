# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountAutoEntryRule(models.Model):
    _name = 'account.auto.entry.rule'
    _description = 'Automatic Entry Rule'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Rule Name',
        required=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    rule_type = fields.Selection([
        ('accrual', 'Accrual'),
        ('prepaid', 'Prepaid Expense'),
        ('depreciation', 'Depreciation'),
        ('allocation', 'Cost Allocation'),
        ('revaluation', 'Currency Revaluation'),
        ('custom', 'Custom')
    ], string='Rule Type', required=True, default='accrual')
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Source Account',
        required=True
    )
    
    dest_account_id = fields.Many2one(
        'account.account',
        string='Destination Account',
        required=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Frequency', default='monthly')
    
    next_run_date = fields.Date(
        string='Next Run Date'
    )
    
    last_run_date = fields.Date(
        string='Last Run Date'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )