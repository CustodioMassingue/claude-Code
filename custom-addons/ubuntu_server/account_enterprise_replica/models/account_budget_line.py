# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class AccountBudgetLine(models.Model):
    _name = 'account.budget.line'
    _description = 'Budget Line'
    _order = 'date_from, name'
    
    name = fields.Char(
        string='Budget Line',
        required=True
    )
    
    budget_id = fields.Many2one(
        'account.budget.management',
        string='Budget',
        required=True,
        ondelete='cascade'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    
    date_from = fields.Date(
        string='Start Date',
        required=True
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True
    )
    
    planned_amount = fields.Monetary(
        string='Planned Amount',
        currency_field='currency_id',
        required=True
    )
    
    practical_amount = fields.Monetary(
        string='Practical Amount',
        compute='_compute_practical_amount',
        currency_field='currency_id'
    )
    
    theoretical_amount = fields.Monetary(
        string='Theoretical Amount',
        compute='_compute_theoretical_amount',
        currency_field='currency_id'
    )
    
    percentage = fields.Float(
        string='Achievement',
        compute='_compute_percentage'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.currency_id',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        related='budget_id.company_id',
        store=True
    )
    
    @api.depends('planned_amount')
    def _compute_practical_amount(self):
        for line in self:
            # Calculate actual spent amount
            line.practical_amount = 0.0
    
    @api.depends('planned_amount', 'date_from', 'date_to')
    def _compute_theoretical_amount(self):
        for line in self:
            # Calculate theoretical amount based on time elapsed
            if line.date_from and line.date_to:
                today = date.today()
                if today <= line.date_from:
                    line.theoretical_amount = 0.0
                elif today >= line.date_to:
                    line.theoretical_amount = line.planned_amount
                else:
                    total_days = (line.date_to - line.date_from).days
                    elapsed_days = (today - line.date_from).days
                    line.theoretical_amount = line.planned_amount * elapsed_days / total_days
            else:
                line.theoretical_amount = 0.0
    
    @api.depends('practical_amount', 'planned_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount:
                line.percentage = (line.practical_amount / line.planned_amount) * 100
            else:
                line.percentage = 0.0