# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountConsolidationCompany(models.Model):
    _name = 'account.consolidation.company'
    _description = 'Consolidation Company Mapping'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Mapping Name',
        required=True,
        tracking=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    source_company_id = fields.Many2one(
        'res.company',
        string='Source Company',
        required=True
    )
    
    consolidation_percentage = fields.Float(
        string='Consolidation %',
        default=100.0,
        required=True,
        tracking=True
    )
    
    consolidation_method = fields.Selection([
        ('full', 'Full Consolidation'),
        ('proportional', 'Proportional Consolidation'),
        ('equity', 'Equity Method')
    ], string='Method', default='full', required=True)
    
    parent_company_id = fields.Many2one(
        'res.company',
        string='Parent Company'
    )
    
    minority_interest_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Minority Interest Account',
        domain="[('chart_id', '=', chart_id)]"
    )
    
    currency_conversion_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Currency Conversion Account',
        domain="[('chart_id', '=', chart_id)]"
    )
    
    active = fields.Boolean(default=True)
    
    # Account mappings
    mapping_ids = fields.One2many(
        'account.consolidation.mapping',
        'company_mapping_id',
        string='Account Mappings'
    )
    
    mapping_count = fields.Integer(
        string='Mappings',
        compute='_compute_mapping_count'
    )
    
    @api.depends('mapping_ids')
    def _compute_mapping_count(self):
        for company in self:
            company.mapping_count = len(company.mapping_ids)
    
    @api.constrains('consolidation_percentage')
    def _check_percentage(self):
        for company in self:
            if company.consolidation_percentage < 0 or company.consolidation_percentage > 100:
                raise ValidationError(_("Consolidation percentage must be between 0 and 100."))
    
    def action_view_mappings(self):
        return {
            'name': _('Account Mappings'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.consolidation.mapping',
            'view_mode': 'tree,form',
            'domain': [('company_mapping_id', '=', self.id)],
            'context': {'default_company_mapping_id': self.id}
        }
    
    def action_auto_map_accounts(self):
        """Automatically map accounts based on code matching"""
        for company in self:
            company._auto_map_accounts()
        return True
    
    def _auto_map_accounts(self):
        """Auto-map accounts with same code"""
        self.ensure_one()
        
        source_accounts = self.env['account.account'].search([
            ('company_id', '=', self.source_company_id.id)
        ])
        
        consolidation_accounts = self.env['account.consolidation.account'].search([
            ('chart_id', '=', self.chart_id.id)
        ])
        
        for source_account in source_accounts:
            # Skip if already mapped
            existing = self.mapping_ids.filtered(
                lambda m: m.source_account_id == source_account
            )
            if existing:
                continue
            
            # Find matching consolidation account by code
            matching = consolidation_accounts.filtered(
                lambda c: c.code == source_account.code
            )
            
            if matching:
                self.env['account.consolidation.mapping'].create({
                    'company_mapping_id': self.id,
                    'source_account_id': source_account.id,
                    'consolidation_account_id': matching[0].id,
                    'chart_id': self.chart_id.id
                })


class AccountConsolidationMapping(models.Model):
    _name = 'account.consolidation.mapping'
    _description = 'Account Consolidation Mapping'
    _rec_name = 'source_account_id'
    
    company_mapping_id = fields.Many2one(
        'account.consolidation.company',
        string='Company Mapping',
        ondelete='cascade'
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        related='company_mapping_id.chart_id',
        store=True
    )
    
    source_account_id = fields.Many2one(
        'account.account',
        string='Source Account',
        required=True
    )
    
    consolidation_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Consolidation Account',
        required=True,
        domain="[('chart_id', '=', chart_id)]"
    )
    
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_source_account', 'UNIQUE(company_mapping_id, source_account_id)',
         'Source account can only be mapped once per company.')
    ]