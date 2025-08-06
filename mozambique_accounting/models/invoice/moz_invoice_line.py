# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP

class MozInvoiceLine(models.Model):
    _name = 'moz.invoice.line'
    _description = 'Mozambican Invoice Line'
    _order = 'sequence, id'
    
    invoice_id = fields.Many2one(
        'moz.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    
    name = fields.Text(
        string='Description',
        required=True
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        domain="[('account_type', 'in', ['income', 'income_other'])]"
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    
    price_unit = fields.Monetary(
        string='Unit Price',
        required=True,
        currency_field='currency_id'
    )
    
    discount = fields.Float(
        string='Discount (%)',
        default=0.0,
        digits='Discount'
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain="[('type_tax_use', '=', 'sale')]"
    )
    
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_price',
        store=True,
        currency_field='currency_id'
    )
    
    price_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_price',
        store=True,
        currency_field='currency_id'
    )
    
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_price',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string='Currency',
        readonly=True
    )
    
    company_id = fields.Many2one(
        related='invoice_id.company_id',
        string='Company',
        readonly=True,
        store=True
    )
    
    # Analytics
    analytic_distribution = fields.Json(
        string='Analytic Distribution'
    )
    
    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids')
    def _compute_price(self):
        for line in self:
            # Calculate base price
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            
            # Calculate subtotal
            subtotal = Decimal(str(line.quantity)) * Decimal(str(price))
            line.price_subtotal = float(subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            # Calculate tax
            if line.tax_ids:
                tax_amount = Decimal('0')
                for tax in line.tax_ids:
                    if tax.amount_type == 'percent':
                        tax_amount += subtotal * (Decimal(str(tax.amount)) / Decimal('100'))
                    elif tax.amount_type == 'fixed':
                        tax_amount += Decimal(str(tax.amount)) * Decimal(str(line.quantity))
                
                line.price_tax = float(tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            else:
                line.price_tax = 0.0
            
            # Calculate total
            line.price_total = line.price_subtotal + line.price_tax
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.get_product_multiline_description_sale()
            self.uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price
            
            # Set default account
            if self.product_id.property_account_income_id:
                self.account_id = self.product_id.property_account_income_id
            elif self.product_id.categ_id.property_account_income_categ_id:
                self.account_id = self.product_id.categ_id.property_account_income_categ_id
            
            # Set default taxes
            if self.product_id.taxes_id:
                self.tax_ids = self.product_id.taxes_id.filtered(
                    lambda tax: tax.company_id == self.company_id
                )
            
            # Apply fiscal position
            if self.invoice_id.fiscal_position_id:
                self.tax_ids = self.invoice_id.fiscal_position_id.map_tax(self.tax_ids)
    
    @api.constrains('discount')
    def _check_discount(self):
        for line in self:
            if line.discount < 0 or line.discount > 100:
                raise ValidationError(_('Discount must be between 0 and 100%.'))
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be positive.'))