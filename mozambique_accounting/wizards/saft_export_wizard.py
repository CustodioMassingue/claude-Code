# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class SaftExportWizard(models.TransientModel):
    _name = 'moz.saft.export.wizard'
    _description = 'SAF-T(MZ) Export Wizard'
    
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1)
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    export_type = fields.Selection([
        ('full', 'Full Export'),
        ('accounting', 'Accounting Only'),
        ('invoices', 'Invoices Only'),
        ('payments', 'Payments Only'),
    ], string='Export Type', default='full', required=True)
    
    include_opening_balance = fields.Boolean(
        string='Include Opening Balances',
        default=True
    )
    
    saft_file = fields.Binary(
        string='SAF-T File',
        readonly=True
    )
    
    saft_filename = fields.Char(
        string='Filename',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='State', default='draft')
    
    def action_export(self):
        """Export SAF-T file"""
        self.ensure_one()
        
        # Create root element
        root = ET.Element('AuditFile')
        root.set('xmlns', 'urn:OECD:StandardAuditFile-Tax:MZ_1.01')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        
        # Add header
        self._add_header(root)
        
        # Add master files
        if self.export_type in ['full', 'accounting']:
            self._add_master_files(root)
        
        # Add general ledger entries
        if self.export_type in ['full', 'accounting']:
            self._add_general_ledger_entries(root)
        
        # Add source documents
        if self.export_type in ['full', 'invoices', 'payments']:
            self._add_source_documents(root)
        
        # Convert to string with pretty print
        xml_string = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8')
        
        # Save file
        self.saft_file = base64.b64encode(pretty_xml)
        self.saft_filename = f"SAF-T_MZ_{self.company_id.vat}_{self.date_from}_{self.date_to}.xml"
        self.state = 'done'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _add_header(self, root):
        """Add header section"""
        header = ET.SubElement(root, 'Header')
        
        # Audit file version
        ET.SubElement(header, 'AuditFileVersion').text = '1.01_01'
        
        # Company ID
        company_id = ET.SubElement(header, 'CompanyID')
        ET.SubElement(company_id, 'TaxRegistrationNumber').text = self.company_id.vat or ''
        ET.SubElement(company_id, 'TaxAccountingBasis').text = 'F'  # Facturação
        ET.SubElement(company_id, 'CompanyName').text = self.company_id.name
        
        # Address
        address = ET.SubElement(company_id, 'CompanyAddress')
        ET.SubElement(address, 'AddressDetail').text = self.company_id.street or ''
        ET.SubElement(address, 'City').text = self.company_id.city or ''
        ET.SubElement(address, 'PostalCode').text = self.company_id.zip or ''
        ET.SubElement(address, 'Province').text = self.company_id.state_id.name if self.company_id.state_id else ''
        ET.SubElement(address, 'Country').text = self.company_id.country_id.code if self.company_id.country_id else 'MZ'
        
        # Fiscal year
        ET.SubElement(header, 'FiscalYear').text = str(self.date_from.year)
        ET.SubElement(header, 'StartDate').text = self.date_from.isoformat()
        ET.SubElement(header, 'EndDate').text = self.date_to.isoformat()
        ET.SubElement(header, 'CurrencyCode').text = self.company_id.currency_id.name
        ET.SubElement(header, 'DateCreated').text = fields.Date.today().isoformat()
        
        # Tax entity
        ET.SubElement(header, 'TaxEntity').text = 'Global'
        
        # Product Company Tax ID
        ET.SubElement(header, 'ProductCompanyTaxID').text = 'NIF999999999'
        ET.SubElement(header, 'SoftwareValidationNumber').text = '0'
        ET.SubElement(header, 'ProductID').text = 'Odoo Mozambique Accounting'
        ET.SubElement(header, 'ProductVersion').text = '18.0.1.0.0'
    
    def _add_master_files(self, root):
        """Add master files section"""
        master_files = ET.SubElement(root, 'MasterFiles')
        
        # General Ledger Accounts
        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id)
        ])
        
        for account in accounts:
            account_elem = ET.SubElement(master_files, 'Account')
            ET.SubElement(account_elem, 'AccountID').text = account.code
            ET.SubElement(account_elem, 'AccountDescription').text = account.name
            ET.SubElement(account_elem, 'OpeningDebitBalance').text = '0.00'
            ET.SubElement(account_elem, 'OpeningCreditBalance').text = '0.00'
            ET.SubElement(account_elem, 'ClosingDebitBalance').text = '0.00'
            ET.SubElement(account_elem, 'ClosingCreditBalance').text = '0.00'
            ET.SubElement(account_elem, 'GroupingCategory').text = self._get_grouping_category(account.code)
            ET.SubElement(account_elem, 'GroupingCode').text = account.code[:2] if len(account.code) >= 2 else account.code
            ET.SubElement(account_elem, 'TaxonomyCode').text = account.code
        
        # Customers
        customers = self.env['res.partner'].search([
            ('customer_rank', '>', 0),
            ('company_id', 'in', [False, self.company_id.id])
        ])
        
        for customer in customers:
            customer_elem = ET.SubElement(master_files, 'Customer')
            ET.SubElement(customer_elem, 'CustomerID').text = str(customer.id)
            ET.SubElement(customer_elem, 'AccountID').text = customer.property_account_receivable_id.code if customer.property_account_receivable_id else '21'
            ET.SubElement(customer_elem, 'CustomerTaxID').text = customer.vat or ''
            ET.SubElement(customer_elem, 'CompanyName').text = customer.name
            ET.SubElement(customer_elem, 'SelfBillingIndicator').text = '0'
            
            # Billing Address
            billing_address = ET.SubElement(customer_elem, 'BillingAddress')
            ET.SubElement(billing_address, 'AddressDetail').text = customer.street or ''
            ET.SubElement(billing_address, 'City').text = customer.city or ''
            ET.SubElement(billing_address, 'PostalCode').text = customer.zip or ''
            ET.SubElement(billing_address, 'Province').text = customer.state_id.name if customer.state_id else ''
            ET.SubElement(billing_address, 'Country').text = customer.country_id.code if customer.country_id else 'MZ'
        
        # Suppliers
        suppliers = self.env['res.partner'].search([
            ('supplier_rank', '>', 0),
            ('company_id', 'in', [False, self.company_id.id])
        ])
        
        for supplier in suppliers:
            supplier_elem = ET.SubElement(master_files, 'Supplier')
            ET.SubElement(supplier_elem, 'SupplierID').text = str(supplier.id)
            ET.SubElement(supplier_elem, 'AccountID').text = supplier.property_account_payable_id.code if supplier.property_account_payable_id else '22'
            ET.SubElement(supplier_elem, 'SupplierTaxID').text = supplier.vat or ''
            ET.SubElement(supplier_elem, 'CompanyName').text = supplier.name
            ET.SubElement(supplier_elem, 'SelfBillingIndicator').text = '0'
            
            # Billing Address
            billing_address = ET.SubElement(supplier_elem, 'BillingAddress')
            ET.SubElement(billing_address, 'AddressDetail').text = supplier.street or ''
            ET.SubElement(billing_address, 'City').text = supplier.city or ''
            ET.SubElement(billing_address, 'PostalCode').text = supplier.zip or ''
            ET.SubElement(billing_address, 'Province').text = supplier.state_id.name if supplier.state_id else ''
            ET.SubElement(billing_address, 'Country').text = supplier.country_id.code if supplier.country_id else 'MZ'
        
        # Tax Table
        taxes = self.env['account.tax'].search([
            ('company_id', '=', self.company_id.id)
        ])
        
        for tax in taxes:
            tax_elem = ET.SubElement(master_files, 'TaxTableEntry')
            ET.SubElement(tax_elem, 'TaxType').text = 'IVA' if 'IVA' in tax.name else 'NS'
            ET.SubElement(tax_elem, 'TaxCountryRegion').text = 'MZ'
            ET.SubElement(tax_elem, 'TaxCode').text = tax.description or tax.name[:10]
            ET.SubElement(tax_elem, 'Description').text = tax.name
            ET.SubElement(tax_elem, 'TaxPercentage').text = str(tax.amount)
    
    def _add_general_ledger_entries(self, root):
        """Add general ledger entries section"""
        gl_entries = ET.SubElement(root, 'GeneralLedgerEntries')
        
        # Number of entries
        journal_entries = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ])
        
        ET.SubElement(gl_entries, 'NumberOfEntries').text = str(len(journal_entries))
        ET.SubElement(gl_entries, 'TotalDebit').text = str(sum(journal_entries.mapped('amount_total')))
        ET.SubElement(gl_entries, 'TotalCredit').text = str(sum(journal_entries.mapped('amount_total')))
        
        # Journal entries by journal
        journals = journal_entries.mapped('journal_id')
        
        for journal in journals:
            journal_elem = ET.SubElement(gl_entries, 'Journal')
            ET.SubElement(journal_elem, 'JournalID').text = journal.code
            ET.SubElement(journal_elem, 'Description').text = journal.name
            
            # Transactions for this journal
            transactions = journal_entries.filtered(lambda m: m.journal_id == journal)
            
            for trans in transactions:
                trans_elem = ET.SubElement(journal_elem, 'Transaction')
                ET.SubElement(trans_elem, 'TransactionID').text = trans.name
                ET.SubElement(trans_elem, 'Period').text = str(trans.date.month)
                ET.SubElement(trans_elem, 'TransactionDate').text = trans.date.isoformat()
                ET.SubElement(trans_elem, 'SourceID').text = trans.create_uid.login if trans.create_uid else 'system'
                ET.SubElement(trans_elem, 'Description').text = trans.ref or trans.name
                ET.SubElement(trans_elem, 'DocArchivalNumber').text = trans.name
                ET.SubElement(trans_elem, 'TransactionType').text = 'N'  # Normal
                
                # Lines
                lines_elem = ET.SubElement(trans_elem, 'Lines')
                for line in trans.line_ids:
                    self._add_transaction_line(lines_elem, line)
    
    def _add_transaction_line(self, parent, line):
        """Add transaction line"""
        line_elem = ET.SubElement(parent, 'DebitLine' if line.debit > 0 else 'CreditLine')
        ET.SubElement(line_elem, 'AccountID').text = line.account_id.code
        ET.SubElement(line_elem, 'SourceDocumentID').text = line.move_id.name
        ET.SubElement(line_elem, 'Description').text = line.name or ''
        
        if line.debit > 0:
            ET.SubElement(line_elem, 'DebitAmount').text = str(line.debit)
        else:
            ET.SubElement(line_elem, 'CreditAmount').text = str(line.credit)
    
    def _add_source_documents(self, root):
        """Add source documents section"""
        source_docs = ET.SubElement(root, 'SourceDocuments')
        
        # Sales Invoices
        if self.export_type in ['full', 'invoices']:
            self._add_sales_invoices(source_docs)
        
        # Payments
        if self.export_type in ['full', 'payments']:
            self._add_payments(source_docs)
    
    def _add_sales_invoices(self, parent):
        """Add sales invoices"""
        sales_invoices = ET.SubElement(parent, 'SalesInvoices')
        
        invoices = self.env['moz.invoice'].search([
            ('company_id', '=', self.company_id.id),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', 'in', ['posted', 'certified'])
        ])
        
        ET.SubElement(sales_invoices, 'NumberOfEntries').text = str(len(invoices))
        ET.SubElement(sales_invoices, 'TotalDebit').text = str(sum(invoices.mapped('amount_total')))
        ET.SubElement(sales_invoices, 'TotalCredit').text = '0.00'
        
        for invoice in invoices:
            invoice_elem = ET.SubElement(sales_invoices, 'Invoice')
            ET.SubElement(invoice_elem, 'InvoiceNo').text = invoice.number
            ET.SubElement(invoice_elem, 'DocumentStatus').text = 'N' if invoice.state == 'certified' else 'A'
            ET.SubElement(invoice_elem, 'Hash').text = invoice.hash_code or ''
            ET.SubElement(invoice_elem, 'HashControl').text = '1'
            ET.SubElement(invoice_elem, 'Period').text = str(invoice.invoice_date.month)
            ET.SubElement(invoice_elem, 'InvoiceDate').text = invoice.invoice_date.isoformat()
            ET.SubElement(invoice_elem, 'InvoiceType').text = invoice.invoice_type
            
            # Special regimes
            special_regimes = ET.SubElement(invoice_elem, 'SpecialRegimes')
            ET.SubElement(special_regimes, 'SelfBillingIndicator').text = '0'
            ET.SubElement(special_regimes, 'CashVATSchemeIndicator').text = '0'
            ET.SubElement(special_regimes, 'ThirdPartiesBillingIndicator').text = '0'
            
            ET.SubElement(invoice_elem, 'SourceID').text = invoice.create_uid.login if invoice.create_uid else 'system'
            ET.SubElement(invoice_elem, 'SystemEntryDate').text = invoice.create_date.date().isoformat()
            ET.SubElement(invoice_elem, 'CustomerID').text = str(invoice.partner_id.id)
            
            # Lines
            for line in invoice.invoice_line_ids:
                line_elem = ET.SubElement(invoice_elem, 'Line')
                ET.SubElement(line_elem, 'LineNumber').text = str(line.sequence)
                ET.SubElement(line_elem, 'ProductCode').text = line.product_id.default_code if line.product_id.default_code else str(line.product_id.id)
                ET.SubElement(line_elem, 'ProductDescription').text = line.name or line.product_id.name
                ET.SubElement(line_elem, 'Quantity').text = str(line.quantity)
                ET.SubElement(line_elem, 'UnitOfMeasure').text = line.uom_id.name
                ET.SubElement(line_elem, 'UnitPrice').text = str(line.price_unit)
                ET.SubElement(line_elem, 'TaxPointDate').text = invoice.invoice_date.isoformat()
                ET.SubElement(line_elem, 'Description').text = line.name or ''
                ET.SubElement(line_elem, 'CreditAmount').text = str(line.price_total)
                
                # Tax
                if line.tax_ids:
                    tax = line.tax_ids[0]
                    tax_elem = ET.SubElement(line_elem, 'Tax')
                    ET.SubElement(tax_elem, 'TaxType').text = 'IVA'
                    ET.SubElement(tax_elem, 'TaxCountryRegion').text = 'MZ'
                    ET.SubElement(tax_elem, 'TaxCode').text = tax.description or 'IVA'
                    ET.SubElement(tax_elem, 'TaxPercentage').text = str(tax.amount)
            
            # Document totals
            totals = ET.SubElement(invoice_elem, 'DocumentTotals')
            ET.SubElement(totals, 'TaxPayable').text = str(invoice.amount_tax)
            ET.SubElement(totals, 'NetTotal').text = str(invoice.amount_untaxed)
            ET.SubElement(totals, 'GrossTotal').text = str(invoice.amount_total)
    
    def _add_payments(self, parent):
        """Add payments section"""
        payments = ET.SubElement(parent, 'Payments')
        ET.SubElement(payments, 'NumberOfEntries').text = '0'
        ET.SubElement(payments, 'TotalDebit').text = '0.00'
        ET.SubElement(payments, 'TotalCredit').text = '0.00'
    
    def _get_grouping_category(self, account_code):
        """Get grouping category based on account code"""
        if account_code.startswith('1'):
            return 'GA'  # Ativo
        elif account_code.startswith('2'):
            return 'GA'  # Ativo
        elif account_code.startswith('3'):
            return 'GA'  # Ativo
        elif account_code.startswith('4'):
            return 'GP'  # Passivo
        elif account_code.startswith('5'):
            return 'GCP'  # Capital Próprio
        elif account_code.startswith('6'):
            return 'GC'  # Custos
        elif account_code.startswith('7'):
            return 'GR'  # Rendimentos
        elif account_code.startswith('8'):
            return 'GR'  # Resultados
        else:
            return 'GO'  # Outros