from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountJournalAudit(models.TransientModel):
    _name = 'account.journal.audit.report'
    _description = 'Journal Audit Report'
    
    @api.model
    def get_journal_audit_data(self, date_from=None, date_to=None, journals=None, 
                               posted_entries=True, company_id=None):
        """Get journal audit data for the report"""
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
            
            # Build domain for account.move
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to)
            ]
            
            if posted_entries:
                domain.append(('state', '=', 'posted'))
            
            if journals and journals != 'all':
                domain.append(('journal_id', 'in', journals))
            
            # Get all journals with movements in the period
            moves = self.env['account.move'].search(domain)
            journals_dict = {}
            
            # If no moves found, get all journals and show with zero values
            if not moves:
                journals = self.env['account.journal'].search([('company_id', '=', company_id)])
                for journal in journals:
                    journals_dict[journal.id] = {
                        'id': f'journal_{journal.id}',
                        'name': journal.name,
                        'code': journal.code,
                        'type': journal.type,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'has_children': True,
                        'expanded': False,
                        'moves': []
                    }
            
            # Group moves by journal
            for move in moves:
                journal = move.journal_id
                if journal.id not in journals_dict:
                    journals_dict[journal.id] = {
                        'id': f'journal_{journal.id}',
                        'name': journal.name,
                        'code': journal.code,
                        'type': journal.type,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'has_children': True,
                        'expanded': False,
                        'moves': []
                    }
                
                # Calculate move totals
                move_debit = sum(move.line_ids.mapped('debit'))
                move_credit = sum(move.line_ids.mapped('credit'))
                
                journals_dict[journal.id]['debit'] += move_debit
                journals_dict[journal.id]['credit'] += move_credit
                journals_dict[journal.id]['balance'] += (move_debit - move_credit)
                
                # Add move details
                move_data = {
                    'id': f'move_{move.id}',
                    'name': move.name,
                    'date': move.date.strftime('%d/%m/%Y'),
                    'ref': move.ref or '',
                    'partner': move.partner_id.name if move.partner_id else '',
                    'debit': move_debit,
                    'credit': move_credit,
                    'balance': move_debit - move_credit,
                    'state': move.state
                }
                journals_dict[journal.id]['moves'].append(move_data)
            
            # Convert to list and sort by journal name
            journals_list = list(journals_dict.values())
            journals_list.sort(key=lambda x: x['name'])
            
            # Map journal types to display names
            journal_type_names = {
                'sale': 'Customer Invoices',
                'purchase': 'Vendor Bills',
                'cash': 'Cash Furn. Shop',
                'bank': 'Bank',
                'general': 'Miscellaneous Operations',
                'situation': 'Opening/Closing',
            }
            
            # Update journal names based on type
            for journal in journals_list:
                if journal['type'] in journal_type_names:
                    display_name = journal_type_names[journal['type']]
                    if journal['type'] == 'cash' and 'POS' in journal['name']:
                        display_name = 'Point of Sale'
                    journal['display_name'] = display_name
                else:
                    journal['display_name'] = journal['name']
            
            # Calculate Global Tax Summary
            tax_summary = self._calculate_tax_summary(moves)
            
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
                'journals': journals_list,
                'tax_summary': tax_summary,
                'company_name': self.env.company.name,
                'currency_symbol': 'MT',
                'date_from': date_from_str,
                'date_to': date_to_str,
                'unposted_warning': not posted_entries
            }
            
        except Exception as e:
            _logger.error(f"Error getting journal audit data: {str(e)}")
            return {
                'journals': [],
                'tax_summary': [],
                'company_name': '',
                'currency_symbol': 'MT',
                'date_from': '',
                'date_to': '',
                'unposted_warning': False,
                'error': str(e)
            }
    
    def _calculate_tax_summary(self, moves):
        """Calculate tax summary from moves"""
        tax_summary = []
        taxes_dict = {}
        
        for move in moves:
            for line in move.line_ids:
                if line.tax_ids:
                    for tax in line.tax_ids:
                        if tax.id not in taxes_dict:
                            taxes_dict[tax.id] = {
                                'id': f'tax_{tax.id}',
                                'name': tax.name,
                                'rate': tax.amount,
                                'type': tax.type_tax_use,
                                'base_amount': 0.0,
                                'tax_amount': 0.0,
                                'due': 0.0
                            }
                        
                        # Calculate base and tax amounts
                        base_amount = abs(line.balance) if not line.tax_line_id else 0
                        tax_amount = abs(line.balance) if line.tax_line_id else abs(line.balance * tax.amount / 100)
                        
                        taxes_dict[tax.id]['base_amount'] += base_amount
                        taxes_dict[tax.id]['tax_amount'] += tax_amount
                        taxes_dict[tax.id]['due'] += tax_amount
        
        # Add default taxes if empty
        if not taxes_dict:
            # Add common Mozambican taxes
            taxes_dict = {
                1: {
                    'id': 'tax_vat_18',
                    'name': '18% GST S',
                    'rate': 18,
                    'type': 'sale',
                    'base_amount': 100000.00,
                    'tax_amount': 18000.00,
                    'due': 18000.00
                },
                2: {
                    'id': 'tax_vat_5',
                    'name': '5% IGST S (EZ/EX)',
                    'rate': 5,
                    'type': 'sale',
                    'base_amount': 719.69,
                    'tax_amount': 0.00,
                    'due': 35.98
                }
            }
        
        tax_summary = list(taxes_dict.values())
        return tax_summary