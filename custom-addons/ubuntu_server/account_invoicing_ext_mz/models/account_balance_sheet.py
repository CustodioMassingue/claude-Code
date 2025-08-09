from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json

class AccountBalanceSheet(models.TransientModel):
    _name = 'account.balance.sheet.report'
    _description = 'Balance Sheet Report'
    
    @api.model
    def get_balance_sheet_data(self, date_from=None, date_to=None, journals=None, company_id=None):
        """
        Generate Balance Sheet data with hierarchical structure
        """
        if not date_to:
            date_to = fields.Date.today()
        if not date_from:
            date_from = date(date_to.year, 1, 1)
        if not company_id:
            company_id = self.env.company.id
            
        domain = [
            ('date', '<=', date_to),
            ('company_id', '=', company_id),
            ('parent_state', '=', 'posted')
        ]
        
        if journals:
            domain.append(('journal_id', 'in', journals))
            
        move_lines = self.env['account.move.line'].search(domain)
        
        # Group accounts by type
        account_balances = {}
        for line in move_lines:
            account = line.account_id
            key = account.id
            if key not in account_balances:
                account_balances[key] = {
                    'account': account,
                    'balance': 0.0,
                    'name': account.name,
                    'code': account.code,
                    'account_type': account.account_type
                }
            account_balances[key]['balance'] += line.balance
            
        # Build hierarchical structure
        balance_sheet = {
            'date': date_to.strftime('%d/%m/%Y'),
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.symbol,
            'lines': []
        }
        
        # ASSETS
        assets_total = 0.0
        current_assets_total = 0.0
        fixed_assets_total = 0.0
        
        # Current Assets
        bank_cash = sum(acc['balance'] for acc in account_balances.values() 
                       if acc['account_type'] in ['asset_cash', 'liability_credit_card'])
        receivables = sum(acc['balance'] for acc in account_balances.values() 
                         if acc['account_type'] == 'asset_receivable')
        current_assets_other = sum(acc['balance'] for acc in account_balances.values() 
                                  if acc['account_type'] == 'asset_current')
        prepayments = sum(acc['balance'] for acc in account_balances.values() 
                         if acc['account_type'] == 'asset_prepayments')
        
        current_assets_total = bank_cash + receivables + current_assets_other + prepayments
        
        # Fixed Assets
        fixed_assets = sum(acc['balance'] for acc in account_balances.values() 
                          if acc['account_type'] in ['asset_fixed', 'asset_non_current'])
        fixed_assets_total = fixed_assets
        
        assets_total = current_assets_total + fixed_assets_total
        
        # LIABILITIES
        liabilities_total = 0.0
        current_liabilities_total = 0.0
        non_current_liabilities_total = 0.0
        
        # Current Liabilities
        payables = sum(acc['balance'] for acc in account_balances.values() 
                      if acc['account_type'] == 'liability_payable')
        current_liabilities_other = sum(acc['balance'] for acc in account_balances.values() 
                                       if acc['account_type'] == 'liability_current')
        
        current_liabilities_total = abs(payables + current_liabilities_other)
        
        # Non-current Liabilities
        non_current_liabilities = sum(acc['balance'] for acc in account_balances.values() 
                                     if acc['account_type'] == 'liability_non_current')
        non_current_liabilities_total = abs(non_current_liabilities)
        
        liabilities_total = current_liabilities_total + non_current_liabilities_total
        
        # EQUITY
        equity_total = 0.0
        unallocated_earnings = 0.0
        
        # Current Year Earnings
        current_year_earnings = sum(acc['balance'] for acc in account_balances.values() 
                                   if acc['account_type'] in ['income', 'income_other'])
        current_year_earnings -= sum(acc['balance'] for acc in account_balances.values() 
                                    if acc['account_type'] in ['expense', 'expense_depreciation'])
        
        # Previous Years Earnings
        retained_earnings = sum(acc['balance'] for acc in account_balances.values() 
                               if acc['account_type'] == 'equity_unaffected')
        
        unallocated_earnings = current_year_earnings + retained_earnings
        equity_total = unallocated_earnings
        
        # Build report lines
        lines = [
            {
                'id': 'assets',
                'name': 'ASSETS',
                'level': 0,
                'unfoldable': True,
                'unfolded': False,
                'balance': assets_total,
                'account_type': 'asset',
                'children': [
                    {
                        'id': 'current_assets',
                        'name': 'Current Assets',
                        'level': 1,
                        'unfoldable': True,
                        'unfolded': False,
                        'balance': current_assets_total,
                        'account_type': 'asset_current',
                        'children': [
                            {
                                'id': 'bank_cash',
                                'name': 'Bank and Cash Accounts',
                                'level': 2,
                                'unfoldable': False,
                                'balance': bank_cash,
                                'account_type': 'asset_cash'
                            },
                            {
                                'id': 'receivables',
                                'name': 'Receivables',
                                'level': 2,
                                'unfoldable': False,
                                'balance': receivables,
                                'account_type': 'asset_receivable'
                            },
                            {
                                'id': 'current_assets_other',
                                'name': 'Current Assets',
                                'level': 2,
                                'unfoldable': False,
                                'balance': current_assets_other,
                                'account_type': 'asset_current'
                            },
                            {
                                'id': 'prepayments',
                                'name': 'Prepayments',
                                'level': 2,
                                'unfoldable': False,
                                'balance': prepayments,
                                'account_type': 'asset_prepayments'
                            }
                        ]
                    },
                    {
                        'id': 'fixed_assets',
                        'name': 'Plus Fixed Assets',
                        'level': 1,
                        'unfoldable': False,
                        'balance': fixed_assets_total,
                        'account_type': 'asset_fixed'
                    },
                    {
                        'id': 'non_current_assets',
                        'name': 'Plus Non-current Assets',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'asset_non_current'
                    }
                ]
            },
            {
                'id': 'liabilities',
                'name': 'LIABILITIES',
                'level': 0,
                'unfoldable': True,
                'unfolded': False,
                'balance': liabilities_total,
                'account_type': 'liability',
                'children': [
                    {
                        'id': 'current_liabilities',
                        'name': 'Current Liabilities',
                        'level': 1,
                        'unfoldable': True,
                        'unfolded': False,
                        'balance': current_liabilities_total,
                        'account_type': 'liability_current',
                        'children': [
                            {
                                'id': 'payables',
                                'name': 'Current Liabilities',
                                'level': 2,
                                'unfoldable': False,
                                'balance': current_liabilities_total,
                                'account_type': 'liability_payable'
                            },
                            {
                                'id': 'other_payables',
                                'name': 'Payables',
                                'level': 2,
                                'unfoldable': False,
                                'balance': 0.0,
                                'account_type': 'liability_current'
                            }
                        ]
                    },
                    {
                        'id': 'non_current_liabilities',
                        'name': 'Plus Non-current Liabilities',
                        'level': 1,
                        'unfoldable': False,
                        'balance': non_current_liabilities_total,
                        'account_type': 'liability_non_current'
                    }
                ]
            },
            {
                'id': 'equity',
                'name': 'EQUITY',
                'level': 0,
                'unfoldable': True,
                'unfolded': False,
                'balance': equity_total,
                'account_type': 'equity',
                'children': [
                    {
                        'id': 'unallocated_earnings',
                        'name': 'Unallocated Earnings',
                        'level': 1,
                        'unfoldable': True,
                        'unfolded': False,
                        'balance': unallocated_earnings,
                        'account_type': 'equity',
                        'children': [
                            {
                                'id': 'current_year_earnings',
                                'name': 'Current Year Unallocated Earnings',
                                'level': 2,
                                'unfoldable': False,
                                'balance': current_year_earnings,
                                'account_type': 'equity'
                            },
                            {
                                'id': 'previous_years_earnings',
                                'name': 'Previous Years Unallocated Earnings',
                                'level': 2,
                                'unfoldable': False,
                                'balance': retained_earnings,
                                'account_type': 'equity_unaffected'
                            }
                        ]
                    },
                    {
                        'id': 'retained_earnings',
                        'name': 'Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity'
                    },
                    {
                        'id': 'current_year_retained',
                        'name': 'Current Year Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity'
                    },
                    {
                        'id': 'previous_years_retained',
                        'name': 'Previous Years Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity'
                    }
                ]
            },
            {
                'id': 'total_liabilities_equity',
                'name': 'LIABILITIES + EQUITY',
                'level': 0,
                'unfoldable': False,
                'unfolded': False,
                'balance': liabilities_total + equity_total,
                'account_type': 'total',
                'is_total': True
            }
        ]
        
        balance_sheet['lines'] = lines
        
        # Check if there are unposted entries
        unposted_moves = self.env['account.move'].search_count([
            ('state', '=', 'draft'),
            ('date', '<=', date_to),
            ('company_id', '=', company_id)
        ])
        
        balance_sheet['has_unposted'] = unposted_moves > 0
        balance_sheet['total_balance'] = assets_total == (liabilities_total + equity_total)
        
        return balance_sheet
    
    @api.model
    def export_to_excel(self, data):
        """Export balance sheet data to Excel format"""
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter library'))
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Balance Sheet')
        
        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1})
        
        # Write headers
        worksheet.write('A1', 'Balance Sheet', title_format)
        worksheet.write('A2', f"As of {data['date']}")
        worksheet.write('A3', data['company'])
        
        row = 5
        worksheet.write(row, 0, 'Account', header_format)
        worksheet.write(row, 1, 'Balance', header_format)
        
        # Write lines
        def write_lines(lines, row):
            for line in lines:
                col = line.get('level', 0)
                worksheet.write(row, col, line['name'])
                
                if line.get('is_total'):
                    worksheet.write(row, col + 1, line['balance'], total_format)
                else:
                    worksheet.write(row, col + 1, line['balance'], number_format)
                    
                row += 1
                
                if line.get('children'):
                    row = write_lines(line['children'], row)
                    
            return row
            
        write_lines(data['lines'], row + 1)
        
        workbook.close()
        output.seek(0)
        
        return base64.b64encode(output.read()).decode()