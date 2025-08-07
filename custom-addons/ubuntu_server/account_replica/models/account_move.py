# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, date_utils
from datetime import datetime, date, timedelta
import json


class AccountMove(models.Model):
    _name = "account.move"
    _description = "Journal Entry"
    _order = 'date desc, name desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _check_company_auto = True
    _rec_name = 'display_name'

    @api.model
    def _get_default_journal(self):
        """Get default journal based on context or type."""
        move_type = self._context.get('default_move_type', 'entry')
        journal_type = 'general'
        if move_type in ['out_invoice', 'out_refund']:
            journal_type = 'sale'
        elif move_type in ['in_invoice', 'in_refund']:
            journal_type = 'purchase'
        
        domain = [('type', '=', journal_type), ('company_id', '=', self.env.company.id)]
        return self.env['account.journal'].search(domain, limit=1)

    @api.depends('name', 'state')
    def _compute_display_name(self):
        for move in self:
            name = move.name or _('Draft')
            if move.state == 'draft':
                name = _('Draft %s') % name
            move.display_name = name

    # Basic Fields
    name = fields.Char(
        string='Number',
        copy=False,
        compute='_compute_name',
        store=True,
        readonly=False,
        tracking=True,
        index=True
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True
    )
    ref = fields.Char(string='Reference', copy=False, tracking=True)
    narration = fields.Text(string='Terms and Conditions')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False,
        tracking=True, default='draft')
    
    # Type
    move_type = fields.Selection([
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Type', required=True, tracking=True,
        default='entry', readonly=True)
    
    is_invoice = fields.Boolean(compute='_compute_is_invoice', store=True)
    
    # Journal & Company
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        readonly=False,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
        default=_get_default_journal
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    
    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        tracking=True,
        default=lambda self: self.env.company.currency_id
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True
    )
    
    # Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Commercial Entity',
        compute='_compute_commercial_partner',
        store=True
    )
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Recipient Bank',
        domain="[('partner_id', '=', partner_id)]"
    )
    
    # Invoice Specific Fields
    invoice_date = fields.Date(
        string='Invoice Date',
        readonly=False,
        copy=False,
        tracking=True
    )
    invoice_date_due = fields.Date(
        string='Due Date',
        readonly=False,
        copy=False,
        tracking=True
    )
    invoice_origin = fields.Char(
        string='Origin',
        readonly=False,
        tracking=True
    )
    invoice_payment_ref = fields.Char(
        string='Payment Reference',
        copy=False
    )
    
    # Payment Terms
    invoice_payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    
    # Fiscal Position
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        domain="[('company_id', '=', company_id)]"
    )
    
    # Lines
    line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Journal Items',
        copy=True
    )
    invoice_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Invoice Lines',
        copy=True,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))]
    )
    
    # Totals
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id'
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    amount_residual = fields.Monetary(
        string='Amount Due',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    amount_untaxed_signed = fields.Monetary(
        string='Untaxed Amount Signed',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    amount_tax_signed = fields.Monetary(
        string='Tax Signed',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    amount_total_signed = fields.Monetary(
        string='Total Signed',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    amount_residual_signed = fields.Monetary(
        string='Amount Due Signed',
        compute='_compute_amount',
        store=True,
        currency_field='company_currency_id'
    )
    
    # Payment State
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
    ], string='Payment Status', compute='_compute_payment_state', store=True)
    
    # Reconciliation
    payment_ids = fields.Many2many(
        'account.payment',
        'account_payment_move_rel',
        'move_id', 'payment_id',
        string='Payments'
    )
    
    # Reverse Entry
    reversed_entry_id = fields.Many2one(
        'account.move',
        string='Reversal of',
        copy=False
    )
    reversal_move_ids = fields.One2many(
        'account.move',
        'reversed_entry_id',
        string='Reversal Entries'
    )
    
    # Auto Post
    auto_post = fields.Boolean(string='Auto-post', default=False)
    to_check = fields.Boolean(
        string='To Check',
        tracking=True,
        help="Check this box if you want to review this journal entry."
    )
    
    # Accounting Date
    accounting_date = fields.Date(
        string='Accounting Date',
        help="Date at which the accounting entries will be created."
    )
    
    # Cash Rounding
    invoice_cash_rounding_id = fields.Many2one(
        'account.cash.rounding',
        string='Cash Rounding Method'
    )
    
    # Source Documents
    invoice_source_email = fields.Char(string='Source Email')
    invoice_partner_display_name = fields.Char(
        compute='_compute_invoice_partner_display',
        store=True
    )
    
    # User
    invoice_user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        tracking=True,
        default=lambda self: self.env.user
    )
    team_id = fields.Many2one('crm.team', string='Sales Team')
    
    # Incoterm
    invoice_incoterm_id = fields.Many2one(
        'account.incoterms',
        string='Incoterm',
        help="International Commercial Terms"
    )
    
    # QR Code
    qr_code_method = fields.Selection([
        ('manual', 'Manual'),
        ('swiss', 'Swiss QR'),
    ], string='QR Code Method')
    
    # Hashing
    restrict_mode_hash_table = fields.Boolean(
        related='journal_id.restrict_mode_hash_table'
    )
    secure_sequence_number = fields.Integer(
        string='Secure Sequence Number',
        readonly=True,
        copy=False
    )
    inalterable_hash = fields.Char(
        string='Inalterable Hash',
        readonly=True,
        copy=False
    )
    
    # Opening/Closing
    is_opening = fields.Boolean(
        string='Opening Entry',
        help="Check this box if this is an opening entry."
    )
    is_closing = fields.Boolean(
        string='Closing Entry',
        help="Check this box if this is a closing entry."
    )
    
    # Tax Closing
    tax_closing_end_date = fields.Date(
        string='Tax Closing End Date',
        help="Technical field used for tax closing."
    )
    
    _sql_constraints = [
        ('check_balanced', 
         'CHECK (1=1)', 
         'A journal entry must be balanced! (This constraint is handled by Python validation)'),
    ]

    @api.depends('move_type')
    def _compute_is_invoice(self):
        for move in self:
            move.is_invoice = move.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

    @api.depends('partner_id')
    def _compute_commercial_partner(self):
        for move in self:
            move.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.depends('partner_id')
    def _compute_invoice_partner_display(self):
        for move in self:
            move.invoice_partner_display_name = move.partner_id.display_name

    @api.depends('state', 'journal_id', 'date')
    def _compute_name(self):
        for move in self:
            if move.state == 'draft':
                move.name = '/'
            elif not move.name or move.name == '/':
                sequence = move.journal_id.sequence_id
                if sequence:
                    move.name = sequence.next_by_code(
                        sequence.code,
                        sequence_date=move.date
                    )
                else:
                    move.name = '/'

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.amount_currency',
                 'line_ids.account_id', 'line_ids.currency_id', 'move_type', 'currency_id', 'company_id')
    def _compute_amount(self):
        for move in self:
            if move.is_invoice:
                # Calculate invoice totals
                sign = -1 if move.move_type in ['in_invoice', 'out_refund'] else 1
                
                move.amount_untaxed = sum(
                    line.price_subtotal for line in move.invoice_line_ids
                    if line.display_type == 'product'
                )
                move.amount_tax = sum(
                    line.price_total - line.price_subtotal for line in move.invoice_line_ids
                    if line.display_type == 'product'
                )
                move.amount_total = move.amount_untaxed + move.amount_tax
                
                # Signed amounts
                move.amount_untaxed_signed = move.amount_untaxed * sign
                move.amount_tax_signed = move.amount_tax * sign
                move.amount_total_signed = move.amount_total * sign
                
                # Residual amount (to be paid)
                if move.state == 'posted':
                    move.amount_residual = move._compute_residual()
                else:
                    move.amount_residual = move.amount_total
                move.amount_residual_signed = move.amount_residual * sign
            else:
                # For journal entries
                move.amount_untaxed = 0.0
                move.amount_tax = 0.0
                move.amount_total = 0.0
                move.amount_residual = 0.0
                move.amount_untaxed_signed = 0.0
                move.amount_tax_signed = 0.0
                move.amount_total_signed = 0.0
                move.amount_residual_signed = 0.0

    def _compute_residual(self):
        """Compute the residual amount to be paid on an invoice."""
        self.ensure_one()
        reconciled_amount = 0.0
        for line in self.line_ids.filtered(lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']):
            for partial in line.partial_reconcile_ids:
                if partial.max_date <= fields.Date.today():
                    reconciled_amount += partial.amount
        return self.amount_total - reconciled_amount

    @api.depends('amount_residual', 'move_type', 'state')
    def _compute_payment_state(self):
        for move in self:
            if move.state != 'posted':
                move.payment_state = 'not_paid'
            elif move.move_type == 'entry':
                move.payment_state = 'not_paid'
            elif float_is_zero(move.amount_residual, precision_rounding=move.currency_id.rounding):
                if move.reversed_entry_id:
                    move.payment_state = 'reversed'
                else:
                    move.payment_state = 'paid'
            elif float_compare(move.amount_residual, move.amount_total, precision_rounding=move.currency_id.rounding) == 0:
                move.payment_state = 'not_paid'
            else:
                move.payment_state = 'partial'

    @api.constrains('line_ids')
    def _check_balanced(self):
        """Ensure the move is balanced."""
        for move in self:
            if move.state == 'draft':
                continue
            if not move.line_ids:
                raise ValidationError(_('A journal entry must have at least one line.'))
            if not float_is_zero(sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit')), precision_rounding=0.01):
                raise ValidationError(_('A journal entry must be balanced (sum of debits must equal sum of credits).'))

    def action_post(self):
        """Post the journal entry."""
        if any(move.state != 'draft' for move in self):
            raise ValidationError(_('Only draft entries can be posted.'))
        
        for move in self:
            # Perform checks
            move._check_balanced()
            
            # Set the name if not set
            if not move.name or move.name == '/':
                move._compute_name()
            
            # Set invoice date if not set
            if move.is_invoice and not move.invoice_date:
                move.invoice_date = move.date
            
            # Post the move
            move.state = 'posted'
            
            # Create analytical lines
            move._create_analytic_lines()
        
        return True

    def action_draft(self):
        """Set the journal entry back to draft."""
        for move in self:
            if move.state == 'cancel':
                move.state = 'draft'
        return True

    def action_cancel(self):
        """Cancel the journal entry."""
        for move in self:
            if move.state == 'posted':
                # Check if can be cancelled
                if move.restrict_mode_hash_table and move.inalterable_hash:
                    raise UserError(_('You cannot modify a posted entry that has been locked with a hash.'))
            move.state = 'cancel'
        return True

    def button_draft(self):
        """UI button to set back to draft."""
        return self.action_draft()

    def button_cancel(self):
        """UI button to cancel."""
        return self.action_cancel()

    def _create_analytic_lines(self):
        """Create analytic lines for the move."""
        # This would create analytic lines based on the move lines
        pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set default values
            if 'journal_id' not in vals:
                vals['journal_id'] = self._get_default_journal().id
            
            # Set the company
            if 'company_id' not in vals:
                vals['company_id'] = self.env.company.id
        
        return super().create(vals_list)

    def write(self, vals):
        # Prevent editing posted moves (with exceptions)
        if any(move.state == 'posted' for move in self) and set(vals.keys()) - {'state', 'to_check'}:
            raise UserError(_('You cannot modify a posted entry.'))
        
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_check(self):
        for move in self:
            if move.state == 'posted':
                raise UserError(_('You cannot delete a posted journal entry.'))

    def action_invoice_sent(self):
        """Open the invoice email composer."""
        self.ensure_one()
        template = self.env.ref('account_replica.email_template_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = {
            'default_model': 'account.move',
            'default_res_id': self.id,
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_invoice_print(self):
        """Print the invoice."""
        self.ensure_one()
        return self.env.ref('account_replica.account_invoice_report').report_action(self)

    def action_register_payment(self):
        """Open the payment registration wizard."""
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_amount': self.amount_residual,
            },
            'target': 'new',
        }