# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import json

class MozFinancialReport(models.AbstractModel):
    _name = 'report.mozambique_accounting.financial_report'
    _description = 'Financial Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values"""
        if not data:
            data = {}
        
        company = self.env.company
        date_from = data.get('date_from', fields.Date.today().replace(day=1))
        date_to = data.get('date_to', fields.Date.today())
        
        # Get financial data
        balance_sheet = self._get_balance_sheet(company, date_to)
        profit_loss = self._get_profit_loss(company, date_from, date_to)
        trial_balance = self._get_trial_balance(company, date_from, date_to)
        
        return {
            'doc_ids': docids,
            'doc_model': 'res.company',
            'docs': company,
            'data': data,
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'balance_sheet': balance_sheet,
            'profit_loss': profit_loss,
            'trial_balance': trial_balance,
        }
    
    def _get_balance_sheet(self, company, date):
        """Get balance sheet data"""
        result = {
            'assets': {
                'current': [],
                'fixed': [],
                'total': 0
            },
            'liabilities': {
                'current': [],
                'long_term': [],
                'total': 0
            },
            'equity': {
                'items': [],
                'total': 0
            }
        }
        
        # Current Assets
        current_asset_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', 'in', ['asset_cash', 'asset_current', 'asset_receivable'])
        ])
        
        for account in current_asset_accounts:
            balance = self._get_account_balance(account, date)
            if balance != 0:
                result['assets']['current'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance
                })
                result['assets']['total'] += balance
        
        # Fixed Assets
        fixed_asset_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'asset_fixed')
        ])
        
        for account in fixed_asset_accounts:
            balance = self._get_account_balance(account, date)
            if balance != 0:
                result['assets']['fixed'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance
                })
                result['assets']['total'] += balance
        
        # Current Liabilities
        current_liability_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', 'in', ['liability_current', 'liability_payable'])
        ])
        
        for account in current_liability_accounts:
            balance = abs(self._get_account_balance(account, date))
            if balance != 0:
                result['liabilities']['current'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance
                })
                result['liabilities']['total'] += balance
        
        # Equity
        equity_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'equity')
        ])
        
        for account in equity_accounts:
            balance = abs(self._get_account_balance(account, date))
            if balance != 0:
                result['equity']['items'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance
                })
                result['equity']['total'] += balance
        
        return result
    
    def _get_profit_loss(self, company, date_from, date_to):
        """Get profit and loss data"""
        result = {
            'revenue': {
                'items': [],
                'total': 0
            },
            'expenses': {
                'items': [],
                'total': 0
            },
            'net_profit': 0
        }
        
        # Revenue
        revenue_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', 'in', ['income', 'income_other'])
        ])
        
        for account in revenue_accounts:
            credit = self._get_account_movement(account, date_from, date_to, 'credit')
            debit = self._get_account_movement(account, date_from, date_to, 'debit')
            balance = credit - debit
            
            if balance != 0:
                result['revenue']['items'].append({
                    'code': account.code,
                    'name': account.name,
                    'amount': balance
                })
                result['revenue']['total'] += balance
        
        # Expenses
        expense_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation'])
        ])
        
        for account in expense_accounts:
            debit = self._get_account_movement(account, date_from, date_to, 'debit')
            credit = self._get_account_movement(account, date_from, date_to, 'credit')
            balance = debit - credit
            
            if balance != 0:
                result['expenses']['items'].append({
                    'code': account.code,
                    'name': account.name,
                    'amount': balance
                })
                result['expenses']['total'] += balance
        
        result['net_profit'] = result['revenue']['total'] - result['expenses']['total']
        
        return result
    
    def _get_trial_balance(self, company, date_from, date_to):
        """Get trial balance data"""
        result = []
        
        accounts = self.env['account.account'].search([
            ('company_id', '=', company.id)
        ], order='code')
        
        total_debit = 0
        total_credit = 0
        
        for account in accounts:
            # Opening balance
            opening_debit = self._get_account_balance(account, date_from, 'debit')
            opening_credit = self._get_account_balance(account, date_from, 'credit')
            
            # Period movements
            period_debit = self._get_account_movement(account, date_from, date_to, 'debit')
            period_credit = self._get_account_movement(account, date_from, date_to, 'credit')
            
            # Closing balance
            closing_debit = opening_debit + period_debit
            closing_credit = opening_credit + period_credit
            
            if any([opening_debit, opening_credit, period_debit, period_credit]):
                result.append({
                    'code': account.code,
                    'name': account.name,
                    'opening_debit': opening_debit,
                    'opening_credit': opening_credit,
                    'period_debit': period_debit,
                    'period_credit': period_credit,
                    'closing_debit': closing_debit,
                    'closing_credit': closing_credit,
                })
                
                total_debit += closing_debit
                total_credit += closing_credit
        
        return {
            'lines': result,
            'total_debit': total_debit,
            'total_credit': total_credit
        }
    
    def _get_account_balance(self, account, date, balance_type='balance'):
        """Get account balance at a specific date"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '<=', date),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', account.company_id.id)
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        if balance_type == 'debit':
            return sum(move_lines.mapped('debit'))
        elif balance_type == 'credit':
            return sum(move_lines.mapped('credit'))
        else:
            return sum(move_lines.mapped('debit')) - sum(move_lines.mapped('credit'))
    
    def _get_account_movement(self, account, date_from, date_to, movement_type):
        """Get account movements in a period"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', account.company_id.id)
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        if movement_type == 'debit':
            return sum(move_lines.mapped('debit'))
        else:
            return sum(move_lines.mapped('credit'))