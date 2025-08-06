# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP

class MozAnalyticAccount(models.Model):
    _name = 'moz.analytic.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Analytic Account'
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
    
    # Type and Group
    account_type = fields.Selection([
        ('project', 'Project'),
        ('contract', 'Contract'),
        ('department', 'Department'),
        ('cost_center', 'Cost Center'),
        ('other', 'Other'),
    ], string='Type', default='other', required=True, tracking=True)
    
    group_id = fields.Many2one(
        'moz.analytic.group',
        string='Group',
        tracking=True
    )
    
    parent_id = fields.Many2one(
        'moz.analytic.account',
        string='Parent Account',
        tracking=True
    )
    
    child_ids = fields.One2many(
        'moz.analytic.account',
        'parent_id',
        string='Child Accounts'
    )
    
    # Partner and Project
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer/Supplier',
        tracking=True
    )
    
    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )
    
    # Budget
    budget_amount = fields.Monetary(
        string='Budget',
        currency_field='currency_id',
        tracking=True
    )
    
    # Dates
    date_start = fields.Date(
        string='Start Date',
        tracking=True
    )
    
    date_end = fields.Date(
        string='End Date',
        tracking=True
    )
    
    # Lines
    line_ids = fields.One2many(
        'moz.analytic.line',
        'account_id',
        string='Analytic Lines'
    )
    
    # Computed fields
    debit = fields.Monetary(
        string='Debit',
        compute='_compute_debit_credit',
        currency_field='currency_id'
    )
    
    credit = fields.Monetary(
        string='Credit',
        compute='_compute_debit_credit',
        currency_field='currency_id'
    )
    
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_debit_credit',
        currency_field='currency_id'
    )
    
    budget_consumed = fields.Float(
        string='Budget Consumed (%)',
        compute='_compute_budget_consumed'
    )
    
    @api.depends('code', 'name')
    def _compute_display_name(self):
        for account in self:
            account.display_name = f"[{account.code}] {account.name}"
    
    @api.depends('line_ids.amount')
    def _compute_debit_credit(self):
        for account in self:
            lines = account.line_ids
            account.debit = sum(line.amount for line in lines if line.amount > 0)
            account.credit = abs(sum(line.amount for line in lines if line.amount < 0))
            account.balance = account.debit - account.credit
    
    @api.depends('balance', 'budget_amount')
    def _compute_budget_consumed(self):
        for account in self:
            if account.budget_amount:
                account.budget_consumed = abs(account.balance / account.budget_amount * 100)
            else:
                account.budget_consumed = 0
    
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive analytic accounts.'))
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for account in self:
            if account.date_start and account.date_end:
                if account.date_start > account.date_end:
                    raise ValidationError(_('End date must be after start date.'))
    
    def action_view_lines(self):
        """Open analytic lines for this account"""
        self.ensure_one()
        return {
            'name': _('Analytic Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.analytic.line',
            'view_mode': 'tree,form,pivot,graph',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id}
        }
    
    def action_view_report(self):
        """Open analytic report for this account"""
        self.ensure_one()
        return {
            'name': _('Analytic Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.analytic.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_ids': [(6, 0, [self.id])],
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
            }
        }


class MozAnalyticGroup(models.Model):
    _name = 'moz.analytic.group'
    _description = 'Analytic Account Group'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Name',
        required=True
    )
    
    code = fields.Char(
        string='Code'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    parent_id = fields.Many2one(
        'moz.analytic.group',
        string='Parent Group'
    )
    
    child_ids = fields.One2many(
        'moz.analytic.group',
        'parent_id',
        string='Child Groups'
    )
    
    account_ids = fields.One2many(
        'moz.analytic.account',
        'group_id',
        string='Accounts'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    description = fields.Text(
        string='Description'
    )
    
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive groups.'))