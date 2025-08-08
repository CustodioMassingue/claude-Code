# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountExecutiveDashboard(models.Model):
    _name = 'account.executive.dashboard'
    _description = 'Executive Financial Dashboard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Dashboard Name',
        required=True,
        default='Executive Dashboard'
    )
    
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
    
    # Access Control
    executive_user_ids = fields.Many2many(
        'res.users',
        'executive_dashboard_users_rel',
        string='Executive Users'
    )
    
    # Period Selection
    period_type = fields.Selection([
        ('mtd', 'Month to Date'),
        ('qtd', 'Quarter to Date'),
        ('ytd', 'Year to Date'),
        ('custom', 'Custom Period')
    ], string='Period', default='mtd')
    
    custom_date_from = fields.Date(string='Custom From')
    custom_date_to = fields.Date(string='Custom To')
    
    # Financial Summary
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    
    total_expenses = fields.Monetary(
        string='Total Expenses',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    
    net_income = fields.Monetary(
        string='Net Income',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    
    gross_margin = fields.Float(
        string='Gross Margin %',
        compute='_compute_financial_summary',
        digits=(5, 2)
    )
    
    operating_margin = fields.Float(
        string='Operating Margin %',
        compute='_compute_financial_summary',
        digits=(5, 2)
    )
    
    net_margin = fields.Float(
        string='Net Margin %',
        compute='_compute_financial_summary',
        digits=(5, 2)
    )
    
    # Balance Sheet Summary
    total_assets = fields.Monetary(
        string='Total Assets',
        compute='_compute_balance_sheet',
        currency_field='currency_id'
    )
    
    total_liabilities = fields.Monetary(
        string='Total Liabilities',
        compute='_compute_balance_sheet',
        currency_field='currency_id'
    )
    
    total_equity = fields.Monetary(
        string='Total Equity',
        compute='_compute_balance_sheet',
        currency_field='currency_id'
    )
    
    # Cash Flow Summary
    operating_cash_flow = fields.Monetary(
        string='Operating Cash Flow',
        compute='_compute_cash_flow',
        currency_field='currency_id'
    )
    
    investing_cash_flow = fields.Monetary(
        string='Investing Cash Flow',
        compute='_compute_cash_flow',
        currency_field='currency_id'
    )
    
    financing_cash_flow = fields.Monetary(
        string='Financing Cash Flow',
        compute='_compute_cash_flow',
        currency_field='currency_id'
    )
    
    net_cash_flow = fields.Monetary(
        string='Net Cash Flow',
        compute='_compute_cash_flow',
        currency_field='currency_id'
    )
    
    # Key Ratios
    current_ratio = fields.Float(
        string='Current Ratio',
        compute='_compute_key_ratios',
        digits=(5, 2)
    )
    
    debt_to_equity = fields.Float(
        string='Debt to Equity',
        compute='_compute_key_ratios',
        digits=(5, 2)
    )
    
    return_on_equity = fields.Float(
        string='ROE %',
        compute='_compute_key_ratios',
        digits=(5, 2)
    )
    
    return_on_assets = fields.Float(
        string='ROA %',
        compute='_compute_key_ratios',
        digits=(5, 2)
    )
    
    # Business Metrics
    customer_count = fields.Integer(
        string='Active Customers',
        compute='_compute_business_metrics'
    )
    
    vendor_count = fields.Integer(
        string='Active Vendors',
        compute='_compute_business_metrics'
    )
    
    average_deal_size = fields.Monetary(
        string='Average Deal Size',
        compute='_compute_business_metrics',
        currency_field='currency_id'
    )
    
    customer_acquisition_cost = fields.Monetary(
        string='Customer Acquisition Cost',
        compute='_compute_business_metrics',
        currency_field='currency_id'
    )
    
    # Dashboard Data JSON
    dashboard_data_json = fields.Text(
        string='Dashboard Data',
        compute='_compute_dashboard_json'
    )
    
    # Chart Configurations
    show_revenue_chart = fields.Boolean(default=True)
    show_expense_chart = fields.Boolean(default=True)
    show_cashflow_chart = fields.Boolean(default=True)
    show_profitability_chart = fields.Boolean(default=True)
    show_balance_sheet_chart = fields.Boolean(default=True)

    @api.depends('period_type', 'custom_date_from', 'custom_date_to')
    def _compute_financial_summary(self):
        for dashboard in self:
            date_from, date_to = dashboard._get_period_dates()
            
            # Revenue
            revenue_domain = [
                ('account_id.account_type', 'in', ['income', 'income_other']),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            revenue_lines = self.env['account.move.line'].search(revenue_domain)
            dashboard.total_revenue = abs(sum(revenue_lines.mapped('balance')))
            
            # Expenses
            expense_domain = [
                ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            expense_lines = self.env['account.move.line'].search(expense_domain)
            dashboard.total_expenses = abs(sum(expense_lines.mapped('balance')))
            
            # Net Income
            dashboard.net_income = dashboard.total_revenue - dashboard.total_expenses
            
            # Margins
            if dashboard.total_revenue:
                # Gross Margin (Revenue - COGS)
                cogs_domain = [
                    ('account_id.account_type', '=', 'expense_direct_cost'),
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('company_id', '=', dashboard.company_id.id)
                ]
                cogs_lines = self.env['account.move.line'].search(cogs_domain)
                cogs = abs(sum(cogs_lines.mapped('balance')))
                
                gross_profit = dashboard.total_revenue - cogs
                dashboard.gross_margin = (gross_profit / dashboard.total_revenue) * 100
                
                # Operating Margin
                operating_expense_domain = [
                    ('account_id.account_type', '=', 'expense'),
                    ('account_id.code', '=like', '6%'),  # Operating expenses
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('company_id', '=', dashboard.company_id.id)
                ]
                operating_expense_lines = self.env['account.move.line'].search(operating_expense_domain)
                operating_expenses = abs(sum(operating_expense_lines.mapped('balance')))
                
                operating_income = gross_profit - operating_expenses
                dashboard.operating_margin = (operating_income / dashboard.total_revenue) * 100
                
                # Net Margin
                dashboard.net_margin = (dashboard.net_income / dashboard.total_revenue) * 100
            else:
                dashboard.gross_margin = 0
                dashboard.operating_margin = 0
                dashboard.net_margin = 0

    @api.depends('company_id')
    def _compute_balance_sheet(self):
        for dashboard in self:
            date_to = dashboard._get_period_dates()[1]
            
            # Assets
            asset_domain = [
                ('account_id.account_type', 'in', [
                    'asset_receivable', 'asset_cash', 'asset_current',
                    'asset_non_current', 'asset_prepayments', 'asset_fixed'
                ]),
                ('parent_state', '=', 'posted'),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            asset_lines = self.env['account.move.line'].search(asset_domain)
            dashboard.total_assets = sum(asset_lines.mapped('balance'))
            
            # Liabilities
            liability_domain = [
                ('account_id.account_type', 'in', [
                    'liability_payable', 'liability_credit_card',
                    'liability_current', 'liability_non_current'
                ]),
                ('parent_state', '=', 'posted'),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            liability_lines = self.env['account.move.line'].search(liability_domain)
            dashboard.total_liabilities = abs(sum(liability_lines.mapped('balance')))
            
            # Equity
            equity_domain = [
                ('account_id.account_type', '=', 'equity'),
                ('parent_state', '=', 'posted'),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            equity_lines = self.env['account.move.line'].search(equity_domain)
            dashboard.total_equity = abs(sum(equity_lines.mapped('balance')))

    @api.depends('period_type', 'custom_date_from', 'custom_date_to')
    def _compute_cash_flow(self):
        for dashboard in self:
            date_from, date_to = dashboard._get_period_dates()
            
            # Operating Activities
            operating_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('company_id', '=', dashboard.company_id.id)
            ])
            
            operating_domain = [
                ('account_id', 'in', operating_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            operating_lines = self.env['account.move.line'].search(operating_domain)
            dashboard.operating_cash_flow = sum(operating_lines.mapped('balance'))
            
            # Investing Activities
            investing_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['asset_fixed', 'asset_non_current']),
                ('company_id', '=', dashboard.company_id.id)
            ])
            
            investing_domain = [
                ('account_id', 'in', investing_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            investing_lines = self.env['account.move.line'].search(investing_domain)
            dashboard.investing_cash_flow = -sum(investing_lines.mapped('balance'))
            
            # Financing Activities
            financing_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['liability_non_current', 'equity']),
                ('company_id', '=', dashboard.company_id.id)
            ])
            
            financing_domain = [
                ('account_id', 'in', financing_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            financing_lines = self.env['account.move.line'].search(financing_domain)
            dashboard.financing_cash_flow = sum(financing_lines.mapped('balance'))
            
            # Net Cash Flow
            dashboard.net_cash_flow = (
                dashboard.operating_cash_flow +
                dashboard.investing_cash_flow +
                dashboard.financing_cash_flow
            )

    @api.depends('total_assets', 'total_liabilities', 'total_equity', 'net_income')
    def _compute_key_ratios(self):
        for dashboard in self:
            date_to = dashboard._get_period_dates()[1]
            
            # Current Ratio
            current_assets_domain = [
                ('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current']),
                ('parent_state', '=', 'posted'),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            current_assets = sum(self.env['account.move.line'].search(current_assets_domain).mapped('balance'))
            
            current_liabilities_domain = [
                ('account_id.account_type', 'in', ['liability_payable', 'liability_current']),
                ('parent_state', '=', 'posted'),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            current_liabilities = abs(sum(self.env['account.move.line'].search(current_liabilities_domain).mapped('balance')))
            
            dashboard.current_ratio = current_assets / current_liabilities if current_liabilities else 0
            
            # Debt to Equity
            dashboard.debt_to_equity = dashboard.total_liabilities / dashboard.total_equity if dashboard.total_equity else 0
            
            # Return on Equity (ROE)
            dashboard.return_on_equity = (dashboard.net_income / dashboard.total_equity * 100) if dashboard.total_equity else 0
            
            # Return on Assets (ROA)
            dashboard.return_on_assets = (dashboard.net_income / dashboard.total_assets * 100) if dashboard.total_assets else 0

    @api.depends('period_type', 'custom_date_from', 'custom_date_to')
    def _compute_business_metrics(self):
        for dashboard in self:
            date_from, date_to = dashboard._get_period_dates()
            
            # Active Customers
            customer_domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            customers = self.env['account.move'].search(customer_domain).mapped('partner_id')
            dashboard.customer_count = len(customers)
            
            # Active Vendors
            vendor_domain = [
                ('move_type', 'in', ['in_invoice', 'in_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            vendors = self.env['account.move'].search(vendor_domain).mapped('partner_id')
            dashboard.vendor_count = len(vendors)
            
            # Average Deal Size
            customer_invoices = self.env['account.move'].search(customer_domain)
            if customer_invoices:
                dashboard.average_deal_size = sum(customer_invoices.mapped('amount_total')) / len(customer_invoices)
            else:
                dashboard.average_deal_size = 0
            
            # Customer Acquisition Cost (simplified)
            marketing_domain = [
                ('account_id.code', '=like', '627%'),  # Marketing expenses
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', dashboard.company_id.id)
            ]
            marketing_expenses = abs(sum(self.env['account.move.line'].search(marketing_domain).mapped('balance')))
            
            new_customers = len(customers)  # Simplified - should track new vs existing
            dashboard.customer_acquisition_cost = marketing_expenses / new_customers if new_customers else 0

    @api.depends('total_revenue', 'total_expenses', 'net_income')
    def _compute_dashboard_json(self):
        for dashboard in self:
            data = {
                'summary': dashboard._get_summary_data(),
                'charts': dashboard._get_chart_data(),
                'trends': dashboard._get_trend_data(),
                'alerts': dashboard._get_alerts(),
                'last_update': fields.Datetime.now().isoformat()
            }
            dashboard.dashboard_data_json = json.dumps(data)

    def _get_period_dates(self):
        """Get date range based on period selection"""
        today = date.today()
        
        if self.period_type == 'mtd':
            date_from = today.replace(day=1)
            date_to = today
        elif self.period_type == 'qtd':
            quarter = (today.month - 1) // 3
            date_from = today.replace(month=quarter * 3 + 1, day=1)
            date_to = today
        elif self.period_type == 'ytd':
            date_from = today.replace(month=1, day=1)
            date_to = today
        elif self.period_type == 'custom':
            date_from = self.custom_date_from or today
            date_to = self.custom_date_to or today
        else:
            date_from = date_to = today
        
        return date_from, date_to

    def _get_summary_data(self):
        """Get summary data for dashboard"""
        return {
            'financial': {
                'revenue': self.total_revenue,
                'expenses': self.total_expenses,
                'net_income': self.net_income,
                'gross_margin': self.gross_margin,
                'operating_margin': self.operating_margin,
                'net_margin': self.net_margin
            },
            'balance_sheet': {
                'assets': self.total_assets,
                'liabilities': self.total_liabilities,
                'equity': self.total_equity
            },
            'cash_flow': {
                'operating': self.operating_cash_flow,
                'investing': self.investing_cash_flow,
                'financing': self.financing_cash_flow,
                'net': self.net_cash_flow
            },
            'ratios': {
                'current_ratio': self.current_ratio,
                'debt_to_equity': self.debt_to_equity,
                'roe': self.return_on_equity,
                'roa': self.return_on_assets
            },
            'business': {
                'customers': self.customer_count,
                'vendors': self.vendor_count,
                'avg_deal': self.average_deal_size,
                'cac': self.customer_acquisition_cost
            }
        }

    def _get_chart_data(self):
        """Generate chart data for dashboard"""
        charts = {}
        
        if self.show_revenue_chart:
            charts['revenue'] = self._get_revenue_chart()
        if self.show_expense_chart:
            charts['expense'] = self._get_expense_chart()
        if self.show_cashflow_chart:
            charts['cashflow'] = self._get_cashflow_chart()
        if self.show_profitability_chart:
            charts['profitability'] = self._get_profitability_chart()
        if self.show_balance_sheet_chart:
            charts['balance_sheet'] = self._get_balance_sheet_chart()
        
        return charts

    def _get_revenue_chart(self):
        """Get revenue trend chart data"""
        date_from, date_to = self._get_period_dates()
        
        # Monthly revenue trend
        query = """
            SELECT 
                DATE_TRUNC('month', date) as month,
                SUM(ABS(balance)) as revenue
            FROM account_move_line
            WHERE account_id IN (
                SELECT id FROM account_account 
                WHERE account_type IN ('income', 'income_other')
                AND company_id = %s
            )
            AND parent_state = 'posted'
            AND date >= %s
            AND date <= %s
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY month
        """
        
        self.env.cr.execute(query, (self.company_id.id, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        return {
            'type': 'line',
            'labels': [r['month'].strftime('%B %Y') for r in results],
            'datasets': [{
                'label': 'Revenue',
                'data': [float(r['revenue']) for r in results],
                'borderColor': '#28a745',
                'backgroundColor': 'rgba(40, 167, 69, 0.1)'
            }]
        }

    def _get_expense_chart(self):
        """Get expense breakdown chart data"""
        date_from, date_to = self._get_period_dates()
        
        # Expense by category
        query = """
            SELECT 
                SUBSTRING(aa.code FROM 1 FOR 2) as category,
                SUM(ABS(aml.balance)) as amount
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aa.account_type IN ('expense', 'expense_depreciation', 'expense_direct_cost')
            AND aa.company_id = %s
            AND aml.parent_state = 'posted'
            AND aml.date >= %s
            AND aml.date <= %s
            GROUP BY SUBSTRING(aa.code FROM 1 FOR 2)
            ORDER BY amount DESC
            LIMIT 10
        """
        
        self.env.cr.execute(query, (self.company_id.id, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        # Map category codes to names
        category_names = {
            '50': 'Cost of Goods Sold',
            '60': 'Personnel Costs',
            '61': 'External Services',
            '62': 'Other Services',
            '63': 'Taxes',
            '64': 'Personnel Charges',
            '65': 'Other Operating Expenses',
            '66': 'Financial Expenses',
            '67': 'Exceptional Expenses',
            '68': 'Depreciation',
            '69': 'Provisions'
        }
        
        labels = [category_names.get(r['category'], f"Category {r['category']}") for r in results]
        data = [float(r['amount']) for r in results]
        
        return {
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                    '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                ]
            }]
        }

    def _get_cashflow_chart(self):
        """Get cash flow waterfall chart data"""
        return {
            'type': 'bar',
            'labels': ['Operating', 'Investing', 'Financing', 'Net'],
            'datasets': [{
                'label': 'Cash Flow',
                'data': [
                    self.operating_cash_flow,
                    self.investing_cash_flow,
                    self.financing_cash_flow,
                    self.net_cash_flow
                ],
                'backgroundColor': [
                    '#28a745' if self.operating_cash_flow > 0 else '#dc3545',
                    '#28a745' if self.investing_cash_flow > 0 else '#dc3545',
                    '#28a745' if self.financing_cash_flow > 0 else '#dc3545',
                    '#28a745' if self.net_cash_flow > 0 else '#dc3545'
                ]
            }]
        }

    def _get_profitability_chart(self):
        """Get profitability metrics chart"""
        return {
            'type': 'radar',
            'labels': ['Gross Margin', 'Operating Margin', 'Net Margin', 'ROE', 'ROA'],
            'datasets': [{
                'label': 'Current Period',
                'data': [
                    self.gross_margin,
                    self.operating_margin,
                    self.net_margin,
                    self.return_on_equity,
                    self.return_on_assets
                ],
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.2)'
            }]
        }

    def _get_balance_sheet_chart(self):
        """Get balance sheet composition chart"""
        return {
            'type': 'bar',
            'labels': ['Assets', 'Liabilities', 'Equity'],
            'datasets': [{
                'label': 'Balance Sheet',
                'data': [
                    self.total_assets,
                    self.total_liabilities,
                    self.total_equity
                ],
                'backgroundColor': ['#36A2EB', '#FF6384', '#4BC0C0']
            }]
        }

    def _get_trend_data(self):
        """Get trend analysis data"""
        # Compare with previous period
        date_from, date_to = self._get_period_dates()
        days_diff = (date_to - date_from).days
        
        prev_date_from = date_from - timedelta(days=days_diff)
        prev_date_to = date_from - timedelta(days=1)
        
        # Previous period revenue
        prev_revenue_domain = [
            ('account_id.account_type', 'in', ['income', 'income_other']),
            ('parent_state', '=', 'posted'),
            ('date', '>=', prev_date_from),
            ('date', '<=', prev_date_to),
            ('company_id', '=', self.company_id.id)
        ]
        prev_revenue = abs(sum(self.env['account.move.line'].search(prev_revenue_domain).mapped('balance')))
        
        # Calculate trends
        revenue_trend = ((self.total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
        
        return {
            'revenue_trend': revenue_trend,
            'period_comparison': {
                'current': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat(),
                    'revenue': self.total_revenue
                },
                'previous': {
                    'from': prev_date_from.isoformat(),
                    'to': prev_date_to.isoformat(),
                    'revenue': prev_revenue
                }
            }
        }

    def _get_alerts(self):
        """Get financial alerts and warnings"""
        alerts = []
        
        # Check current ratio
        if self.current_ratio < 1.0:
            alerts.append({
                'type': 'warning',
                'message': f'Current ratio is below 1.0 ({self.current_ratio:.2f})',
                'metric': 'current_ratio'
            })
        
        # Check debt to equity
        if self.debt_to_equity > 2.0:
            alerts.append({
                'type': 'warning',
                'message': f'Debt to equity ratio is high ({self.debt_to_equity:.2f})',
                'metric': 'debt_to_equity'
            })
        
        # Check net margin
        if self.net_margin < 0:
            alerts.append({
                'type': 'danger',
                'message': f'Negative net margin ({self.net_margin:.2f}%)',
                'metric': 'net_margin'
            })
        
        # Check cash flow
        if self.net_cash_flow < 0:
            alerts.append({
                'type': 'info',
                'message': f'Negative net cash flow ({self.net_cash_flow:,.2f})',
                'metric': 'cash_flow'
            })
        
        return alerts

    def action_refresh_dashboard(self):
        """Manually refresh dashboard"""
        self._compute_financial_summary()
        self._compute_balance_sheet()
        self._compute_cash_flow()
        self._compute_key_ratios()
        self._compute_business_metrics()
        self._compute_dashboard_json()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_export_dashboard(self):
        """Export dashboard to PDF"""
        return self.env.ref('account_enterprise_replica.action_report_executive_dashboard').report_action(self)

    def action_schedule_report(self):
        """Schedule automated report delivery"""
        return {
            'name': _('Schedule Dashboard Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.executive.dashboard.schedule',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_dashboard_id': self.id,
            }
        }

    @api.model
    def send_scheduled_reports(self):
        """Cron job to send scheduled reports"""
        schedules = self.env['account.executive.dashboard.schedule'].search([
            ('active', '=', True),
            ('next_run', '<=', fields.Datetime.now())
        ])
        
        for schedule in schedules:
            schedule.send_report()
            schedule.calculate_next_run()