# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountKpiConfig(models.Model):
    _name = 'account.kpi.config'
    _description = 'KPI Configuration'
    _order = 'sequence, name'
    
    dashboard_id = fields.Many2one(
        'account.kpi.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    name = fields.Char(
        string='KPI Name',
        required=True
    )
    
    code = fields.Char(
        string='KPI Code',
        required=True
    )
    
    kpi_type = fields.Selection([
        ('financial', 'Financial'),
        ('operational', 'Operational'),
        ('efficiency', 'Efficiency'),
        ('liquidity', 'Liquidity'),
        ('profitability', 'Profitability'),
        ('activity', 'Activity'),
        ('custom', 'Custom')
    ], string='KPI Type', required=True, default='financial')
    
    calculation_method = fields.Selection([
        ('formula', 'Formula'),
        ('sql', 'SQL Query'),
        ('python', 'Python Code'),
        ('aggregate', 'Aggregation')
    ], string='Calculation Method', required=True, default='formula')
    
    formula = fields.Text(
        string='Formula/Code',
        help='Formula, SQL query, or Python code depending on calculation method'
    )
    
    target_value = fields.Float(
        string='Target Value',
        digits=(16, 2)
    )
    
    min_value = fields.Float(
        string='Minimum Value',
        digits=(16, 2)
    )
    
    max_value = fields.Float(
        string='Maximum Value',
        digits=(16, 2)
    )
    
    current_value = fields.Float(
        string='Current Value',
        compute='_compute_current_value',
        digits=(16, 2)
    )
    
    unit = fields.Char(
        string='Unit',
        help='Unit of measurement (e.g., %, days, ratio)'
    )
    
    color = fields.Selection([
        ('success', 'Green'),
        ('warning', 'Yellow'),
        ('danger', 'Red'),
        ('info', 'Blue'),
        ('default', 'Gray')
    ], string='Color', compute='_compute_color', store=True)
    
    icon = fields.Char(
        string='Icon',
        default='fa-chart-line'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('calculation_method', 'formula')
    def _compute_current_value(self):
        for kpi in self:
            # Implement KPI calculation logic here
            kpi.current_value = 0.0
    
    @api.depends('current_value', 'target_value', 'min_value', 'max_value')
    def _compute_color(self):
        for kpi in self:
            if not kpi.target_value:
                kpi.color = 'default'
            elif kpi.current_value >= kpi.target_value:
                kpi.color = 'success'
            elif kpi.min_value and kpi.current_value >= kpi.min_value:
                kpi.color = 'warning'
            else:
                kpi.color = 'danger'