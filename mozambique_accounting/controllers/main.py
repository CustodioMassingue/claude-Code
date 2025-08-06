# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class MozAccountingMain(http.Controller):
    
    @http.route('/mozambique_accounting/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        """Main dashboard for Mozambique Accounting"""
        # Get dashboard data
        company = request.env.company
        
        # Recent invoices
        recent_invoices = request.env['moz.invoice'].search([
            ('company_id', '=', company.id)
        ], limit=10, order='invoice_date desc')
        
        # Pending reconciliations
        pending_reconciliations = request.env['moz.bank.statement'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'open')
        ])
        
        # Overdue invoices
        overdue_invoices = request.env['moz.invoice'].search([
            ('company_id', '=', company.id),
            ('payment_state', '!=', 'paid'),
            ('due_date', '<', fields.Date.today())
        ])
        
        values = {
            'company': company,
            'recent_invoices': recent_invoices,
            'pending_reconciliations': pending_reconciliations,
            'overdue_invoices': overdue_invoices,
        }
        
        return request.render('mozambique_accounting.dashboard_template', values)
    
    @http.route('/mozambique_accounting/invoice/<int:invoice_id>/certificate', type='http', auth='public')
    def invoice_certificate(self, invoice_id, **kwargs):
        """Public page to view invoice certificate"""
        invoice = request.env['moz.invoice'].sudo().browse(invoice_id)
        
        if not invoice.exists() or invoice.state != 'certified':
            return request.not_found()
        
        values = {
            'invoice': invoice,
            'company': invoice.company_id,
        }
        
        return request.render('mozambique_accounting.invoice_certificate_template', values)