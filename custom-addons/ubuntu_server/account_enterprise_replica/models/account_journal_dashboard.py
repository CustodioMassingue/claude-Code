# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountJournalDashboard(models.Model):
    _inherit = 'account.journal'
    _description = 'Journal Dashboard with Advanced Analytics'

    # Dashboard Configuration
    dashboard_graph_type = fields.Selection([
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('donut', 'Donut Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('heatmap', 'Heatmap'),
        ('waterfall', 'Waterfall')
    ], string='Dashboard Graph Type', default='bar')
    
    dashboard_period = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Period')
    ], string='Dashboard Period', default='month')
    
    dashboard_custom_start = fields.Date(string='Custom Start Date')
    dashboard_custom_end = fields.Date(string='Custom End Date')
    
    show_outstanding = fields.Boolean(string='Show Outstanding', default=True)
    show_draft = fields.Boolean(string='Show Draft Entries', default=True)
    show_reconciled = fields.Boolean(string='Show Reconciled', default=True)
    
    # KPI Fields (Computed)
    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )
    
    total_payments = fields.Monetary(
        string='Total Payments',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )
    
    outstanding_amount = fields.Monetary(
        string='Outstanding Amount',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )
    
    overdue_amount = fields.Monetary(
        string='Overdue Amount',
        compute='_compute_dashboard_data',
        currency_field='currency_id'
    )
    
    draft_count = fields.Integer(
        string='Draft Entries',
        compute='_compute_dashboard_data'
    )
    
    to_reconcile_count = fields.Integer(
        string='To Reconcile',
        compute='_compute_dashboard_data'
    )
    
    # Performance Metrics
    avg_payment_days = fields.Float(
        string='Avg Payment Days',
        compute='_compute_dashboard_data',
        digits=(16, 2)
    )
    
    collection_efficiency = fields.Float(
        string='Collection Efficiency %',
        compute='_compute_dashboard_data',
        digits=(5, 2)
    )
    
    reconciliation_rate = fields.Float(
        string='Reconciliation Rate %',
        compute='_compute_dashboard_data',
        digits=(5, 2)
    )
    
    # Dashboard Data JSON
    dashboard_data_json = fields.Text(
        string='Dashboard Data',
        compute='_compute_dashboard_json'
    )
    
    enterprise_dashboard_graph_json = fields.Text(
        string='Enterprise Dashboard Graph',
        compute='_compute_enterprise_dashboard_graph'
    )

    @api.depends('type', 'dashboard_period', 'dashboard_custom_start', 'dashboard_custom_end')
    def _compute_dashboard_data(self):
        for journal in self:
            # Get date range
            date_from, date_to = journal._get_dashboard_date_range()
            
            # Initialize values
            journal.total_invoiced = 0
            journal.total_payments = 0
            journal.outstanding_amount = 0
            journal.overdue_amount = 0
            journal.draft_count = 0
            journal.to_reconcile_count = 0
            journal.avg_payment_days = 0
            journal.collection_efficiency = 0
            journal.reconciliation_rate = 0
            
            if journal.type == 'sale':
                journal._compute_sale_dashboard_data(date_from, date_to)
            elif journal.type == 'purchase':
                journal._compute_purchase_dashboard_data(date_from, date_to)
            elif journal.type == 'bank':
                journal._compute_bank_dashboard_data(date_from, date_to)
            elif journal.type == 'cash':
                journal._compute_cash_dashboard_data(date_from, date_to)
            elif journal.type == 'general':
                journal._compute_general_dashboard_data(date_from, date_to)

    def _get_dashboard_date_range(self):
        """Get date range based on dashboard period setting"""
        today = date.today()
        
        if self.dashboard_period == 'today':
            date_from = date_to = today
        elif self.dashboard_period == 'week':
            date_from = today - timedelta(days=today.weekday())
            date_to = today
        elif self.dashboard_period == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif self.dashboard_period == 'quarter':
            quarter = (today.month - 1) // 3
            date_from = today.replace(month=quarter * 3 + 1, day=1)
            date_to = today
        elif self.dashboard_period == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today
        elif self.dashboard_period == 'custom':
            date_from = self.dashboard_custom_start or today
            date_to = self.dashboard_custom_end or today
        else:
            date_from = date_to = today
        
        return date_from, date_to

    def _compute_sale_dashboard_data(self, date_from, date_to):
        """Compute dashboard data for sale journals"""
        Move = self.env['account.move']
        
        # Total Invoiced
        invoices = Move.search([
            ('journal_id', '=', self.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to)
        ])
        
        self.total_invoiced = sum(invoices.mapped('amount_total_signed'))
        
        # Outstanding Amount
        self.outstanding_amount = sum(invoices.mapped('amount_residual_signed'))
        
        # Overdue Amount
        today = date.today()
        overdue_invoices = invoices.filtered(
            lambda i: i.invoice_date_due and i.invoice_date_due < today and i.amount_residual > 0
        )
        self.overdue_amount = sum(overdue_invoices.mapped('amount_residual_signed'))
        
        # Draft Entries
        draft_moves = Move.search_count([
            ('journal_id', '=', self.id),
            ('state', '=', 'draft'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        self.draft_count = draft_moves
        
        # Payments Received
        payments = self.env['account.payment'].search([
            ('journal_id', '=', self.id),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        self.total_payments = sum(payments.mapped('amount'))
        
        # Average Payment Days
        paid_invoices = invoices.filtered(lambda i: i.payment_state == 'paid')
        if paid_invoices:
            total_days = sum([
                (i.invoice_payment_date - i.invoice_date).days
                for i in paid_invoices
                if i.invoice_payment_date and i.invoice_date
            ])
            self.avg_payment_days = total_days / len(paid_invoices) if paid_invoices else 0
        
        # Collection Efficiency
        if self.total_invoiced:
            self.collection_efficiency = (self.total_payments / self.total_invoiced) * 100
        
        # To Reconcile Count
        to_reconcile = self.env['account.move.line'].search_count([
            ('journal_id', '=', self.id),
            ('account_id.reconcile', '=', True),
            ('reconciled', '=', False),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        self.to_reconcile_count = to_reconcile

    def _compute_purchase_dashboard_data(self, date_from, date_to):
        """Compute dashboard data for purchase journals"""
        Move = self.env['account.move']
        
        # Total Bills
        bills = Move.search([
            ('journal_id', '=', self.id),
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to)
        ])
        
        self.total_invoiced = sum(bills.mapped('amount_total_signed'))
        self.outstanding_amount = sum(bills.mapped('amount_residual_signed'))
        
        # Overdue Bills
        today = date.today()
        overdue_bills = bills.filtered(
            lambda b: b.invoice_date_due and b.invoice_date_due < today and b.amount_residual > 0
        )
        self.overdue_amount = sum(overdue_bills.mapped('amount_residual_signed'))
        
        # Draft Entries
        self.draft_count = Move.search_count([
            ('journal_id', '=', self.id),
            ('state', '=', 'draft'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        
        # Payments Made
        payments = self.env['account.payment'].search([
            ('journal_id', '=', self.id),
            ('payment_type', '=', 'outbound'),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        self.total_payments = sum(payments.mapped('amount'))
        
        # Average Payment Days
        paid_bills = bills.filtered(lambda b: b.payment_state == 'paid')
        if paid_bills:
            total_days = sum([
                (b.invoice_payment_date - b.invoice_date).days
                for b in paid_bills
                if b.invoice_payment_date and b.invoice_date
            ])
            self.avg_payment_days = total_days / len(paid_bills) if paid_bills else 0

    def _compute_bank_dashboard_data(self, date_from, date_to):
        """Compute dashboard data for bank journals"""
        # Bank Balance
        bank_account = self.default_account_id
        if bank_account:
            domain = [
                ('account_id', '=', bank_account.id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted')
            ]
            
            balance = sum(self.env['account.move.line'].search(domain).mapped('balance'))
            self.outstanding_amount = balance
        
        # Unreconciled Items
        if bank_account:
            unreconciled = self.env['account.move.line'].search_count([
                ('account_id', '=', bank_account.id),
                ('reconciled', '=', False),
                ('display_type', 'not in', ('line_section', 'line_note')),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ])
            self.to_reconcile_count = unreconciled
        
        # Bank Statements
        statements = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        
        # Reconciliation Rate
        if statements:
            total_lines = sum(statements.mapped('line_ids.id.__len__'))
            reconciled_lines = sum(statements.mapped(
                lambda s: len(s.line_ids.filtered('is_reconciled'))
            ))
            if total_lines:
                self.reconciliation_rate = (reconciled_lines / total_lines) * 100

    def _compute_cash_dashboard_data(self, date_from, date_to):
        """Compute dashboard data for cash journals"""
        # Cash Balance
        cash_account = self.default_account_id
        if cash_account:
            domain = [
                ('account_id', '=', cash_account.id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted')
            ]
            
            balance = sum(self.env['account.move.line'].search(domain).mapped('balance'))
            self.outstanding_amount = balance
        
        # Cash Transactions
        Move = self.env['account.move']
        cash_moves = Move.search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        
        # Total Cash In/Out
        cash_in = sum(cash_moves.mapped(
            lambda m: sum(m.line_ids.filtered(lambda l: l.debit > 0).mapped('debit'))
        ))
        cash_out = sum(cash_moves.mapped(
            lambda m: sum(m.line_ids.filtered(lambda l: l.credit > 0).mapped('credit'))
        ))
        
        self.total_invoiced = cash_in
        self.total_payments = cash_out

    def _compute_general_dashboard_data(self, date_from, date_to):
        """Compute dashboard data for general journals"""
        Move = self.env['account.move']
        
        # Total Entries
        moves = Move.search([
            ('journal_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        
        # Posted vs Draft
        posted_moves = moves.filtered(lambda m: m.state == 'posted')
        draft_moves = moves.filtered(lambda m: m.state == 'draft')
        
        self.draft_count = len(draft_moves)
        
        # Total Debit/Credit
        if posted_moves:
            total_debit = sum(posted_moves.mapped(
                lambda m: sum(m.line_ids.mapped('debit'))
            ))
            total_credit = sum(posted_moves.mapped(
                lambda m: sum(m.line_ids.mapped('credit'))
            ))
            
            self.total_invoiced = total_debit
            self.total_payments = total_credit
        
        # Unreconciled Items
        unreconciled = self.env['account.move.line'].search_count([
            ('journal_id', '=', self.id),
            ('account_id.reconcile', '=', True),
            ('reconciled', '=', False),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        self.to_reconcile_count = unreconciled

    @api.depends('dashboard_data_json')
    def _compute_dashboard_json(self):
        for journal in self:
            date_from, date_to = journal._get_dashboard_date_range()
            
            dashboard_data = {
                'journal_type': journal.type,
                'period': journal.dashboard_period,
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'kpis': {
                    'total_invoiced': journal.total_invoiced,
                    'total_payments': journal.total_payments,
                    'outstanding_amount': journal.outstanding_amount,
                    'overdue_amount': journal.overdue_amount,
                    'draft_count': journal.draft_count,
                    'to_reconcile_count': journal.to_reconcile_count,
                    'avg_payment_days': journal.avg_payment_days,
                    'collection_efficiency': journal.collection_efficiency,
                    'reconciliation_rate': journal.reconciliation_rate,
                },
                'charts': journal._get_dashboard_charts(date_from, date_to)
            }
            
            journal.dashboard_data_json = json.dumps(dashboard_data)

    def _get_dashboard_charts(self, date_from, date_to):
        """Generate chart data for dashboard"""
        charts = {}
        
        if self.type in ['sale', 'purchase']:
            charts['invoice_trend'] = self._get_invoice_trend_chart(date_from, date_to)
            charts['payment_analysis'] = self._get_payment_analysis_chart(date_from, date_to)
            charts['aging_analysis'] = self._get_aging_analysis_chart()
        elif self.type in ['bank', 'cash']:
            charts['cash_flow'] = self._get_cash_flow_chart(date_from, date_to)
            charts['reconciliation_status'] = self._get_reconciliation_chart()
        else:
            charts['entry_analysis'] = self._get_entry_analysis_chart(date_from, date_to)
        
        return charts

    def _get_invoice_trend_chart(self, date_from, date_to):
        """Get invoice trend data for chart"""
        Move = self.env['account.move']
        
        # Group by month
        move_type = 'out_invoice' if self.type == 'sale' else 'in_invoice'
        
        query = """
            SELECT 
                DATE_TRUNC('month', invoice_date) as month,
                COUNT(*) as count,
                SUM(amount_total_signed) as total
            FROM account_move
            WHERE journal_id = %s
                AND move_type = %s
                AND state = 'posted'
                AND invoice_date >= %s
                AND invoice_date <= %s
            GROUP BY DATE_TRUNC('month', invoice_date)
            ORDER BY month
        """
        
        self.env.cr.execute(query, (self.id, move_type, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        return {
            'type': 'line',
            'labels': [r['month'].strftime('%B %Y') for r in results],
            'datasets': [{
                'label': 'Invoice Amount',
                'data': [float(r['total']) for r in results],
                'borderColor': '#875A7B',
                'backgroundColor': 'rgba(135, 90, 123, 0.2)',
            }]
        }

    def _get_payment_analysis_chart(self, date_from, date_to):
        """Get payment analysis chart data"""
        payment_type = 'inbound' if self.type == 'sale' else 'outbound'
        
        query = """
            SELECT 
                payment_method_line_id,
                COUNT(*) as count,
                SUM(amount) as total
            FROM account_payment
            WHERE journal_id = %s
                AND payment_type = %s
                AND state = 'posted'
                AND date >= %s
                AND date <= %s
            GROUP BY payment_method_line_id
        """
        
        self.env.cr.execute(query, (self.id, payment_type, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        payment_methods = self.env['account.payment.method.line'].browse(
            [r['payment_method_line_id'] for r in results if r['payment_method_line_id']]
        )
        
        labels = []
        data = []
        for result in results:
            if result['payment_method_line_id']:
                method = payment_methods.filtered(lambda m: m.id == result['payment_method_line_id'])
                labels.append(method.name if method else 'Unknown')
                data.append(float(result['total']))
        
        return {
            'type': 'pie',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
                ]
            }]
        }

    def _get_aging_analysis_chart(self):
        """Get aging analysis chart data"""
        today = date.today()
        move_type = ['out_invoice', 'out_refund'] if self.type == 'sale' else ['in_invoice', 'in_refund']
        
        moves = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('move_type', 'in', move_type),
            ('state', '=', 'posted'),
            ('amount_residual', '!=', 0)
        ])
        
        aging_buckets = {
            'Current': 0,
            '1-30 days': 0,
            '31-60 days': 0,
            '61-90 days': 0,
            'Over 90 days': 0
        }
        
        for move in moves:
            if not move.invoice_date_due:
                continue
            
            days_overdue = (today - move.invoice_date_due).days
            
            if days_overdue <= 0:
                aging_buckets['Current'] += move.amount_residual_signed
            elif days_overdue <= 30:
                aging_buckets['1-30 days'] += move.amount_residual_signed
            elif days_overdue <= 60:
                aging_buckets['31-60 days'] += move.amount_residual_signed
            elif days_overdue <= 90:
                aging_buckets['61-90 days'] += move.amount_residual_signed
            else:
                aging_buckets['Over 90 days'] += move.amount_residual_signed
        
        return {
            'type': 'bar',
            'labels': list(aging_buckets.keys()),
            'datasets': [{
                'label': 'Outstanding Amount',
                'data': list(aging_buckets.values()),
                'backgroundColor': '#875A7B'
            }]
        }

    def _get_cash_flow_chart(self, date_from, date_to):
        """Get cash flow chart data"""
        account = self.default_account_id
        if not account:
            return {}
        
        query = """
            SELECT 
                DATE_TRUNC('week', date) as week,
                SUM(CASE WHEN debit > 0 THEN debit ELSE 0 END) as inflow,
                SUM(CASE WHEN credit > 0 THEN credit ELSE 0 END) as outflow
            FROM account_move_line
            WHERE account_id = %s
                AND parent_state = 'posted'
                AND date >= %s
                AND date <= %s
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY week
        """
        
        self.env.cr.execute(query, (account.id, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        return {
            'type': 'bar',
            'labels': [r['week'].strftime('%Y-%m-%d') for r in results],
            'datasets': [
                {
                    'label': 'Inflow',
                    'data': [float(r['inflow']) for r in results],
                    'backgroundColor': '#4BC0C0'
                },
                {
                    'label': 'Outflow',
                    'data': [float(r['outflow']) for r in results],
                    'backgroundColor': '#FF6384'
                }
            ]
        }

    def _get_reconciliation_chart(self):
        """Get reconciliation status chart"""
        account = self.default_account_id
        if not account:
            return {}
        
        reconciled = self.env['account.move.line'].search_count([
            ('account_id', '=', account.id),
            ('reconciled', '=', True),
            ('display_type', 'not in', ('line_section', 'line_note'))
        ])
        
        unreconciled = self.env['account.move.line'].search_count([
            ('account_id', '=', account.id),
            ('reconciled', '=', False),
            ('display_type', 'not in', ('line_section', 'line_note'))
        ])
        
        return {
            'type': 'donut',
            'labels': ['Reconciled', 'Unreconciled'],
            'datasets': [{
                'data': [reconciled, unreconciled],
                'backgroundColor': ['#36A2EB', '#FFCE56']
            }]
        }

    def _get_entry_analysis_chart(self, date_from, date_to):
        """Get entry analysis chart for general journals"""
        query = """
            SELECT 
                state,
                COUNT(*) as count
            FROM account_move
            WHERE journal_id = %s
                AND date >= %s
                AND date <= %s
            GROUP BY state
        """
        
        self.env.cr.execute(query, (self.id, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        state_labels = {
            'draft': 'Draft',
            'posted': 'Posted',
            'cancel': 'Cancelled'
        }
        
        labels = [state_labels.get(r['state'], r['state']) for r in results]
        data = [r['count'] for r in results]
        
        return {
            'type': 'pie',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#FFCE56', '#36A2EB', '#FF6384']
            }]
        }

    @api.depends('type')
    def _compute_enterprise_dashboard_graph(self):
        for journal in self:
            if journal.type in ['sale', 'purchase']:
                journal.enterprise_dashboard_graph_json = journal._get_invoice_kanban_graph()
            elif journal.type in ['bank', 'cash']:
                journal.enterprise_dashboard_graph_json = journal._get_cash_kanban_graph()
            else:
                journal.enterprise_dashboard_graph_json = journal._get_general_kanban_graph()

    def _get_invoice_kanban_graph(self):
        """Get graph data for invoice journals in kanban view"""
        # Last 30 days trend
        today = date.today()
        date_from = today - timedelta(days=30)
        
        move_type = 'out_invoice' if self.type == 'sale' else 'in_invoice'
        
        query = """
            SELECT 
                DATE(invoice_date) as date,
                SUM(amount_total_signed) as total
            FROM account_move
            WHERE journal_id = %s
                AND move_type = %s
                AND state = 'posted'
                AND invoice_date >= %s
                AND invoice_date <= %s
            GROUP BY DATE(invoice_date)
            ORDER BY date
        """
        
        self.env.cr.execute(query, (self.id, move_type, date_from, today))
        results = self.env.cr.dictfetchall()
        
        data = []
        for single_date in (date_from + timedelta(n) for n in range(31)):
            result = next((r for r in results if r['date'] == single_date), None)
            data.append({
                'x': single_date.isoformat(),
                'y': float(result['total']) if result else 0
            })
        
        return json.dumps({
            'type': 'line',
            'data': data,
            'title': 'Last 30 Days Trend'
        })

    def _get_cash_kanban_graph(self):
        """Get graph data for cash/bank journals in kanban view"""
        account = self.default_account_id
        if not account:
            return json.dumps({})
        
        # Balance evolution for last 30 days
        today = date.today()
        date_from = today - timedelta(days=30)
        
        query = """
            SELECT 
                date,
                SUM(balance) OVER (ORDER BY date) as running_balance
            FROM account_move_line
            WHERE account_id = %s
                AND parent_state = 'posted'
                AND date >= %s
                AND date <= %s
            ORDER BY date
        """
        
        self.env.cr.execute(query, (account.id, date_from, today))
        results = self.env.cr.dictfetchall()
        
        data = [{
            'x': r['date'].isoformat(),
            'y': float(r['running_balance'])
        } for r in results]
        
        return json.dumps({
            'type': 'area',
            'data': data,
            'title': 'Balance Evolution'
        })

    def _get_general_kanban_graph(self):
        """Get graph data for general journals in kanban view"""
        # Entries by day for last 7 days
        today = date.today()
        date_from = today - timedelta(days=7)
        
        query = """
            SELECT 
                DATE(date) as date,
                COUNT(*) as count
            FROM account_move
            WHERE journal_id = %s
                AND state = 'posted'
                AND date >= %s
                AND date <= %s
            GROUP BY DATE(date)
            ORDER BY date
        """
        
        self.env.cr.execute(query, (self.id, date_from, today))
        results = self.env.cr.dictfetchall()
        
        data = []
        for single_date in (date_from + timedelta(n) for n in range(8)):
            result = next((r for r in results if r['date'] == single_date), None)
            data.append({
                'x': single_date.strftime('%a'),
                'y': result['count'] if result else 0
            })
        
        return json.dumps({
            'type': 'bar',
            'data': data,
            'title': 'Entries This Week'
        })

    def action_open_dashboard_settings(self):
        """Open dashboard configuration wizard"""
        return {
            'name': _('Dashboard Settings'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal.dashboard.config',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
                'default_graph_type': self.dashboard_graph_type,
                'default_period': self.dashboard_period,
            }
        }

    def refresh_dashboard(self):
        """Manually refresh dashboard data"""
        self._compute_dashboard_data()
        self._compute_dashboard_json()
        self._compute_enterprise_dashboard_graph()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }