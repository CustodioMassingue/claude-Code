# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class AccountConsolidationPeriod(models.Model):
    _name = 'account.consolidation.period'
    _description = 'Consolidation Period'
    _order = 'date_start desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Period Name',
        required=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        ondelete='cascade'
    )
    
    journal_id = fields.Many2one(
        'account.consolidation.journal',
        string='Consolidation Journal',
        ondelete='cascade'
    )
    
    date_start = fields.Date(
        string='Start Date',
        required=True
    )
    
    date_end = fields.Date(
        string='End Date',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('consolidating', 'Consolidating'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    company_ids = fields.Many2many(
        'res.company',
        'consolidation_period_company_rel',
        'period_id',
        'company_id',
        string='Companies to Consolidate'
    )
    
    consolidation_rate = fields.Float(
        string='Consolidation Rate',
        digits=(16, 6),
        default=1.0
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_start > period.date_end:
                raise ValidationError(_('Start date must be before end date'))
    
    def action_open(self):
        self.state = 'open'
    
    def action_consolidate(self):
        self.state = 'consolidating'
        # Trigger consolidation process
        return True
    
    def action_done(self):
        self.state = 'done'
    
    def action_cancel(self):
        self.state = 'cancelled'