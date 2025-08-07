# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, type, code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _rec_name = 'display_name'

    def _default_inbound_payment_methods(self):
        return self.env['account.payment.method'].search([
            ('payment_type', '=', 'inbound')
        ])

    def _default_outbound_payment_methods(self):
        return self.env['account.payment.method'].search([
            ('payment_type', '=', 'outbound')
        ])

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for journal in self:
            journal.display_name = f"[{journal.code}] {journal.name}"

    @api.depends('type')
    def _compute_default_account(self):
        for journal in self:
            if journal.type == 'sale':
                journal.default_account_suggested = 'income'
            elif journal.type == 'purchase':
                journal.default_account_suggested = 'expense'
            else:
                journal.default_account_suggested = False

    # Basic Fields
    name = fields.Char(string='Journal Name', required=True, tracking=True)
    code = fields.Char(string='Short Code', size=5, required=True, tracking=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    active = fields.Boolean(default=True)
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'General'),
    ], string='Type', required=True, tracking=True,
        help="Select 'Sale' for customer invoices. "
             "Select 'Purchase' for vendor bills. "
             "Select 'Cash' or 'Bank' for payment methods. "
             "Select 'General' for miscellaneous operations.")
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    sequence = fields.Integer(default=10)
    
    # Account Configuration
    default_account_id = fields.Many2one(
        'account.account',
        string='Default Account',
        ondelete='restrict',
        copy=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    default_account_suggested = fields.Char(compute='_compute_default_account')
    
    suspense_account_id = fields.Many2one(
        'account.account',
        string='Suspense Account',
        ondelete='restrict',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help="Bank statements transactions will be posted on the suspense account "
             "until the reconciliation of the transaction."
    )
    
    profit_account_id = fields.Many2one(
        'account.account',
        string='Profit Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help="Used to register a profit when the ending balance of a cash register differs from the computed one."
    )
    
    loss_account_id = fields.Many2one(
        'account.account',
        string='Loss Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help="Used to register a loss when the ending balance of a cash register differs from the computed one."
    )
    
    # Sequence Configuration
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        copy=False,
        ondelete='restrict'
    )
    refund_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Credit Note Sequence',
        copy=False,
        ondelete='restrict'
    )
    payment_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Payment Sequence',
        copy=False,
        ondelete='restrict'
    )
    
    # Bank Configuration
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account',
        ondelete='restrict',
        copy=False,
        domain="[('company_id', '=', company_id)]"
    )
    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', string='Bank')
    
    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='The currency used to enter statements'
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True
    )
    
    # Payment Methods
    inbound_payment_method_line_ids = fields.One2many(
        'account.payment.method.line',
        'journal_id',
        domain=[('payment_type', '=', 'inbound')],
        string='Inbound Payment Methods'
    )
    outbound_payment_method_line_ids = fields.One2many(
        'account.payment.method.line',
        'journal_id',
        domain=[('payment_type', '=', 'outbound')],
        string='Outbound Payment Methods'
    )
    
    # Invoice Settings
    invoice_reference_type = fields.Selection([
        ('none', 'Free Reference'),
        ('partner', 'Based on Customer'),
        ('invoice', 'Based on Invoice'),
    ], string='Communication Type', default='invoice')
    
    invoice_reference_model = fields.Selection([
        ('odoo', 'Odoo'),
        ('euro', 'European'),
    ], string='Communication Standard', default='odoo')
    
    # Groups
    group_invoice_lines = fields.Boolean(
        string='Group Invoice Lines',
        help="If checked, the system will group invoice lines on the invoice."
    )
    
    # Entry Control
    restrict_mode_hash_table = fields.Boolean(
        string='Lock Posted Entries with Hash',
        help="If checked, posted entries will be locked with a hash."
    )
    
    # Alias
    alias_id = fields.Many2one(
        'mail.alias',
        string='Email Alias',
        ondelete='restrict',
        copy=False
    )
    alias_domain = fields.Char('Alias Domain', compute='_compute_alias_domain')
    alias_name = fields.Char('Alias Name', copy=False)
    
    # Dashboard
    kanban_dashboard = fields.Text(compute='_compute_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show on Dashboard', default=True)
    color = fields.Integer('Color Index', default=0)
    
    # Statistics
    entries_count = fields.Integer(compute='_compute_entries_count')
    
    # Advanced Settings
    post_at_bank_rec = fields.Boolean(
        string='Post at Bank Reconciliation',
        help="If checked, journal entries will be posted automatically at bank reconciliation."
    )
    
    # Dedicated Sequence
    secure_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secure Sequence',
        ondelete='restrict',
        copy=False,
        help="Sequence used for entries that require a secure numbering."
    )
    
    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'The journal code must be unique per company!'),
    ]

    @api.depends('company_id')
    def _compute_alias_domain(self):
        for journal in self:
            journal.alias_domain = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.domain')

    @api.depends('move_line_ids')
    def _compute_entries_count(self):
        move_data = self.env['account.move'].read_group(
            [('journal_id', 'in', self.ids)],
            ['journal_id'],
            ['journal_id']
        )
        move_counts = {d['journal_id'][0]: d['journal_id_count'] for d in move_data}
        for journal in self:
            journal.entries_count = move_counts.get(journal.id, 0)

    def _compute_kanban_dashboard(self):
        for journal in self:
            journal.kanban_dashboard = json.dumps(journal._get_journal_dashboard_data())

    def _compute_kanban_dashboard_graph(self):
        for journal in self:
            journal.kanban_dashboard_graph = json.dumps(journal._get_dashboard_graph_data())

    def _get_journal_dashboard_data(self):
        """Return the data for the journal dashboard kanban card."""
        self.ensure_one()
        return {
            'number_draft': 0,
            'number_waiting': 0,
            'number_late': 0,
            'sum_draft': 0,
            'sum_waiting': 0,
            'sum_late': 0,
            'currency_id': self.currency_id.id or self.company_currency_id.id,
            'bank_balance': 0,
            'outstanding_pay_account_balance': 0,
        }

    def _get_dashboard_graph_data(self):
        """Return the graph data for the journal dashboard."""
        self.ensure_one()
        return [{'values': [], 'title': '', 'key': 'graph_key', 'color': 0}]

    @api.model_create_multi
    def create(self, vals_list):
        journals = super().create(vals_list)
        for journal in journals:
            # Create sequences if needed
            if not journal.sequence_id:
                journal._create_sequence()
            # Create payment method lines
            journal._create_payment_method_lines()
        return journals

    def write(self, vals):
        res = super().write(vals)
        if 'type' in vals:
            self._create_payment_method_lines()
        return res

    def _create_sequence(self):
        """Create the sequence for the journal."""
        for journal in self:
            vals = {
                'name': f"{journal.name} Sequence",
                'code': f"account.journal.{journal.code}",
                'implementation': 'standard',
                'prefix': f"{journal.code}/%(year)s/",
                'padding': 5,
                'number_increment': 1,
                'use_date_range': True,
                'company_id': journal.company_id.id,
            }
            journal.sequence_id = self.env['ir.sequence'].sudo().create(vals)

    def _create_payment_method_lines(self):
        """Create default payment method lines."""
        for journal in self:
            if journal.type in ['bank', 'cash']:
                # Create inbound payment methods
                for method in self._default_inbound_payment_methods():
                    if not journal.inbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id == method):
                        self.env['account.payment.method.line'].create({
                            'journal_id': journal.id,
                            'payment_method_id': method.id,
                            'payment_type': 'inbound',
                        })
                # Create outbound payment methods
                for method in self._default_outbound_payment_methods():
                    if not journal.outbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id == method):
                        self.env['account.payment.method.line'].create({
                            'journal_id': journal.id,
                            'payment_method_id': method.id,
                            'payment_type': 'outbound',
                        })

    def action_open_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id},
        }

    def action_open_reconcile(self):
        self.ensure_one()
        if self.type in ['bank', 'cash']:
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {'journal_id': self.id},
            }
        return False

    def action_configure_bank_journal(self):
        """Open the bank journal configuration wizard."""
        self.ensure_one()
        return {
            'name': _('Configure Bank Journal'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class AccountJournalGroup(models.Model):
    _name = "account.journal.group"
    _description = "Journal Group"
    _order = "sequence, name"

    name = fields.Char(string='Journal Group', required=True, translate=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    excluded_journal_ids = fields.Many2many(
        'account.journal',
        string='Excluded Journals',
        domain="[('company_id', '=', company_id)]"
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id)', 'The journal group name must be unique per company!'),
    ]