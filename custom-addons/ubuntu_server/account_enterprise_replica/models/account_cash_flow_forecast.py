# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)


class AccountCashFlowForecast(models.Model):
    _name = 'account.cash.flow.forecast'
    _description = 'Cash Flow Forecast'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Forecast Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')
    
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    date_to = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.today() + timedelta(days=90))
    
    forecast_method = fields.Selection([
        ('historical', 'Historical Trend'),
        ('budget', 'Budget Based'),
        ('ml', 'Machine Learning'),
        ('manual', 'Manual Input')
    ], string='Forecast Method', default='historical')
    
    forecast_lines = fields.One2many('account.cash.flow.forecast.line', 'forecast_id', string='Forecast Lines')
    
    total_inflow = fields.Monetary(string='Total Inflow', compute='_compute_totals', currency_field='currency_id')
    total_outflow = fields.Monetary(string='Total Outflow', compute='_compute_totals', currency_field='currency_id')
    net_cash_flow = fields.Monetary(string='Net Cash Flow', compute='_compute_totals', currency_field='currency_id')
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='currency_id')
    closing_balance = fields.Monetary(string='Closing Balance', compute='_compute_totals', currency_field='currency_id')
    
    accuracy_score = fields.Float(string='Forecast Accuracy %', compute='_compute_accuracy')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], string='Status', default='draft', tracking=True)
    
    @api.depends('forecast_lines.amount')
    def _compute_totals(self):
        for forecast in self:
            inflow = sum(forecast.forecast_lines.filtered(lambda l: l.flow_type == 'inflow').mapped('amount'))
            outflow = sum(forecast.forecast_lines.filtered(lambda l: l.flow_type == 'outflow').mapped('amount'))
            forecast.total_inflow = inflow
            forecast.total_outflow = outflow
            forecast.net_cash_flow = inflow - outflow
            forecast.closing_balance = forecast.opening_balance + forecast.net_cash_flow
    
    def _compute_accuracy(self):
        for forecast in self:
            # Compare with actual if date has passed
            if forecast.date_to < date.today():
                actual_lines = forecast.forecast_lines.filtered(lambda l: l.actual_amount > 0)
                if actual_lines:
                    total_forecast = sum(actual_lines.mapped('amount'))
                    total_actual = sum(actual_lines.mapped('actual_amount'))
                    if total_forecast:
                        accuracy = 100 - (abs(total_forecast - total_actual) / total_forecast * 100)
                        forecast.accuracy_score = max(0, accuracy)
                    else:
                        forecast.accuracy_score = 0
                else:
                    forecast.accuracy_score = 0
            else:
                forecast.accuracy_score = 0
    
    def action_generate_forecast(self):
        self.forecast_lines.unlink()
        if self.forecast_method == 'historical':
            self._generate_historical_forecast()
        elif self.forecast_method == 'budget':
            self._generate_budget_forecast()
        elif self.forecast_method == 'ml':
            self._generate_ml_forecast()
        return True
    
    def _generate_historical_forecast(self):
        """Generate forecast based on historical trends"""
        # Get historical data for the same period in previous year
        historical_start = self.date_from - relativedelta(years=1)
        historical_end = self.date_to - relativedelta(years=1)
        
        # Analyze receivables pattern
        receivables = self._analyze_receivables_pattern(historical_start, historical_end)
        payables = self._analyze_payables_pattern(historical_start, historical_end)
        
        # Generate daily forecasts
        current_date = self.date_from
        while current_date <= self.date_to:
            # Inflow forecast
            daily_revenue = receivables.get(current_date.weekday(), 10000)
            self.env['account.cash.flow.forecast.line'].create({
                'forecast_id': self.id,
                'date': current_date,
                'flow_type': 'inflow',
                'category': 'sales',
                'amount': daily_revenue,
                'confidence': 75.0,
                'description': 'Projected sales revenue'
            })
            
            # Outflow forecast
            daily_expense = payables.get(current_date.weekday(), 8000)
            self.env['account.cash.flow.forecast.line'].create({
                'forecast_id': self.id,
                'date': current_date,
                'flow_type': 'outflow',
                'category': 'purchases',
                'amount': daily_expense,
                'confidence': 70.0,
                'description': 'Projected expenses'
            })
            
            current_date += timedelta(days=1)
    
    def _analyze_receivables_pattern(self, date_from, date_to):
        """Analyze historical receivables pattern"""
        # Simplified pattern analysis
        return {
            0: 12000,  # Monday
            1: 11000,  # Tuesday
            2: 10000,  # Wednesday
            3: 11500,  # Thursday
            4: 13000,  # Friday
            5: 5000,   # Saturday
            6: 3000    # Sunday
        }
    
    def _analyze_payables_pattern(self, date_from, date_to):
        """Analyze historical payables pattern"""
        # Simplified pattern analysis
        return {
            0: 9000,   # Monday
            1: 8500,   # Tuesday
            2: 8000,   # Wednesday
            3: 8500,   # Thursday
            4: 10000,  # Friday
            5: 3000,   # Saturday
            6: 2000    # Sunday
        }
    
    def _generate_budget_forecast(self):
        """Generate forecast based on budget data"""
        # Link with budget module if available
        pass
    
    def _generate_ml_forecast(self):
        """Generate forecast using machine learning"""
        # Simplified ML forecast - would use actual ML libraries in production
        pass
    
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_done(self):
        self.state = 'done'


class AccountCashFlowForecastLine(models.Model):
    _name = 'account.cash.flow.forecast.line'
    _description = 'Cash Flow Forecast Line'
    _order = 'date, flow_type'
    
    forecast_id = fields.Many2one('account.cash.flow.forecast', string='Forecast', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    
    flow_type = fields.Selection([
        ('inflow', 'Inflow'),
        ('outflow', 'Outflow')
    ], string='Type', required=True)
    
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchases', 'Purchases'),
        ('payroll', 'Payroll'),
        ('tax', 'Tax'),
        ('loan', 'Loan'),
        ('investment', 'Investment'),
        ('other', 'Other')
    ], string='Category')
    
    source = fields.Selection([
        ('invoice', 'Customer Invoice'),
        ('bill', 'Vendor Bill'),
        ('payment', 'Payment'),
        ('manual', 'Manual Entry')
    ], string='Source')
    
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    amount = fields.Monetary(string='Forecast Amount', currency_field='currency_id', required=True)
    actual_amount = fields.Monetary(string='Actual Amount', currency_field='currency_id')
    variance = fields.Monetary(string='Variance', compute='_compute_variance', currency_field='currency_id')
    
    currency_id = fields.Many2one(related='forecast_id.currency_id', string='Currency')
    
    confidence = fields.Float(string='Confidence %', default=80.0)
    description = fields.Char(string='Description')
    
    @api.depends('amount', 'actual_amount')
    def _compute_variance(self):
        for line in self:
            line.variance = line.actual_amount - line.amount