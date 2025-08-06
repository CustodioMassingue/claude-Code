# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import logging

_logger = logging.getLogger(__name__)


class MozTax(models.Model):
    """Tax Model for Mozambican Tax System"""
    
    _name = 'moz.tax'
    _description = 'Mozambican Tax'
    _order = 'sequence, name'
    _rec_name = 'display_name'
    
    # Basic Fields
    name = fields.Char(
        string='Tax Name',
        required=True,
        index=True,
        translate=True,
        help='Full name of the tax'
    )
    
    description = fields.Char(
        string='Label on Invoices',
        translate=True,
        help='Label to be shown on invoices'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    active = fields.Boolean(
        default=True,
        help='Set active to false to hide the tax without removing it'
    )
    
    sequence = fields.Integer(
        default=10,
        help='Used to order taxes in views'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Tax Type and Scope
    type_tax_use = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchases'),
        ('none', 'None'),
    ], string='Tax Type',
       default='sale',
       required=True,
       help='Determines where the tax can be used'
    )
    
    tax_scope = fields.Selection([
        ('service', 'Services'),
        ('consu', 'Consumables'),
        ('product', 'Products'),
    ], string='Tax Scope',
       help='Restrict tax to specific product types'
    )
    
    # Amount Type
    amount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('percent_of_price', '% of Price'),
        ('percent_of_price_taxed', '% of Price Tax Included'),
    ], string='Tax Computation',
       default='percent',
       required=True
    )
    
    amount = fields.Float(
        string='Amount',
        required=True,
        digits=(16, 4),
        help='Tax amount or percentage'
    )
    
    # Tax Group
    tax_group_id = fields.Many2one(
        'moz.tax.group',
        string='Tax Group',
        required=True,
        help='Tax group for reporting'
    )
    
    # Accounts
    invoice_repartition_line_ids = fields.One2many(
        'moz.tax.repartition.line',
        'invoice_tax_id',
        string='Distribution for Invoices',
        copy=True
    )
    
    refund_repartition_line_ids = fields.One2many(
        'moz.tax.repartition.line',
        'refund_tax_id',
        string='Distribution for Credit Notes',
        copy=True
    )
    
    # Advanced Options
    price_include = fields.Boolean(
        string='Included in Price',
        default=False,
        help='Tax included in product price'
    )
    
    include_base_amount = fields.Boolean(
        string='Include in Base Amount',
        default=False,
        help='Include this tax amount in base for next taxes'
    )
    
    analytic = fields.Boolean(
        string='Analytic',
        default=False,
        help='Tax generates analytic entries'
    )
    
    # Children Taxes
    children_tax_ids = fields.Many2many(
        'moz.tax',
        'moz_tax_filiation_rel',
        'parent_tax',
        'child_tax',
        string='Children Taxes',
        help='For grouped taxes'
    )
    
    # Mozambican Specific Fields
    tax_code = fields.Char(
        string='Tax Code',
        required=True,
        help='Official tax code (e.g., IVA, IRPS, IRPC)'
    )
    
    at_tax_type = fields.Selection([
        ('IVA', 'IVA - Imposto sobre Valor Acrescentado'),
        ('IS', 'IS - Imposto do Selo'),
        ('IRPS', 'IRPS - Imposto sobre Rendimento de Pessoas Singulares'),
        ('IRPC', 'IRPC - Imposto sobre Rendimento de Pessoas Colectivas'),
        ('ISPC', 'ISPC - Imposto Simplificado para Pequenos Contribuintes'),
        ('ICE', 'ICE - Imposto sobre Consumos Específicos'),
        ('IVA_REV', 'IVA - Reverse Charge'),
        ('IVA_EX', 'IVA - Exempted'),
        ('OUT', 'Other'),
    ], string='Mozambican Tax Type',
       required=True,
       help='Tax type for AT reporting'
    )
    
    saft_tax_code = fields.Char(
        string='SAF-T Tax Code',
        help='Tax code for SAF-T(MZ) reporting'
    )
    
    tax_region = fields.Selection([
        ('MOZ', 'Mozambique'),
        ('PT', 'Portugal'),
        ('SADC', 'SADC Region'),
        ('INT', 'International'),
    ], string='Tax Region',
       default='MOZ',
       help='Region where tax applies'
    )
    
    withholding = fields.Boolean(
        string='Is Withholding Tax',
        default=False,
        help='This is a withholding tax'
    )
    
    withholding_rate = fields.Float(
        string='Withholding Rate (%)',
        digits=(16, 2),
        help='Rate for withholding taxes'
    )
    
    legal_reference = fields.Text(
        string='Legal Reference',
        help='Legal basis for this tax (laws, decrees, etc.)'
    )
    
    # Computed Fields
    @api.depends('name', 'amount', 'amount_type')
    def _compute_display_name(self):
        for tax in self:
            if tax.amount_type == 'percent':
                tax.display_name = f"{tax.name} ({tax.amount}%)"
            elif tax.amount_type == 'fixed':
                tax.display_name = f"{tax.name} ({tax.amount} MT)"
            else:
                tax.display_name = tax.name
    
    # Constraints
    @api.constrains('amount_type', 'amount')
    def _check_amount(self):
        for tax in self:
            if tax.amount_type == 'percent' and (tax.amount < 0 or tax.amount > 100):
                raise ValidationError(
                    _("Tax percentage must be between 0 and 100!")
                )
            elif tax.amount < 0:
                raise ValidationError(
                    _("Tax amount cannot be negative!")
                )
    
    @api.constrains('tax_code', 'company_id')
    def _check_tax_code_unique(self):
        for tax in self:
            duplicate = self.search([
                ('tax_code', '=', tax.tax_code),
                ('company_id', '=', tax.company_id.id),
                ('id', '!=', tax.id)
            ])
            
            if duplicate:
                raise ValidationError(
                    _("Tax code '%s' already exists!") % tax.tax_code
                )
    
    @api.constrains('withholding', 'withholding_rate')
    def _check_withholding(self):
        for tax in self:
            if tax.withholding and not tax.withholding_rate:
                raise ValidationError(
                    _("Withholding tax must have a withholding rate!")
                )
    
    # CRUD Methods
    @api.model
    def create(self, vals):
        tax = super().create(vals)
        
        # Create default repartition lines if not provided
        if not tax.invoice_repartition_line_ids:
            tax._create_default_repartition_lines('invoice')
        
        if not tax.refund_repartition_line_ids:
            tax._create_default_repartition_lines('refund')
        
        return tax
    
    def unlink(self):
        for tax in self:
            # Check if tax is used in any transaction
            move_lines = self.env['moz.move.line'].search([
                '|',
                ('tax_ids', 'in', tax.id),
                ('tax_line_id', '=', tax.id)
            ], limit=1)
            
            if move_lines:
                raise UserError(
                    _("Cannot delete tax %s as it is used in transactions!") % tax.display_name
                )
        
        return super().unlink()
    
    # Business Methods
    def _create_default_repartition_lines(self, repartition_type: str):
        """Create default repartition lines"""
        self.ensure_one()
        
        # Base line
        base_line = {
            'factor_percent': 100,
            'repartition_type': 'base',
            'plus_report_line_ids': [(0, 0, {'tag_name': f'Base {self.name}'})]
        }
        
        # Tax line
        tax_line = {
            'factor_percent': 100,
            'repartition_type': 'tax',
            'plus_report_line_ids': [(0, 0, {'tag_name': self.name})]
        }
        
        if repartition_type == 'invoice':
            self.invoice_repartition_line_ids = [
                (0, 0, base_line),
                (0, 0, tax_line)
            ]
        else:
            # For refunds, negative tags
            base_line['minus_report_line_ids'] = base_line.pop('plus_report_line_ids')
            tax_line['minus_report_line_ids'] = tax_line.pop('plus_report_line_ids')
            
            self.refund_repartition_line_ids = [
                (0, 0, base_line),
                (0, 0, tax_line)
            ]
    
    def compute_all(self, price_unit: float, currency: Optional[models.Model] = None,
                   quantity: float = 1.0, product: Optional[models.Model] = None,
                   partner: Optional[models.Model] = None,
                   is_refund: bool = False) -> Dict:
        """Compute tax amounts"""
        
        if not currency:
            currency = self.company_id.currency_id
        
        # Use Decimal for precision
        price_decimal = Decimal(str(price_unit))
        quantity_decimal = Decimal(str(quantity))
        
        base_amount = price_decimal * quantity_decimal
        
        taxes = []
        total_excluded = base_amount
        total_included = base_amount
        total_void = base_amount
        
        for tax in self:
            tax_amount = Decimal('0')
            
            if tax.amount_type == 'percent':
                if tax.price_include:
                    # Tax included in price
                    tax_amount = base_amount - (base_amount / (1 + Decimal(str(tax.amount)) / 100))
                else:
                    # Tax excluded from price
                    tax_amount = base_amount * (Decimal(str(tax.amount)) / 100)
            
            elif tax.amount_type == 'fixed':
                tax_amount = Decimal(str(tax.amount)) * quantity_decimal
            
            elif tax.amount_type == 'percent_of_price':
                tax_amount = price_decimal * (Decimal(str(tax.amount)) / 100) * quantity_decimal
            
            elif tax.amount_type == 'percent_of_price_taxed':
                tax_amount = price_decimal * (Decimal(str(tax.amount)) / 100) * quantity_decimal
                if not tax.price_include:
                    base_amount += tax_amount
            
            # Round to currency precision
            tax_amount = float(tax_amount.quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            ))
            
            taxes.append({
                'id': tax.id,
                'name': tax.name,
                'amount': tax_amount,
                'base': float(base_amount),
                'sequence': tax.sequence,
                'tax_code': tax.tax_code,
                'at_tax_type': tax.at_tax_type,
            })
            
            if tax.price_include:
                total_excluded = total_excluded - Decimal(str(tax_amount))
            else:
                total_included = total_included + Decimal(str(tax_amount))
            
            # Update base for compound taxes
            if tax.include_base_amount:
                base_amount += Decimal(str(tax_amount))
        
        return {
            'taxes': taxes,
            'total_excluded': float(total_excluded),
            'total_included': float(total_included),
            'total_void': float(total_void),
            'base_tags': [],
        }
    
    def get_tax_accounts(self, product: Optional[models.Model] = None,
                        partner: Optional[models.Model] = None) -> Tuple:
        """Get tax accounts for a given product/partner"""
        self.ensure_one()
        
        # Get accounts from repartition lines
        invoice_lines = self.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'tax'
        )
        refund_lines = self.refund_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'tax'
        )
        
        invoice_account = invoice_lines[0].account_id if invoice_lines else False
        refund_account = refund_lines[0].account_id if refund_lines else False
        
        return invoice_account, refund_account
    
    @api.model
    def create_mozambican_taxes(self):
        """Create standard Mozambican taxes according to current legislation"""
        
        taxes_data = [
            # ============ IVA - Imposto sobre Valor Acrescentado ============
            {
                'name': 'IVA 16%',
                'tax_code': 'IVA16',
                'amount': 16,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'at_tax_type': 'IVA',
                'saft_tax_code': 'IVA-16',
                'description': 'IVA 16%',
                'legal_reference': 'Lei n.º 32/2016, de 30 de Dezembro - Código do IVA (Taxa: 16% - Art. 27º)'
            },
            {
                'name': 'IVA 16% (Compras)',
                'tax_code': 'IVA16_P',
                'amount': 16,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IVA',
                'saft_tax_code': 'IVA-16',
                'description': 'IVA 16%',
                'legal_reference': 'Lei n.º 32/2016, de 30 de Dezembro - Código do IVA (Taxa: 16% - Art. 27º)'
            },
            {
                'name': 'IVA Taxa Zero',
                'tax_code': 'IVA0',
                'amount': 0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'at_tax_type': 'IVA',
                'saft_tax_code': 'IVA-0',
                'description': 'IVA 0%',
                'legal_reference': 'Lei n.º 32/2016 - Art. 28º (Exportações e operações assimiladas)'
            },
            {
                'name': 'IVA Isento',
                'tax_code': 'IVA_EX',
                'amount': 0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'at_tax_type': 'IVA_EX',
                'saft_tax_code': 'IVA-ISE',
                'description': 'IVA Isento',
                'legal_reference': 'Lei n.º 32/2016 - Art. 9º (Lista de isenções)'
            },
            {
                'name': 'IVA Autoliquidação',
                'tax_code': 'IVA_REV',
                'amount': 16,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IVA_REV',
                'saft_tax_code': 'IVA-REV',
                'description': 'IVA Reverse Charge',
                'legal_reference': 'Lei n.º 32/2016 - Art. 7º (Inversão do sujeito passivo)'
            },
            
            # ============ IRPS - Imposto sobre Rendimento de Pessoas Singulares ============
            # Categoria A - Trabalho Dependente
            {
                'name': 'IRPS Cat. A - 10%',
                'tax_code': 'IRPS_A10',
                'amount': 10,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-A10',
                'withholding': True,
                'withholding_rate': 10,
                'description': 'IRPS Cat. A 10%',
                'legal_reference': 'Lei n.º 33/2007 atualizada pela Lei n.º 5/2023 - Tabela Cat. A'
            },
            {
                'name': 'IRPS Cat. A - 15%',
                'tax_code': 'IRPS_A15',
                'amount': 15,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-A15',
                'withholding': True,
                'withholding_rate': 15,
                'description': 'IRPS Cat. A 15%',
                'legal_reference': 'Lei n.º 33/2007 atualizada pela Lei n.º 5/2023 - Tabela Cat. A'
            },
            {
                'name': 'IRPS Cat. A - 20%',
                'tax_code': 'IRPS_A20',
                'amount': 20,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-A20',
                'withholding': True,
                'withholding_rate': 20,
                'description': 'IRPS Cat. A 20%',
                'legal_reference': 'Lei n.º 33/2007 atualizada pela Lei n.º 5/2023 - Tabela Cat. A'
            },
            {
                'name': 'IRPS Cat. A - 25%',
                'tax_code': 'IRPS_A25',
                'amount': 25,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-A25',
                'withholding': True,
                'withholding_rate': 25,
                'description': 'IRPS Cat. A 25%',
                'legal_reference': 'Lei n.º 33/2007 atualizada pela Lei n.º 5/2023 - Tabela Cat. A'
            },
            {
                'name': 'IRPS Cat. A - 32%',
                'tax_code': 'IRPS_A32',
                'amount': 32,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-A32',
                'withholding': True,
                'withholding_rate': 32,
                'description': 'IRPS Cat. A 32%',
                'legal_reference': 'Lei n.º 33/2007 atualizada pela Lei n.º 5/2023 - Tabela Cat. A'
            },
            
            # Categoria B - Rendimentos Empresariais e Profissionais
            {
                'name': 'IRPS Cat. B - Serviços 20%',
                'tax_code': 'IRPS_B20',
                'amount': 20,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-B20',
                'withholding': True,
                'withholding_rate': 20,
                'description': 'IRPS Cat. B 20%',
                'legal_reference': 'Lei n.º 33/2007 - Art. 67º (Serviços)'
            },
            
            # Categoria C - Rendimentos de Capitais
            {
                'name': 'IRPS Cat. C - Dividendos 20%',
                'tax_code': 'IRPS_C20',
                'amount': 20,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-C20',
                'withholding': True,
                'withholding_rate': 20,
                'description': 'IRPS Dividendos 20%',
                'legal_reference': 'Lei n.º 33/2007 - Art. 71º (Rendimentos de capitais)'
            },
            
            # Categoria D - Rendimentos Prediais
            {
                'name': 'IRPS Cat. D - Rendas 10%',
                'tax_code': 'IRPS_D10',
                'amount': 10,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IRPS',
                'saft_tax_code': 'IRPS-D10',
                'withholding': True,
                'withholding_rate': 10,
                'description': 'IRPS Rendas 10%',
                'legal_reference': 'Lei n.º 33/2007 - Art. 72º (Rendimentos prediais)'
            },
            
            # ============ IRPC - Imposto sobre Rendimento de Pessoas Colectivas ============
            {
                'name': 'IRPC 32%',
                'tax_code': 'IRPC32',
                'amount': 32,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'IRPC',
                'saft_tax_code': 'IRPC-32',
                'description': 'IRPC 32%',
                'legal_reference': 'Lei n.º 34/2007, de 31 de Dezembro - Código do IRPC (Taxa: 32%)'
            },
            {
                'name': 'IRPC Agricultura 10%',
                'tax_code': 'IRPC_AGRI10',
                'amount': 10,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'IRPC',
                'saft_tax_code': 'IRPC-AGRI',
                'description': 'IRPC Agricultura 10%',
                'legal_reference': 'Lei n.º 34/2007 - Regime especial agricultura (10 primeiros anos)'
            },
            {
                'name': 'Pagamento Especial por Conta (PEC)',
                'tax_code': 'PEC',
                'amount': 0.5,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'IRPC',
                'saft_tax_code': 'PEC',
                'description': 'PEC 0.5%',
                'legal_reference': 'Lei n.º 34/2007 - Art. 106º (Pagamentos por conta)'
            },
            {
                'name': 'Pagamento por Conta (PC)',
                'tax_code': 'PC',
                'amount': 0.5,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'IRPC',
                'saft_tax_code': 'PC',
                'description': 'PC 0.5%',
                'legal_reference': 'Lei n.º 34/2007 - Art. 107º (Pagamento por conta)'
            },
            
            # ============ INSS - Instituto Nacional de Segurança Social ============
            {
                'name': 'INSS Trabalhador 3%',
                'tax_code': 'INSS_TRAB',
                'amount': 3,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'OUT',
                'saft_tax_code': 'INSS-T3',
                'description': 'INSS Trab. 3%',
                'legal_reference': 'Lei n.º 4/2007, de 7 de Fevereiro - Segurança Social'
            },
            {
                'name': 'INSS Entidade Patronal 4%',
                'tax_code': 'INSS_EMP',
                'amount': 4,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'OUT',
                'saft_tax_code': 'INSS-E4',
                'description': 'INSS Emp. 4%',
                'legal_reference': 'Lei n.º 4/2007, de 7 de Fevereiro - Segurança Social'
            },
            
            # ============ Imposto do Selo ============
            {
                'name': 'Imposto do Selo - Contratos 0.03%',
                'tax_code': 'IS_CONT',
                'amount': 0.03,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'at_tax_type': 'IS',
                'saft_tax_code': 'IS-003',
                'description': 'Imp. Selo 0.03%',
                'legal_reference': 'Decreto n.º 6/2017, de 31 de Março - Tabela Geral'
            },
            {
                'name': 'Imposto do Selo - Letras 0.05%',
                'tax_code': 'IS_LET',
                'amount': 0.05,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'at_tax_type': 'IS',
                'saft_tax_code': 'IS-005',
                'description': 'Imp. Selo 0.05%',
                'legal_reference': 'Decreto n.º 6/2017, de 31 de Março - Letras e Livranças'
            },
            {
                'name': 'Imposto do Selo - Seguros 3%',
                'tax_code': 'IS_SEG',
                'amount': 3,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'at_tax_type': 'IS',
                'saft_tax_code': 'IS-SEG3',
                'description': 'Imp. Selo Seguros 3%',
                'legal_reference': 'Decreto n.º 6/2017, de 31 de Março - Prémios de seguro'
            },
            {
                'name': 'Imposto do Selo - Cheques',
                'tax_code': 'IS_CHQ',
                'amount': 100,
                'amount_type': 'fixed',
                'type_tax_use': 'sale',
                'at_tax_type': 'IS',
                'saft_tax_code': 'IS-CHQ',
                'description': 'Imp. Selo Cheques',
                'legal_reference': 'Decreto n.º 6/2017, de 31 de Março - 100 MT por folha'
            },
            
            # ============ ISPC - Imposto Simplificado para Pequenos Contribuintes ============
            {
                'name': 'ISPC 3%',
                'tax_code': 'ISPC3',
                'amount': 3,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'ISPC',
                'saft_tax_code': 'ISPC-3',
                'description': 'ISPC 3%',
                'legal_reference': 'Lei n.º 5/2009 - Volume negócios 100.001 a 500.000 MT'
            },
            {
                'name': 'ISPC 5%',
                'tax_code': 'ISPC5',
                'amount': 5,
                'amount_type': 'percent',
                'type_tax_use': 'none',
                'at_tax_type': 'ISPC',
                'saft_tax_code': 'ISPC-5',
                'description': 'ISPC 5%',
                'legal_reference': 'Lei n.º 5/2009 - Volume negócios 500.001 a 2.500.000 MT'
            },
            {
                'name': 'ISPC Fixo',
                'tax_code': 'ISPC_FIXO',
                'amount': 75000,
                'amount_type': 'fixed',
                'type_tax_use': 'none',
                'at_tax_type': 'ISPC',
                'saft_tax_code': 'ISPC-FIX',
                'description': 'ISPC Fixo Anual',
                'legal_reference': 'Lei n.º 5/2009 - Volume negócios até 100.000 MT (75.000 MT/ano)'
            }
        ]
        
        for tax_data in taxes_data:
            # Check if tax already exists
            existing = self.search([
                ('tax_code', '=', tax_data['tax_code']),
                ('company_id', '=', self.env.company.id)
            ])
            
            if not existing:
                # Get or create tax group
                group = self.env['moz.tax.group'].search([
                    ('code', '=', tax_data['at_tax_type'])
                ], limit=1)
                
                if not group:
                    group = self.env['moz.tax.group'].create({
                        'name': tax_data['at_tax_type'],
                        'code': tax_data['at_tax_type']
                    })
                
                tax_data['tax_group_id'] = group.id
                tax_data['company_id'] = self.env.company.id
                
                self.create(tax_data)
                _logger.info("Created tax: %s", tax_data['name'])
    
    def action_view_tax_lines(self):
        """View all tax lines for this tax"""
        self.ensure_one()
        
        return {
            'name': _('Tax Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move.line',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('tax_ids', 'in', self.id),
                ('tax_line_id', '=', self.id)
            ],
            'context': {}
        }