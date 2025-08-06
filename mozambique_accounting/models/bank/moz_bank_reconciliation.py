# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
from decimal import Decimal, ROUND_HALF_UP

class MozBankReconcileModel(models.Model):
    _name = 'moz.bank.reconcile.model'
    _description = 'Bank Reconciliation Model'
    _order = 'sequence, id'
    
    name = fields.Char(
        string='Name',
        required=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Matching criteria
    match_type = fields.Selection([
        ('contains', 'Contains'),
        ('exact', 'Exact Match'),
        ('regex', 'Regular Expression'),
        ('amount_range', 'Amount Range'),
    ], string='Match Type', default='contains', required=True)
    
    match_text = fields.Char(
        string='Match Text',
        help='Text to match in statement line description'
    )
    
    match_regex = fields.Char(
        string='Regular Expression',
        help='Regular expression pattern'
    )
    
    match_amount_min = fields.Monetary(
        string='Minimum Amount',
        currency_field='currency_id'
    )
    
    match_amount_max = fields.Monetary(
        string='Maximum Amount',
        currency_field='currency_id'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    # Actions
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    note = fields.Text(
        string='Notes'
    )
    
    # Statistics
    match_count = fields.Integer(
        string='Match Count',
        readonly=True
    )
    
    last_match_date = fields.Date(
        string='Last Match Date',
        readonly=True
    )
    
    def _match_statement_line(self, line):
        """Check if this model matches the statement line"""
        self.ensure_one()
        
        # Check partner
        if self.partner_id and line.partner_id != self.partner_id:
            return False
        
        # Check match type
        if self.match_type == 'contains':
            if self.match_text and self.match_text.lower() not in (line.name or '').lower():
                return False
                
        elif self.match_type == 'exact':
            if self.match_text and self.match_text.lower() != (line.name or '').lower():
                return False
                
        elif self.match_type == 'regex':
            if self.match_regex:
                try:
                    if not re.search(self.match_regex, line.name or '', re.IGNORECASE):
                        return False
                except re.error:
                    return False
                    
        elif self.match_type == 'amount_range':
            amount = abs(line.amount)
            if self.match_amount_min and amount < self.match_amount_min:
                return False
            if self.match_amount_max and amount > self.match_amount_max:
                return False
        
        # Update statistics
        self.sudo().write({
            'match_count': self.match_count + 1,
            'last_match_date': fields.Date.today()
        })
        
        return True
    
    @api.model
    def create_from_statement_line(self, line):
        """Create a new reconciliation model from a statement line"""
        return self.create({
            'name': f"Rule for {line.name[:30]}",
            'match_type': 'contains',
            'match_text': line.name[:50] if line.name else '',
            'partner_id': line.partner_id.id if line.partner_id else False,
            'account_id': line.account_id.id if line.account_id else self.env.company.account_journal_suspense_account_id.id,
            'tax_ids': [(6, 0, line.tax_ids.ids)] if line.tax_ids else False,
        })


class MozBankReconciliation(models.Model):
    _name = 'moz.bank.reconciliation'
    _description = 'Bank Reconciliation Process'
    _order = 'date desc'
    
    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('Bank Reconciliation')
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', '=', 'bank')]"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    statement_ids = fields.Many2many(
        'moz.bank.statement',
        string='Bank Statements'
    )
    
    # Reconciliation status
    total_lines = fields.Integer(
        string='Total Lines',
        compute='_compute_reconciliation_stats'
    )
    
    reconciled_lines = fields.Integer(
        string='Reconciled Lines',
        compute='_compute_reconciliation_stats'
    )
    
    unreconciled_lines = fields.Integer(
        string='Unreconciled Lines',
        compute='_compute_reconciliation_stats'
    )
    
    reconciliation_rate = fields.Float(
        string='Reconciliation Rate (%)',
        compute='_compute_reconciliation_stats'
    )
    
    @api.depends('statement_ids.line_ids.is_reconciled')
    def _compute_reconciliation_stats(self):
        for rec in self:
            lines = rec.statement_ids.mapped('line_ids')
            rec.total_lines = len(lines)
            rec.reconciled_lines = len(lines.filtered('is_reconciled'))
            rec.unreconciled_lines = rec.total_lines - rec.reconciled_lines
            rec.reconciliation_rate = (rec.reconciled_lines / rec.total_lines * 100) if rec.total_lines else 0
    
    def action_auto_reconcile(self):
        """Run automatic reconciliation on all statement lines"""
        self.ensure_one()
        
        reconciled_count = 0
        for statement in self.statement_ids:
            for line in statement.line_ids.filtered(lambda l: not l.is_reconciled):
                if line._auto_reconcile():
                    reconciled_count += 1
        
        if reconciled_count:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Auto Reconciliation Complete'),
                    'message': _('%s lines were automatically reconciled.') % reconciled_count,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Matches Found'),
                    'message': _('No lines could be automatically reconciled.'),
                    'type': 'warning',
                }
            }
    
    def action_open_unreconciled(self):
        """Open list of unreconciled lines"""
        self.ensure_one()
        
        lines = self.statement_ids.mapped('line_ids').filtered(lambda l: not l.is_reconciled)
        
        return {
            'name': _('Unreconciled Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.bank.statement.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', lines.ids)],
            'context': {'search_default_unreconciled': 1}
        }