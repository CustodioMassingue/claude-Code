from odoo import http
from odoo.http import request
import json
from datetime import datetime, date

class BalanceSheetController(http.Controller):
    
    @http.route('/account/balance_sheet/data', type='json', auth='user')
    def get_balance_sheet_data(self, date_to=None, date_from=None, journals=None, company_id=None, comparison=False):
        """
        Fetch balance sheet data via AJAX
        """
        if not request.env.user.has_group('account.group_account_user'):
            return {'error': 'Access denied'}
            
        try:
            # Parse dates if strings
            if date_to and isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if date_from and isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                
            # Get balance sheet data
            balance_sheet_model = request.env['account.balance.sheet.report']
            data = balance_sheet_model.get_balance_sheet_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id
            )
            
            # Add comparison data if requested
            if comparison and date_to:
                # Get comparison data (previous period)
                from dateutil.relativedelta import relativedelta
                comparison_date = date_to - relativedelta(years=1)
                comparison_data = balance_sheet_model.get_balance_sheet_data(
                    date_to=comparison_date,
                    journals=journals,
                    company_id=company_id
                )
                data['comparison'] = comparison_data
                
            return {
                'success': True,
                'data': data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/account/balance_sheet/expand_line', type='json', auth='user')
    def expand_line(self, line_id, date_to=None, journals=None, company_id=None):
        """
        Expand a specific line to get detailed accounts
        """
        if not request.env.user.has_group('account.group_account_user'):
            return {'error': 'Access denied'}
            
        try:
            # Map line_id to account types
            account_type_map = {
                'bank_cash': ['asset_cash', 'liability_credit_card'],
                'receivables': ['asset_receivable'],
                'current_assets_other': ['asset_current'],
                'prepayments': ['asset_prepayments'],
                'payables': ['liability_payable'],
                'current_liabilities_other': ['liability_current'],
            }
            
            if line_id not in account_type_map:
                return {'sub_lines': []}
                
            # Get detailed accounts
            domain = [
                ('account_type', 'in', account_type_map[line_id]),
                ('company_id', '=', company_id or request.env.company.id)
            ]
            
            if date_to:
                if isinstance(date_to, str):
                    date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                domain.append(('date', '<=', date_to))
                
            if journals:
                domain.append(('journal_id', 'in', journals))
                
            # Get account lines
            move_lines = request.env['account.move.line'].search(domain)
            
            # Group by account
            accounts = {}
            for line in move_lines:
                acc_id = line.account_id.id
                if acc_id not in accounts:
                    accounts[acc_id] = {
                        'id': f'account_{acc_id}',
                        'code': line.account_id.code,
                        'name': f"{line.account_id.code} {line.account_id.name}",
                        'balance': 0.0,
                        'level': 3,
                        'unfoldable': False
                    }
                accounts[acc_id]['balance'] += line.balance
                
            sub_lines = list(accounts.values())
            sub_lines.sort(key=lambda x: x['code'])
            
            return {
                'success': True,
                'sub_lines': sub_lines
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/account/balance_sheet/export_excel', type='http', auth='user')
    def export_excel(self, date_to=None, date_from=None, journals=None, company_id=None):
        """
        Export balance sheet to Excel
        """
        if not request.env.user.has_group('account.group_account_user'):
            return request.not_found()
            
        try:
            # Parse parameters
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if journals:
                journals = json.loads(journals) if isinstance(journals, str) else journals
            if company_id:
                company_id = int(company_id)
                
            # Get balance sheet data
            balance_sheet_model = request.env['account.balance.sheet.report']
            data = balance_sheet_model.get_balance_sheet_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id
            )
            
            # Generate Excel file
            excel_data = balance_sheet_model.export_to_excel(data)
            
            # Return file
            filename = f"balance_sheet_{date_to or date.today()}.xlsx"
            return request.make_response(
                excel_data,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename={filename}')
                ]
            )
            
        except Exception as e:
            return request.not_found()
    
    @http.route('/account/balance_sheet/export_pdf', type='http', auth='user')
    def export_pdf(self, date_to=None, date_from=None, journals=None, company_id=None):
        """
        Export balance sheet to PDF
        """
        if not request.env.user.has_group('account.group_account_user'):
            return request.not_found()
            
        try:
            # Parse parameters
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if journals:
                journals = json.loads(journals) if isinstance(journals, str) else journals
            if company_id:
                company_id = int(company_id)
                
            # Get balance sheet data
            balance_sheet_model = request.env['account.balance.sheet.report']
            data = balance_sheet_model.get_balance_sheet_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id
            )
            
            # Generate PDF using report action
            report = request.env.ref('account_invoicing_ext_mz.action_report_balance_sheet')
            pdf = report._render_qweb_pdf([0], data={'form': data})[0]
            
            # Return file
            filename = f"balance_sheet_{date_to or date.today()}.pdf"
            return request.make_response(
                pdf,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename={filename}')
                ]
            )
            
        except Exception as e:
            return request.not_found()