# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountConsolidationMoveLine(models.Model):
    _name = 'account.consolidation.move.line'
    _description = 'Consolidation Journal Item'
    _rec_name = 'name'
    
    move_id = fields.Many2one(
        'account.consolidation.move',
        string='Consolidation Entry',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Label',
        required=True
    )
    
    account_id = fields.Many2one(
        'account.consolidation.account',
        string='Consolidation Account',
        required=True
    )
    
    debit = fields.Monetary(
        string='Debit',
        currency_field='currency_id'
    )
    
    credit = fields.Monetary(
        string='Credit',
        currency_field='currency_id'
    )
    
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='move_id.currency_id',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='move_id.company_id',
        store=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    date = fields.Date(
        string='Date',
        related='move_id.date',
        store=True
    )
    
    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit
    
    @api.constrains('debit', 'credit')
    def _check_amounts(self):
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError(_('Debit and credit amounts must be positive'))