# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional
import logging

_logger = logging.getLogger(__name__)


class MozJournal(models.Model):
    """Accounting Journal for Mozambican transactions"""
    
    _name = 'moz.journal'
    _description = 'Mozambican Accounting Journal'
    _order = 'sequence, code, id'
    
    # Basic Fields
    name = fields.Char(
        string='Journal Name',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Short Code',
        size=10,
        required=True,
        index=True,
        help='Unique code for this journal'
    )
    
    active = fields.Boolean(
        default=True,
        help='Set active to false to hide the journal without removing it'
    )
    
    # Journal Type
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'General'),
        ('situation', 'Opening/Closing'),
        ('memorial', 'Memorial'),
    ], string='Type', required=True, 
       help='Select the type of journal for specific behavior')
    
    # Sequence and Numbering
    sequence = fields.Integer(
        default=10,
        help='Used to order journals in views'
    )
    
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        help='Sequence for automatic numbering of journal entries',
        copy=False
    )
    
    refund_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Credit Note Sequence',
        help='Sequence for credit notes',
        copy=False
    )
    
    # Accounts Configuration
    default_debit_account_id = fields.Many2one(
        'moz.account',
        string='Default Debit Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    
    default_credit_account_id = fields.Many2one(
        'moz.account',
        string='Default Credit Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    
    payment_debit_account_id = fields.Many2one(
        'moz.account',
        string='Outstanding Receipts Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help='Account for outstanding customer payments'
    )
    
    payment_credit_account_id = fields.Many2one(
        'moz.account',
        string='Outstanding Payments Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help='Account for outstanding supplier payments'
    )
    
    # Company and Currency
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Journal currency different from company currency',
        domain="[('active', '=', True)]"
    )
    
    # Bank Configuration
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account',
        help='Bank account associated with this journal'
    )
    
    bank_statements_source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('file_import', 'File Import'),
        ('online_sync', 'Online Synchronization'),
    ], string='Bank Feed', default='manual')
    
    # Control Fields
    restrict_mode_hash_table = fields.Boolean(
        string='Lock Posted Entries with Hash',
        help='Use hash values to ensure posted entries cannot be modified'
    )
    
    sequence_override_regex = fields.Text(
        string='Sequence Override Pattern',
        help='Regex pattern to override sequence numbering'
    )
    
    # Mozambican Specific Fields
    at_series = fields.Char(
        string='AT Document Series',
        help='Series registered with Tax Authority for this journal'
    )
    
    at_validation_code = fields.Char(
        string='AT Validation Code',
        help='Validation code from Tax Authority'
    )
    
    require_certification = fields.Boolean(
        string='Require AT Certification',
        help='Documents in this journal require Tax Authority certification'
    )
    
    saft_journal_type = fields.Selection([
        ('VD', 'Vendas (Sales)'),
        ('CO', 'Compras (Purchases)'),
        ('TE', 'Tesouraria (Treasury)'),
        ('OU', 'Outros (Others)'),
        ('AP', 'Apuramento (Clearance)'),
        ('RE', 'Regularizações (Adjustments)'),
    ], string='SAF-T Journal Type', 
       help='Journal type for SAF-T(MZ) reporting')
    
    # Display Fields
    show_on_dashboard = fields.Boolean(
        string='Show on Dashboard',
        default=True,
        help='Display this journal on the accounting dashboard'
    )
    
    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color for dashboard display'
    )
    
    # Statistics
    entries_count = fields.Integer(
        string='Number of Entries',
        compute='_compute_entries_count'
    )
    
    last_entry_date = fields.Date(
        string='Last Entry Date',
        compute='_compute_last_entry_date'
    )
    
    # Computed Fields
    @api.depends('type')
    def _compute_entries_count(self):
        for journal in self:
            journal.entries_count = self.env['moz.move'].search_count([
                ('journal_id', '=', journal.id)
            ])
    
    @api.depends('type')
    def _compute_last_entry_date(self):
        for journal in self:
            last_move = self.env['moz.move'].search([
                ('journal_id', '=', journal.id)
            ], order='date desc', limit=1)
            
            journal.last_entry_date = last_move.date if last_move else False
    
    # Constraints
    @api.constrains('code')
    def _check_code_unique(self):
        for journal in self:
            if self.search_count([
                ('code', '=', journal.code),
                ('company_id', '=', journal.company_id.id),
                ('id', '!=', journal.id)
            ]) > 0:
                raise ValidationError(
                    _("Journal code '%s' already exists!") % journal.code
                )
    
    @api.constrains('type', 'bank_account_id')
    def _check_bank_account(self):
        for journal in self:
            if journal.type == 'bank' and not journal.bank_account_id:
                raise ValidationError(
                    _("Bank journal must have a bank account configured.")
                )
    
    @api.constrains('type', 'default_debit_account_id', 'default_credit_account_id')
    def _check_default_accounts(self):
        for journal in self:
            if journal.type in ('cash', 'bank'):
                if not journal.default_debit_account_id or not journal.default_credit_account_id:
                    raise ValidationError(
                        _("Cash and Bank journals must have default debit and credit accounts.")
                    )
    
    # Business Methods
    @api.model
    def create(self, vals):
        """Override create to set up sequences automatically"""
        journal = super().create(vals)
        
        # Create sequences if not provided
        if not journal.sequence_id:
            journal._create_sequence()
        
        if journal.type in ('sale', 'purchase') and not journal.refund_sequence_id:
            journal._create_refund_sequence()
        
        return journal
    
    def _create_sequence(self):
        """Create main sequence for journal entries"""
        self.ensure_one()
        
        sequence_vals = {
            'name': f"{self.name} Sequence",
            'code': f"moz.journal.{self.code}",
            'implementation': 'no_gap',
            'prefix': f"{self.code}/%(year)s/",
            'padding': 5,
            'number_increment': 1,
            'use_date_range': True,
            'company_id': self.company_id.id,
        }
        
        self.sequence_id = self.env['ir.sequence'].sudo().create(sequence_vals)
    
    def _create_refund_sequence(self):
        """Create sequence for credit notes"""
        self.ensure_one()
        
        prefix = 'NC' if self.type == 'sale' else 'NCD'
        
        sequence_vals = {
            'name': f"{self.name} Credit Note Sequence",
            'code': f"moz.journal.refund.{self.code}",
            'implementation': 'no_gap',
            'prefix': f"{prefix}/{self.code}/%(year)s/",
            'padding': 5,
            'number_increment': 1,
            'use_date_range': True,
            'company_id': self.company_id.id,
        }
        
        self.refund_sequence_id = self.env['ir.sequence'].sudo().create(sequence_vals)
    
    def get_next_sequence_number(self, refund: bool = False) -> str:
        """Get next sequence number for journal entry"""
        self.ensure_one()
        
        sequence = self.refund_sequence_id if refund else self.sequence_id
        
        if not sequence:
            raise UserError(
                _("No sequence configured for journal %s") % self.name
            )
        
        return sequence.next_by_id()
    
    def validate_for_entry(self) -> bool:
        """Validate if journal can be used for new entries"""
        self.ensure_one()
        
        if not self.active:
            raise UserError(
                _("Cannot create entries in inactive journal %s") % self.name
            )
        
        if self.type in ('cash', 'bank'):
            if not self.default_debit_account_id or not self.default_credit_account_id:
                raise UserError(
                    _("Journal %s is not properly configured. Default accounts are missing.") % self.name
                )
        
        return True
    
    def action_open_entries(self):
        """Open all journal entries for this journal"""
        self.ensure_one()
        
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move',
            'view_mode': 'tree,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id}
        }
    
    def action_create_new_entry(self):
        """Create a new journal entry in this journal"""
        self.ensure_one()
        self.validate_for_entry()
        
        return {
            'name': _('New Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_date': fields.Date.today(),
            }
        }
    
    @api.model
    def get_dashboard_data(self) -> List[Dict]:
        """Get journal data for dashboard display"""
        journals = self.search([('show_on_dashboard', '=', True)])
        
        data = []
        for journal in journals:
            data.append({
                'id': journal.id,
                'name': journal.name,
                'code': journal.code,
                'type': journal.type,
                'color': journal.color,
                'entries_count': journal.entries_count,
                'last_entry_date': journal.last_entry_date,
            })
        
        return data