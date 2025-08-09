from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountAgedReceivable(models.TransientModel):
    _name = 'account.aged.receivable.report'
    _description = 'Aged Receivable Report'
    
    @api.model
    def get_aged_receivable_data(self, as_of_date=None, account_type='receivable', 
                                 partner_ids=None, period_length=30, 
                                 posted_entries=True, company_id=None):
        """Get aged receivable data for the report"""
        try:
            if not company_id:
                company_id = self.env.company.id
            
            # Set default date if not provided
            if not as_of_date:
                as_of_date = fields.Date.today()
            else:
                if isinstance(as_of_date, str):
                    as_of_date = fields.Date.from_string(as_of_date)
            
            # Calculate period dates
            date_periods = []
            for i in range(5):  # 5 periods: 1-30, 31-60, 61-90, 91-120, Older
                if i == 0:
                    date_periods.append({
                        'name': f'1-{period_length}',
                        'start': as_of_date - timedelta(days=period_length),
                        'end': as_of_date
                    })
                elif i < 4:
                    date_periods.append({
                        'name': f'{period_length * i + 1}-{period_length * (i + 1)}',
                        'start': as_of_date - timedelta(days=period_length * (i + 1)),
                        'end': as_of_date - timedelta(days=period_length * i + 1)
                    })
                else:
                    date_periods.append({
                        'name': 'Older',
                        'start': date(1900, 1, 1),
                        'end': as_of_date - timedelta(days=period_length * 4 + 1)
                    })
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
                ('date', '<=', as_of_date),
                ('reconciled', '=', False),
                ('parent_state', '=', 'posted') if posted_entries else ('parent_state', '!=', 'cancel')
            ]
            
            # Filter by account type
            if account_type == 'receivable':
                domain.append(('account_id.account_type', '=', 'asset_receivable'))
            elif account_type == 'payable':
                domain.append(('account_id.account_type', '=', 'liability_payable'))
            else:
                domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))
            
            if partner_ids:
                domain.append(('partner_id', 'in', partner_ids))
            
            # Get all unreconciled move lines
            move_lines = self.env['account.move.line'].search(domain)
            
            partners_dict = {}
            totals = {
                'invoice_date': 0.0,
                'at_date': 0.0,
                'period_1': 0.0,
                'period_2': 0.0,
                'period_3': 0.0,
                'period_4': 0.0,
                'older': 0.0,
                'total': 0.0
            }
            
            # Group move lines by partner
            for line in move_lines:
                partner = line.partner_id
                partner_key = partner.id if partner else 0
                
                if partner_key not in partners_dict:
                    partners_dict[partner_key] = {
                        'id': f'partner_{partner_key}',
                        'name': partner.name if partner else 'Unknown Partner',
                        'ref': partner.ref if partner else '',
                        'invoice_date': 0.0,
                        'at_date': 0.0,
                        'period_1': 0.0,
                        'period_2': 0.0,
                        'period_3': 0.0,
                        'period_4': 0.0,
                        'older': 0.0,
                        'total': 0.0,
                        'has_children': True,
                        'expanded': False,
                        'lines': []
                    }
                
                # Calculate balance
                balance = line.debit - line.credit
                if account_type == 'payable':
                    balance = -balance
                
                # Determine which period this line belongs to
                line_date = line.date
                days_overdue = (as_of_date - line_date).days
                
                # Add to appropriate period
                if days_overdue <= 0:
                    partners_dict[partner_key]['at_date'] += balance
                    totals['at_date'] += balance
                elif days_overdue <= period_length:
                    partners_dict[partner_key]['period_1'] += balance
                    totals['period_1'] += balance
                elif days_overdue <= period_length * 2:
                    partners_dict[partner_key]['period_2'] += balance
                    totals['period_2'] += balance
                elif days_overdue <= period_length * 3:
                    partners_dict[partner_key]['period_3'] += balance
                    totals['period_3'] += balance
                elif days_overdue <= period_length * 4:
                    partners_dict[partner_key]['period_4'] += balance
                    totals['period_4'] += balance
                else:
                    partners_dict[partner_key]['older'] += balance
                    totals['older'] += balance
                
                # Invoice date amount (original amount)
                partners_dict[partner_key]['invoice_date'] += balance
                totals['invoice_date'] += balance
                
                # Total
                partners_dict[partner_key]['total'] += balance
                totals['total'] += balance
                
                # Add line details
                line_data = {
                    'id': f'line_{line.id}',
                    'date': line.date.strftime('%d/%m/%Y'),
                    'move_name': line.move_id.name,
                    'ref': line.ref or line.move_id.ref or '',
                    'account_code': line.account_id.code,
                    'account_name': line.account_id.name,
                    'amount': balance,
                    'days_overdue': days_overdue
                }
                partners_dict[partner_key]['lines'].append(line_data)
            
            # Convert to list and sort by partner name
            partners_list = list(partners_dict.values())
            partners_list.sort(key=lambda x: x['name'])
            
            # Format date for return
            if as_of_date and isinstance(as_of_date, str):
                as_of_date_str = as_of_date
            elif as_of_date:
                as_of_date_str = as_of_date.strftime('%Y-%m-%d')
            else:
                as_of_date_str = ''
            
            return {
                'partners': partners_list,
                'totals': totals,
                'periods': [
                    {'name': 'Invoice Date', 'key': 'invoice_date'},
                    {'name': 'At Date', 'key': 'at_date'},
                    {'name': f'1-{period_length}', 'key': 'period_1'},
                    {'name': f'{period_length + 1}-{period_length * 2}', 'key': 'period_2'},
                    {'name': f'{period_length * 2 + 1}-{period_length * 3}', 'key': 'period_3'},
                    {'name': f'{period_length * 3 + 1}-{period_length * 4}', 'key': 'period_4'},
                    {'name': 'Older', 'key': 'older'},
                    {'name': 'Total', 'key': 'total'}
                ],
                'company_name': self.env.company.name,
                'currency_symbol': 'MT',
                'as_of_date': as_of_date_str,
                'account_type': account_type,
                'period_length': period_length,
                'unposted_warning': not posted_entries
            }
            
        except Exception as e:
            _logger.error(f"Error getting aged receivable data: {str(e)}")
            return {
                'partners': [],
                'totals': {
                    'invoice_date': 0.0,
                    'at_date': 0.0,
                    'period_1': 0.0,
                    'period_2': 0.0,
                    'period_3': 0.0,
                    'period_4': 0.0,
                    'older': 0.0,
                    'total': 0.0
                },
                'periods': [],
                'company_name': '',
                'currency_symbol': 'MT',
                'as_of_date': '',
                'account_type': 'receivable',
                'period_length': 30,
                'unposted_warning': False,
                'error': str(e)
            }