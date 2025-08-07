# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import formatLang, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import json
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import calendar
from collections import defaultdict


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    kanban_dashboard = fields.Text(compute='_compute_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph', string='Dashboard Graph')
    show_on_dashboard = fields.Boolean(string='Show on Dashboard', default=True)
    
    @api.depends('type', 'company_id')
    def _compute_kanban_dashboard(self):
        """Compute dashboard data for each journal"""
        for journal in self:
            journal.kanban_dashboard = json.dumps(journal._get_journal_dashboard_data())
    
    @api.depends('type')
    def _compute_kanban_dashboard_graph(self):
        """Compute graph data for dashboard"""
        for journal in self:
            if journal.type in ['sale', 'purchase']:
                journal.kanban_dashboard_graph = json.dumps(journal._get_journal_dashboard_graph_data())
            else:
                journal.kanban_dashboard_graph = json.dumps({'values': []})
    
    def _get_journal_dashboard_data(self):
        """Get dashboard data based on journal type"""
        self.ensure_one()
        
        data = {
            'journal_id': self.id,
            'journal_name': self.name,
            'journal_type': self.type,
            'currency_id': self.currency_id.id or self.company_id.currency_id.id,
            'currency_symbol': self.currency_id.symbol or self.company_id.currency_id.symbol,
            'company_id': self.company_id.id,
        }
        
        if self.type == 'sale':
            data.update(self._get_sale_journal_dashboard_data())
        elif self.type == 'purchase':
            data.update(self._get_purchase_journal_dashboard_data())
        elif self.type == 'bank':
            data.update(self._get_bank_journal_dashboard_data())
        elif self.type == 'cash':
            data.update(self._get_cash_journal_dashboard_data())
        else:
            data.update(self._get_general_journal_dashboard_data())
            
        return data
    
    def _get_sale_journal_dashboard_data(self):
        """Dashboard data for sales journal"""
        currency = self.currency_id or self.company_id.currency_id
        today = fields.Date.today()
        
        # Base domain for this journal
        domain = [
            ('journal_id', '=', self.id),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ]
        
        # Draft invoices
        draft_invoices = self.env['account.move'].search(
            domain + [('state', '=', 'draft')]
        )
        
        # Invoices to send (posted but not sent)
        to_send = self.env['account.move'].search(
            domain + [
                ('state', '=', 'posted'),
                ('is_move_sent', '=', False),
                ('move_type', '=', 'out_invoice')
            ]
        )
        
        # Overdue invoices
        overdue = self.env['account.move'].search(
            domain + [
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', today),
                ('move_type', '=', 'out_invoice')
            ]
        )
        
        # Invoices to check (recently paid or with issues)
        to_check = self.env['account.move'].search(
            domain + [
                ('state', '=', 'posted'),
                ('payment_state', '=', 'in_payment'),
                ('move_type', '=', 'out_invoice')
            ]
        )
        
        # Calculate totals with proper decimal precision
        draft_total = sum(draft_invoices.mapped('amount_total'))
        to_send_total = sum(to_send.mapped('amount_total'))
        overdue_total = sum(overdue.mapped('amount_residual'))
        to_check_total = sum(to_check.mapped('amount_residual'))
        
        # Last month comparison
        last_month_start = (today - relativedelta(months=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)
        
        last_month_invoices = self.env['account.move'].search(
            domain + [
                ('invoice_date', '>=', last_month_start),
                ('invoice_date', '<=', last_month_end),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice')
            ]
        )
        last_month_total = sum(last_month_invoices.mapped('amount_total'))
        
        # This month so far
        this_month_start = today.replace(day=1)
        this_month_invoices = self.env['account.move'].search(
            domain + [
                ('invoice_date', '>=', this_month_start),
                ('invoice_date', '<=', today),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice')
            ]
        )
        this_month_total = sum(this_month_invoices.mapped('amount_total'))
        
        return {
            'title': _('Customer Invoices'),
            'number_draft': len(draft_invoices),
            'sum_draft': formatLang(self.env, draft_total, currency_obj=currency),
            'sum_draft_str': formatLang(self.env, draft_total, currency_obj=currency),
            'number_to_send': len(to_send),
            'sum_to_send': formatLang(self.env, to_send_total, currency_obj=currency),
            'sum_to_send_str': formatLang(self.env, to_send_total, currency_obj=currency),
            'number_overdue': len(overdue),
            'sum_overdue': formatLang(self.env, overdue_total, currency_obj=currency),
            'sum_overdue_str': formatLang(self.env, overdue_total, currency_obj=currency),
            'number_to_check': len(to_check),
            'sum_to_check': formatLang(self.env, to_check_total, currency_obj=currency),
            'sum_to_check_str': formatLang(self.env, to_check_total, currency_obj=currency),
            'number_unpaid': len(to_send) + len(overdue),
            'sum_unpaid_str': formatLang(self.env, to_send_total + overdue_total, currency_obj=currency),
            'number_late': len(overdue),
            'sum_late_str': formatLang(self.env, overdue_total, currency_obj=currency),
            'last_month_total': formatLang(self.env, last_month_total, currency_obj=currency),
            'this_month_total': formatLang(self.env, this_month_total, currency_obj=currency),
            'has_sequence_holes': self._check_sequence_holes('out_invoice'),
        }
    
    def _get_purchase_journal_dashboard_data(self):
        """Dashboard data for purchase journal"""
        currency = self.currency_id or self.company_id.currency_id
        today = fields.Date.today()
        
        # Base domain
        domain = [
            ('journal_id', '=', self.id),
            ('move_type', 'in', ['in_invoice', 'in_refund'])
        ]
        
        # Draft bills
        draft_bills = self.env['account.move'].search(
            domain + [('state', '=', 'draft')]
        )
        
        # Bills to pay
        to_pay = self.env['account.move'].search(
            domain + [
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('move_type', '=', 'in_invoice')
            ]
        )
        
        # Late bills (overdue)
        late_bills = self.env['account.move'].search(
            domain + [
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', today),
                ('move_type', '=', 'in_invoice')
            ]
        )
        
        # Bills to approve (draft with uploaded documents)
        to_approve = self.env['account.move'].search(
            domain + [
                ('state', '=', 'draft'),
                ('move_type', '=', 'in_invoice')
            ]
        )
        
        # Calculate totals
        draft_total = sum(draft_bills.mapped('amount_total'))
        to_pay_total = sum(to_pay.mapped('amount_residual'))
        late_total = sum(late_bills.mapped('amount_residual'))
        to_approve_total = sum(to_approve.mapped('amount_total'))
        
        # This month bills
        this_month_start = today.replace(day=1)
        this_month_bills = self.env['account.move'].search(
            domain + [
                ('invoice_date', '>=', this_month_start),
                ('invoice_date', '<=', today),
                ('state', '=', 'posted'),
                ('move_type', '=', 'in_invoice')
            ]
        )
        this_month_total = sum(this_month_bills.mapped('amount_total'))
        
        return {
            'title': _('Vendor Bills'),
            'number_draft': len(draft_bills),
            'sum_draft': formatLang(self.env, draft_total, currency_obj=currency),
            'number_to_pay': len(to_pay),
            'sum_to_pay': formatLang(self.env, to_pay_total, currency_obj=currency),
            'number_late': len(late_bills),
            'sum_late': formatLang(self.env, late_total, currency_obj=currency),
            'number_to_approve': len(to_approve),
            'sum_to_approve': formatLang(self.env, to_approve_total, currency_obj=currency),
            'this_month_total': formatLang(self.env, this_month_total, currency_obj=currency),
            'has_sequence_holes': self._check_sequence_holes('in_invoice'),
        }
    
    def _get_bank_journal_dashboard_data(self):
        """Dashboard data for bank journal"""
        currency = self.currency_id or self.company_id.currency_id
        
        # Get last bank statement
        last_statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.id)
        ], order='date desc, id desc', limit=1)
        
        # Get balance
        account_balance = 0
        if self.default_account_id:
            query = """
                SELECT COALESCE(SUM(balance), 0) as balance
                FROM account_move_line
                WHERE account_id = %s
                AND parent_state = 'posted'
                AND company_id = %s
            """
            self.env.cr.execute(query, (self.default_account_id.id, self.company_id.id))
            result = self.env.cr.dictfetchone()
            account_balance = result['balance'] if result else 0
        
        # Count unreconciled items
        unreconciled_count = 0
        if self.default_account_id:
            unreconciled_count = self.env['account.move.line'].search_count([
                ('account_id', '=', self.default_account_id.id),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                ('amount_residual', '!=', 0)
            ])
        
        # Get outstanding payments/receipts
        outstanding_payments = self.env['account.payment'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('is_reconciled', '=', False),
            ('payment_type', '=', 'outbound')
        ])
        
        outstanding_receipts = self.env['account.payment'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('is_reconciled', '=', False),
            ('payment_type', '=', 'inbound')
        ])
        
        outstanding_payments_total = sum(outstanding_payments.mapped('amount'))
        outstanding_receipts_total = sum(outstanding_receipts.mapped('amount'))
        
        # Last sync info
        last_sync = False
        if last_statement:
            last_sync = format_date(self.env, last_statement.date)
        
        return {
            'title': self.name,
            'balance': formatLang(self.env, account_balance, currency_obj=currency),
            'bank_balance_str': formatLang(self.env, account_balance, currency_obj=currency),
            'last_sync': last_sync or _('Never'),
            'to_reconcile': unreconciled_count,
            'number_to_reconcile': unreconciled_count,
            'outstanding_payments_count': len(outstanding_payments),
            'outstanding_payments_total': formatLang(self.env, outstanding_payments_total, currency_obj=currency),
            'payments_amount_str': formatLang(self.env, outstanding_payments_total + outstanding_receipts_total, currency_obj=currency),
            'outstanding_receipts_count': len(outstanding_receipts),
            'outstanding_receipts_total': formatLang(self.env, outstanding_receipts_total, currency_obj=currency),
            'bank_account': self.bank_account_id.acc_number if self.bank_account_id else False,
            'has_statements': bool(last_statement),
        }
    
    def _get_cash_journal_dashboard_data(self):
        """Dashboard data for cash journal"""
        currency = self.currency_id or self.company_id.currency_id
        
        # Get balance
        account_balance = 0
        if self.default_account_id:
            query = """
                SELECT COALESCE(SUM(balance), 0) as balance
                FROM account_move_line
                WHERE account_id = %s
                AND parent_state = 'posted'
                AND company_id = %s
            """
            self.env.cr.execute(query, (self.default_account_id.id, self.company_id.id))
            result = self.env.cr.dictfetchone()
            account_balance = result['balance'] if result else 0
        
        # Today's transactions
        today = fields.Date.today()
        today_moves = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('date', '=', today),
            ('state', '=', 'posted')
        ])
        
        # Calculate ins and outs for today
        cash_in_today = 0
        cash_out_today = 0
        
        for move in today_moves:
            for line in move.line_ids.filtered(lambda l: l.account_id == self.default_account_id):
                if line.debit > 0:
                    cash_in_today += line.debit
                if line.credit > 0:
                    cash_out_today += line.credit
        
        # Pending cash moves
        pending_moves = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'draft')
        ])
        
        return {
            'title': self.name,
            'balance': formatLang(self.env, account_balance, currency_obj=currency),
            'cash_balance_str': formatLang(self.env, account_balance, currency_obj=currency),
            'cash_in_today': formatLang(self.env, cash_in_today, currency_obj=currency),
            'cash_out_today': formatLang(self.env, cash_out_today, currency_obj=currency),
            'number_draft': len(pending_moves),
            'today_transactions': len(today_moves),
        }
    
    def _get_general_journal_dashboard_data(self):
        """Dashboard data for general/miscellaneous journal"""
        currency = self.currency_id or self.company_id.currency_id
        
        # Draft entries
        draft_entries = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'draft')
        ])
        
        # Posted entries this month
        today = fields.Date.today()
        this_month_start = today.replace(day=1)
        posted_entries = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('date', '>=', this_month_start),
            ('date', '<=', today)
        ])
        
        # Entries to review (posted today)
        to_review = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('date', '=', today)
        ])
        
        return {
            'title': self.name,
            'number_draft': len(draft_entries),
            'number_posted': len(posted_entries),
            'number_to_review': len(to_review),
            'entries_this_month': len(posted_entries),
        }
    
    def _get_journal_dashboard_graph_data(self):
        """Get enhanced graph data with multiple metrics"""
        self.ensure_one()
        
        data = []
        today = fields.Date.today()
        currency = self.currency_id or self.company_id.currency_id
        
        if self.type == 'sale':
            # Get sales data for last 30 days with amounts
            for i in range(30, -1, -1):
                current_date = today - timedelta(days=i)
                
                invoices = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '=', current_date),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'out_invoice')
                ])
                
                daily_total = sum(invoices.mapped('amount_total'))
                data.append({
                    'x': current_date.strftime('%Y-%m-%d'),
                    'y': len(invoices),
                    'amount': daily_total,
                    'name': _('Invoices'),
                    'label': f"{len(invoices)} invoices - {formatLang(self.env, daily_total, currency_obj=currency)}"
                })
                
        elif self.type == 'purchase':
            # Get purchase data for last 30 days with amounts
            for i in range(30, -1, -1):
                current_date = today - timedelta(days=i)
                
                bills = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '=', current_date),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'in_invoice')
                ])
                
                daily_total = sum(bills.mapped('amount_total'))
                data.append({
                    'x': current_date.strftime('%Y-%m-%d'),
                    'y': len(bills),
                    'amount': daily_total,
                    'name': _('Bills'),
                    'label': f"{len(bills)} bills - {formatLang(self.env, daily_total, currency_obj=currency)}"
                })
                
        elif self.type == 'bank':
            # Get bank balance trend for last 30 days
            if self.default_account_id:
                for i in range(30, -1, -1):
                    current_date = today - timedelta(days=i)
                    
                    # Calculate balance up to this date
                    query = """
                        SELECT COALESCE(SUM(balance), 0) as balance
                        FROM account_move_line
                        WHERE account_id = %s
                        AND parent_state = 'posted'
                        AND date <= %s
                        AND company_id = %s
                    """
                    self.env.cr.execute(query, (
                        self.default_account_id.id,
                        current_date,
                        self.company_id.id
                    ))
                    result = self.env.cr.dictfetchone()
                    balance = result['balance'] if result else 0
                    
                    data.append({
                        'x': current_date.strftime('%Y-%m-%d'),
                        'y': balance,
                        'name': _('Balance'),
                        'label': formatLang(self.env, balance, currency_obj=currency)
                    })
                    
        elif self.type == 'cash':
            # Get cash flow trend for last 30 days
            if self.default_account_id:
                for i in range(30, -1, -1):
                    current_date = today - timedelta(days=i)
                    
                    # Get cash movements for this date
                    moves = self.env['account.move.line'].search([
                        ('account_id', '=', self.default_account_id.id),
                        ('date', '=', current_date),
                        ('parent_state', '=', 'posted')
                    ])
                    
                    cash_in = sum(moves.mapped('debit'))
                    cash_out = sum(moves.mapped('credit'))
                    net_flow = cash_in - cash_out
                    
                    data.append({
                        'x': current_date.strftime('%Y-%m-%d'),
                        'y': net_flow,
                        'cash_in': cash_in,
                        'cash_out': cash_out,
                        'name': _('Net Cash Flow'),
                        'label': f"In: {formatLang(self.env, cash_in, currency_obj=currency)} / Out: {formatLang(self.env, cash_out, currency_obj=currency)}"
                    })
        
        return {
            'values': data,
            'currency': currency.symbol,
            'journal_type': self.type
        }
    
    def _check_sequence_holes(self, move_type):
        """Check if there are sequence holes in posted moves"""
        moves = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'posted'),
            ('move_type', '=', move_type)
        ], order='name')
        
        if len(moves) < 2:
            return False
            
        # Simple check for sequence continuity
        # This is a simplified version - implement full logic based on your sequence configuration
        return False
    
    # Action methods for dashboard buttons
    
    def action_create_new(self):
        """Create new invoice/bill based on journal type"""
        self.ensure_one()
        
        if self.type == 'sale':
            return self.action_create_sale_invoice()
        elif self.type == 'purchase':
            return self.action_create_purchase_bill()
        elif self.type in ['bank', 'cash']:
            return self.action_register_payment()
        else:
            return self.action_create_journal_entry()
    
    def action_create_sale_invoice(self):
        """Create a new customer invoice"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'context': {
                'default_move_type': 'out_invoice',
                'default_journal_id': self.id,
            },
            'target': 'current',
        }
    
    def action_create_purchase_bill(self):
        """Create a new vendor bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Vendor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'context': {
                'default_move_type': 'in_invoice',
                'default_journal_id': self.id,
            },
            'target': 'current',
        }
    
    def action_register_payment(self):
        """Register a payment"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_payment_type': 'inbound' if self.type == 'bank' else 'outbound',
            },
            'target': 'current',
        }
    
    def action_create_journal_entry(self):
        """Create a journal entry"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'context': {
                'default_move_type': 'entry',
                'default_journal_id': self.id,
            },
            'target': 'current',
        }
    
    def action_view_all(self):
        """View all entries for this journal"""
        self.ensure_one()
        
        if self.type == 'sale':
            return self.action_view_sales()
        elif self.type == 'purchase':
            return self.action_view_purchases()
        elif self.type in ['bank', 'cash']:
            return self.action_view_bank_cash()
        else:
            return self.action_view_entries()
    
    def action_view_sales(self):
        """View sales invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('journal_id', '=', self.id),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
            ],
            'context': {
                'default_move_type': 'out_invoice',
                'default_journal_id': self.id,
            },
        }
    
    def action_view_purchases(self):
        """View purchase bills"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bills'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('journal_id', '=', self.id),
                ('move_type', 'in', ['in_invoice', 'in_refund'])
            ],
            'context': {
                'default_move_type': 'in_invoice',
                'default_journal_id': self.id,
            },
        }
    
    def action_view_bank_cash(self):
        """View bank/cash transactions"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bank Transactions') if self.type == 'bank' else _('Cash Transactions'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id},
        }
    
    def action_view_entries(self):
        """View journal entries"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id},
        }
    
    def action_open_reconcile(self):
        """Open reconciliation wizard"""
        self.ensure_one()
        
        if self.type in ['bank', 'cash']:
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {
                    'statement_line_ids': [],
                    'company_ids': self.company_id.ids,
                },
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reconcile'),
                'res_model': 'account.reconcile.model',
                'view_mode': 'list,form',
                'context': {'default_company_id': self.company_id.id},
            }
    
    def action_upload_document(self):
        """Upload document action - creates vendor bill with attachment wizard"""
        self.ensure_one()
        
        if self.type == 'purchase':
            # Open vendor bill creation with document upload capability
            return {
                'type': 'ir.actions.act_window',
                'name': _('Upload Vendor Bill'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'context': {
                    'default_move_type': 'in_invoice',
                    'default_journal_id': self.id,
                    'default_is_invoice': True,
                },
                'target': 'current',
            }
        elif self.type == 'sale':
            return self.action_create_sale_invoice()
        
        return True
    
    def action_configure_journal(self):
        """Open journal configuration"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Journal'),
            'res_model': 'account.journal',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_configure_bank(self):
        """Open bank configuration"""
        self.ensure_one()
        if self.type in ['bank', 'cash']:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Bank Configuration'),
                'res_model': 'account.journal',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'form_view_ref': 'account.view_account_journal_form'},
            }
        return True
    
    def action_print_report(self):
        """Print journal report"""
        self.ensure_one()
        # This would generate a PDF report based on journal type
        return {
            'type': 'ir.actions.report',
            'report_name': 'account.report_journal',
            'report_type': 'qweb-pdf',
            'data': None,
            'context': {
                'journal_ids': [self.id],
            },
        }
    
    def action_export_data(self):
        """Export journal data"""
        self.ensure_one()
        # Open export wizard for the relevant model
        if self.type in ['sale', 'purchase']:
            model = 'account.move'
            domain = [
                ('journal_id', '=', self.id),
                ('move_type', 'in', ['out_invoice', 'out_refund'] if self.type == 'sale' else ['in_invoice', 'in_refund'])
            ]
        else:
            model = 'account.move.line'
            domain = [('journal_id', '=', self.id)]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Data'),
            'res_model': model,
            'view_mode': 'list',
            'domain': domain,
            'context': {
                'search_default_journal_id': self.id,
            },
            'target': 'current',
        }
    
    def get_journal_dashboard_datas(self):
        """Get all dashboard data for journals - called by JS"""
        domain = [('show_on_dashboard', '=', True)]
        journals = self.search(domain)
        
        result = {}
        for journal in journals:
            result[journal.id] = {
                'dashboard': json.loads(journal.kanban_dashboard),
                'graph': json.loads(journal.kanban_dashboard_graph),
            }
        
        return result
    
    def get_weekly_data(self, weeks=12):
        """Get weekly aggregated data for charts"""
        self.ensure_one()
        
        weekly_data = []
        today = fields.Date.today()
        currency = self.currency_id or self.company_id.currency_id
        
        # Calculate start of current week (Monday)
        days_since_monday = today.weekday()
        current_week_start = today - timedelta(days=days_since_monday)
        
        for week in range(weeks - 1, -1, -1):
            week_start = current_week_start - timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)
            
            if self.type == 'sale':
                invoices = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '>=', week_start),
                    ('invoice_date', '<=', week_end),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'out_invoice')
                ])
                
                weekly_total = sum(invoices.mapped('amount_total'))
                weekly_data.append({
                    'week': f"W{week_start.isocalendar()[1]}",
                    'period': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                    'count': len(invoices),
                    'total': weekly_total,
                    'formatted_total': formatLang(self.env, weekly_total, currency_obj=currency)
                })
                
            elif self.type == 'purchase':
                bills = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '>=', week_start),
                    ('invoice_date', '<=', week_end),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'in_invoice')
                ])
                
                weekly_total = sum(bills.mapped('amount_total'))
                weekly_data.append({
                    'week': f"W{week_start.isocalendar()[1]}",
                    'period': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                    'count': len(bills),
                    'total': weekly_total,
                    'formatted_total': formatLang(self.env, weekly_total, currency_obj=currency)
                })
        
        return weekly_data
    
    def get_monthly_data(self, months=12):
        """Get monthly aggregated data for charts"""
        self.ensure_one()
        
        monthly_data = []
        today = fields.Date.today()
        currency = self.currency_id or self.company_id.currency_id
        
        for month_offset in range(months - 1, -1, -1):
            month_date = today - relativedelta(months=month_offset)
            month_start = month_date.replace(day=1)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            if self.type == 'sale':
                invoices = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '>=', month_start),
                    ('invoice_date', '<=', month_end),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'out_invoice')
                ])
                
                monthly_total = sum(invoices.mapped('amount_total'))
                monthly_data.append({
                    'month': month_date.strftime('%B %Y'),
                    'month_short': month_date.strftime('%b'),
                    'count': len(invoices),
                    'total': monthly_total,
                    'formatted_total': formatLang(self.env, monthly_total, currency_obj=currency),
                    'avg_invoice': monthly_total / len(invoices) if invoices else 0
                })
                
            elif self.type == 'purchase':
                bills = self.env['account.move'].search([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '>=', month_start),
                    ('invoice_date', '<=', month_end),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'in_invoice')
                ])
                
                monthly_total = sum(bills.mapped('amount_total'))
                monthly_data.append({
                    'month': month_date.strftime('%B %Y'),
                    'month_short': month_date.strftime('%b'),
                    'count': len(bills),
                    'total': monthly_total,
                    'formatted_total': formatLang(self.env, monthly_total, currency_obj=currency),
                    'avg_bill': monthly_total / len(bills) if bills else 0
                })
        
        return monthly_data
    
    @api.model
    def get_dashboard_chart_data(self, journal_id, period='30'):
        """API endpoint for fetching chart data with different periods"""
        journal = self.browse(journal_id)
        
        if period == '7':
            # Last 7 days
            return journal._get_journal_dashboard_graph_data()
        elif period == '30':
            # Last 30 days (default)
            return journal._get_journal_dashboard_graph_data()
        elif period == '90':
            # Weekly for last 3 months
            weekly_data = journal.get_weekly_data(weeks=12)
            return {
                'values': [
                    {
                        'x': item['period'],
                        'y': item['count'],
                        'amount': item['total'],
                        'label': f"{item['count']} - {item['formatted_total']}"
                    }
                    for item in weekly_data
                ],
                'period_type': 'weekly'
            }
        elif period == '365':
            # Monthly for last year
            monthly_data = journal.get_monthly_data(months=12)
            return {
                'values': [
                    {
                        'x': item['month_short'],
                        'y': item['count'],
                        'amount': item['total'],
                        'label': f"{item['count']} - {item['formatted_total']}"
                    }
                    for item in monthly_data
                ],
                'period_type': 'monthly'
            }
        
        return {'values': []}
    
    @api.model
    def ensure_dashboard_journals(self):
        """Ensure all journals show on dashboard and create missing ones if needed"""
        company = self.env.company
        
        # Define required journal types with their properties
        required_journals = [
            {'name': 'Customer Invoices', 'code': 'SAL', 'type': 'sale'},
            {'name': 'Vendor Bills', 'code': 'PUR', 'type': 'purchase'},
            {'name': 'Bank', 'code': 'BNK1', 'type': 'bank'},
            {'name': 'Cash', 'code': 'CSH1', 'type': 'cash'},
            {'name': 'Miscellaneous Operations', 'code': 'MISC', 'type': 'general'},
        ]
        
        for journal_data in required_journals:
            # Try to find existing journal by type
            existing = self.search([
                ('type', '=', journal_data['type']),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if existing:
                # Update existing journal to show on dashboard
                existing.write({'show_on_dashboard': True})
            else:
                # Create new journal if none exists
                self.create({
                    'name': journal_data['name'],
                    'code': journal_data['code'],
                    'type': journal_data['type'],
                    'company_id': company.id,
                    'show_on_dashboard': True,
                })
        
        return True