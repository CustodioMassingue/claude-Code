# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class MozAccountingAPI(http.Controller):
    
    @http.route('/api/moz/invoice/certify', type='json', auth='user', methods=['POST'])
    def certify_invoice(self, invoice_id):
        """API endpoint to certify an invoice with AT"""
        try:
            invoice = request.env['moz.invoice'].browse(invoice_id)
            if not invoice.exists():
                return {'success': False, 'error': 'Invoice not found'}
            
            if invoice.state != 'posted':
                return {'success': False, 'error': 'Invoice must be posted before certification'}
            
            invoice.action_certify()
            
            return {
                'success': True,
                'hash_code': invoice.hash_code,
                'at_code': invoice.at_code,
                'certification_date': invoice.certification_date.isoformat() if invoice.certification_date else None
            }
        except Exception as e:
            _logger.error(f"Error certifying invoice {invoice_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/moz/saft/export', type='json', auth='user', methods=['POST'])
    def export_saft(self, date_from, date_to, company_id=None):
        """API endpoint to export SAF-T file"""
        try:
            if not company_id:
                company_id = request.env.company.id
            
            wizard = request.env['moz.saft.export.wizard'].create({
                'date_from': date_from,
                'date_to': date_to,
                'company_id': company_id,
                'export_type': 'full'
            })
            
            wizard.action_export()
            
            return {
                'success': True,
                'file': wizard.saft_file.decode('utf-8') if wizard.saft_file else None,
                'filename': wizard.saft_filename
            }
        except Exception as e:
            _logger.error(f"Error exporting SAF-T: {e}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/moz/invoice/validate', type='json', auth='public', methods=['POST'])
    def validate_invoice(self, invoice_number, hash_code):
        """API endpoint to validate invoice hash"""
        try:
            invoice = request.env['moz.invoice'].sudo().search([
                ('number', '=', invoice_number),
                ('hash_code', '=', hash_code)
            ], limit=1)
            
            if invoice:
                return {
                    'success': True,
                    'valid': True,
                    'invoice': {
                        'number': invoice.number,
                        'date': invoice.invoice_date.isoformat(),
                        'partner': invoice.partner_id.name,
                        'total': invoice.amount_total,
                        'state': invoice.state
                    }
                }
            else:
                return {
                    'success': True,
                    'valid': False,
                    'message': 'Invoice not found or hash mismatch'
                }
        except Exception as e:
            _logger.error(f"Error validating invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/moz/dashboard/data', type='json', auth='user', methods=['GET'])
    def get_dashboard_data(self):
        """API endpoint to get dashboard data"""
        try:
            company = request.env.company
            today = fields.Date.today()
            
            # Get current month range
            month_start = today.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            # Sales this month
            sales = request.env['moz.invoice'].search([
                ('company_id', '=', company.id),
                ('invoice_date', '>=', month_start),
                ('invoice_date', '<=', month_end),
                ('state', 'in', ['posted', 'certified']),
                ('invoice_type', 'in', ['FT', 'FR', 'VD', 'FS'])
            ])
            
            # Pending reconciliation
            pending_reconciliation = request.env['moz.bank.statement.line'].search_count([
                ('company_id', '=', company.id),
                ('is_reconciled', '=', False)
            ])
            
            # Assets
            assets = request.env['moz.asset'].search([
                ('company_id', '=', company.id),
                ('state', '=', 'open')
            ])
            
            return {
                'success': True,
                'data': {
                    'sales_month': sum(sales.mapped('amount_total')),
                    'sales_count': len(sales),
                    'pending_reconciliation': pending_reconciliation,
                    'active_assets': len(assets),
                    'assets_value': sum(assets.mapped('book_value')),
                    'currency': company.currency_id.name
                }
            }
        except Exception as e:
            _logger.error(f"Error getting dashboard data: {e}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/moz/bank/import', type='http', auth='user', methods=['POST'], csrf=False)
    def import_bank_statement(self, **kwargs):
        """API endpoint to import bank statement"""
        try:
            file_data = kwargs.get('file')
            journal_id = int(kwargs.get('journal_id'))
            file_type = kwargs.get('file_type', 'csv')
            
            if not file_data:
                return json.dumps({'success': False, 'error': 'No file provided'})
            
            # Create import wizard
            wizard = request.env['moz.bank.statement.import'].create({
                'journal_id': journal_id,
                'file_type': file_type,
                'file_data': file_data.read().encode('base64'),
                'filename': file_data.filename
            })
            
            # Import file
            statement = wizard.import_file()
            
            return json.dumps({
                'success': True,
                'statement_id': statement.id,
                'statement_name': statement.name
            })
        except Exception as e:
            _logger.error(f"Error importing bank statement: {e}")
            return json.dumps({'success': False, 'error': str(e)})