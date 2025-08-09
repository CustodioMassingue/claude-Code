from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json

class AccountProfitLoss(models.TransientModel):
    _name = 'account.profit.loss.report'
    _description = 'Profit and Loss Report'
    
    @api.model
    def get_profit_loss_data(self, date_from=None, date_to=None, journals=None, company_id=None,
                            only_posted=True, include_draft=False, hide_zero=False,
                            comparison=False, comparison_date_from=None, comparison_date_to=None,
                            comparison_mode='none', analytic_accounts=None, analytic_plans=None,
                            include_simulations=False, **kwargs):
        """
        Generate Profit and Loss data with hierarchical structure
        """
        if not date_to:
            date_to = fields.Date.today()
        if isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)
        if not date_from:
            date_from = date(date_to.year, 1, 1)
        if isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
        if not company_id:
            company_id = self.env.company.id
            
        domain = [
            ('date', '>=', date_from),
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
            'income': [],
            'income_other': [],
            'expense': [],
            'expense_depreciation': [],
            'expense_direct_cost': [],
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
            # For P&L, we need credit - debit for income, debit - credit for expenses
            if account.account_type in ['income', 'income_other']:
                account_balances[key]['balance'] -= line.balance  # Negative balance becomes positive
            else:
                account_balances[key]['balance'] += line.balance
        
        # Organize accounts by type for detail view
        for acc_id, acc_data in account_balances.items():
            acc_type = acc_data['account_type']
            if acc_type in accounts_detail and acc_data['balance'] != 0:
                accounts_detail[acc_type].append({
                    'id': f'account_{acc_id}',
                    'code': acc_data['code'],
                    'name': f"{acc_data['code']} {acc_data['name']}",
                    'balance': abs(acc_data['balance']),
                    'level': 3,
                    'unfoldable': False,
                    'account_type': acc_type
                })
        
        # Sort accounts by code
        for acc_type in accounts_detail:
            accounts_detail[acc_type].sort(key=lambda x: x.get('code', ''))
            
        # Calculate totals
        # Income
        operating_income_accounts = accounts_detail.get('income', [])
        operating_income_total = sum(acc['balance'] for acc in operating_income_accounts)
        
        other_income_accounts = accounts_detail.get('income_other', [])
        other_income_total = sum(acc['balance'] for acc in other_income_accounts)
        
        # Cost of Revenue
        cost_of_revenue_accounts = accounts_detail.get('expense_direct_cost', [])
        cost_of_revenue_total = sum(acc['balance'] for acc in cost_of_revenue_accounts)
        
        # Gross Profit
        gross_profit = operating_income_total - cost_of_revenue_total
        
        # Total Income
        total_income = gross_profit + other_income_total
        
        # Expenses
        expense_accounts = accounts_detail.get('expense', [])
        expense_total = sum(acc['balance'] for acc in expense_accounts)
        
        depreciation_accounts = accounts_detail.get('expense_depreciation', [])
        depreciation_total = sum(acc['balance'] for acc in depreciation_accounts)
        
        total_expenses = expense_total + depreciation_total
        
        # Net Profit
        net_profit = total_income - total_expenses
        
        # Get stock values (opening and closing)
        opening_stock = 0.0
        closing_stock = 0.0
        
        # Build hierarchical structure
        profit_loss = {
            'date_from': date_from.strftime('%d/%m/%Y'),
            'date_to': date_to.strftime('%d/%m/%Y'),
            'date_range': f"{date_from.year} - {date_to.year}" if date_from.year != date_to.year else str(date_to.year),
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.symbol,
            'lines': []
        }
        
        # Build report lines with expandable sub-categories
        lines = [
            {
                'id': 'net_profit',
                'name': 'Net Profit',
                'level': 0,
                'unfoldable': False,
                'unfolded': False,
                'balance': net_profit,
                'is_total': True,
                'style': 'background-color: #e0e0e0; font-weight: bold;',
                'children': []
            },
            {
                'id': 'closing_stock',
                'name': 'Closing Stock',
                'level': 0,
                'unfoldable': False,
                'balance': closing_stock,
                'style': 'background-color: #f0f0f0;',
                'children': []
            },
            {
                'id': 'income',
                'name': 'Income',
                'level': 0,
                'unfoldable': True,
                'unfolded': False,
                'balance': total_income,
                'style': 'background-color: #f0f0f0;',
                'children': [
                    {
                        'id': 'gross_profit',
                        'name': 'Gross Profit',
                        'level': 1,
                        'unfoldable': True,
                        'balance': gross_profit,
                        'children': [
                            {
                                'id': 'operating_income',
                                'name': 'Operating Income',
                                'level': 2,
                                'unfoldable': True,
                                'balance': operating_income_total,
                                'children': operating_income_accounts
                            },
                            {
                                'id': 'cost_of_revenue',
                                'name': 'Cost of Revenue',
                                'level': 2,
                                'unfoldable': True if cost_of_revenue_accounts else False,
                                'balance': -cost_of_revenue_total if cost_of_revenue_total else 0.0,
                                'children': cost_of_revenue_accounts
                            }
                        ]
                    },
                    {
                        'id': 'other_income',
                        'name': 'Other Income',
                        'level': 1,
                        'unfoldable': True if other_income_accounts else False,
                        'balance': other_income_total,
                        'children': other_income_accounts
                    }
                ]
            },
            {
                'id': 'opening_stock',
                'name': 'Opening Stock',
                'level': 0,
                'unfoldable': False,
                'balance': opening_stock,
                'style': 'background-color: #f0f0f0;',
                'children': []
            },
            {
                'id': 'expenses',
                'name': 'Expenses',
                'level': 0,
                'unfoldable': True,
                'unfolded': False,
                'balance': -total_expenses if total_expenses else 0.0,
                'style': 'background-color: #f0f0f0;',
                'children': [
                    {
                        'id': 'operating_expenses',
                        'name': 'Expenses',
                        'level': 1,
                        'unfoldable': True if expense_accounts else False,
                        'balance': -expense_total if expense_total else 0.0,
                        'children': expense_accounts
                    },
                    {
                        'id': 'depreciation',
                        'name': 'Depreciation',
                        'level': 1,
                        'unfoldable': True if depreciation_accounts else False,
                        'balance': -depreciation_total if depreciation_total else 0.0,
                        'children': depreciation_accounts
                    }
                ]
            }
        ]
        
        profit_loss['lines'] = lines
        
        # Check if there are unposted entries
        unposted_moves = self.env['account.move'].search_count([
            ('state', '=', 'draft'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', company_id)
        ])
        
        profit_loss['has_unposted'] = unposted_moves > 0
        profit_loss['net_profit'] = net_profit
        profit_loss['total_income'] = total_income
        profit_loss['total_expenses'] = total_expenses
        
        # Add comparison data if requested
        if comparison and comparison_date_from and comparison_date_to:
            comparison_from = fields.Date.from_string(comparison_date_from) if isinstance(comparison_date_from, str) else comparison_date_from
            comparison_to = fields.Date.from_string(comparison_date_to) if isinstance(comparison_date_to, str) else comparison_date_to
            
            comparison_data = self.get_profit_loss_data(
                date_from=comparison_from,
                date_to=comparison_to,
                journals=journals,
                company_id=company_id,
                only_posted=only_posted,
                include_draft=include_draft,
                hide_zero=hide_zero,
                comparison=False  # Avoid recursive comparison
            )
            
            profit_loss['comparison'] = {
                'date_from': comparison_from.strftime('%d/%m/%Y'),
                'date_to': comparison_to.strftime('%d/%m/%Y'),
                'date_range': f"{comparison_from.year} - {comparison_to.year}" if comparison_from.year != comparison_to.year else str(comparison_to.year),
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
            
            if profit_loss.get('comparison'):
                map_comparison_balances(lines, profit_loss['comparison']['lines'])
        
        return profit_loss
    
    @api.model
    def export_to_excel(self, data):
        """Export profit and loss data to Excel format"""
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter library'))
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Profit and Loss')
        
        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        total_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1})
        
        # Write headers
        worksheet.write('A1', 'Profit and Loss', title_format)
        worksheet.write('A2', f"{data['date_from']} to {data['date_to']}")
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