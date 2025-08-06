# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import hashlib
import qrcode
import base64
from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json

class MozInvoice(models.Model):
    _name = 'moz.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Mozambican Certified Invoice'
    _order = 'invoice_date desc, sequence desc'
    _rec_name = 'number'

    # Basic Information
    number = fields.Char(
        string='Invoice Number',
        readonly=True,
        copy=False,
        index=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Sequence Number',
        readonly=True,
        copy=False,
        help='Sequential number without gaps'
    )
    
    invoice_type = fields.Selection([
        ('FT', 'Fatura'),
        ('FR', 'Fatura-Recibo'),
        ('VD', 'Venda a Dinheiro'),
        ('FS', 'Fatura Simplificada'),
        ('NC', 'Nota de Crédito'),
        ('ND', 'Nota de Débito'),
        ('GT', 'Guia de Transporte'),
        ('GR', 'Guia de Remessa'),
        ('CM', 'Consulta de Mesa'),
        ('PP', 'Pré-Pagamento'),
    ], string='Document Type', required=True, default='FT', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('certified', 'Certified'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, readonly=True)
    
    # Dates
    invoice_date = fields.Date(
        string='Invoice Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    due_date = fields.Date(
        string='Due Date',
        required=True,
        tracking=True
    )
    
    # Partner Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True
    )
    
    partner_vat = fields.Char(
        related='partner_id.vat',
        string='NUIT',
        readonly=True,
        store=True
    )
    
    partner_street = fields.Char(
        related='partner_id.street',
        string='Address',
        readonly=True
    )
    
    # Company Information
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True
    )
    
    # Lines
    invoice_line_ids = fields.One2many(
        'moz.invoice.line',
        'invoice_id',
        string='Invoice Lines',
        copy=True
    )
    
    # Tax fields
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    
    amount_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    
    # IVA Breakdown
    tax_summary_ids = fields.One2many(
        'moz.invoice.tax.summary',
        'invoice_id',
        string='Tax Summary',
        compute='_compute_tax_summary',
        store=True
    )
    
    # Certification Fields
    certification_date = fields.Datetime(
        string='Certification Date',
        readonly=True,
        copy=False
    )
    
    hash_code = fields.Char(
        string='Hash Code',
        readonly=True,
        copy=False,
        help='SHA-256 hash for invoice certification'
    )
    
    previous_hash = fields.Char(
        string='Previous Hash',
        readonly=True,
        copy=False,
        help='Hash from previous invoice'
    )
    
    qr_code = fields.Binary(
        string='QR Code',
        readonly=True,
        copy=False,
        attachment=True
    )
    
    at_code = fields.Char(
        string='AT Validation Code',
        readonly=True,
        copy=False,
        help='Validation code from Tax Authority'
    )
    
    # Payment Information
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        tracking=True
    )
    
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ], string='Payment State', default='not_paid', tracking=True)
    
    # Accounting
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'sale')]",
        tracking=True
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )
    
    # Additional Info
    reference = fields.Char(
        string='Customer Reference',
        tracking=True
    )
    
    narration = fields.Text(
        string='Terms and Conditions'
    )
    
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        tracking=True
    )
    
    # Computed Fields
    invoice_has_discount = fields.Boolean(
        compute='_compute_has_discount',
        string='Has Discount'
    )
    
    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids')
    def _compute_amounts(self):
        for invoice in self:
            amount_untaxed = sum(line.price_subtotal for line in invoice.invoice_line_ids)
            
            # Calculate taxes
            tax_lines = {}
            for line in invoice.invoice_line_ids:
                for tax in line.tax_ids:
                    tax_amount = line.price_subtotal * (tax.amount / 100)
                    if tax.id not in tax_lines:
                        tax_lines[tax.id] = 0
                    tax_lines[tax.id] += tax_amount
            
            amount_tax = sum(tax_lines.values())
            
            invoice.amount_untaxed = amount_untaxed
            invoice.amount_tax = amount_tax
            invoice.amount_total = amount_untaxed + amount_tax
    
    @api.depends('invoice_line_ids.discount')
    def _compute_has_discount(self):
        for invoice in self:
            invoice.invoice_has_discount = any(line.discount > 0 for line in invoice.invoice_line_ids)
    
    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_tax_summary(self):
        for invoice in self:
            tax_summary = {}
            for line in invoice.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax.id not in tax_summary:
                        tax_summary[tax.id] = {
                            'tax_id': tax.id,
                            'tax_name': tax.name,
                            'tax_rate': tax.amount,
                            'base_amount': 0,
                            'tax_amount': 0,
                        }
                    tax_summary[tax.id]['base_amount'] += line.price_subtotal
                    tax_summary[tax.id]['tax_amount'] += line.price_subtotal * (tax.amount / 100)
            
            # Clear existing records
            invoice.tax_summary_ids.unlink()
            
            # Create new summary records
            for tax_data in tax_summary.values():
                self.env['moz.invoice.tax.summary'].create({
                    'invoice_id': invoice.id,
                    'tax_id': tax_data['tax_id'],
                    'base_amount': tax_data['base_amount'],
                    'tax_amount': tax_data['tax_amount'],
                })
    
    @api.model
    def create(self, vals):
        if not vals.get('number'):
            # Get next sequence number
            sequence = self.env['ir.sequence'].next_by_code('moz.invoice')
            if not sequence:
                raise UserError(_('Please configure the invoice sequence.'))
            vals['number'] = sequence
            
            # Get sequential number without gaps
            last_invoice = self.search(
                [('company_id', '=', vals.get('company_id', self.env.company.id))],
                order='sequence desc',
                limit=1
            )
            vals['sequence'] = (last_invoice.sequence or 0) + 1
        
        return super().create(vals)
    
    def action_post(self):
        """Post the invoice and create accounting entries"""
        for invoice in self:
            if invoice.state != 'draft':
                raise UserError(_('Only draft invoices can be posted.'))
            
            # Validate invoice lines
            if not invoice.invoice_line_ids:
                raise UserError(_('Please add at least one invoice line.'))
            
            # Create accounting move
            move = self._create_account_move()
            
            invoice.write({
                'state': 'posted',
                'move_id': move.id
            })
            
            # Auto-certify if configured
            if self.env.company.auto_certify_invoices:
                invoice.action_certify()
        
        return True
    
    def action_certify(self):
        """Certify the invoice with AT"""
        for invoice in self:
            if invoice.state not in ['posted']:
                raise UserError(_('Only posted invoices can be certified.'))
            
            if invoice.hash_code:
                raise UserError(_('Invoice is already certified.'))
            
            # Get previous invoice hash
            previous_invoice = self.search([
                ('sequence', '<', invoice.sequence),
                ('company_id', '=', invoice.company_id.id),
                ('state', '=', 'certified')
            ], order='sequence desc', limit=1)
            
            previous_hash = previous_invoice.hash_code if previous_invoice else ''
            
            # Generate hash
            hash_data = invoice._prepare_hash_data(previous_hash)
            hash_code = hashlib.sha256(hash_data.encode()).hexdigest()
            
            # Generate QR Code
            qr_data = invoice._prepare_qr_data(hash_code)
            qr_code = invoice._generate_qr_code(qr_data)
            
            # Get AT validation code (mock for now)
            at_code = invoice._get_at_validation_code(hash_code)
            
            invoice.write({
                'state': 'certified',
                'certification_date': fields.Datetime.now(),
                'hash_code': hash_code,
                'previous_hash': previous_hash,
                'qr_code': qr_code,
                'at_code': at_code
            })
        
        return True
    
    def action_cancel(self):
        """Cancel the invoice"""
        for invoice in self:
            if invoice.state == 'certified':
                raise UserError(_('Certified invoices cannot be cancelled. Create a credit note instead.'))
            
            if invoice.move_id:
                invoice.move_id.button_cancel()
                invoice.move_id.unlink()
            
            invoice.state = 'cancelled'
        
        return True
    
    def action_draft(self):
        """Reset to draft"""
        for invoice in self:
            if invoice.state == 'certified':
                raise UserError(_('Certified invoices cannot be reset to draft.'))
            
            invoice.state = 'draft'
        
        return True
    
    def _prepare_hash_data(self, previous_hash):
        """Prepare data for hash generation"""
        self.ensure_one()
        
        # Format: Date;SystemEntryDate;Number;Total;PreviousHash
        data_parts = [
            self.invoice_date.strftime('%Y-%m-%d'),
            fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            self.number,
            str(self.amount_total),
            previous_hash or ''
        ]
        
        return ';'.join(data_parts)
    
    def _prepare_qr_data(self, hash_code):
        """Prepare data for QR code"""
        self.ensure_one()
        
        qr_data = {
            'NIF': self.company_id.vat or '',
            'NUIT': self.partner_vat or '',
            'Numero': self.number,
            'Data': self.invoice_date.strftime('%Y-%m-%d'),
            'Total': float(self.amount_total),
            'Hash': hash_code[:8],  # First 8 chars of hash
        }
        
        return json.dumps(qr_data)
    
    def _generate_qr_code(self, data):
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue())
        
        return img_str
    
    def _get_at_validation_code(self, hash_code):
        """Get validation code from AT (mock implementation)"""
        # In production, this would call AT web service
        return f"AT-{hash_code[:8].upper()}"
    
    def _create_account_move(self):
        """Create accounting entries for the invoice"""
        self.ensure_one()
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.invoice_date,
            'ref': self.number,
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice' if self.invoice_type in ['FT', 'FR', 'VD', 'FS'] else 'out_refund',
            'currency_id': self.currency_id.id,
            'line_ids': [],
        }
        
        # Customer line
        move_vals['line_ids'].append((0, 0, {
            'name': f"{self.invoice_type}/{self.number}",
            'account_id': self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.amount_total if self.invoice_type != 'NC' else 0,
            'credit': self.amount_total if self.invoice_type == 'NC' else 0,
            'currency_id': self.currency_id.id,
        }))
        
        # Revenue lines
        for line in self.invoice_line_ids:
            move_vals['line_ids'].append((0, 0, {
                'name': line.name or line.product_id.name,
                'account_id': line.account_id.id,
                'partner_id': self.partner_id.id,
                'debit': 0 if self.invoice_type != 'NC' else line.price_subtotal,
                'credit': line.price_subtotal if self.invoice_type != 'NC' else 0,
                'currency_id': self.currency_id.id,
            }))
        
        # Tax lines
        for tax_summary in self.tax_summary_ids:
            move_vals['line_ids'].append((0, 0, {
                'name': f"IVA {tax_summary.tax_id.name}",
                'account_id': tax_summary.tax_id.account_id.id,
                'partner_id': self.partner_id.id,
                'debit': 0 if self.invoice_type != 'NC' else tax_summary.tax_amount,
                'credit': tax_summary.tax_amount if self.invoice_type != 'NC' else 0,
                'currency_id': self.currency_id.id,
                'tax_base_amount': tax_summary.base_amount,
            }))
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move
    
    @api.constrains('state', 'hash_code')
    def _check_certification_immutable(self):
        """Ensure certified invoices cannot be modified"""
        for invoice in self:
            if invoice.state == 'certified' and invoice.hash_code:
                if any(field in self._context.get('modified_fields', []) 
                       for field in ['invoice_line_ids', 'amount_total', 'partner_id', 'invoice_date']):
                    raise ValidationError(_('Certified invoices cannot be modified.'))


class MozInvoiceTaxSummary(models.Model):
    _name = 'moz.invoice.tax.summary'
    _description = 'Invoice Tax Summary'
    
    invoice_id = fields.Many2one(
        'moz.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade'
    )
    
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax',
        required=True
    )
    
    base_amount = fields.Monetary(
        string='Base Amount',
        currency_field='currency_id'
    )
    
    tax_amount = fields.Monetary(
        string='Tax Amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string='Currency'
    )