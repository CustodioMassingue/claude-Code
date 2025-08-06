# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class FiscalDeclarationWizard(models.TransientModel):
    _name = 'moz.fiscal.declaration.wizard'
    _description = 'Fiscal Declaration Wizard'
    
    declaration_type = fields.Selection([
        ('iva', 'IVA Declaration'),
        ('irpc', 'IRPC Declaration'),
        ('irps', 'IRPS Declaration'),
        ('m20', 'Model M/20 - Annual Declaration'),
    ], string='Declaration Type', required=True, default='iva')
    
    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Period Type', required=True, default='monthly')
    
    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year
    )
    
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month')
    
    quarter = fields.Selection([
        ('1', 'Q1'), ('2', 'Q2'), ('3', 'Q3'), ('4', 'Q4'),
    ], string='Quarter')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # IVA specific fields
    iva_sales_base = fields.Monetary(
        string='Sales Base Amount',
        currency_field='currency_id'
    )
    
    iva_sales_tax = fields.Monetary(
        string='Sales VAT Amount',
        currency_field='currency_id'
    )
    
    iva_purchases_base = fields.Monetary(
        string='Purchases Base Amount',
        currency_field='currency_id'
    )
    
    iva_purchases_tax = fields.Monetary(
        string='Purchases VAT Amount',
        currency_field='currency_id'
    )
    
    iva_payable = fields.Monetary(
        string='VAT Payable',
        compute='_compute_iva_payable',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency'
    )
    
    declaration_file = fields.Binary(
        string='Declaration File',
        readonly=True
    )
    
    declaration_filename = fields.Char(
        string='Filename',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('done', 'Done'),
    ], string='State', default='draft')
    
    @api.depends('iva_sales_tax', 'iva_purchases_tax')
    def _compute_iva_payable(self):
        for wizard in self:
            wizard.iva_payable = wizard.iva_sales_tax - wizard.iva_purchases_tax
    
    def action_calculate(self):
        """Calculate tax amounts"""
        self.ensure_one()
        
        if self.declaration_type == 'iva':
            self._calculate_iva()
        elif self.declaration_type == 'irpc':
            self._calculate_irpc()
        elif self.declaration_type == 'irps':
            self._calculate_irps()
        
        self.state = 'calculated'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _calculate_iva(self):
        """Calculate IVA amounts"""
        # Get date range
        date_from, date_to = self._get_date_range()
        
        # Sales invoices
        sales_invoices = self.env['moz.invoice'].search([
            ('company_id', '=', self.company_id.id),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('state', 'in', ['posted', 'certified']),
            ('invoice_type', 'in', ['FT', 'FR', 'VD', 'FS'])
        ])
        
        self.iva_sales_base = sum(sales_invoices.mapped('amount_untaxed'))
        self.iva_sales_tax = sum(sales_invoices.mapped('amount_tax'))
        
        # Purchase invoices
        purchase_invoices = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice')
        ])
        
        self.iva_purchases_base = sum(purchase_invoices.mapped('amount_untaxed'))
        self.iva_purchases_tax = sum(purchase_invoices.mapped('amount_tax'))
    
    def _calculate_irpc(self):
        """Calculate IRPC amounts"""
        # Simplified calculation - should be expanded based on requirements
        pass
    
    def _calculate_irps(self):
        """Calculate IRPS amounts"""
        # Simplified calculation - should be expanded based on requirements
        pass
    
    def _get_date_range(self):
        """Get date range based on period selection"""
        if self.period_type == 'monthly':
            month = int(self.month)
            date_from = datetime(self.year, month, 1).date()
            if month == 12:
                date_to = datetime(self.year, 12, 31).date()
            else:
                date_to = datetime(self.year, month + 1, 1).date()
                date_to = date_to.replace(day=1) - timedelta(days=1)
        elif self.period_type == 'quarterly':
            quarter = int(self.quarter)
            month_start = (quarter - 1) * 3 + 1
            month_end = quarter * 3
            date_from = datetime(self.year, month_start, 1).date()
            if month_end == 12:
                date_to = datetime(self.year, 12, 31).date()
            else:
                date_to = datetime(self.year, month_end + 1, 1).date()
                date_to = date_to.replace(day=1) - timedelta(days=1)
        else:  # annual
            date_from = datetime(self.year, 1, 1).date()
            date_to = datetime(self.year, 12, 31).date()
        
        return date_from, date_to
    
    def action_generate_declaration(self):
        """Generate declaration file"""
        self.ensure_one()
        
        if self.state != 'calculated':
            raise UserError(_('Please calculate the amounts first.'))
        
        # Generate declaration based on type
        if self.declaration_type == 'iva':
            content = self._generate_iva_declaration()
        else:
            content = "Declaration not yet implemented"
        
        # Save file
        self.declaration_file = base64.b64encode(content.encode('utf-8'))
        self.declaration_filename = f"{self.declaration_type}_{self.year}_{self.month or self.quarter or 'annual'}.txt"
        self.state = 'done'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _generate_iva_declaration(self):
        """Generate IVA declaration content"""
        content = []
        content.append(f"DECLARAÇÃO PERIÓDICA DO IVA")
        content.append(f"=" * 50)
        content.append(f"NUIT: {self.company_id.vat}")
        content.append(f"Denominação: {self.company_id.name}")
        content.append(f"Período: {self.year}/{self.month or self.quarter or 'Anual'}")
        content.append(f"")
        content.append(f"OPERAÇÕES REALIZADAS")
        content.append(f"-" * 30)
        content.append(f"Vendas e Prestações de Serviços:")
        content.append(f"  Base Tributável: {self.iva_sales_base:,.2f} MT")
        content.append(f"  IVA Liquidado: {self.iva_sales_tax:,.2f} MT")
        content.append(f"")
        content.append(f"Aquisições de Bens e Serviços:")
        content.append(f"  Base Tributável: {self.iva_purchases_base:,.2f} MT")
        content.append(f"  IVA Dedutível: {self.iva_purchases_tax:,.2f} MT")
        content.append(f"")
        content.append(f"APURAMENTO DO IMPOSTO")
        content.append(f"-" * 30)
        content.append(f"IVA a Pagar/Recuperar: {self.iva_payable:,.2f} MT")
        
        return "\n".join(content)