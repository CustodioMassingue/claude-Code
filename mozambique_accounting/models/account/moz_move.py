# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import logging

_logger = logging.getLogger(__name__)


class MozMove(models.Model):
    """Accounting Move (Journal Entry) for Mozambican accounting"""
    
    _name = 'moz.move'
    _description = 'Mozambican Accounting Move'
    _order = 'date desc, name desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Fields
    name = fields.Char(
        string='Number',
        required=True,
        readonly=True,
        copy=False,
        default='/',
        index=True,
        tracking=True
    )
    
    ref = fields.Char(
        string='Reference',
        copy=False,
        tracking=True,
        help='Reference of the document that generated this entry'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Effective date for accounting'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
       default='draft',
       required=True,
       readonly=True,
       copy=False,
       tracking=True,
       help='Draft: Entry can be modified\n'
            'Posted: Entry is validated and cannot be modified\n'
            'Cancelled: Entry has been cancelled'
    )
    
    # Journal and Company
    journal_id = fields.Many2one(
        'moz.journal',
        string='Journal',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True,
        store=True
    )
    
    # Move Type
    move_type = fields.Selection([
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Type',
       default='entry',
       required=True,
       readonly=True,
       states={'draft': [('readonly', False)]},
       tracking=True
    )
    
    # Fiscal Period
    fiscal_year_id = fields.Many2one(
        'moz.fiscal.year',
        string='Fiscal Year',
        compute='_compute_fiscal_period',
        store=True
    )
    
    fiscal_period_id = fields.Many2one(
        'moz.fiscal.period',
        string='Fiscal Period',
        compute='_compute_fiscal_period',
        store=True
    )
    
    # Lines
    line_ids = fields.One2many(
        'moz.move.line',
        'move_id',
        string='Journal Items',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    # Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )
    
    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
        help='The currency used for this entry'
    )
    
    # Amounts
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    
    amount_total_signed = fields.Monetary(
        string='Total Signed',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id',
        help='Total in company currency, negative for credit notes'
    )
    
    amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    
    # Reconciliation
    to_check = fields.Boolean(
        string='To Check',
        default=False,
        tracking=True,
        help='Check if this entry needs special verification'
    )
    
    auto_post = fields.Boolean(
        string='Auto-post',
        default=False,
        help='Automatically post this entry when saved'
    )
    
    # Reversal
    reversed_entry_id = fields.Many2one(
        'moz.move',
        string='Reversal of',
        readonly=True,
        copy=False
    )
    
    reversal_move_ids = fields.One2many(
        'moz.move',
        'reversed_entry_id',
        string='Reversal Entries'
    )
    
    # Mozambican Specific Fields
    at_hash = fields.Char(
        string='AT Hash',
        readonly=True,
        copy=False,
        help='Hash value for Tax Authority certification'
    )
    
    at_hash_date = fields.Datetime(
        string='Hash Date',
        readonly=True,
        copy=False
    )
    
    at_software_code = fields.Char(
        string='Software Certification Code',
        readonly=True,
        default='MOZ-ODOO-001'
    )
    
    certification_required = fields.Boolean(
        string='Requires Certification',
        compute='_compute_certification_required',
        store=True
    )
    
    saft_source_id = fields.Char(
        string='SAF-T Source ID',
        readonly=True,
        copy=False,
        help='Source document ID for SAF-T reporting'
    )
    
    # Computed Fields
    @api.depends('date')
    def _compute_fiscal_period(self):
        for move in self:
            if move.date:
                # Find fiscal year
                fiscal_year = self.env['moz.fiscal.year'].search([
                    ('company_id', '=', move.company_id.id),
                    ('date_from', '<=', move.date),
                    ('date_to', '>=', move.date),
                    ('state', '!=', 'closed')
                ], limit=1)
                
                move.fiscal_year_id = fiscal_year
                
                # Find fiscal period
                if fiscal_year:
                    fiscal_period = self.env['moz.fiscal.period'].search([
                        ('fiscal_year_id', '=', fiscal_year.id),
                        ('date_from', '<=', move.date),
                        ('date_to', '>=', move.date),
                        ('state', '!=', 'closed')
                    ], limit=1)
                    
                    move.fiscal_period_id = fiscal_period
                else:
                    move.fiscal_period_id = False
            else:
                move.fiscal_year_id = False
                move.fiscal_period_id = False
    
    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.amount_currency', 'move_type')
    def _compute_amount(self):
        for move in self:
            total_debit = sum(move.line_ids.mapped('debit'))
            total_credit = sum(move.line_ids.mapped('credit'))
            
            if move.move_type in ('out_invoice', 'in_refund', 'out_receipt'):
                move.amount_total = total_debit
                move.amount_total_signed = total_debit
            elif move.move_type in ('in_invoice', 'out_refund', 'in_receipt'):
                move.amount_total = total_credit
                move.amount_total_signed = -total_credit
            else:
                move.amount_total = abs(total_debit - total_credit)
                move.amount_total_signed = total_debit - total_credit
            
            # Calculate tax amount (simplified - should be enhanced)
            tax_lines = move.line_ids.filtered(lambda l: l.tax_line_id)
            move.amount_tax = sum(tax_lines.mapped('balance'))
            move.amount_untaxed = move.amount_total - abs(move.amount_tax)
    
    @api.depends('journal_id', 'move_type')
    def _compute_certification_required(self):
        for move in self:
            move.certification_required = (
                move.journal_id.require_certification and 
                move.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            )
    
    # Constraints
    @api.constrains('line_ids')
    def _check_balanced(self):
        for move in self:
            if move.state == 'posted':
                total_debit = sum(move.line_ids.mapped('debit'))
                total_credit = sum(move.line_ids.mapped('credit'))
                
                # Use Decimal for precision
                debit_decimal = Decimal(str(total_debit))
                credit_decimal = Decimal(str(total_credit))
                
                if abs(debit_decimal - credit_decimal) > Decimal('0.01'):
                    raise ValidationError(
                        _("Entry is not balanced!\nTotal Debit: %s\nTotal Credit: %s\nDifference: %s") % 
                        (total_debit, total_credit, abs(total_debit - total_credit))
                    )
    
    @api.constrains('date', 'fiscal_period_id')
    def _check_fiscal_period(self):
        for move in self:
            if move.fiscal_period_id and move.fiscal_period_id.state == 'closed':
                raise ValidationError(
                    _("Cannot create or modify entries in closed fiscal period %s") % 
                    move.fiscal_period_id.name
                )
    
    @api.constrains('state', 'at_hash')
    def _check_hash_immutable(self):
        for move in self:
            if move.state == 'posted' and move.at_hash:
                # Check if trying to modify a hashed entry
                if move._origin and move._origin.at_hash != move.at_hash:
                    raise ValidationError(
                        _("Cannot modify a posted entry with AT certification hash!")
                    )
    
    # CRUD Methods
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal = self.env['moz.journal'].browse(vals.get('journal_id'))
            if journal:
                is_refund = vals.get('move_type', '') in ('out_refund', 'in_refund')
                vals['name'] = journal.get_next_sequence_number(refund=is_refund)
        
        move = super().create(vals)
        
        # Auto-post if configured
        if move.auto_post and move.state == 'draft':
            move.action_post()
        
        return move
    
    def write(self, vals):
        # Prevent modification of posted entries
        if any(move.state == 'posted' for move in self) and not self.env.context.get('force_write'):
            restricted_fields = set(vals.keys()) - {'state', 'to_check'}
            if restricted_fields:
                raise UserError(
                    _("Cannot modify posted entries! Restricted fields: %s") % 
                    ', '.join(restricted_fields)
                )
        
        return super().write(vals)
    
    def unlink(self):
        for move in self:
            if move.state == 'posted':
                raise UserError(
                    _("Cannot delete posted entries! Entry: %s") % move.name
                )
            if move.at_hash:
                raise UserError(
                    _("Cannot delete certified entries! Entry: %s") % move.name
                )
        
        return super().unlink()
    
    # Business Methods
    def action_post(self):
        """Post journal entries"""
        for move in self:
            if move.state != 'draft':
                continue
            
            # Validations
            move._check_balanced()
            move._validate_move()
            
            # Generate hash for certified documents
            if move.certification_required:
                move._generate_at_hash()
            
            # Update state
            move.write({'state': 'posted'})
            
            # Log the posting
            move.message_post(
                body=_("Entry posted by %s") % self.env.user.name
            )
        
        return True
    
    def action_draft(self):
        """Return entries to draft state"""
        for move in self:
            if move.state == 'cancelled':
                move.write({'state': 'draft'})
            elif move.state == 'posted':
                if move.at_hash:
                    raise UserError(
                        _("Cannot return certified entry %s to draft!") % move.name
                    )
                
                # Check if any line is reconciled
                if any(line.reconciled for line in move.line_ids):
                    raise UserError(
                        _("Cannot return entry %s to draft as it contains reconciled lines!") % move.name
                    )
                
                move.write({'state': 'draft'})
        
        return True
    
    def action_cancel(self):
        """Cancel journal entries"""
        for move in self:
            if move.state == 'draft':
                continue
            
            if move.at_hash:
                raise UserError(
                    _("Cannot cancel certified entry %s!") % move.name
                )
            
            # Check reconciliation
            if any(line.reconciled for line in move.line_ids):
                raise UserError(
                    _("Cannot cancel entry %s as it contains reconciled lines!") % move.name
                )
            
            move.write({'state': 'cancelled'})
            
            move.message_post(
                body=_("Entry cancelled by %s") % self.env.user.name
            )
        
        return True
    
    def button_create_reversal(self):
        """Create a reversal entry"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("Can only reverse posted entries!"))
        
        # Create reversal entry
        reversal_date = fields.Date.context_today(self)
        
        reversal_vals = {
            'ref': _('Reversal of %s') % self.name,
            'date': reversal_date,
            'journal_id': self.journal_id.id,
            'reversed_entry_id': self.id,
            'move_type': self.move_type,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'line_ids': [],
        }
        
        # Reverse all lines
        for line in self.line_ids:
            reversal_line = {
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id if line.partner_id else False,
                'name': _('Reversal: %s') % (line.name or ''),
                'debit': line.credit,
                'credit': line.debit,
                'amount_currency': -line.amount_currency if line.amount_currency else 0,
                'currency_id': line.currency_id.id if line.currency_id else False,
                'analytic_account_id': line.analytic_account_id.id if line.analytic_account_id else False,
            }
            reversal_vals['line_ids'].append((0, 0, reversal_line))
        
        reversal_move = self.create(reversal_vals)
        
        # Show the reversal entry
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move',
            'res_id': reversal_move.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _validate_move(self):
        """Additional validations before posting"""
        self.ensure_one()
        
        # Check if all required fields are set on lines
        for line in self.line_ids:
            if not line.account_id:
                raise ValidationError(_("All lines must have an account!"))
            
            if line.account_id.deprecated:
                raise ValidationError(
                    _("Cannot use deprecated account %s") % line.account_id.display_name
                )
            
            if line.account_id.require_partner and not line.partner_id:
                raise ValidationError(
                    _("Account %s requires a partner!") % line.account_id.display_name
                )
            
            if line.account_id.require_analytic and not line.analytic_account_id:
                raise ValidationError(
                    _("Account %s requires an analytic account!") % line.account_id.display_name
                )
        
        # Check fiscal period
        if not self.fiscal_period_id:
            raise ValidationError(
                _("No fiscal period found for date %s") % self.date
            )
        
        return True
    
    def _generate_at_hash(self):
        """Generate AT certification hash"""
        self.ensure_one()
        
        if not self.certification_required:
            return
        
        # Get previous hash
        previous_move = self.search([
            ('journal_id', '=', self.journal_id.id),
            ('at_hash', '!=', False),
            ('date', '<=', self.date),
            ('id', '<', self.id)
        ], order='date desc, id desc', limit=1)
        
        previous_hash = previous_move.at_hash if previous_move else ''
        
        # Build hash string
        hash_string = ';'.join([
            str(self.date),
            str(self.name),
            str(self.amount_total),
            previous_hash
        ])
        
        # Generate SHA256 hash
        hash_object = hashlib.sha256(hash_string.encode())
        
        self.write({
            'at_hash': hash_object.hexdigest(),
            'at_hash_date': fields.Datetime.now()
        })
        
        _logger.info("Generated AT hash for move %s: %s", self.name, self.at_hash)
    
    def action_open_journal_items(self):
        """Open journal items view"""
        self.ensure_one()
        
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move.line',
            'view_mode': 'tree,form',
            'domain': [('move_id', '=', self.id)],
            'context': {'default_move_id': self.id}
        }
    
    @api.model
    def get_saft_data(self, date_from: str, date_to: str) -> List[Dict]:
        """Get move data for SAF-T export"""
        moves = self.search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.company.id)
        ])
        
        saft_data = []
        for move in moves:
            move_data = {
                'transaction_id': move.name,
                'period': move.fiscal_period_id.code if move.fiscal_period_id else '',
                'transaction_date': str(move.date),
                'source_id': move.saft_source_id or move.ref or '',
                'description': move.ref or '',
                'doc_archival_number': move.id,
                'gl_posting_date': str(move.date),
                'customer_id': move.partner_id.vat if move.partner_id and move.partner_id.vat else '',
                'supplier_id': '',
                'lines': []
            }
            
            for line in move.line_ids:
                line_data = {
                    'record_id': line.id,
                    'account_id': line.account_id.code,
                    'analysis': [],
                    'source_document_id': line.ref or '',
                    'description': line.name or '',
                    'debit_amount': float(line.debit),
                    'credit_amount': float(line.credit)
                }
                
                if line.analytic_account_id:
                    line_data['analysis'].append({
                        'analysis_type': 'ANA',
                        'analysis_id': line.analytic_account_id.code,
                        'analysis_amount': float(line.balance)
                    })
                
                move_data['lines'].append(line_data)
            
            saft_data.append(move_data)
        
        return saft_data