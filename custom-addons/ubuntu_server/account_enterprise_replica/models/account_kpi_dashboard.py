# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountKPIDashboard(models.Model):
    _name = 'account.kpi.dashboard'
    _description = 'Financial KPI Dashboard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Dashboard Name',
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
        help='Users who can view this dashboard'
    )
    
    is_default = fields.Boolean(
        string='Default Dashboard'
    )
    
    refresh_interval = fields.Integer(
        string='Auto Refresh (seconds)',
        default=300
    )
    
    # KPI Configuration
    kpi_ids = fields.One2many(
        'account.kpi.config',
        'dashboard_id',
        string='KPIs'
    )
    
    # Layout Configuration
    layout_type = fields.Selection([
        ('grid', 'Grid Layout'),
        ('list', 'List Layout'),
        ('masonry', 'Masonry Layout'),
        ('custom', 'Custom Layout')
    ], string='Layout Type', default='grid')
    
    columns = fields.Integer(
        string='Number of Columns',
        default=4
    )
    
    # Dashboard Data
    dashboard_data = fields.Text(
        string='Dashboard Data',
        compute='_compute_dashboard_data'
    )
    
    last_refresh = fields.Datetime(
        string='Last Refresh',
        readonly=True
    )

    @api.depends('kpi_ids')
    def _compute_dashboard_data(self):
        for dashboard in self:
            kpi_data = []
            
            for kpi in dashboard.kpi_ids:
                data = kpi._compute_kpi_value()
                kpi_data.append({
                    'id': kpi.id,
                    'name': kpi.name,
                    'type': kpi.kpi_type,
                    'value': data['value'],
                    'previous_value': data.get('previous_value'),
                    'change': data.get('change'),
                    'change_percentage': data.get('change_percentage'),
                    'trend': data.get('trend'),
                    'chart_data': data.get('chart_data'),
                    'color': kpi.color,
                    'icon': kpi.icon,
                    'size': kpi.widget_size,
                    'position': kpi.position
                })
            
            dashboard.dashboard_data = json.dumps({
                'kpis': kpi_data,
                'layout': dashboard.layout_type,
                'columns': dashboard.columns,
                'last_refresh': fields.Datetime.now().isoformat()
            })
            
            dashboard.last_refresh = fields.Datetime.now()

    def action_refresh_dashboard(self):
        """Manually refresh dashboard data"""
        self._compute_dashboard_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_configure_kpis(self):
        """Open KPI configuration wizard"""
        return {
            'name': _('Configure KPIs'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.kpi.config',
            'view_mode': 'tree,form',
            'domain': [('dashboard_id', '=', self.id)],
            'context': {
                'default_dashboard_id': self.id,
            }
        }

    @api.model
    def get_default_dashboard(self):
        """Get default dashboard for current user"""
        dashboard = self.search([
            ('user_ids', 'in', self.env.user.id),
            ('is_default', '=', True)
        ], limit=1)
        
        if not dashboard:
            dashboard = self.search([
                ('is_default', '=', True),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
        
        return dashboard


class AccountKPIConfig(models.Model):
    _name = 'account.kpi.config'
    _description = 'KPI Configuration'
    _order = 'position, sequence'
    
    name = fields.Char(
        string='KPI Name',
        required=True
    )
    
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
    
    position = fields.Integer(
        string='Grid Position',
        default=1
    )
    
    kpi_type = fields.Selection([
        # Financial Metrics
        ('revenue', 'Revenue'),
        ('gross_profit', 'Gross Profit'),
        ('net_profit', 'Net Profit'),
        ('ebitda', 'EBITDA'),
        ('operating_margin', 'Operating Margin'),
        
        # Liquidity Metrics
        ('current_ratio', 'Current Ratio'),
        ('quick_ratio', 'Quick Ratio'),
        ('cash_ratio', 'Cash Ratio'),
        ('working_capital', 'Working Capital'),
        
        # Efficiency Metrics
        ('asset_turnover', 'Asset Turnover'),
        ('inventory_turnover', 'Inventory Turnover'),
        ('receivables_turnover', 'Receivables Turnover'),
        ('payables_turnover', 'Payables Turnover'),
        
        # Cash Flow Metrics
        ('operating_cash_flow', 'Operating Cash Flow'),
        ('free_cash_flow', 'Free Cash Flow'),
        ('cash_conversion_cycle', 'Cash Conversion Cycle'),
        
        # Profitability Ratios
        ('roi', 'Return on Investment'),
        ('roe', 'Return on Equity'),
        ('roa', 'Return on Assets'),
        ('roce', 'Return on Capital Employed'),
        
        # Leverage Ratios
        ('debt_ratio', 'Debt Ratio'),
        ('debt_equity', 'Debt to Equity'),
        ('interest_coverage', 'Interest Coverage'),
        
        # Activity Metrics
        ('dso', 'Days Sales Outstanding'),
        ('dpo', 'Days Payables Outstanding'),
        ('dio', 'Days Inventory Outstanding'),
        
        # Custom
        ('custom', 'Custom KPI')
    ], string='KPI Type', required=True)
    
    # Period Configuration
    period_type = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Period')
    ], string='Period', default='month')
    
    date_from = fields.Date(
        string='Date From'
    )
    
    date_to = fields.Date(
        string='Date To'
    )
    
    compare_period = fields.Boolean(
        string='Compare with Previous Period',
        default=True
    )
    
    # Display Configuration
    widget_type = fields.Selection([
        ('number', 'Number'),
        ('gauge', 'Gauge'),
        ('progress', 'Progress Bar'),
        ('chart', 'Chart'),
        ('sparkline', 'Sparkline')
    ], string='Widget Type', default='number')
    
    widget_size = fields.Selection([
        ('small', 'Small (1x1)'),
        ('medium', 'Medium (2x1)'),
        ('large', 'Large (2x2)'),
        ('xlarge', 'Extra Large (4x2)')
    ], string='Widget Size', default='small')
    
    color = fields.Selection([
        ('primary', 'Primary'),
        ('success', 'Success'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
        ('dark', 'Dark')
    ], string='Color Theme', default='primary')
    
    icon = fields.Char(
        string='Icon',
        default='fa-chart-line'
    )
    
    # Threshold Configuration
    threshold_good = fields.Float(
        string='Good Threshold'
    )
    
    threshold_warning = fields.Float(
        string='Warning Threshold'
    )
    
    threshold_critical = fields.Float(
        string='Critical Threshold'
    )
    
    # Custom Formula
    custom_formula = fields.Text(
        string='Custom Formula',
        help='Python expression to calculate custom KPI'
    )
    
    # Alert Configuration
    enable_alerts = fields.Boolean(
        string='Enable Alerts'
    )
    
    alert_condition = fields.Selection([
        ('above', 'Above Threshold'),
        ('below', 'Below Threshold'),
        ('change', 'Change Percentage')
    ], string='Alert Condition')
    
    alert_threshold = fields.Float(
        string='Alert Threshold'
    )

    def _compute_kpi_value(self):
        """Compute KPI value based on type"""
        self.ensure_one()
        
        # Get date range
        date_from, date_to = self._get_date_range()
        
        # Calculate based on KPI type
        if self.kpi_type == 'revenue':
            return self._calculate_revenue(date_from, date_to)
        elif self.kpi_type == 'gross_profit':
            return self._calculate_gross_profit(date_from, date_to)
        elif self.kpi_type == 'net_profit':
            return self._calculate_net_profit(date_from, date_to)
        elif self.kpi_type == 'ebitda':
            return self._calculate_ebitda(date_from, date_to)
        elif self.kpi_type == 'current_ratio':
            return self._calculate_current_ratio(date_to)
        elif self.kpi_type == 'quick_ratio':
            return self._calculate_quick_ratio(date_to)
        elif self.kpi_type == 'working_capital':
            return self._calculate_working_capital(date_to)
        elif self.kpi_type == 'dso':
            return self._calculate_dso(date_from, date_to)
        elif self.kpi_type == 'dpo':
            return self._calculate_dpo(date_from, date_to)
        elif self.kpi_type == 'roi':
            return self._calculate_roi(date_from, date_to)
        elif self.kpi_type == 'custom':
            return self._calculate_custom_kpi(date_from, date_to)
        else:
            return {'value': 0, 'trend': []}

    def _get_date_range(self):
        """Get date range for KPI calculation"""
        today = date.today()
        
        if self.period_type == 'today':
            date_from = date_to = today
        elif self.period_type == 'week':
            date_from = today - timedelta(days=today.weekday())
            date_to = today
        elif self.period_type == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif self.period_type == 'quarter':
            quarter = (today.month - 1) // 3
            date_from = today.replace(month=quarter * 3 + 1, day=1)
            date_to = today
        elif self.period_type == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today
        else:
            date_from = self.date_from or today
            date_to = self.date_to or today
        
        return date_from, date_to

    def _calculate_revenue(self, date_from, date_to):
        """Calculate revenue KPI"""
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        invoices = self.env['account.move'].search(domain)
        current_value = sum(invoices.mapped('amount_total_signed'))
        
        # Previous period
        previous_value = 0
        if self.compare_period:
            days_diff = (date_to - date_from).days
            prev_date_from = date_from - timedelta(days=days_diff)
            prev_date_to = date_from - timedelta(days=1)
            
            prev_domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', prev_date_from),
                ('invoice_date', '<=', prev_date_to),
                ('company_id', '=', self.dashboard_id.company_id.id)
            ]
            
            prev_invoices = self.env['account.move'].search(prev_domain)
            previous_value = sum(prev_invoices.mapped('amount_total_signed'))
        
        # Calculate change
        change = current_value - previous_value
        change_percentage = (change / previous_value * 100) if previous_value else 0
        
        # Generate trend data
        trend = self._generate_trend_data(date_from, date_to, 'revenue')
        
        return {
            'value': current_value,
            'previous_value': previous_value,
            'change': change,
            'change_percentage': change_percentage,
            'trend': trend
        }

    def _calculate_gross_profit(self, date_from, date_to):
        """Calculate gross profit KPI"""
        # Revenue
        revenue_domain = [
            ('account_id.account_type', '=', 'income'),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        revenue_lines = self.env['account.move.line'].search(revenue_domain)
        revenue = abs(sum(revenue_lines.mapped('balance')))
        
        # Cost of Goods Sold
        cogs_domain = [
            ('account_id.account_type', '=', 'expense'),
            ('account_id.code', '=like', '5%'),  # Assuming COGS accounts start with 5
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        cogs_lines = self.env['account.move.line'].search(cogs_domain)
        cogs = abs(sum(cogs_lines.mapped('balance')))
        
        gross_profit = revenue - cogs
        
        return {
            'value': gross_profit,
            'trend': self._generate_trend_data(date_from, date_to, 'gross_profit')
        }

    def _calculate_net_profit(self, date_from, date_to):
        """Calculate net profit KPI"""
        # Total Income
        income_domain = [
            ('account_id.account_type', 'in', ['income', 'income_other']),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        income_lines = self.env['account.move.line'].search(income_domain)
        total_income = abs(sum(income_lines.mapped('balance')))
        
        # Total Expenses
        expense_domain = [
            ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        expense_lines = self.env['account.move.line'].search(expense_domain)
        total_expenses = abs(sum(expense_lines.mapped('balance')))
        
        net_profit = total_income - total_expenses
        
        return {
            'value': net_profit,
            'trend': self._generate_trend_data(date_from, date_to, 'net_profit')
        }

    def _calculate_ebitda(self, date_from, date_to):
        """Calculate EBITDA"""
        net_profit = self._calculate_net_profit(date_from, date_to)['value']
        
        # Add back Interest, Tax, Depreciation, and Amortization
        adjustments_domain = [
            '|', '|', '|',
            ('account_id.code', '=like', '66%'),  # Interest
            ('account_id.code', '=like', '63%'),  # Tax
            ('account_id.code', '=like', '68%'),  # Depreciation
            ('account_id.code', '=like', '69%'),  # Amortization
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        adjustment_lines = self.env['account.move.line'].search(adjustments_domain)
        adjustments = abs(sum(adjustment_lines.mapped('balance')))
        
        ebitda = net_profit + adjustments
        
        return {
            'value': ebitda,
            'trend': self._generate_trend_data(date_from, date_to, 'ebitda')
        }

    def _calculate_current_ratio(self, date_to):
        """Calculate current ratio"""
        # Current Assets
        current_assets_domain = [
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        current_assets_lines = self.env['account.move.line'].search(current_assets_domain)
        current_assets = sum(current_assets_lines.mapped('balance'))
        
        # Current Liabilities
        current_liabilities_domain = [
            ('account_id.account_type', 'in', ['liability_payable', 'liability_current']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        current_liabilities_lines = self.env['account.move.line'].search(current_liabilities_domain)
        current_liabilities = abs(sum(current_liabilities_lines.mapped('balance')))
        
        current_ratio = current_assets / current_liabilities if current_liabilities else 0
        
        return {
            'value': round(current_ratio, 2),
            'trend': []
        }

    def _calculate_quick_ratio(self, date_to):
        """Calculate quick ratio (acid test)"""
        # Quick Assets (Current Assets - Inventory)
        quick_assets_domain = [
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_cash']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        quick_assets_lines = self.env['account.move.line'].search(quick_assets_domain)
        quick_assets = sum(quick_assets_lines.mapped('balance'))
        
        # Current Liabilities
        current_liabilities_domain = [
            ('account_id.account_type', 'in', ['liability_payable', 'liability_current']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        current_liabilities_lines = self.env['account.move.line'].search(current_liabilities_domain)
        current_liabilities = abs(sum(current_liabilities_lines.mapped('balance')))
        
        quick_ratio = quick_assets / current_liabilities if current_liabilities else 0
        
        return {
            'value': round(quick_ratio, 2),
            'trend': []
        }

    def _calculate_working_capital(self, date_to):
        """Calculate working capital"""
        # Current Assets
        current_assets_domain = [
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        current_assets_lines = self.env['account.move.line'].search(current_assets_domain)
        current_assets = sum(current_assets_lines.mapped('balance'))
        
        # Current Liabilities
        current_liabilities_domain = [
            ('account_id.account_type', 'in', ['liability_payable', 'liability_current']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        current_liabilities_lines = self.env['account.move.line'].search(current_liabilities_domain)
        current_liabilities = abs(sum(current_liabilities_lines.mapped('balance')))
        
        working_capital = current_assets - current_liabilities
        
        return {
            'value': working_capital,
            'trend': []
        }

    def _calculate_dso(self, date_from, date_to):
        """Calculate Days Sales Outstanding"""
        # Average Accounts Receivable
        receivable_domain = [
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        receivable_lines = self.env['account.move.line'].search(receivable_domain)
        accounts_receivable = sum(receivable_lines.mapped('balance'))
        
        # Credit Sales
        days = (date_to - date_from).days or 1
        revenue = self._calculate_revenue(date_from, date_to)['value']
        daily_sales = revenue / days if days else 0
        
        dso = accounts_receivable / daily_sales if daily_sales else 0
        
        return {
            'value': round(dso, 1),
            'trend': []
        }

    def _calculate_dpo(self, date_from, date_to):
        """Calculate Days Payables Outstanding"""
        # Average Accounts Payable
        payable_domain = [
            ('account_id.account_type', '=', 'liability_payable'),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        payable_lines = self.env['account.move.line'].search(payable_domain)
        accounts_payable = abs(sum(payable_lines.mapped('balance')))
        
        # Cost of Goods Sold
        days = (date_to - date_from).days or 1
        
        cogs_domain = [
            ('account_id.account_type', '=', 'expense'),
            ('account_id.code', '=like', '5%'),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        cogs_lines = self.env['account.move.line'].search(cogs_domain)
        cogs = abs(sum(cogs_lines.mapped('balance')))
        daily_cogs = cogs / days if days else 0
        
        dpo = accounts_payable / daily_cogs if daily_cogs else 0
        
        return {
            'value': round(dpo, 1),
            'trend': []
        }

    def _calculate_roi(self, date_from, date_to):
        """Calculate Return on Investment"""
        # Net Profit
        net_profit = self._calculate_net_profit(date_from, date_to)['value']
        
        # Total Assets
        assets_domain = [
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_fixed']),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        assets_lines = self.env['account.move.line'].search(assets_domain)
        total_assets = sum(assets_lines.mapped('balance'))
        
        roi = (net_profit / total_assets * 100) if total_assets else 0
        
        return {
            'value': round(roi, 2),
            'trend': []
        }

    def _calculate_custom_kpi(self, date_from, date_to):
        """Calculate custom KPI using formula"""
        if not self.custom_formula:
            return {'value': 0, 'trend': []}
        
        # Prepare safe evaluation context
        env = self.env
        company = self.dashboard_id.company_id
        
        safe_globals = {
            'env': env,
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'sum': sum,
            'abs': abs,
            'round': round,
            'len': len,
            'float': float,
        }
        
        try:
            # Evaluate custom formula
            value = eval(self.custom_formula, safe_globals)
            return {
                'value': value,
                'trend': []
            }
        except Exception as e:
            _logger.error(f"Error calculating custom KPI: {e}")
            return {'value': 0, 'trend': []}

    def _generate_trend_data(self, date_from, date_to, kpi_type):
        """Generate trend data for sparkline charts"""
        trend_data = []
        
        # Generate 7 data points
        days_range = (date_to - date_from).days
        interval = max(1, days_range // 7)
        
        for i in range(7):
            point_date = date_from + timedelta(days=i * interval)
            if point_date > date_to:
                break
            
            # Calculate value for this point
            if kpi_type == 'revenue':
                value = self._get_revenue_at_date(point_date)
            elif kpi_type == 'gross_profit':
                value = self._get_gross_profit_at_date(point_date)
            elif kpi_type == 'net_profit':
                value = self._get_net_profit_at_date(point_date)
            else:
                value = 0
            
            trend_data.append(value)
        
        return trend_data

    def _get_revenue_at_date(self, target_date):
        """Get revenue up to specific date"""
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '<=', target_date),
            ('company_id', '=', self.dashboard_id.company_id.id)
        ]
        
        invoices = self.env['account.move'].search(domain)
        return sum(invoices.mapped('amount_total_signed'))

    def _get_gross_profit_at_date(self, target_date):
        """Get gross profit up to specific date"""
        # Simplified calculation for trend
        revenue = self._get_revenue_at_date(target_date)
        return revenue * 0.4  # Assuming 40% gross margin

    def _get_net_profit_at_date(self, target_date):
        """Get net profit up to specific date"""
        # Simplified calculation for trend
        revenue = self._get_revenue_at_date(target_date)
        return revenue * 0.15  # Assuming 15% net margin

    def check_alerts(self):
        """Check if KPI triggers any alerts"""
        if not self.enable_alerts:
            return
        
        data = self._compute_kpi_value()
        value = data.get('value', 0)
        
        alert_triggered = False
        
        if self.alert_condition == 'above' and value > self.alert_threshold:
            alert_triggered = True
        elif self.alert_condition == 'below' and value < self.alert_threshold:
            alert_triggered = True
        elif self.alert_condition == 'change':
            change_percentage = data.get('change_percentage', 0)
            if abs(change_percentage) > self.alert_threshold:
                alert_triggered = True
        
        if alert_triggered:
            self._send_alert(value, data)

    def _send_alert(self, value, data):
        """Send alert notification"""
        # Create activity for dashboard owner
        self.dashboard_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'KPI Alert: {self.name}',
            note=f'KPI {self.name} has triggered an alert. Current value: {value}'
        )