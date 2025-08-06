# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from typing import Dict, List, Optional
import logging

_logger = logging.getLogger(__name__)


class MozTaxGroup(models.Model):
    """Tax Groups for Mozambican Tax Reporting"""
    
    _name = 'moz.tax.group'
    _description = 'Mozambican Tax Group'
    _order = 'sequence, name'
    
    # Basic Fields
    name = fields.Char(
        string='Tax Group',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        index=True,
        help='Unique code for the tax group'
    )
    
    sequence = fields.Integer(
        default=10,
        help='Sequence for ordering'
    )
    
    active = fields.Boolean(
        default=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Tax Type
    tax_type = fields.Selection([
        ('iva', 'IVA - Imposto sobre Valor Acrescentado'),
        ('irps', 'IRPS - Imposto sobre Rendimento de Pessoas Singulares'),
        ('irpc', 'IRPC - Imposto sobre Rendimento de Pessoas Colectivas'),
        ('is', 'IS - Imposto do Selo'),
        ('ispc', 'ISPC - Imposto Simplificado para Pequenos Contribuintes'),
        ('ice', 'ICE - Imposto sobre Consumos Específicos'),
        ('other', 'Other'),
    ], string='Tax Type',
       required=True,
       help='Type of tax for this group'
    )
    
    # Reporting
    property_tax_payable_account_id = fields.Many2one(
        'moz.account',
        string='Tax Payable Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Account for tax payable'
    )
    
    property_tax_receivable_account_id = fields.Many2one(
        'moz.account',
        string='Tax Receivable Account',
        domain="[('account_type', '=', 'asset_current')]",
        help='Account for tax receivable'
    )
    
    property_advance_tax_payment_account_id = fields.Many2one(
        'moz.account',
        string='Advance Tax Payment Account',
        domain="[('account_type', '=', 'asset_current')]",
        help='Account for advance tax payments'
    )
    
    # Related Taxes
    tax_ids = fields.One2many(
        'moz.tax',
        'tax_group_id',
        string='Taxes'
    )
    
    tax_count = fields.Integer(
        string='Number of Taxes',
        compute='_compute_tax_count'
    )
    
    # Mozambican Specific
    at_tax_type = fields.Char(
        string='AT Tax Type Code',
        help='Tax type code for AT reporting'
    )
    
    modelo_number = fields.Char(
        string='Modelo Number',
        help='Tax declaration form number (e.g., Modelo 10, Modelo 20)'
    )
    
    declaration_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Declaration Frequency',
       help='Frequency of tax declarations'
    )
    
    payment_deadline_days = fields.Integer(
        string='Payment Deadline (days)',
        default=20,
        help='Number of days after period end for payment'
    )
    
    # Computed Fields
    @api.depends('tax_ids')
    def _compute_tax_count(self):
        for group in self:
            group.tax_count = len(group.tax_ids)
    
    # Constraints
    @api.constrains('code')
    def _check_code_unique(self):
        for group in self:
            duplicate = self.search([
                ('code', '=', group.code),
                ('company_id', '=', group.company_id.id if group.company_id else False),
                ('id', '!=', group.id)
            ])
            
            if duplicate:
                raise ValidationError(
                    _("Tax group code '%s' already exists!") % group.code
                )
    
    # Business Methods
    def get_tax_summary(self, date_from: str, date_to: str) -> Dict:
        """Get tax summary for reporting period"""
        self.ensure_one()
        
        # Get all move lines with taxes from this group
        tax_lines = self.env['moz.move.line'].search([
            ('tax_line_id.tax_group_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('parent_state', '=', 'posted')
        ])
        
        base_lines = self.env['moz.move.line'].search([
            ('tax_ids.tax_group_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('parent_state', '=', 'posted')
        ])
        
        summary = {
            'group': self.name,
            'code': self.code,
            'tax_type': self.tax_type,
            'base_amount': sum(base_lines.mapped('balance')),
            'tax_amount': sum(tax_lines.mapped('balance')),
            'taxes': {}
        }
        
        # Detail by tax
        for tax in self.tax_ids:
            tax_specific_lines = tax_lines.filtered(
                lambda l: l.tax_line_id == tax
            )
            base_specific_lines = base_lines.filtered(
                lambda l: tax in l.tax_ids
            )
            
            summary['taxes'][tax.tax_code] = {
                'name': tax.name,
                'base': sum(base_specific_lines.mapped('balance')),
                'tax': sum(tax_specific_lines.mapped('balance'))
            }
        
        return summary
    
    def action_view_taxes(self):
        """View all taxes in this group"""
        self.ensure_one()
        
        return {
            'name': _('Taxes'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.tax',
            'view_mode': 'tree,form',
            'domain': [('tax_group_id', '=', self.id)],
            'context': {'default_tax_group_id': self.id}
        }
    
    def action_generate_declaration(self):
        """Generate tax declaration for this group"""
        self.ensure_one()
        
        # This would open a wizard for generating tax declaration
        return {
            'name': _('Generate Tax Declaration'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.tax.declaration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_tax_group_id': self.id,
                'default_declaration_type': self.tax_type,
            }
        }
    
    @api.model
    def create_mozambican_tax_groups(self):
        """Create standard Mozambican tax groups"""
        
        groups_data = [
            {
                'name': 'IVA - Imposto sobre Valor Acrescentado',
                'code': 'IVA',
                'tax_type': 'iva',
                'at_tax_type': 'IVA',
                'modelo_number': 'Modelo A',
                'declaration_frequency': 'monthly',
                'payment_deadline_days': 20
            },
            {
                'name': 'IRPS - Imposto sobre Rendimento de Pessoas Singulares',
                'code': 'IRPS',
                'tax_type': 'irps',
                'at_tax_type': 'IRPS',
                'modelo_number': 'Modelo 10',
                'declaration_frequency': 'monthly',
                'payment_deadline_days': 20
            },
            {
                'name': 'IRPC - Imposto sobre Rendimento de Pessoas Colectivas',
                'code': 'IRPC',
                'tax_type': 'irpc',
                'at_tax_type': 'IRPC',
                'modelo_number': 'Modelo 20',
                'declaration_frequency': 'yearly',
                'payment_deadline_days': 150
            },
            {
                'name': 'Imposto do Selo',
                'code': 'IS',
                'tax_type': 'is',
                'at_tax_type': 'IS',
                'declaration_frequency': 'monthly',
                'payment_deadline_days': 20
            },
            {
                'name': 'ISPC - Imposto Simplificado para Pequenos Contribuintes',
                'code': 'ISPC',
                'tax_type': 'ispc',
                'at_tax_type': 'ISPC',
                'declaration_frequency': 'quarterly',
                'payment_deadline_days': 30
            },
            {
                'name': 'ICE - Imposto sobre Consumos Específicos',
                'code': 'ICE',
                'tax_type': 'ice',
                'at_tax_type': 'ICE',
                'declaration_frequency': 'monthly',
                'payment_deadline_days': 20
            }
        ]
        
        for group_data in groups_data:
            # Check if group already exists
            existing = self.search([
                ('code', '=', group_data['code'])
            ])
            
            if not existing:
                group_data['company_id'] = self.env.company.id
                self.create(group_data)
                _logger.info("Created tax group: %s", group_data['name'])