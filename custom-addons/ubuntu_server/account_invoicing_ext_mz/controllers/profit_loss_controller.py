from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime, date

_logger = logging.getLogger(__name__)

class ProfitLossController(http.Controller):
    
    @http.route('/account/profit_loss/data', type='json', auth='user')
    def get_profit_loss_data(self, date_from=None, date_to=None, journals=None, company_id=None,
                            comparison=False, comparison_date_from=None, comparison_date_to=None,
                            comparison_mode='none', only_posted=True, include_draft=False,
                            include_simulations=False, hide_zero=False, analytic_accounts=None,
                            analytic_plans=None, partners=None, **kwargs):
        """
        Fetch profit and loss data via AJAX
        """
        if not request.env.user.has_group('account.group_account_user'):
            return {'error': 'Access denied'}
            
        try:
            # Parse dates if strings
            if date_from and isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to and isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if comparison_date_from and isinstance(comparison_date_from, str):
                comparison_date_from = datetime.strptime(comparison_date_from, '%Y-%m-%d').date()
            if comparison_date_to and isinstance(comparison_date_to, str):
                comparison_date_to = datetime.strptime(comparison_date_to, '%Y-%m-%d').date()
                
            # Get profit and loss data
            profit_loss_model = request.env['account.profit.loss.report']
            data = profit_loss_model.get_profit_loss_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id,
                only_posted=only_posted,
                include_draft=include_draft,
                hide_zero=hide_zero,
                comparison=comparison,
                comparison_date_from=comparison_date_from,
                comparison_date_to=comparison_date_to,
                comparison_mode=comparison_mode,
                analytic_accounts=analytic_accounts,
                analytic_plans=analytic_plans,
                include_simulations=include_simulations
            )
                
            return {
                'success': True,
                'data': data
            }
            
        except Exception as e:
            _logger.error(f"Error generating profit and loss: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/account/profit_loss/expand_line', type='json', auth='user')
    def expand_line(self, line_id, date_from=None, date_to=None, journals=None, company_id=None):
        """
        Expand a specific line to get detailed accounts
        """
        if not request.env.user.has_group('account.group_account_user'):
            return {'error': 'Access denied'}
            
        try:
            # Map line_id to account types
            account_type_map = {
                'operating_income': ['income'],
                'other_income': ['income_other'],
                'cost_of_revenue': ['expense_direct_cost'],
                'operating_expenses': ['expense'],
                'depreciation': ['expense_depreciation'],
            }
            
            if line_id not in account_type_map:
                return {'sub_lines': []}
                
            # Get detailed accounts
            domain = [
                ('account_type', 'in', account_type_map[line_id]),
                ('company_id', '=', company_id or request.env.company.id)
            ]
            
            if date_from:
                if isinstance(date_from, str):
                    date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                domain.append(('date', '>=', date_from))
                
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
                # For P&L, income is credit - debit, expenses are debit - credit
                if line.account_id.account_type in ['income', 'income_other']:
                    accounts[acc_id]['balance'] -= line.balance
                else:
                    accounts[acc_id]['balance'] += line.balance
                
            sub_lines = list(accounts.values())
            sub_lines = [acc for acc in sub_lines if acc['balance'] != 0]  # Filter zero balances
            sub_lines.sort(key=lambda x: x['code'])
            
            return {
                'success': True,
                'sub_lines': sub_lines
            }
            
        except Exception as e:
            _logger.error(f"Error expanding line: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/account/profit_loss/export_excel', type='http', auth='user')
    def export_excel(self, date_from=None, date_to=None, journals=None, company_id=None):
        """
        Export profit and loss to Excel
        """
        if not request.env.user.has_group('account.group_account_user'):
            return request.not_found()
            
        try:
            # Parse parameters
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if journals:
                journals = json.loads(journals) if isinstance(journals, str) else journals
            if company_id:
                company_id = int(company_id)
                
            # Get profit and loss data
            profit_loss_model = request.env['account.profit.loss.report']
            data = profit_loss_model.get_profit_loss_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id
            )
            
            # Generate Excel file
            excel_data = profit_loss_model.export_to_excel(data)
            
            # Return file
            filename = f"profit_loss_{date_from or date.today()}_{date_to or date.today()}.xlsx"
            return request.make_response(
                excel_data,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename={filename}')
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error exporting to Excel: {str(e)}")
            return request.not_found()
    
    @http.route('/account/profit_loss/export_pdf', type='http', auth='user')
    def export_pdf(self, date_from=None, date_to=None, journals=None, company_id=None):
        """
        Export profit and loss to PDF
        """
        if not request.env.user.has_group('account.group_account_user'):
            return request.not_found()
            
        try:
            # Parse parameters
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            if journals:
                journals = json.loads(journals) if isinstance(journals, str) else journals
            if company_id:
                company_id = int(company_id)
                
            # Get profit and loss data
            profit_loss_model = request.env['account.profit.loss.report']
            data = profit_loss_model.get_profit_loss_data(
                date_from=date_from,
                date_to=date_to,
                journals=journals,
                company_id=company_id
            )
            
            # Generate PDF using report action
            report = request.env.ref('account_invoicing_ext_mz.action_report_profit_loss')
            pdf = report._render_qweb_pdf([0], data={'form': data})[0]
            
            # Return file
            filename = f"profit_loss_{date_from or date.today()}_{date_to or date.today()}.pdf"
            return request.make_response(
                pdf,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename={filename}')
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error exporting to PDF: {str(e)}")
            return request.not_found()