# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ConsolidationWizard(models.TransientModel):
    _name = 'account.consolidation.wizard'
    _description = 'Consolidation Wizard'
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True
    )
    
    period_id = fields.Many2one(
        'account.consolidation.period',
        string='Period',
        domain="[('chart_id', '=', chart_id)]"
    )
    
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today
    )
    
    company_ids = fields.Many2many(
        'account.consolidation.company',
        string='Companies to Consolidate',
        domain="[('chart_id', '=', chart_id)]"
    )
    
    consolidation_method = fields.Selection([
        ('full', 'Full Consolidation'),
        ('proportional', 'Proportional Consolidation'),
        ('equity', 'Equity Method')
    ], string='Method', default='full', required=True)
    
    include_eliminations = fields.Boolean(
        string='Process Eliminations',
        default=True
    )
    
    include_minority = fields.Boolean(
        string='Calculate Minority Interest',
        default=True
    )
    
    currency_conversion = fields.Boolean(
        string='Apply Currency Conversion',
        default=True
    )
    
    generate_report = fields.Boolean(
        string='Generate Report After Consolidation',
        default=True
    )
    
    def action_consolidate(self):
        """Run consolidation process"""
        self.ensure_one()
        
        if not self.chart_id:
            raise UserError(_('Please select a consolidation chart.'))
        
        if not self.company_ids:
            self.company_ids = self.chart_id.company_ids
        
        # Create or get period
        if not self.period_id:
            self.period_id = self._create_period()
        
        # Set period on chart
        self.chart_id.current_period_id = self.period_id
        
        # Run consolidation
        self.chart_id.action_consolidate()
        
        # Generate report if requested
        if self.generate_report:
            return self._generate_consolidation_report()
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _create_period(self):
        """Create consolidation period"""
        return self.env['account.consolidation.period'].create({
            'name': f"Period {self.date_from} - {self.date_to}",
            'chart_id': self.chart_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
    
    def _generate_consolidation_report(self):
        """Generate and display consolidation report"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'account_enterprise_replica.consolidation_report',
            'report_type': 'qweb-html',
            'data': {
                'chart_id': self.chart_id.id,
                'period_id': self.period_id.id,
            },
            'context': self.env.context,
        }