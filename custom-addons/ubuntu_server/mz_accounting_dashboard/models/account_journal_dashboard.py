# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import formatLang, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import json
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    kanban_dashboard = fields.Text(compute='_compute_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
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
            'number_to_send': len(to_send),
            'sum_to_send': formatLang(self.env, to_send_total, currency_obj=currency),
            'number_overdue': len(overdue),
            'sum_overdue': formatLang(self.env, overdue_total, currency_obj=currency),
            'number_to_check': len(to_check),
            'sum_to_check': formatLang(self.env, to_check_total, currency_obj=currency),
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
            'last_sync': last_sync or _('Never'),
            'to_reconcile': unreconciled_count,
            'outstanding_payments_count': len(outstanding_payments),
            'outstanding_payments_total': formatLang(self.env, outstanding_payments_total, currency_obj=currency),
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
        """Get graph data for the last 30 days"""
        self.ensure_one()
        
        data = []
        today = fields.Date.today()
        
        # Get data for last 30 days
        for i in range(30, -1, -1):
            current_date = today - timedelta(days=i)
            
            if self.type == 'sale':
                # Count invoices created on this date
                invoices = self.env['account.move'].search_count([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '=', current_date),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'out_invoice')
                ])
                data.append({'x': current_date.strftime('%Y-%m-%d'), 'y': invoices, 'name': _('Invoices')})
                
            elif self.type == 'purchase':
                # Count bills created on this date
                bills = self.env['account.move'].search_count([
                    ('journal_id', '=', self.id),
                    ('invoice_date', '=', current_date),
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'in_invoice')
                ])
                data.append({'x': current_date.strftime('%Y-%m-%d'), 'y': bills, 'name': _('Bills')})
        
        return {'values': data}
    
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
        """Upload document action"""
        self.ensure_one()
        
        # This would typically open a document upload wizard
        # For now, create a new draft bill/invoice for document attachment
        if self.type == 'purchase':
            return self.action_create_purchase_bill()
        elif self.type == 'sale':
            return self.action_create_sale_invoice()
        
        return True
    
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