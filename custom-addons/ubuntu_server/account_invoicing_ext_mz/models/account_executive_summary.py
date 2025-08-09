from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountExecutiveSummary(models.TransientModel):
    _name = 'account.executive.summary.report'
    _description = 'Executive Summary Report'
    
    @api.model
    def get_executive_summary_data(self, date_from=None, date_to=None, comparison=None, company_id=None):
        """Get executive summary data for the report"""
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
            
            # Get currency
            currency = self.env.company.currency_id
            currency_symbol = 'MZN'  # Metical for Mozambique
            
            # Build domain for account.move.line
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted')
            ]
            
            # Get all move lines for the period
            move_lines = self.env['account.move.line'].search(domain)
            
            # CASH SECTION
            # Get cash and bank accounts
            cash_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['asset_cash', 'asset_bank'])
            ])
            
            # Calculate cash flows
            cash_lines = move_lines.filtered(lambda l: l.account_id.id in cash_accounts.ids)
            cash_received = sum(l.credit for l in cash_lines)
            cash_spent = sum(l.debit for l in cash_lines)
            cash_surplus = cash_received - cash_spent
            
            # Calculate closing bank balance
            closing_balance_domain = [
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', cash_accounts.ids)
            ]
            closing_lines = self.env['account.move.line'].search(closing_balance_domain)
            closing_bank_balance = sum(closing_lines.mapped('balance'))
            
            # PROFITABILITY SECTION
            # Revenue accounts (income)
            revenue_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['income', 'income_other'])
            ])
            revenue_lines = move_lines.filtered(lambda l: l.account_id.id in revenue_accounts.ids)
            revenue = abs(sum(revenue_lines.mapped('balance')))
            
            # Cost of Revenue (COGS)
            cogs_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', '=', 'expense_direct_cost')
            ])
            cogs_lines = move_lines.filtered(lambda l: l.account_id.id in cogs_accounts.ids)
            cost_of_revenue = sum(cogs_lines.mapped('balance'))
            
            # Gross profit
            gross_profit = revenue - cost_of_revenue
            
            # Operating expenses
            expense_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['expense', 'expense_depreciation'])
            ])
            expense_lines = move_lines.filtered(lambda l: l.account_id.id in expense_accounts.ids)
            expenses = sum(expense_lines.mapped('balance'))
            
            # Net profit
            net_profit = gross_profit - expenses
            
            # BALANCE SHEET SECTION
            # Receivables
            receivable_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', '=', 'asset_receivable')
            ])
            receivable_domain = [
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', receivable_accounts.ids)
            ]
            receivable_lines = self.env['account.move.line'].search(receivable_domain)
            receivables = sum(receivable_lines.mapped('balance'))
            
            # Payables
            payable_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', '=', 'liability_payable')
            ])
            payable_domain = [
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', payable_accounts.ids)
            ]
            payable_lines = self.env['account.move.line'].search(payable_domain)
            payables = abs(sum(payable_lines.mapped('balance')))
            
            # Net assets (Total assets - Total liabilities)
            asset_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['asset_fixed', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_receivable', 'asset_cash', 'asset_bank'])
            ])
            asset_domain = [
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', asset_accounts.ids)
            ]
            asset_lines = self.env['account.move.line'].search(asset_domain)
            total_assets = sum(asset_lines.mapped('balance'))
            
            liability_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'])
            ])
            liability_domain = [
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', liability_accounts.ids)
            ]
            liability_lines = self.env['account.move.line'].search(liability_domain)
            total_liabilities = abs(sum(liability_lines.mapped('balance')))
            
            net_assets = total_assets - total_liabilities
            
            # PERFORMANCE SECTION
            # Calculate margins
            gross_profit_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
            net_profit_margin = (net_profit / revenue * 100) if revenue > 0 else 0
            return_on_assets = (net_profit / total_assets * 100) if total_assets > 0 else 0
            
            # POSITION SECTION
            # Average debtors days (DSO - Days Sales Outstanding)
            days_in_period = (date_to - date_from).days
            average_daily_sales = revenue / days_in_period if days_in_period > 0 else 0
            average_debtors_days = receivables / average_daily_sales if average_daily_sales > 0 else 0
            
            # Average creditors days (DPO - Days Payables Outstanding)
            average_daily_purchases = cost_of_revenue / days_in_period if days_in_period > 0 else 0
            average_creditors_days = payables / average_daily_purchases if average_daily_purchases > 0 else 0
            
            # Short term cash forecast (simplified)
            short_term_cash = closing_bank_balance + receivables - payables
            
            # Current ratio (current assets / current liabilities)
            current_asset_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['asset_current', 'asset_receivable', 'asset_cash', 'asset_bank', 'asset_prepayments'])
            ])
            current_asset_lines = self.env['account.move.line'].search([
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', current_asset_accounts.ids)
            ])
            current_assets = sum(current_asset_lines.mapped('balance'))
            
            current_liability_accounts = self.env['account.account'].search([
                ('company_id', '=', company_id),
                ('account_type', 'in', ['liability_current', 'liability_payable', 'liability_credit_card'])
            ])
            current_liability_lines = self.env['account.move.line'].search([
                ('company_id', '=', company_id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('account_id', 'in', current_liability_accounts.ids)
            ])
            current_liabilities = abs(sum(current_liability_lines.mapped('balance')))
            
            current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
            
            # Build the sections data
            sections = []
            
            # Cash Section
            cash_section = {
                'id': 'cash',
                'name': 'Cash',
                'type': 'header',
                'items': [
                    {'id': 'cash_received', 'name': 'Cash received', 'value': cash_received, 'info': False},
                    {'id': 'cash_spent', 'name': 'Cash spent', 'value': cash_spent, 'info': False},
                    {'id': 'cash_surplus', 'name': 'Cash surplus', 'value': cash_surplus, 'info': False},
                    {'id': 'closing_bank', 'name': 'Closing bank balance', 'value': closing_bank_balance, 'info': False}
                ]
            }
            sections.append(cash_section)
            
            # Profitability Section
            profitability_section = {
                'id': 'profitability',
                'name': 'Profitability',
                'type': 'header',
                'items': [
                    {'id': 'revenue', 'name': 'Revenue', 'value': revenue, 'info': False},
                    {'id': 'cost_revenue', 'name': 'Cost of Revenue', 'value': cost_of_revenue, 'info': False},
                    {'id': 'gross_profit', 'name': 'Gross profit', 'value': gross_profit, 'info': False},
                    {'id': 'expenses', 'name': 'Expenses', 'value': expenses, 'info': False},
                    {'id': 'net_profit', 'name': 'Net Profit', 'value': net_profit, 'info': False}
                ]
            }
            sections.append(profitability_section)
            
            # Balance Sheet Section
            balance_section = {
                'id': 'balance_sheet',
                'name': 'Balance Sheet',
                'type': 'header',
                'items': [
                    {'id': 'receivables', 'name': 'Receivables', 'value': receivables, 'info': False},
                    {'id': 'payables', 'name': 'Payables', 'value': payables, 'info': False},
                    {'id': 'net_assets', 'name': 'Net assets', 'value': net_assets, 'info': False}
                ]
            }
            sections.append(balance_section)
            
            # Performance Section
            performance_section = {
                'id': 'performance',
                'name': 'Performance',
                'type': 'header',
                'items': [
                    {'id': 'gross_margin', 'name': 'Gross profit margin (gross profit / operating income)', 'value': gross_profit_margin, 'info': False, 'is_percentage': True},
                    {'id': 'net_margin', 'name': 'Net profit margin (net profit / income)', 'value': net_profit_margin, 'info': False, 'is_percentage': True},
                    {'id': 'return_assets', 'name': 'Return on investments (net profit / assets)', 'value': return_on_assets, 'info': False, 'is_percentage': True}
                ]
            }
            sections.append(performance_section)
            
            # Position Section
            position_section = {
                'id': 'position',
                'name': 'Position',
                'type': 'header',
                'items': [
                    {'id': 'debtors_days', 'name': 'Average debtors days', 'value': average_debtors_days, 'info': False, 'is_days': True},
                    {'id': 'creditors_days', 'name': 'Average creditors days', 'value': average_creditors_days, 'info': False, 'is_days': True},
                    {'id': 'cash_forecast', 'name': 'Short term cash forecast', 'value': short_term_cash, 'info': False},
                    {'id': 'current_ratio', 'name': 'Current assets to liabilities', 'value': current_ratio, 'info': False, 'is_ratio': True}
                ]
            }
            sections.append(position_section)
            
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
                'sections': sections,
                'company_name': self.env.company.name,
                'currency_symbol': currency_symbol,
                'date_from': date_from_str,
                'date_to': date_to_str
            }
            
        except Exception as e:
            _logger.error(f"Error getting executive summary data: {str(e)}")
            return {
                'sections': [],
                'company_name': '',
                'currency_symbol': 'MZN',
                'date_from': '',
                'date_to': '',
                'error': str(e)
            }