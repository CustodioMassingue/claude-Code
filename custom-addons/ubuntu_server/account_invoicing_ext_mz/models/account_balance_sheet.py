from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json

class AccountBalanceSheet(models.TransientModel):
    _name = 'account.balance.sheet.report'
    _description = 'Balance Sheet Report'
    
    @api.model
    def get_balance_sheet_data(self, date_from=None, date_to=None, journals=None, company_id=None, 
                              only_posted=True, include_draft=False, hide_zero=False,
                              comparison=False, comparison_date=None, comparison_mode='none',
                              analytic_accounts=None, analytic_plans=None, **kwargs):
        """
        Generate Balance Sheet data with hierarchical structure
        """
        if not date_to:
            date_to = fields.Date.today()
        if isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)
        if not date_from:
            date_from = date(date_to.year, 1, 1)
        if not company_id:
            company_id = self.env.company.id
            
        domain = [
            ('date', '<=', date_to),
            ('company_id', '=', company_id),
        ]
        
        # Filter by posted state
        if only_posted and not include_draft:
            domain.append(('parent_state', '=', 'posted'))
        elif not only_posted or include_draft:
            domain.append(('parent_state', 'in', ['posted', 'draft']))
        
        if journals:
            domain.append(('journal_id', 'in', journals))
        
        # Apply analytic filtering if provided
        if analytic_accounts:
            domain.append(('analytic_account_id', 'in', analytic_accounts))
            
        move_lines = self.env['account.move.line'].search(domain)
        
        # Group accounts by type with details
        account_balances = {}
        accounts_detail = {
            'asset_cash': [],
            'liability_credit_card': [],
            'asset_receivable': [],
            'asset_current': [],
            'asset_prepayments': [],
            'asset_fixed': [],
            'asset_non_current': [],
            'liability_payable': [],
            'liability_current': [],
            'liability_non_current': [],
            'equity': [],
            'equity_unaffected': [],
            'income': [],
            'income_other': [],
            'expense': [],
            'expense_depreciation': []
        }
        
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
        
        # Organize accounts by type for detail view
        for acc_id, acc_data in account_balances.items():
            acc_type = acc_data['account_type']
            if acc_type in accounts_detail and acc_data['balance'] != 0:
                accounts_detail[acc_type].append({
                    'id': f'account_{acc_id}',
                    'code': acc_data['code'],
                    'name': f"{acc_data['code']} {acc_data['name']}" if acc_data['code'] else acc_data['name'],
                    'balance': acc_data['balance'],
                    'level': 3,
                    'unfoldable': False,
                    'account_type': acc_type
                })
        
        # Sort accounts by code
        for acc_type in accounts_detail:
            accounts_detail[acc_type].sort(key=lambda x: x.get('code', ''))
            
        # Build hierarchical structure
        balance_sheet = {
            'date': date_to.strftime('%d/%m/%Y'),
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.symbol,
            'lines': []
        }
        
        # Calculate totals
        # Bank and Cash
        bank_cash_accounts = accounts_detail.get('asset_cash', []) + accounts_detail.get('liability_credit_card', [])
        bank_cash_total = sum(acc['balance'] for acc in bank_cash_accounts)
        
        # Receivables
        receivables_accounts = accounts_detail.get('asset_receivable', [])
        receivables_total = sum(acc['balance'] for acc in receivables_accounts)
        
        # Current Assets Other
        current_assets_accounts = accounts_detail.get('asset_current', [])
        current_assets_other_total = sum(acc['balance'] for acc in current_assets_accounts)
        
        # Prepayments
        prepayments_accounts = accounts_detail.get('asset_prepayments', [])
        prepayments_total = sum(acc['balance'] for acc in prepayments_accounts)
        
        current_assets_total = bank_cash_total + receivables_total + current_assets_other_total + prepayments_total
        
        # Fixed Assets
        fixed_assets_accounts = accounts_detail.get('asset_fixed', []) + accounts_detail.get('asset_non_current', [])
        fixed_assets_total = sum(acc['balance'] for acc in fixed_assets_accounts)
        
        assets_total = current_assets_total + fixed_assets_total
        
        # Current Liabilities
        current_liabilities_accounts = accounts_detail.get('liability_current', [])
        current_liabilities_total = abs(sum(acc['balance'] for acc in current_liabilities_accounts))
        
        # Payables
        payables_accounts = accounts_detail.get('liability_payable', [])
        payables_total = abs(sum(acc['balance'] for acc in payables_accounts))
        
        # Non-current Liabilities
        non_current_liabilities_accounts = accounts_detail.get('liability_non_current', [])
        non_current_liabilities_total = abs(sum(acc['balance'] for acc in non_current_liabilities_accounts))
        
        liabilities_total = current_liabilities_total + payables_total + non_current_liabilities_total
        
        # Equity calculations
        current_year_earnings = sum(acc['balance'] for acc in accounts_detail.get('income', []) + accounts_detail.get('income_other', []))
        current_year_earnings -= sum(acc['balance'] for acc in accounts_detail.get('expense', []) + accounts_detail.get('expense_depreciation', []))
        
        retained_earnings = sum(acc['balance'] for acc in accounts_detail.get('equity_unaffected', []))
        unallocated_earnings = current_year_earnings + retained_earnings
        equity_total = unallocated_earnings
        
        # Build report lines with expandable sub-categories
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
                                'unfoldable': True,  # Now expandable
                                'balance': bank_cash_total,
                                'account_type': 'asset_cash',
                                'children': bank_cash_accounts  # Add account details
                            },
                            {
                                'id': 'receivables',
                                'name': 'Receivables',
                                'level': 2,
                                'unfoldable': True,  # Now expandable
                                'balance': receivables_total,
                                'account_type': 'asset_receivable',
                                'children': receivables_accounts  # Add account details
                            },
                            {
                                'id': 'current_assets_other',
                                'name': 'Current Assets',
                                'level': 2,
                                'unfoldable': True,  # Now expandable
                                'balance': current_assets_other_total,
                                'account_type': 'asset_current',
                                'children': current_assets_accounts  # Add account details
                            },
                            {
                                'id': 'prepayments',
                                'name': 'Prepayments',
                                'level': 2,
                                'unfoldable': True if prepayments_accounts else False,
                                'balance': prepayments_total,
                                'account_type': 'asset_prepayments',
                                'children': prepayments_accounts
                            }
                        ]
                    },
                    {
                        'id': 'fixed_assets',
                        'name': 'Plus Fixed Assets',
                        'level': 1,
                        'unfoldable': True if fixed_assets_accounts else False,
                        'balance': fixed_assets_total,
                        'account_type': 'asset_fixed',
                        'children': fixed_assets_accounts
                    },
                    {
                        'id': 'non_current_assets',
                        'name': 'Plus Non-current Assets',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'asset_non_current',
                        'children': []
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
                        'balance': current_liabilities_total + payables_total,
                        'account_type': 'liability_current',
                        'children': [
                            {
                                'id': 'current_liabilities_detail',
                                'name': 'Current Liabilities',
                                'level': 2,
                                'unfoldable': True,  # Now expandable
                                'balance': current_liabilities_total,
                                'account_type': 'liability_current',
                                'children': current_liabilities_accounts  # Add account details
                            },
                            {
                                'id': 'payables',
                                'name': 'Payables',
                                'level': 2,
                                'unfoldable': True if payables_accounts else False,
                                'balance': payables_total,
                                'account_type': 'liability_payable',
                                'children': payables_accounts
                            }
                        ]
                    },
                    {
                        'id': 'non_current_liabilities',
                        'name': 'Plus Non-current Liabilities',
                        'level': 1,
                        'unfoldable': True if non_current_liabilities_accounts else False,
                        'balance': non_current_liabilities_total,
                        'account_type': 'liability_non_current',
                        'children': non_current_liabilities_accounts
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
                                'account_type': 'equity',
                                'children': []
                            },
                            {
                                'id': 'previous_years_earnings',
                                'name': 'Previous Years Unallocated Earnings',
                                'level': 2,
                                'unfoldable': False,
                                'balance': retained_earnings,
                                'account_type': 'equity_unaffected',
                                'children': []
                            }
                        ]
                    },
                    {
                        'id': 'retained_earnings',
                        'name': 'Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity',
                        'children': []
                    },
                    {
                        'id': 'current_year_retained',
                        'name': 'Current Year Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity',
                        'children': []
                    },
                    {
                        'id': 'previous_years_retained',
                        'name': 'Previous Years Retained Earnings',
                        'level': 1,
                        'unfoldable': False,
                        'balance': 0.0,
                        'account_type': 'equity',
                        'children': []
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
                'is_total': True,
                'children': []
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
        
        # Add comparison data if requested
        if comparison and comparison_date:
            comparison_date_obj = fields.Date.from_string(comparison_date) if isinstance(comparison_date, str) else comparison_date
            comparison_data = self.get_balance_sheet_data(
                date_from=date_from,
                date_to=comparison_date_obj,
                journals=journals,
                company_id=company_id,
                only_posted=only_posted,
                include_draft=include_draft,
                hide_zero=hide_zero,
                comparison=False  # Avoid recursive comparison
            )
            balance_sheet['comparison'] = {
                'date': comparison_date_obj.strftime('%d/%m/%Y'),
                'lines': comparison_data.get('lines', [])
            }
            
            # Map comparison balances to main lines
            def map_comparison_balances(main_lines, comp_lines):
                comp_dict = {line['id']: line['balance'] for line in comp_lines}
                for main_line in main_lines:
                    main_line['comparison_balance'] = comp_dict.get(main_line['id'], 0.0)
                    if main_line.get('children'):
                        comp_children = next((cl['children'] for cl in comp_lines if cl['id'] == main_line['id']), [])
                        if comp_children:
                            map_comparison_balances(main_line['children'], comp_children)
            
            if balance_sheet.get('comparison'):
                map_comparison_balances(lines, balance_sheet['comparison']['lines'])
        
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