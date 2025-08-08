# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import json
import logging

_logger = logging.getLogger(__name__)


class AccountConsolidationMove(models.Model):
    _name = 'account.consolidation.move'
    _description = 'Consolidation Journal Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'
    
    name = fields.Char(
        string='Number',
        required=True,
        readonly=True,
        default='/',
        copy=False
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    ref = fields.Char(
        string='Reference',
        tracking=True
    )
    
    journal_id = fields.Many2one(
        'account.consolidation.journal',
        string='Journal',
        required=True
    )
    
    chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        related='journal_id.consolidation_chart_id',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='chart_id.company_id',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True
    )
    
    period_id = fields.Many2one(
        'account.consolidation.period',
        string='Period',
        domain="[('journal_id', '=', journal_id)]"
    )
    
    line_ids = fields.One2many(
        'account.consolidation.move.line',
        'move_id',
        string='Journal Items',
        copy=True
    )
    
    # Totals
    total_debit = fields.Monetary(
        string='Total Debit',
        compute='_compute_totals',
        currency_field='currency_id',
        store=True
    )
    
    total_credit = fields.Monetary(
        string='Total Credit',
        compute='_compute_totals',
        currency_field='currency_id',
        store=True
    )
    
    # Source tracking
    source_move_ids = fields.Many2many(
        'account.move',
        string='Source Entries',
        help='Original entries from subsidiary companies'
    )
    
    consolidation_type = fields.Selection([
        ('manual', 'Manual'),
        ('imported', 'Imported'),
        ('elimination', 'Elimination'),
        ('adjustment', 'Adjustment'),
        ('conversion', 'Currency Conversion')
    ], string='Type', default='manual')
    
    # Audit fields
    posted_by = fields.Many2one(
        'res.users',
        string='Posted By',
        readonly=True
    )
    
    posted_date = fields.Datetime(
        string='Posted Date',
        readonly=True
    )

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for move in self:
            move.total_debit = sum(move.line_ids.mapped('debit'))
            move.total_credit = sum(move.line_ids.mapped('credit'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal = self.env['account.consolidation.journal'].browse(vals['journal_id'])
            if journal.sequence_id:
                vals['name'] = journal.sequence_id.next_by_id()
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('account.consolidation.move') or '/'
        return super().create(vals)

    def action_post(self):
        for move in self:
            if move.state != 'draft':
                continue
            
            # Check balance
            if not move._check_balanced():
                raise UserError(_('Cannot post unbalanced entry.'))
            
            # Check period
            if move.period_id and move.period_id.state == 'closed':
                raise UserError(_('Cannot post entry in closed period.'))
            
            move.write({
                'state': 'posted',
                'posted_by': self.env.user.id,
                'posted_date': fields.Datetime.now()
            })

    def action_cancel(self):
        for move in self:
            if move.state == 'cancelled':
                continue
            move.state = 'cancelled'

    def action_draft(self):
        for move in self:
            move.state = 'draft'

    def _check_balanced(self):
        self.ensure_one()
        return abs(self.total_debit - self.total_credit) < 0.01


class AccountConsolidationMoveLine(models.Model):
    _name = 'account.consolidation.move.line'
    _description = 'Consolidation Journal Item'
    
    move_id = fields.Many2one(
        'account.consolidation.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade'
    )
    
    account_id = fields.Many2one(
        'account.consolidation.account',
        string='Account',
        required=True,
        domain="[('chart_id', '=', parent.chart_id)]"
    )
    
    name = fields.Char(
        string='Label',
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
        currency_field='currency_id',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='move_id.currency_id',
        string='Currency'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags'
    )

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.constrains('debit', 'credit')
    def _check_amounts(self):
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError(_('Debit and credit amounts must be positive.'))
            if line.debit and line.credit:
                raise ValidationError(_('Cannot have both debit and credit on the same line.'))