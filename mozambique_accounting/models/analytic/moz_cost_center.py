# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MozCostCenter(models.Model):
    _name = 'moz.cost.center'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cost Center'
    _order = 'code, name'
    _rec_name = 'display_name'
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        index=True
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Type
    cost_type = fields.Selection([
        ('production', 'Production'),
        ('administration', 'Administration'),
        ('sales', 'Sales'),
        ('rd', 'Research & Development'),
        ('support', 'Support'),
        ('other', 'Other'),
    ], string='Type', default='other', required=True, tracking=True)
    
    # Hierarchy
    parent_id = fields.Many2one(
        'moz.cost.center',
        string='Parent Cost Center',
        tracking=True
    )
    
    child_ids = fields.One2many(
        'moz.cost.center',
        'parent_id',
        string='Child Cost Centers'
    )
    
    # Manager
    manager_id = fields.Many2one(
        'res.users',
        string='Manager',
        tracking=True
    )
    
    member_ids = fields.Many2many(
        'res.users',
        'moz_cost_center_users_rel',
        'cost_center_id',
        'user_id',
        string='Members'
    )
    
    # Budget
    budget_amount = fields.Monetary(
        string='Annual Budget',
        currency_field='currency_id',
        tracking=True
    )
    
    budget_ids = fields.One2many(
        'moz.cost.center.budget',
        'cost_center_id',
        string='Budget Lines'
    )
    
    # Allocation
    allocation_method = fields.Selection([
        ('direct', 'Direct'),
        ('percentage', 'Percentage'),
        ('usage', 'Usage Based'),
        ('headcount', 'Headcount'),
    ], string='Allocation Method', default='direct')
    
    allocation_percentage = fields.Float(
        string='Allocation %',
        default=100.0
    )
    
    # Analytics
    analytic_account_id = fields.Many2one(
        'moz.analytic.account',
        string='Analytic Account'
    )
    
    line_ids = fields.One2many(
        'moz.analytic.line',
        'cost_center_id',
        string='Analytic Lines'
    )
    
    # Computed fields
    total_cost = fields.Monetary(
        string='Total Cost',
        compute='_compute_total_cost',
        currency_field='currency_id'
    )
    
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_total_revenue',
        currency_field='currency_id'
    )
    
    profit_loss = fields.Monetary(
        string='Profit/Loss',
        compute='_compute_profit_loss',
        currency_field='currency_id'
    )
    
    budget_consumed = fields.Float(
        string='Budget Consumed (%)',
        compute='_compute_budget_consumed'
    )
    
    @api.depends('code', 'name')
    def _compute_display_name(self):
        for center in self:
            center.display_name = f"[{center.code}] {center.name}"
    
    @api.depends('line_ids.amount')
    def _compute_total_cost(self):
        for center in self:
            costs = center.line_ids.filtered(lambda l: l.amount < 0)
            center.total_cost = abs(sum(costs.mapped('amount')))
    
    @api.depends('line_ids.amount')
    def _compute_total_revenue(self):
        for center in self:
            revenues = center.line_ids.filtered(lambda l: l.amount > 0)
            center.total_revenue = sum(revenues.mapped('amount'))
    
    @api.depends('total_revenue', 'total_cost')
    def _compute_profit_loss(self):
        for center in self:
            center.profit_loss = center.total_revenue - center.total_cost
    
    @api.depends('total_cost', 'budget_amount')
    def _compute_budget_consumed(self):
        for center in self:
            if center.budget_amount:
                center.budget_consumed = (center.total_cost / center.budget_amount) * 100
            else:
                center.budget_consumed = 0
    
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive cost centers.'))
    
    @api.constrains('allocation_percentage')
    def _check_allocation_percentage(self):
        for center in self:
            if center.allocation_percentage < 0 or center.allocation_percentage > 100:
                raise ValidationError(_('Allocation percentage must be between 0 and 100.'))
    
    def action_view_lines(self):
        """View analytic lines for this cost center"""
        self.ensure_one()
        return {
            'name': _('Cost Center Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.analytic.line',
            'view_mode': 'tree,form,pivot,graph',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {'default_cost_center_id': self.id}
        }
    
    def action_allocate_costs(self):
        """Allocate costs to other cost centers"""
        self.ensure_one()
        return {
            'name': _('Allocate Costs'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.cost.allocation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id,
                'default_amount': self.total_cost,
                'default_method': self.allocation_method,
            }
        }


class MozCostCenterBudget(models.Model):
    _name = 'moz.cost.center.budget'
    _description = 'Cost Center Budget'
    _order = 'date_from desc'
    
    cost_center_id = fields.Many2one(
        'moz.cost.center',
        string='Cost Center',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Name',
        required=True
    )
    
    date_from = fields.Date(
        string='From Date',
        required=True
    )
    
    date_to = fields.Date(
        string='To Date',
        required=True
    )
    
    amount = fields.Monetary(
        string='Budget Amount',
        required=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='cost_center_id.currency_id',
        string='Currency'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='State', default='draft')
    
    actual_amount = fields.Monetary(
        string='Actual Amount',
        compute='_compute_actual_amount',
        currency_field='currency_id'
    )
    
    variance = fields.Monetary(
        string='Variance',
        compute='_compute_variance',
        currency_field='currency_id'
    )
    
    variance_percentage = fields.Float(
        string='Variance %',
        compute='_compute_variance'
    )
    
    @api.depends('cost_center_id.line_ids', 'date_from', 'date_to')
    def _compute_actual_amount(self):
        for budget in self:
            lines = budget.cost_center_id.line_ids.filtered(
                lambda l: budget.date_from <= l.date <= budget.date_to and l.amount < 0
            )
            budget.actual_amount = abs(sum(lines.mapped('amount')))
    
    @api.depends('amount', 'actual_amount')
    def _compute_variance(self):
        for budget in self:
            budget.variance = budget.amount - budget.actual_amount
            if budget.amount:
                budget.variance_percentage = (budget.variance / budget.amount) * 100
            else:
                budget.variance_percentage = 0
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from >= budget.date_to:
                raise ValidationError(_('End date must be after start date.'))