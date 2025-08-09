from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountTrialBalance(models.TransientModel):
    _name = 'account.trial.balance.report'
    _description = 'Trial Balance Report'
    
    @api.model
    def get_trial_balance_data(self, date_from=None, date_to=None, journals=None, 
                               analytic=None, posted_entries=True, comparison=None, company_id=None):
        """Get trial balance data for the report"""
        try:
            if not company_id:
                company_id = self.env.company.id
            
            # Set default dates if not provided
            if not date_to:
                date_to = fields.Date.today()
            else:
                if isinstance(date_to, str):
                    date_to = fields.Date.from_string(date_to)
                    
            if not date_from:
                # Get first day of the month for date_to
                date_from = date(date_to.year, date_to.month, 1)
            else:
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
            ]
            
            if posted_entries:
                domain.append(('parent_state', '=', 'posted'))
            
            if journals and journals != 'all':
                domain.append(('journal_id', 'in', journals))
            
            # Get all accounts
            accounts = self.env['account.account'].search([
                ('company_id', '=', company_id)
            ], order='code')
            
            accounts_data = []
            
            # Calculate totals
            total_initial_debit = 0.0
            total_initial_credit = 0.0
            total_period_debit = 0.0
            total_period_credit = 0.0
            total_end_debit = 0.0
            total_end_credit = 0.0
            
            for account in accounts:
                # Calculate initial balance (before date_from)
                initial_domain = domain + [
                    ('date', '<', date_from),
                    ('account_id', '=', account.id)
                ]
                initial_lines = self.env['account.move.line'].search(initial_domain)
                initial_balance = sum(initial_lines.mapped('balance'))
                initial_debit = max(initial_balance, 0.0)
                initial_credit = abs(min(initial_balance, 0.0))
                
                # Calculate period movements
                period_domain = domain + [
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('account_id', '=', account.id)
                ]
                period_lines = self.env['account.move.line'].search(period_domain)
                period_debit = sum(period_lines.mapped('debit'))
                period_credit = sum(period_lines.mapped('credit'))
                
                # Calculate end balance
                end_balance = initial_balance + period_debit - period_credit
                end_debit = max(end_balance, 0.0)
                end_credit = abs(min(end_balance, 0.0))
                
                # Skip accounts with no movements and zero balances
                if (initial_balance == 0 and period_debit == 0 and period_credit == 0 and end_balance == 0):
                    continue
                
                account_data = {
                    'id': f'account_{account.id}',
                    'code': account.code,
                    'name': account.name,
                    'initial_debit': initial_debit,
                    'initial_credit': initial_credit,
                    'period_debit': period_debit,
                    'period_credit': period_credit,
                    'end_debit': end_debit,
                    'end_credit': end_credit,
                    'has_info': True
                }
                
                accounts_data.append(account_data)
                
                # Add to totals
                total_initial_debit += initial_debit
                total_initial_credit += initial_credit
                total_period_debit += period_debit
                total_period_credit += period_credit
                total_end_debit += end_debit
                total_end_credit += end_credit
            
            # Format dates for return
            if date_from and isinstance(date_from, str):
                date_from_str = date_from
            elif date_from:
                date_from_str = date_from.strftime('%Y-%m-%d')
            else:
                date_from_str = ''
                
            if date_to and isinstance(date_to, str):
                date_to_str = date_to
            elif date_to:
                date_to_str = date_to.strftime('%Y-%m-%d')
            else:
                date_to_str = ''
            
            return {
                'accounts': accounts_data,
                'totals': {
                    'initial_debit': total_initial_debit,
                    'initial_credit': total_initial_credit,
                    'period_debit': total_period_debit,
                    'period_credit': total_period_credit,
                    'end_debit': total_end_debit,
                    'end_credit': total_end_credit
                },
                'company_name': self.env.company.name,
                'currency_symbol': 'MZN',
                'date_from': date_from_str,
                'date_to': date_to_str,
                'unposted_warning': not posted_entries
            }
            
        except Exception as e:
            _logger.error(f"Error getting trial balance data: {str(e)}")
            return {
                'accounts': [],
                'totals': {
                    'initial_debit': 0.0,
                    'initial_credit': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0,
                    'end_debit': 0.0,
                    'end_credit': 0.0
                },
                'company_name': '',
                'currency_symbol': 'MZN',
                'date_from': '',
                'date_to': '',
                'unposted_warning': False,
                'error': str(e)
            }