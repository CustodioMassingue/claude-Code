# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Account Reconciliation"
    _order = "create_date desc"

    name = fields.Char(string='Reference', required=True, copy=False, default='/')
    partial_reconcile_ids = fields.One2many(
        'account.partial.reconcile',
        'full_reconcile_id',
        string='Partial Reconciliations'
    )
    reconciled_line_ids = fields.One2many(
        'account.move.line',
        'full_reconcile_id',
        string='Matched Journal Items'
    )
    exchange_move_id = fields.Many2one(
        'account.move',
        string='Exchange Gain/Loss Journal Entry'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.full.reconcile') or '/'
        return super().create(vals_list)

    def unlink(self):
        """When deleting a full reconcile, also unlink the partial reconciles."""
        partials = self.partial_reconcile_ids
        res = super().unlink()
        partials.unlink()
        return res


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Account Reconciliation"
    _rec_name = 'id'
    
    debit_move_id = fields.Many2one(
        'account.move.line',
        string='Debit Move Line',
        required=True,
        index=True
    )
    credit_move_id = fields.Many2one(
        'account.move.line', 
        string='Credit Move Line',
        required=True,
        index=True
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='company_currency_id'
    )
    amount_currency = fields.Monetary(
        string='Amount in Currency',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='debit_move_id.company_id',
        store=True
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id'
    )
    full_reconcile_id = fields.Many2one(
        'account.full.reconcile',
        string='Full Reconciliation',
        ondelete='cascade'
    )
    max_date = fields.Date(
        string='Max Date',
        compute='_compute_max_date',
        store=True
    )
    exchange_move_id = fields.Many2one(
        'account.move',
        string='Exchange Gain/Loss Journal Entry'
    )

    @api.depends('debit_move_id.date', 'credit_move_id.date')
    def _compute_max_date(self):
        for rec in self:
            if rec.debit_move_id and rec.credit_move_id:
                rec.max_date = max(rec.debit_move_id.date, rec.credit_move_id.date)
            else:
                rec.max_date = False

    @api.constrains('debit_move_id', 'credit_move_id')
    def _check_same_account(self):
        for rec in self:
            if rec.debit_move_id.account_id != rec.credit_move_id.account_id:
                raise ValidationError(_("You cannot reconcile entries from different accounts."))

    @api.constrains('amount')
    def _check_amount_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be positive."))

    def unlink(self):
        """When unlinking partial reconciles, update the reconciled amounts on move lines."""
        move_lines = self.debit_move_id | self.credit_move_id
        res = super().unlink()
        move_lines._compute_amount_reconciled()
        return res