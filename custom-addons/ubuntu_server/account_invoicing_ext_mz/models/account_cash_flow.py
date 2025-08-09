from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountCashFlow(models.TransientModel):
    _name = 'account.cash.flow.report'
    _description = 'Cash Flow Statement Report'
    
    @api.model
    def get_cash_flow_data(self, date_from=None, date_to=None, journals=None, company_id=None):
        """Get cash flow data for the report"""
        try:
            if not company_id:
                company_id = self.env.company.id
            
            # Set default dates if not provided
            if not date_to:
                date_to = fields.Date.today()
            else:
                # Convert string to date if needed
                if isinstance(date_to, str):
                    date_to = fields.Date.from_string(date_to)
                    
            if not date_from:
                # Get first day of the month for date_to
                date_from = date(date_to.year, date_to.month, 1)
            else:
                # Convert string to date if needed
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted')
            ]
            
            if journals:
                domain.append(('journal_id', 'in', journals))
            
            # Get all move lines
            move_lines = self.env['account.move.line'].search(domain)
            
            # Get cash and cash equivalent accounts (typically bank and cash accounts)
            cash_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['asset_cash', 'asset_bank'])
            ])
            
            # Calculate beginning balance (balance at start of period)
            beginning_domain = [
                ('company_id', '=', company_id),
                ('date', '<', date_from),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', cash_accounts.ids)
            ]
            beginning_lines = self.env['account.move.line'].search(beginning_domain)
            beginning_balance = sum(beginning_lines.mapped('balance'))
            
            # Calculate cash flows during the period
            period_lines = move_lines.filtered(lambda l: l.account_id.id in cash_accounts.ids)
            
            # Categorize cash flows
            operating_cash = 0.0
            investing_cash = 0.0
            financing_cash = 0.0
            unclassified_cash = 0.0
            
            operating_cash_in = []
            operating_cash_out = []
            investing_cash_in = []
            investing_cash_out = []
            financing_cash_in = []
            financing_cash_out = []
            unclassified_cash_in = []
            unclassified_cash_out = []
            
            for line in period_lines:
                amount = line.balance
                account_name = f"{line.account_id.code} {line.account_id.name}"
                
                # Categorize based on journal type and account type
                # This is simplified - in real implementation, you'd have more sophisticated categorization
                if line.journal_id.type in ['sale', 'purchase']:
                    # Operating activities
                    operating_cash += amount
                    if amount > 0:
                        operating_cash_in.append({
                            'id': f'operating_in_{line.id}',
                            'name': account_name,
                            'amount': amount,
                            'level': 4
                        })
                    else:
                        operating_cash_out.append({
                            'id': f'operating_out_{line.id}',
                            'name': account_name,
                            'amount': abs(amount),
                            'level': 4
                        })
                elif line.journal_id.type == 'bank':
                    # Check if it's investment or financing based on account
                    if 'loan' in line.account_id.name.lower() or 'financing' in line.account_id.name.lower():
                        financing_cash += amount
                        if amount > 0:
                            financing_cash_in.append({
                                'id': f'financing_in_{line.id}',
                                'name': account_name,
                                'amount': amount,
                                'level': 4
                            })
                        else:
                            financing_cash_out.append({
                                'id': f'financing_out_{line.id}',
                                'name': account_name,
                                'amount': abs(amount),
                                'level': 4
                            })
                    elif 'investment' in line.account_id.name.lower() or 'asset' in line.account_id.name.lower():
                        investing_cash += amount
                        if amount > 0:
                            investing_cash_in.append({
                                'id': f'investing_in_{line.id}',
                                'name': account_name,
                                'amount': amount,
                                'level': 4
                            })
                        else:
                            investing_cash_out.append({
                                'id': f'investing_out_{line.id}',
                                'name': account_name,
                                'amount': abs(amount),
                                'level': 4
                            })
                    else:
                        # Unclassified
                        unclassified_cash += amount
                        if amount > 0:
                            unclassified_cash_in.append({
                                'id': f'unclassified_in_{line.id}',
                                'name': account_name,
                                'amount': amount,
                                'level': 4
                            })
                        else:
                            unclassified_cash_out.append({
                                'id': f'unclassified_out_{line.id}',
                                'name': account_name,
                                'amount': abs(amount),
                                'level': 4
                            })
                else:
                    # Unclassified
                    unclassified_cash += amount
                    if amount > 0:
                        unclassified_cash_in.append({
                            'id': f'unclassified_in_{line.id}',
                            'name': account_name,
                            'amount': amount,
                            'level': 4
                        })
                    else:
                        unclassified_cash_out.append({
                            'id': f'unclassified_out_{line.id}',
                            'name': account_name,
                            'amount': abs(amount),
                            'level': 4
                        })
            
            # Calculate net increase and closing balance
            net_increase = operating_cash + investing_cash + financing_cash + unclassified_cash
            closing_balance = beginning_balance + net_increase
            
            # Build the hierarchical structure
            lines = []
            
            # Beginning balance
            lines.append({
                'id': 'beginning_balance',
                'name': 'Cash and cash equivalents, beginning of period',
                'amount': beginning_balance,
                'level': 0,
                'is_header': True,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
            # Net increase section
            net_increase_line = {
                'id': 'net_increase',
                'name': 'Net increase in cash and cash equivalents',
                'amount': net_increase,
                'level': 0,
                'is_header': True,
                'has_children': True,
                'expanded': True,
                'children': []
            }
            
            # Operating activities
            operating_line = {
                'id': 'operating',
                'name': 'Cash flows from operating activities',
                'amount': operating_cash,
                'level': 1,
                'has_children': True,
                'expanded': False,
                'children': []
            }
            
            if operating_cash_in:
                operating_line['children'].append({
                    'id': 'operating_receipts',
                    'name': 'Advance Payments received from customers',
                    'amount': sum(item['amount'] for item in operating_cash_in),
                    'level': 2,
                    'has_children': False,
                    'expanded': False,
                    'children': []
                })
            
            if operating_cash_out:
                operating_line['children'].append({
                    'id': 'operating_payments',
                    'name': 'Advance payments made to suppliers',
                    'amount': sum(item['amount'] for item in operating_cash_out),
                    'level': 2,
                    'has_children': False,
                    'expanded': False,
                    'children': []
                })
            
            operating_line['children'].append({
                'id': 'operating_received',
                'name': 'Cash received from operating activities',
                'amount': sum(item['amount'] for item in operating_cash_in),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
            operating_line['children'].append({
                'id': 'operating_paid',
                'name': 'Cash paid for operating activities',
                'amount': sum(item['amount'] for item in operating_cash_out),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
            net_increase_line['children'].append(operating_line)
            
            # Investing activities
            investing_line = {
                'id': 'investing',
                'name': 'Cash flows from investing & extraordinary activities',
                'amount': investing_cash,
                'level': 1,
                'has_children': True,
                'expanded': False,
                'children': []
            }
            
            # Cash in from investing (always show, even if empty)
            cash_in_line = {
                'id': 'investing_cash_in',
                'name': 'Cash in',
                'amount': sum(item['amount'] for item in investing_cash_in),
                'level': 2,
                'has_children': len(investing_cash_in) > 0,
                'expanded': False,
                'children': investing_cash_in
            }
            investing_line['children'].append(cash_in_line)
            
            # Cash out from investing
            cash_out_line = {
                'id': 'investing_cash_out',
                'name': 'Cash out',
                'amount': sum(item['amount'] for item in investing_cash_out),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            }
            investing_line['children'].append(cash_out_line)
            
            net_increase_line['children'].append(investing_line)
            
            # Financing activities
            financing_line = {
                'id': 'financing',
                'name': 'Cash flows from financing activities',
                'amount': financing_cash,
                'level': 1,
                'has_children': True,
                'expanded': False,
                'children': []
            }
            
            financing_line['children'].append({
                'id': 'financing_cash_in',
                'name': 'Cash in',
                'amount': sum(item['amount'] for item in financing_cash_in),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
            financing_line['children'].append({
                'id': 'financing_cash_out',
                'name': 'Cash out',
                'amount': sum(item['amount'] for item in financing_cash_out),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
            net_increase_line['children'].append(financing_line)
            
            # Unclassified activities
            unclassified_line = {
                'id': 'unclassified',
                'name': 'Cash flows from unclassified activities',
                'amount': unclassified_cash,
                'level': 1,
                'has_children': True,
                'expanded': False,
                'children': []
            }
            
            # Cash in from unclassified (always show, even if empty)
            cash_in_line = {
                'id': 'unclassified_cash_in',
                'name': 'Cash in',
                'amount': sum(item['amount'] for item in unclassified_cash_in),
                'level': 2,
                'has_children': len(unclassified_cash_in) > 0,
                'expanded': False,
                'children': unclassified_cash_in
            }
            unclassified_line['children'].append(cash_in_line)
            
            # Cash out from unclassified
            cash_out_line = {
                'id': 'unclassified_cash_out',
                'name': 'Cash out',
                'amount': sum(item['amount'] for item in unclassified_cash_out),
                'level': 2,
                'has_children': False,
                'expanded': False,
                'children': []
            }
            unclassified_line['children'].append(cash_out_line)
            
            net_increase_line['children'].append(unclassified_line)
            
            lines.append(net_increase_line)
            
            # Closing balance
            lines.append({
                'id': 'closing_balance',
                'name': 'Cash and cash equivalents, closing balance',
                'amount': closing_balance,
                'level': 0,
                'is_header': True,
                'has_children': False,
                'expanded': False,
                'children': []
            })
            
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
                'lines': lines,
                'company_name': self.env.company.name,
                'date_from': date_from_str,
                'date_to': date_to_str
            }
            
        except Exception as e:
            _logger.error(f"Error getting cash flow data: {str(e)}")
            return {
                'lines': [],
                'company_name': '',
                'date_from': '',
                'date_to': '',
                'error': str(e)
            }