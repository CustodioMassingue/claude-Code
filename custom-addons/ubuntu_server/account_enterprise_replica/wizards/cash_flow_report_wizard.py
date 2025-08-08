# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class CashFlowReportWizard(models.TransientModel):
    _name = 'cash.flow.report.wizard'
    _description = 'Cash Flow Report Wizard'
    
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
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    report_type = fields.Selection([
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
        ('forecast', 'With Forecast')
    ], string='Report Type', default='summary', required=True)
    
    def action_generate_report(self):
        """Generate cash flow report"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'account_enterprise_replica.cash_flow_report',
            'report_type': 'qweb-html',
            'data': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'report_type': self.report_type,
            },
            'context': self.env.context,
        }