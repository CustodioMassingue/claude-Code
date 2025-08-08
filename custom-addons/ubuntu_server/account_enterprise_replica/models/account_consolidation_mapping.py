# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountConsolidationMapping(models.Model):
    _name = 'account.consolidation.mapping'
    _description = 'Account Consolidation Mapping'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Mapping Name',
        compute='_compute_name',
        store=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        ondelete='cascade'
    )
    
    consolidation_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Consolidation Account',
        required=True,
        ondelete='cascade'
    )
    
    company_mapping_id = fields.Many2one(
        'account.consolidation.company',
        string='Company Mapping',
        ondelete='cascade'
    )
    
    source_account_id = fields.Many2one(
        'account.account',
        string='Source Account',
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )
    
    mapping_type = fields.Selection([
        ('normal', 'Normal'),
        ('elimination', 'Elimination'),
        ('adjustment', 'Adjustment'),
        ('reclassification', 'Reclassification')
    ], string='Mapping Type', default='normal')
    
    conversion_rate = fields.Float(
        string='Conversion Rate',
        digits=(16, 6),
        default=1.0
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('source_account_id', 'consolidation_account_id')
    def _compute_name(self):
        for mapping in self:
            if mapping.source_account_id and mapping.consolidation_account_id:
                mapping.name = f"{mapping.source_account_id.code} -> {mapping.consolidation_account_id.code}"
            else:
                mapping.name = "New Mapping"