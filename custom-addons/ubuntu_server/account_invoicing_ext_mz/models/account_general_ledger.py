from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountGeneralLedger(models.TransientModel):
    _name = 'account.general.ledger.report'
    _description = 'General Ledger Report'
    
    @api.model
    def get_general_ledger_data(self, date_from=None, date_to=None, journals=None, 
                                analytic=None, posted_entries=True, company_id=None):
        """Get general ledger data for the report"""
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
                # Get first day of the fiscal year
                fiscal_year_start = date(date_to.year, 1, 1)
                date_from = fiscal_year_start
            else:
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            
            if posted_entries:
                domain.append(('parent_state', '=', 'posted'))
            
            if journals and journals != 'all':
                domain.append(('journal_id', 'in', journals))
            
            # Get all accounts with movements in the period
            move_lines = self.env['account.move.line'].search(domain, order='account_id, date, id')
            
            # Group by account
            accounts_data = {}
            for line in move_lines:
                account = line.account_id
                account_key = account.id
                
                if account_key not in accounts_data:
                    # Calculate initial balance (before date_from)
                    initial_domain = [
                        ('company_id', '=', company_id),
                        ('date', '<', date_from),
                        ('account_id', '=', account.id)
                    ]
                    if posted_entries:
                        initial_domain.append(('parent_state', '=', 'posted'))
                    
                    initial_lines = self.env['account.move.line'].search(initial_domain)
                    initial_balance = sum(initial_lines.mapped('balance'))
                    
                    accounts_data[account_key] = {
                        'id': f'account_{account.id}',
                        'code': account.code,
                        'name': account.name,
                        'account_type': account.account_type,
                        'initial_balance': initial_balance,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': initial_balance,
                        'has_children': True,
                        'expanded': False,
                        'lines': []
                    }
                
                # Add line details
                line_data = {
                    'id': f'line_{line.id}',
                    'date': line.date.strftime('%d/%m/%Y'),
                    'move_name': line.move_id.name,
                    'ref': line.ref or '',
                    'partner': line.partner_id.name if line.partner_id else '',
                    'currency': line.currency_id.name if line.currency_id else 'MZN',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': 0.0,  # Will calculate running balance
                    'communication': line.name or '',
                    'journal_items': f"{line.move_id.name} - {line.name}" if line.name else line.move_id.name
                }
                
                accounts_data[account_key]['lines'].append(line_data)
                accounts_data[account_key]['debit'] += line.debit
                accounts_data[account_key]['credit'] += line.credit
                accounts_data[account_key]['balance'] += line.balance
            
            # Calculate running balances for each account's lines
            for account_data in accounts_data.values():
                running_balance = account_data['initial_balance']
                for line in account_data['lines']:
                    running_balance += line['debit'] - line['credit']
                    line['balance'] = running_balance
            
            # Convert to list and sort by account code
            accounts_list = list(accounts_data.values())
            accounts_list.sort(key=lambda x: x['code'])
            
            # Calculate totals
            total_debit = sum(acc['debit'] for acc in accounts_list)
            total_credit = sum(acc['credit'] for acc in accounts_list)
            total_balance = sum(acc['balance'] for acc in accounts_list)
            
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
                'accounts': accounts_list,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_balance': total_balance,
                'company_name': self.env.company.name,
                'currency_symbol': 'MZN',
                'date_from': date_from_str,
                'date_to': date_to_str,
                'unposted_warning': not posted_entries
            }
            
        except Exception as e:
            _logger.error(f"Error getting general ledger data: {str(e)}")
            return {
                'accounts': [],
                'total_debit': 0.0,
                'total_credit': 0.0,
                'total_balance': 0.0,
                'company_name': '',
                'currency_symbol': 'MZN',
                'date_from': '',
                'date_to': '',
                'unposted_warning': False,
                'error': str(e)
            }