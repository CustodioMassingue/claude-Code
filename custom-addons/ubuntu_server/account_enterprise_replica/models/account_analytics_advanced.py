# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticsAdvanced(models.Model):
    _name = 'account.analytics.advanced'
    _description = 'Advanced Financial Analytics'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Analysis Name',
        required=True
    )
    
    analysis_type = fields.Selection([
        ('variance', 'Variance Analysis'),
        ('trend', 'Trend Analysis'),
        ('ratio', 'Ratio Analysis'),
        ('segment', 'Segment Analysis'),
        ('product', 'Product Profitability'),
        ('customer', 'Customer Profitability'),
        ('project', 'Project Profitability'),
        ('department', 'Department Analysis'),
        ('forecast', 'Financial Forecast'),
        ('benchmark', 'Benchmark Analysis'),
        ('cohort', 'Cohort Analysis'),
        ('break_even', 'Break-Even Analysis'),
        ('sensitivity', 'Sensitivity Analysis'),
        ('scenario', 'Scenario Analysis')
    ], string='Analysis Type', required=True, default='variance')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency'
    )
    
    # Period Configuration
    period_type = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
        ('custom', 'Custom')
    ], string='Period Type', default='month')
    
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )
    
    comparison_date_from = fields.Date(
        string='Comparison From'
    )
    
    comparison_date_to = fields.Date(
        string='Comparison To'
    )
    
    # Filters
    account_ids = fields.Many2many(
        'account.account',
        string='Accounts',
        domain="[('company_id', '=', company_id)]"
    )
    
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        domain="[('company_id', '=', company_id)]"
    )
    
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags',
        domain="[('company_id', '=', company_id)]"
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products'
    )
    
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        domain="[('company_id', '=', company_id)]"
    )
    
    # Analysis Results
    analysis_data = fields.Text(
        string='Analysis Data',
        compute='_compute_analysis_data'
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_analysis_summary',
        currency_field='currency_id'
    )
    
    comparison_amount = fields.Monetary(
        string='Comparison Amount',
        compute='_compute_analysis_summary',
        currency_field='currency_id'
    )
    
    variance_amount = fields.Monetary(
        string='Variance Amount',
        compute='_compute_analysis_summary',
        currency_field='currency_id'
    )
    
    variance_percentage = fields.Float(
        string='Variance %',
        compute='_compute_analysis_summary',
        digits=(5, 2)
    )
    
    # Visualization Settings
    chart_type = fields.Selection([
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('scatter', 'Scatter Plot'),
        ('heatmap', 'Heatmap'),
        ('waterfall', 'Waterfall'),
        ('treemap', 'Treemap'),
        ('sunburst', 'Sunburst')
    ], string='Chart Type', default='bar')
    
    group_by = fields.Selection([
        ('account', 'Account'),
        ('partner', 'Partner'),
        ('product', 'Product'),
        ('analytic', 'Analytic Account'),
        ('tag', 'Analytic Tag'),
        ('date', 'Date'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year')
    ], string='Group By', default='account')
    
    # Advanced Settings
    include_unposted = fields.Boolean(
        string='Include Unposted Entries'
    )
    
    include_initial_balance = fields.Boolean(
        string='Include Initial Balance',
        default=True
    )
    
    hide_zero_lines = fields.Boolean(
        string='Hide Zero Lines',
        default=True
    )

    @api.depends('analysis_type', 'date_from', 'date_to')
    def _compute_analysis_data(self):
        for analysis in self:
            if analysis.analysis_type == 'variance':
                data = analysis._perform_variance_analysis()
            elif analysis.analysis_type == 'trend':
                data = analysis._perform_trend_analysis()
            elif analysis.analysis_type == 'ratio':
                data = analysis._perform_ratio_analysis()
            elif analysis.analysis_type == 'segment':
                data = analysis._perform_segment_analysis()
            elif analysis.analysis_type == 'product':
                data = analysis._perform_product_profitability()
            elif analysis.analysis_type == 'customer':
                data = analysis._perform_customer_profitability()
            elif analysis.analysis_type == 'project':
                data = analysis._perform_project_profitability()
            elif analysis.analysis_type == 'department':
                data = analysis._perform_department_analysis()
            elif analysis.analysis_type == 'forecast':
                data = analysis._perform_financial_forecast()
            elif analysis.analysis_type == 'benchmark':
                data = analysis._perform_benchmark_analysis()
            elif analysis.analysis_type == 'cohort':
                data = analysis._perform_cohort_analysis()
            elif analysis.analysis_type == 'break_even':
                data = analysis._perform_break_even_analysis()
            elif analysis.analysis_type == 'sensitivity':
                data = analysis._perform_sensitivity_analysis()
            elif analysis.analysis_type == 'scenario':
                data = analysis._perform_scenario_analysis()
            else:
                data = {}
            
            analysis.analysis_data = json.dumps(data)

    @api.depends('analysis_data')
    def _compute_analysis_summary(self):
        for analysis in self:
            if analysis.analysis_data:
                data = json.loads(analysis.analysis_data)
                analysis.total_amount = data.get('total_amount', 0)
                analysis.comparison_amount = data.get('comparison_amount', 0)
                analysis.variance_amount = data.get('variance_amount', 0)
                analysis.variance_percentage = data.get('variance_percentage', 0)
            else:
                analysis.total_amount = 0
                analysis.comparison_amount = 0
                analysis.variance_amount = 0
                analysis.variance_percentage = 0

    def _get_base_domain(self):
        """Get base domain for move lines"""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        
        if not self.include_unposted:
            domain.append(('parent_state', '=', 'posted'))
        
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        
        return domain

    def _perform_variance_analysis(self):
        """Perform budget vs actual variance analysis"""
        # Get actual data
        actual_domain = self._get_base_domain()
        actual_lines = self.env['account.move.line'].search(actual_domain)
        
        # Group by account
        actual_by_account = defaultdict(float)
        for line in actual_lines:
            actual_by_account[line.account_id] += line.balance
        
        # Get budget data (if budget module is installed)
        budget_by_account = self._get_budget_data()
        
        # Calculate variances
        variance_data = []
        for account, actual in actual_by_account.items():
            budget = budget_by_account.get(account, 0)
            variance = actual - budget
            variance_pct = (variance / budget * 100) if budget else 0
            
            variance_data.append({
                'account_id': account.id,
                'account_name': account.name,
                'account_code': account.code,
                'actual': actual,
                'budget': budget,
                'variance': variance,
                'variance_percentage': variance_pct,
                'status': 'favorable' if variance >= 0 else 'unfavorable'
            })
        
        # Sort by variance amount
        variance_data.sort(key=lambda x: abs(x['variance']), reverse=True)
        
        total_actual = sum(d['actual'] for d in variance_data)
        total_budget = sum(d['budget'] for d in variance_data)
        total_variance = total_actual - total_budget
        
        return {
            'type': 'variance',
            'items': variance_data,
            'total_amount': total_actual,
            'comparison_amount': total_budget,
            'variance_amount': total_variance,
            'variance_percentage': (total_variance / total_budget * 100) if total_budget else 0,
            'chart_data': self._prepare_variance_chart(variance_data)
        }

    def _perform_trend_analysis(self):
        """Perform trend analysis over time"""
        domain = self._get_base_domain()
        lines = self.env['account.move.line'].search(domain, order='date')
        
        # Group by period
        if self.group_by == 'month':
            period_format = '%Y-%m'
        elif self.group_by == 'quarter':
            period_format = 'Q%q %Y'
        elif self.group_by == 'year':
            period_format = '%Y'
        else:
            period_format = '%Y-%m-%d'
        
        trend_data = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})
        
        for line in lines:
            period = line.date.strftime(period_format)
            trend_data[period]['debit'] += line.debit
            trend_data[period]['credit'] += line.credit
            trend_data[period]['balance'] += line.balance
        
        # Convert to list and sort
        trend_list = [
            {
                'period': period,
                'debit': data['debit'],
                'credit': data['credit'],
                'balance': data['balance'],
                'net': data['debit'] - data['credit']
            }
            for period, data in sorted(trend_data.items())
        ]
        
        # Calculate growth rates
        for i in range(1, len(trend_list)):
            prev = trend_list[i-1]['balance']
            curr = trend_list[i]['balance']
            growth = ((curr - prev) / prev * 100) if prev else 0
            trend_list[i]['growth_rate'] = growth
        
        total = sum(item['balance'] for item in trend_list)
        
        return {
            'type': 'trend',
            'items': trend_list,
            'total_amount': total,
            'chart_data': self._prepare_trend_chart(trend_list)
        }

    def _perform_ratio_analysis(self):
        """Perform financial ratio analysis"""
        date_to = self.date_to
        
        # Get financial data
        ratios = {}
        
        # Liquidity Ratios
        current_assets = self._get_account_balance(['asset_current', 'asset_cash', 'asset_receivable'], date_to)
        current_liabilities = self._get_account_balance(['liability_current', 'liability_payable'], date_to)
        inventory = self._get_account_balance(['asset_current'], date_to, code_prefix='14')
        
        ratios['current_ratio'] = current_assets / current_liabilities if current_liabilities else 0
        ratios['quick_ratio'] = (current_assets - inventory) / current_liabilities if current_liabilities else 0
        
        # Profitability Ratios
        revenue = abs(self._get_account_balance(['income'], self.date_from, date_to))
        net_income = self._get_net_income(self.date_from, date_to)
        total_assets = self._get_account_balance(['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_fixed'], date_to)
        equity = abs(self._get_account_balance(['equity'], date_to))
        
        ratios['profit_margin'] = (net_income / revenue * 100) if revenue else 0
        ratios['return_on_assets'] = (net_income / total_assets * 100) if total_assets else 0
        ratios['return_on_equity'] = (net_income / equity * 100) if equity else 0
        
        # Efficiency Ratios
        receivables = self._get_account_balance(['asset_receivable'], date_to)
        payables = abs(self._get_account_balance(['liability_payable'], date_to))
        days = (date_to - self.date_from).days
        
        ratios['receivables_turnover'] = revenue / receivables if receivables else 0
        ratios['payables_turnover'] = revenue / payables if payables else 0
        ratios['asset_turnover'] = revenue / total_assets if total_assets else 0
        
        # Leverage Ratios
        total_debt = abs(self._get_account_balance(['liability_current', 'liability_non_current'], date_to))
        ratios['debt_ratio'] = total_debt / total_assets if total_assets else 0
        ratios['debt_to_equity'] = total_debt / equity if equity else 0
        
        # Prepare ratio categories
        ratio_categories = {
            'Liquidity': ['current_ratio', 'quick_ratio'],
            'Profitability': ['profit_margin', 'return_on_assets', 'return_on_equity'],
            'Efficiency': ['receivables_turnover', 'payables_turnover', 'asset_turnover'],
            'Leverage': ['debt_ratio', 'debt_to_equity']
        }
        
        return {
            'type': 'ratio',
            'ratios': ratios,
            'categories': ratio_categories,
            'total_amount': revenue,
            'chart_data': self._prepare_ratio_chart(ratios, ratio_categories)
        }

    def _perform_segment_analysis(self):
        """Perform segment-based profitability analysis"""
        domain = self._get_base_domain()
        lines = self.env['account.move.line'].search(domain)
        
        # Group by analytic account (segment)
        segment_data = defaultdict(lambda: {
            'revenue': 0,
            'costs': 0,
            'profit': 0,
            'transactions': 0
        })
        
        for line in lines:
            segment = line.analytic_account_id or 'unassigned'
            
            if line.account_id.account_type in ['income', 'income_other']:
                segment_data[segment]['revenue'] += abs(line.balance)
            elif line.account_id.account_type in ['expense', 'expense_depreciation', 'expense_direct_cost']:
                segment_data[segment]['costs'] += abs(line.balance)
            
            segment_data[segment]['transactions'] += 1
        
        # Calculate profit and margins
        segment_list = []
        for segment, data in segment_data.items():
            data['profit'] = data['revenue'] - data['costs']
            data['margin'] = (data['profit'] / data['revenue'] * 100) if data['revenue'] else 0
            
            segment_name = segment.name if segment != 'unassigned' else 'Unassigned'
            segment_list.append({
                'segment': segment_name,
                'revenue': data['revenue'],
                'costs': data['costs'],
                'profit': data['profit'],
                'margin': data['margin'],
                'transactions': data['transactions']
            })
        
        # Sort by revenue
        segment_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        total_revenue = sum(s['revenue'] for s in segment_list)
        total_profit = sum(s['profit'] for s in segment_list)
        
        return {
            'type': 'segment',
            'items': segment_list,
            'total_amount': total_revenue,
            'total_profit': total_profit,
            'chart_data': self._prepare_segment_chart(segment_list)
        }

    def _perform_product_profitability(self):
        """Analyze product profitability"""
        # Get invoice lines with products
        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('product_id', '!=', False)
        ]
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        invoice_lines = self.env['account.move.line'].search(domain)
        
        # Group by product
        product_data = defaultdict(lambda: {
            'quantity': 0,
            'revenue': 0,
            'cost': 0,
            'profit': 0,
            'transactions': 0
        })
        
        for line in invoice_lines:
            product = line.product_id
            
            if line.move_id.move_type in ['out_invoice', 'out_refund']:
                sign = 1 if line.move_id.move_type == 'out_invoice' else -1
                product_data[product]['revenue'] += line.price_subtotal * sign
                product_data[product]['quantity'] += line.quantity * sign
                
                # Calculate cost
                cost = product.standard_price * line.quantity * sign
                product_data[product]['cost'] += cost
            
            product_data[product]['transactions'] += 1
        
        # Calculate profit and margins
        product_list = []
        for product, data in product_data.items():
            data['profit'] = data['revenue'] - data['cost']
            data['margin'] = (data['profit'] / data['revenue'] * 100) if data['revenue'] else 0
            data['unit_profit'] = data['profit'] / data['quantity'] if data['quantity'] else 0
            
            product_list.append({
                'product_id': product.id,
                'product_name': product.name,
                'product_code': product.default_code or '',
                'quantity': data['quantity'],
                'revenue': data['revenue'],
                'cost': data['cost'],
                'profit': data['profit'],
                'margin': data['margin'],
                'unit_profit': data['unit_profit'],
                'transactions': data['transactions']
            })
        
        # Sort by profit
        product_list.sort(key=lambda x: x['profit'], reverse=True)
        
        total_revenue = sum(p['revenue'] for p in product_list)
        total_profit = sum(p['profit'] for p in product_list)
        
        return {
            'type': 'product',
            'items': product_list,
            'total_amount': total_revenue,
            'total_profit': total_profit,
            'chart_data': self._prepare_product_chart(product_list)
        }

    def _perform_customer_profitability(self):
        """Analyze customer profitability"""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund'])
        ]
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        invoice_lines = self.env['account.move.line'].search(domain)
        
        # Group by customer
        customer_data = defaultdict(lambda: {
            'revenue': 0,
            'cost': 0,
            'profit': 0,
            'invoices': 0,
            'credit_notes': 0,
            'outstanding': 0
        })
        
        for line in invoice_lines:
            if not line.partner_id:
                continue
            
            customer = line.partner_id
            
            if line.move_id.move_type == 'out_invoice':
                customer_data[customer]['revenue'] += line.price_subtotal
                customer_data[customer]['invoices'] += 1
                customer_data[customer]['outstanding'] += line.amount_residual
            else:
                customer_data[customer]['revenue'] -= line.price_subtotal
                customer_data[customer]['credit_notes'] += 1
            
            # Estimate cost (simplified)
            if line.product_id:
                cost = line.product_id.standard_price * line.quantity
                customer_data[customer]['cost'] += cost
        
        # Calculate profit and lifetime value
        customer_list = []
        for customer, data in customer_data.items():
            data['profit'] = data['revenue'] - data['cost']
            data['margin'] = (data['profit'] / data['revenue'] * 100) if data['revenue'] else 0
            
            # Calculate customer lifetime value (simplified)
            customer_age_days = (date.today() - customer.create_date.date()).days
            if customer_age_days > 0:
                annual_revenue = data['revenue'] * 365 / customer_age_days
                data['lifetime_value'] = annual_revenue * 3  # Assume 3-year lifetime
            else:
                data['lifetime_value'] = data['revenue']
            
            customer_list.append({
                'customer_id': customer.id,
                'customer_name': customer.name,
                'revenue': data['revenue'],
                'cost': data['cost'],
                'profit': data['profit'],
                'margin': data['margin'],
                'invoices': data['invoices'],
                'credit_notes': data['credit_notes'],
                'outstanding': data['outstanding'],
                'lifetime_value': data['lifetime_value']
            })
        
        # Sort by revenue
        customer_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        total_revenue = sum(c['revenue'] for c in customer_list)
        total_profit = sum(c['profit'] for c in customer_list)
        
        return {
            'type': 'customer',
            'items': customer_list,
            'total_amount': total_revenue,
            'total_profit': total_profit,
            'chart_data': self._prepare_customer_chart(customer_list)
        }

    def _perform_project_profitability(self):
        """Analyze project profitability"""
        # Similar to segment analysis but focused on projects
        return self._perform_segment_analysis()

    def _perform_department_analysis(self):
        """Analyze department costs and performance"""
        domain = self._get_base_domain()
        lines = self.env['account.move.line'].search(domain)
        
        # Group by department (using analytic tags)
        department_data = defaultdict(lambda: {
            'revenue': 0,
            'expenses': 0,
            'headcount': 0,
            'productivity': 0
        })
        
        for line in lines:
            # Assume department is tracked via analytic tags
            for tag in line.analytic_tag_ids:
                if tag.name.startswith('DEPT_'):
                    dept_name = tag.name.replace('DEPT_', '')
                    
                    if line.account_id.account_type in ['income', 'income_other']:
                        department_data[dept_name]['revenue'] += abs(line.balance)
                    elif line.account_id.account_type in ['expense', 'expense_depreciation']:
                        department_data[dept_name]['expenses'] += abs(line.balance)
        
        # Convert to list
        department_list = []
        for dept, data in department_data.items():
            data['profit'] = data['revenue'] - data['expenses']
            data['margin'] = (data['profit'] / data['revenue'] * 100) if data['revenue'] else 0
            
            department_list.append({
                'department': dept,
                'revenue': data['revenue'],
                'expenses': data['expenses'],
                'profit': data['profit'],
                'margin': data['margin']
            })
        
        department_list.sort(key=lambda x: x['profit'], reverse=True)
        
        total_revenue = sum(d['revenue'] for d in department_list)
        total_expenses = sum(d['expenses'] for d in department_list)
        
        return {
            'type': 'department',
            'items': department_list,
            'total_amount': total_revenue,
            'total_expenses': total_expenses,
            'chart_data': self._prepare_department_chart(department_list)
        }

    def _perform_financial_forecast(self):
        """Perform financial forecasting"""
        # Get historical data
        historical_months = 12
        history_start = self.date_from - relativedelta(months=historical_months)
        
        historical_data = self._get_historical_trend(history_start, self.date_from)
        
        # Simple linear regression for forecast
        forecast_data = self._calculate_forecast(historical_data, 6)  # 6 months forecast
        
        return {
            'type': 'forecast',
            'historical': historical_data,
            'forecast': forecast_data,
            'total_amount': sum(f['predicted'] for f in forecast_data),
            'chart_data': self._prepare_forecast_chart(historical_data, forecast_data)
        }

    def _perform_benchmark_analysis(self):
        """Perform benchmark analysis against industry standards"""
        # This would typically compare against industry data
        # For demo, we'll compare against target values
        
        metrics = {
            'gross_margin': {'actual': 35.2, 'benchmark': 40.0},
            'operating_margin': {'actual': 12.5, 'benchmark': 15.0},
            'current_ratio': {'actual': 1.8, 'benchmark': 2.0},
            'debt_to_equity': {'actual': 0.7, 'benchmark': 0.5},
            'inventory_turnover': {'actual': 6.2, 'benchmark': 8.0},
            'dso': {'actual': 45, 'benchmark': 30}
        }
        
        benchmark_list = []
        for metric, values in metrics.items():
            performance = (values['actual'] / values['benchmark']) * 100
            benchmark_list.append({
                'metric': metric.replace('_', ' ').title(),
                'actual': values['actual'],
                'benchmark': values['benchmark'],
                'performance': performance,
                'gap': values['actual'] - values['benchmark']
            })
        
        return {
            'type': 'benchmark',
            'items': benchmark_list,
            'chart_data': self._prepare_benchmark_chart(benchmark_list)
        }

    def _perform_cohort_analysis(self):
        """Perform customer cohort analysis"""
        # Analyze customer behavior by cohort (month of first purchase)
        return {
            'type': 'cohort',
            'items': [],
            'chart_data': {}
        }

    def _perform_break_even_analysis(self):
        """Perform break-even analysis"""
        # Calculate break-even point
        fixed_costs = self._get_fixed_costs()
        variable_costs = self._get_variable_costs()
        revenue = abs(self._get_account_balance(['income'], self.date_from, self.date_to))
        units_sold = 1000  # Would need actual unit data
        
        price_per_unit = revenue / units_sold if units_sold else 0
        variable_cost_per_unit = variable_costs / units_sold if units_sold else 0
        contribution_margin = price_per_unit - variable_cost_per_unit
        
        break_even_units = fixed_costs / contribution_margin if contribution_margin else 0
        break_even_revenue = break_even_units * price_per_unit
        
        return {
            'type': 'break_even',
            'fixed_costs': fixed_costs,
            'variable_costs': variable_costs,
            'contribution_margin': contribution_margin,
            'break_even_units': break_even_units,
            'break_even_revenue': break_even_revenue,
            'total_amount': revenue,
            'chart_data': self._prepare_break_even_chart(
                fixed_costs, variable_cost_per_unit, price_per_unit
            )
        }

    def _perform_sensitivity_analysis(self):
        """Perform sensitivity analysis"""
        # Analyze impact of variable changes on profit
        base_revenue = abs(self._get_account_balance(['income'], self.date_from, self.date_to))
        base_costs = abs(self._get_account_balance(['expense'], self.date_from, self.date_to))
        base_profit = base_revenue - base_costs
        
        # Test different scenarios
        scenarios = []
        for revenue_change in [-20, -10, 0, 10, 20]:
            for cost_change in [-10, -5, 0, 5, 10]:
                new_revenue = base_revenue * (1 + revenue_change / 100)
                new_costs = base_costs * (1 + cost_change / 100)
                new_profit = new_revenue - new_costs
                profit_change = ((new_profit - base_profit) / base_profit) * 100
                
                scenarios.append({
                    'revenue_change': revenue_change,
                    'cost_change': cost_change,
                    'profit': new_profit,
                    'profit_change': profit_change
                })
        
        return {
            'type': 'sensitivity',
            'base_profit': base_profit,
            'scenarios': scenarios,
            'total_amount': base_revenue,
            'chart_data': self._prepare_sensitivity_chart(scenarios)
        }

    def _perform_scenario_analysis(self):
        """Perform scenario analysis (best/worst/likely)"""
        base_revenue = abs(self._get_account_balance(['income'], self.date_from, self.date_to))
        base_costs = abs(self._get_account_balance(['expense'], self.date_from, self.date_to))
        
        scenarios = {
            'worst': {
                'revenue': base_revenue * 0.7,
                'costs': base_costs * 1.2,
                'probability': 20
            },
            'likely': {
                'revenue': base_revenue,
                'costs': base_costs,
                'probability': 60
            },
            'best': {
                'revenue': base_revenue * 1.3,
                'costs': base_costs * 0.9,
                'probability': 20
            }
        }
        
        for name, scenario in scenarios.items():
            scenario['profit'] = scenario['revenue'] - scenario['costs']
            scenario['margin'] = (scenario['profit'] / scenario['revenue'] * 100) if scenario['revenue'] else 0
        
        expected_profit = sum(
            s['profit'] * s['probability'] / 100
            for s in scenarios.values()
        )
        
        return {
            'type': 'scenario',
            'scenarios': scenarios,
            'expected_profit': expected_profit,
            'total_amount': base_revenue,
            'chart_data': self._prepare_scenario_chart(scenarios)
        }

    # Helper methods
    def _get_account_balance(self, account_types, date_from=None, date_to=None):
        """Get total balance for account types"""
        domain = [
            ('account_id.account_type', 'in', account_types),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted')
        ]
        
        if date_to:
            domain.append(('date', '<=', date_to))
        if date_from:
            domain.append(('date', '>=', date_from))
        
        lines = self.env['account.move.line'].search(domain)
        return sum(lines.mapped('balance'))

    def _get_net_income(self, date_from, date_to):
        """Calculate net income"""
        income = abs(self._get_account_balance(['income', 'income_other'], date_from, date_to))
        expenses = abs(self._get_account_balance(['expense', 'expense_depreciation', 'expense_direct_cost'], date_from, date_to))
        return income - expenses

    def _get_budget_data(self):
        """Get budget data for variance analysis"""
        # Simplified - would integrate with budget module
        return defaultdict(float)

    def _get_fixed_costs(self):
        """Get fixed costs for break-even analysis"""
        # Simplified - would need proper cost classification
        return abs(self._get_account_balance(['expense'], self.date_from, self.date_to)) * 0.6

    def _get_variable_costs(self):
        """Get variable costs for break-even analysis"""
        # Simplified - would need proper cost classification
        return abs(self._get_account_balance(['expense'], self.date_from, self.date_to)) * 0.4

    def _get_historical_trend(self, date_from, date_to):
        """Get historical trend data"""
        # Simplified implementation
        return []

    def _calculate_forecast(self, historical_data, periods):
        """Calculate forecast using simple linear regression"""
        # Simplified implementation
        return []

    # Chart preparation methods
    def _prepare_variance_chart(self, data):
        """Prepare variance chart data"""
        top_10 = data[:10]
        return {
            'type': 'bar',
            'labels': [d['account_name'] for d in top_10],
            'datasets': [
                {
                    'label': 'Actual',
                    'data': [d['actual'] for d in top_10],
                    'backgroundColor': '#36A2EB'
                },
                {
                    'label': 'Budget',
                    'data': [d['budget'] for d in top_10],
                    'backgroundColor': '#FF6384'
                }
            ]
        }

    def _prepare_trend_chart(self, data):
        """Prepare trend chart data"""
        return {
            'type': 'line',
            'labels': [d['period'] for d in data],
            'datasets': [{
                'label': 'Balance',
                'data': [d['balance'] for d in data],
                'borderColor': '#875A7B',
                'fill': False
            }]
        }

    def _prepare_ratio_chart(self, ratios, categories):
        """Prepare ratio chart data"""
        return {
            'type': 'radar',
            'labels': list(ratios.keys()),
            'datasets': [{
                'label': 'Current',
                'data': list(ratios.values()),
                'borderColor': '#36A2EB',
                'backgroundColor': 'rgba(54, 162, 235, 0.2)'
            }]
        }

    def _prepare_segment_chart(self, data):
        """Prepare segment chart data"""
        return {
            'type': 'pie',
            'labels': [d['segment'] for d in data[:10]],
            'datasets': [{
                'data': [d['profit'] for d in data[:10]],
                'backgroundColor': [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                    '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                ]
            }]
        }

    def _prepare_product_chart(self, data):
        """Prepare product profitability chart"""
        top_10 = data[:10]
        return {
            'type': 'bar',
            'labels': [d['product_name'][:20] for d in top_10],
            'datasets': [{
                'label': 'Profit',
                'data': [d['profit'] for d in top_10],
                'backgroundColor': '#28a745'
            }]
        }

    def _prepare_customer_chart(self, data):
        """Prepare customer chart data"""
        top_10 = data[:10]
        return {
            'type': 'bar',
            'labels': [d['customer_name'][:20] for d in top_10],
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': [d['revenue'] for d in top_10],
                    'backgroundColor': '#36A2EB'
                },
                {
                    'label': 'Profit',
                    'data': [d['profit'] for d in top_10],
                    'backgroundColor': '#28a745'
                }
            ]
        }

    def _prepare_department_chart(self, data):
        """Prepare department chart data"""
        return {
            'type': 'bar',
            'labels': [d['department'] for d in data],
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': [d['revenue'] for d in data],
                    'backgroundColor': '#36A2EB'
                },
                {
                    'label': 'Expenses',
                    'data': [d['expenses'] for d in data],
                    'backgroundColor': '#FF6384'
                }
            ]
        }

    def _prepare_forecast_chart(self, historical, forecast):
        """Prepare forecast chart data"""
        return {
            'type': 'line',
            'datasets': [
                {
                    'label': 'Historical',
                    'borderColor': '#36A2EB',
                    'fill': False
                },
                {
                    'label': 'Forecast',
                    'borderColor': '#FF6384',
                    'borderDash': [5, 5],
                    'fill': False
                }
            ]
        }

    def _prepare_benchmark_chart(self, data):
        """Prepare benchmark chart data"""
        return {
            'type': 'bar',
            'labels': [d['metric'] for d in data],
            'datasets': [
                {
                    'label': 'Actual',
                    'data': [d['actual'] for d in data],
                    'backgroundColor': '#36A2EB'
                },
                {
                    'label': 'Benchmark',
                    'data': [d['benchmark'] for d in data],
                    'backgroundColor': '#FF6384'
                }
            ]
        }

    def _prepare_break_even_chart(self, fixed_costs, variable_cost_per_unit, price_per_unit):
        """Prepare break-even chart data"""
        units = list(range(0, 2000, 100))
        revenues = [u * price_per_unit for u in units]
        total_costs = [fixed_costs + (u * variable_cost_per_unit) for u in units]
        
        return {
            'type': 'line',
            'labels': units,
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': revenues,
                    'borderColor': '#28a745',
                    'fill': False
                },
                {
                    'label': 'Total Costs',
                    'data': total_costs,
                    'borderColor': '#dc3545',
                    'fill': False
                }
            ]
        }

    def _prepare_sensitivity_chart(self, scenarios):
        """Prepare sensitivity chart data"""
        return {
            'type': 'heatmap',
            'data': scenarios
        }

    def _prepare_scenario_chart(self, scenarios):
        """Prepare scenario chart data"""
        return {
            'type': 'bar',
            'labels': list(scenarios.keys()),
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': [s['revenue'] for s in scenarios.values()],
                    'backgroundColor': '#36A2EB'
                },
                {
                    'label': 'Costs',
                    'data': [s['costs'] for s in scenarios.values()],
                    'backgroundColor': '#FF6384'
                },
                {
                    'label': 'Profit',
                    'data': [s['profit'] for s in scenarios.values()],
                    'backgroundColor': '#28a745'
                }
            ]
        }

    def action_export_analysis(self):
        """Export analysis to Excel"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'account_enterprise_replica.report_analytics_excel',
            'report_type': 'xlsx',
            'data': {'id': self.id},
            'context': self.env.context
        }

    def action_print_analysis(self):
        """Print analysis report"""
        return self.env.ref('account_enterprise_replica.action_report_analytics').report_action(self)

    def action_schedule_analysis(self):
        """Schedule automated analysis"""
        return {
            'name': _('Schedule Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytics.schedule',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_analysis_id': self.id,
            }
        }