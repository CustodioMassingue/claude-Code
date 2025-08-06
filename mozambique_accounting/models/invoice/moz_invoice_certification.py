# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class MozInvoiceCertification(models.Model):
    _name = 'moz.invoice.certification'
    _description = 'Invoice Certification with AT'
    _order = 'certification_date desc'
    
    invoice_id = fields.Many2one(
        'moz.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade'
    )
    
    certification_date = fields.Datetime(
        string='Certification Date',
        required=True,
        default=fields.Datetime.now
    )
    
    request_data = fields.Text(
        string='Request Data',
        readonly=True
    )
    
    response_data = fields.Text(
        string='Response Data',
        readonly=True
    )
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    
    at_transaction_id = fields.Char(
        string='AT Transaction ID',
        readonly=True
    )
    
    def certify_with_at(self):
        """Send invoice to AT for certification"""
        self.ensure_one()
        
        # Prepare request data
        request_data = self._prepare_certification_request()
        self.request_data = json.dumps(request_data, indent=2)
        
        try:
            # Call AT web service
            response = self._call_at_service(request_data)
            self.response_data = json.dumps(response, indent=2)
            
            if response.get('success'):
                self.status = 'success'
                self.at_transaction_id = response.get('transactionId')
                
                # Update invoice with certification data
                self.invoice_id.write({
                    'at_code': response.get('validationCode'),
                    'hash_code': response.get('hash'),
                })
                
                _logger.info(f"Invoice {self.invoice_id.number} certified successfully")
            else:
                self.status = 'error'
                self.error_message = response.get('error', 'Unknown error')
                _logger.error(f"Certification failed for invoice {self.invoice_id.number}: {self.error_message}")
                
        except Exception as e:
            self.status = 'error'
            self.error_message = str(e)
            _logger.error(f"Certification error for invoice {self.invoice_id.number}: {e}")
            raise UserError(_("Certification failed: %s") % str(e))
    
    def _prepare_certification_request(self):
        """Prepare the certification request data"""
        invoice = self.invoice_id
        company = invoice.company_id
        
        # Invoice items
        items = []
        for line in invoice.invoice_line_ids:
            items.append({
                'description': line.name,
                'quantity': line.quantity,
                'unitPrice': line.price_unit,
                'discount': line.discount,
                'taxRate': line.tax_ids[0].amount if line.tax_ids else 0,
                'totalAmount': line.price_total
            })
        
        # Build request
        request_data = {
            'taxpayerNUIT': company.vat,
            'taxpayerName': company.name,
            'taxpayerAddress': company.street or '',
            'invoiceType': invoice.invoice_type,
            'invoiceNumber': invoice.number,
            'invoiceDate': invoice.invoice_date.isoformat(),
            'customerNUIT': invoice.partner_vat or '',
            'customerName': invoice.partner_id.name,
            'customerAddress': invoice.partner_street or '',
            'items': items,
            'subtotal': invoice.amount_untaxed,
            'taxAmount': invoice.amount_tax,
            'totalAmount': invoice.amount_total,
            'previousHash': invoice.previous_hash or '',
            'softwareName': 'Odoo Mozambique Accounting',
            'softwareVersion': '18.0.1.0.0',
        }
        
        return request_data
    
    def _call_at_service(self, request_data):
        """Call AT web service for certification"""
        # Get AT configuration
        config = self.env['ir.config_parameter'].sudo()
        at_url = config.get_param('moz_accounting.at_certification_url', '')
        at_token = config.get_param('moz_accounting.at_api_token', '')
        
        if not at_url:
            # Mock response for testing
            return {
                'success': True,
                'transactionId': f"AT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'validationCode': f"VAL-{request_data['invoiceNumber']}",
                'hash': self.invoice_id.hash_code or 'MOCK-HASH',
                'timestamp': datetime.now().isoformat()
            }
        
        # Make actual API call
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {at_token}'
        }
        
        response = requests.post(
            at_url,
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    @api.model
    def process_pending_certifications(self):
        """Cron job to process pending certifications"""
        pending = self.search([('status', '=', 'pending')], limit=50)
        for cert in pending:
            try:
                cert.certify_with_at()
            except Exception as e:
                _logger.error(f"Failed to process certification {cert.id}: {e}")