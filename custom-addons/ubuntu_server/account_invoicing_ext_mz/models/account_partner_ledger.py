from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountPartnerLedger(models.TransientModel):
    _name = 'account.partner.ledger.report'
    _description = 'Partner Ledger Report'
    
    @api.model
    def get_partner_ledger_data(self, date_from=None, date_to=None, partner_ids=None, 
                                account_type='all', posted_entries=True, company_id=None):
        """Get partner ledger data for the report"""
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
                # Get first day of the year for date_to
                date_from = date(date_to.year, 1, 1)
            else:
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted') if posted_entries else ('parent_state', '!=', 'cancel')
            ]
            
            # Filter by account type (receivable/payable)
            if account_type == 'receivable':
                domain.append(('account_id.account_type', '=', 'asset_receivable'))
            elif account_type == 'payable':
                domain.append(('account_id.account_type', '=', 'liability_payable'))
            else:
                domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))
            
            if partner_ids:
                domain.append(('partner_id', 'in', partner_ids))
            
            # Get all move lines
            move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')
            
            partners_dict = {}
            
            # Group move lines by partner
            for line in move_lines:
                partner = line.partner_id
                partner_key = partner.id if partner else 0
                
                if partner_key not in partners_dict:
                    partners_dict[partner_key] = {
                        'id': f'partner_{partner_key}',
                        'name': partner.name if partner else 'Unknown Partner',
                        'ref': partner.ref if partner else '',
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'initial_balance': 0.0,
                        'has_children': True,
                        'expanded': False,
                        'lines': []
                    }
                
                # Add line details
                line_data = {
                    'id': f'line_{line.id}',
                    'date': line.date.strftime('%d/%m/%Y'),
                    'move_name': line.move_id.name,
                    'ref': line.ref or line.move_id.ref or '',
                    'account_code': line.account_id.code,
                    'account_name': line.account_id.name,
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': line.debit - line.credit,
                    'cumulative_balance': 0.0,  # Will be calculated later
                    'currency': line.currency_id.name if line.currency_id else '',
                    'amount_currency': line.amount_currency if line.currency_id else 0.0
                }
                
                partners_dict[partner_key]['lines'].append(line_data)
                partners_dict[partner_key]['debit'] += line.debit
                partners_dict[partner_key]['credit'] += line.credit
                partners_dict[partner_key]['balance'] += (line.debit - line.credit)
            
            # Calculate cumulative balances for each partner's lines
            for partner_data in partners_dict.values():
                cumulative = partner_data['initial_balance']
                for line in partner_data['lines']:
                    cumulative += line['balance']
                    line['cumulative_balance'] = cumulative
            
            # Convert to list and sort by partner name
            partners_list = list(partners_dict.values())
            partners_list.sort(key=lambda x: x['name'])
            
            # Calculate totals
            total_debit = sum(p['debit'] for p in partners_list)
            total_credit = sum(p['credit'] for p in partners_list)
            total_balance = sum(p['balance'] for p in partners_list)
            
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
                'partners': partners_list,
                'totals': {
                    'debit': total_debit,
                    'credit': total_credit,
                    'balance': total_balance
                },
                'company_name': self.env.company.name,
                'currency_symbol': 'MT',
                'date_from': date_from_str,
                'date_to': date_to_str,
                'account_type': account_type,
                'unposted_warning': not posted_entries
            }
            
        except Exception as e:
            _logger.error(f"Error getting partner ledger data: {str(e)}")
            return {
                'partners': [],
                'totals': {
                    'debit': 0.0,
                    'credit': 0.0,
                    'balance': 0.0
                },
                'company_name': '',
                'currency_symbol': 'MT',
                'date_from': '',
                'date_to': '',
                'account_type': 'all',
                'unposted_warning': False,
                'error': str(e)
            }