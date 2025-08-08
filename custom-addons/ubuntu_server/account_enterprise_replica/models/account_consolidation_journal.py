# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountConsolidationJournal(models.Model):
    _name = 'account.consolidation.journal'
    _description = 'Consolidation Journal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Journal Name',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Short Code',
        size=5,
        required=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    consolidation_chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        required=True,
        ondelete='cascade'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Consolidation Company',
        related='consolidation_chart_id.company_id',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True
    )
    
    journal_type = fields.Selection([
        ('general', 'General'),
        ('elimination', 'Elimination'),
        ('adjustment', 'Adjustment'),
        ('reclassification', 'Reclassification'),
        ('conversion', 'Currency Conversion'),
        ('minority', 'Minority Interest'),
        ('goodwill', 'Goodwill')
    ], string='Type', default='general', required=True)
    
    # Related source journals
    source_journal_ids = fields.Many2many(
        'account.journal',
        'consolidation_journal_source_rel',
        'consolidation_journal_id',
        'source_journal_id',
        string='Source Journals',
        help='Original journals from subsidiary companies'
    )
    
    # Consolidation periods
    consolidation_period_ids = fields.One2many(
        'account.consolidation.period',
        'journal_id',
        string='Consolidation Periods'
    )
    
    # Default accounts for specific operations
    default_debit_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Default Debit Account',
        domain="[('chart_id', '=', consolidation_chart_id)]"
    )
    
    default_credit_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Default Credit Account',
        domain="[('chart_id', '=', consolidation_chart_id)]"
    )
    
    elimination_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Elimination Account',
        domain="[('chart_id', '=', consolidation_chart_id)]"
    )
    
    # Entry numbering
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        help='Sequence for automatic entry numbering'
    )
    
    last_entry_number = fields.Char(
        string='Last Entry Number',
        compute='_compute_last_entry_number'
    )
    
    # Statistics
    move_count = fields.Integer(
        string='Number of Entries',
        compute='_compute_statistics'
    )
    
    posted_move_count = fields.Integer(
        string='Posted Entries',
        compute='_compute_statistics'
    )
    
    total_debit = fields.Monetary(
        string='Total Debit',
        compute='_compute_statistics',
        currency_field='currency_id'
    )
    
    total_credit = fields.Monetary(
        string='Total Credit',
        compute='_compute_statistics',
        currency_field='currency_id'
    )
    
    # Automation settings
    auto_post = fields.Boolean(
        string='Auto-Post Entries',
        help='Automatically post entries after import'
    )
    
    auto_eliminate = fields.Boolean(
        string='Auto-Eliminate',
        help='Automatically create elimination entries'
    )
    
    elimination_rules = fields.Text(
        string='Elimination Rules',
        help='JSON configuration for automatic eliminations'
    )

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for journal in self:
            name = f"[{journal.code}] {journal.name}"
            result.append((journal.id, name))
        return result

    def _compute_last_entry_number(self):
        for journal in self:
            last_move = self.env['account.consolidation.move'].search([
                ('journal_id', '=', journal.id)
            ], order='name desc', limit=1)
            journal.last_entry_number = last_move.name if last_move else _('None')

    def _compute_statistics(self):
        for journal in self:
            moves = self.env['account.consolidation.move'].search([
                ('journal_id', '=', journal.id)
            ])
            
            journal.move_count = len(moves)
            journal.posted_move_count = len(moves.filtered(lambda m: m.state == 'posted'))
            
            # Calculate totals
            lines = moves.mapped('line_ids')
            journal.total_debit = sum(lines.mapped('debit'))
            journal.total_credit = sum(lines.mapped('credit'))

    @api.constrains('code')
    def _check_code_unique(self):
        for journal in self:
            duplicate = self.search([
                ('id', '!=', journal.id),
                ('code', '=', journal.code),
                ('consolidation_chart_id', '=', journal.consolidation_chart_id.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("Journal code '%s' already exists in this consolidation chart.") % journal.code
                )

    def action_create_entry(self):
        """Create a new consolidation entry in this journal"""
        return {
            'name': _('New Consolidation Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.consolidation.move',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_chart_id': self.consolidation_chart_id.id,
            }
        }

    def action_view_entries(self):
        """View all entries in this journal"""
        return {
            'name': _('Consolidation Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.consolidation.move',
            'view_mode': 'tree,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {
                'default_journal_id': self.id,
            }
        }

    def action_import_entries(self):
        """Import entries from source companies"""
        for journal in self:
            if not journal.source_journal_ids:
                raise UserError(_("No source journals configured for import."))
            
            # Create import wizard
            wizard = self.env['account.consolidation.import.wizard'].create({
                'consolidation_journal_id': journal.id,
                'source_journal_ids': [(6, 0, journal.source_journal_ids.ids)],
                'date_from': fields.Date.today().replace(day=1),
                'date_to': fields.Date.today(),
            })
            
            return {
                'name': _('Import Entries'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.consolidation.import.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
            }

    def action_create_elimination_entries(self):
        """Create automatic elimination entries"""
        for journal in self:
            if journal.journal_type != 'elimination':
                raise UserError(_("This action is only available for elimination journals."))
            
            # Find intercompany transactions
            elimination_entries = journal._find_elimination_entries()
            
            if not elimination_entries:
                raise UserError(_("No intercompany transactions found for elimination."))
            
            # Create elimination entries
            created_moves = self.env['account.consolidation.move']
            for entry_data in elimination_entries:
                move = self._create_elimination_move(entry_data)
                created_moves |= move
            
            # Auto-post if configured
            if journal.auto_post and created_moves:
                created_moves.action_post()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('%d elimination entries created.') % len(created_moves),
                    'type': 'success',
                }
            }

    def _find_elimination_entries(self):
        """Find intercompany transactions that need elimination"""
        elimination_entries = []
        
        # Get all companies in consolidation
        companies = self.consolidation_chart_id.company_mapping_ids.mapped('source_company_id')
        
        # Find intercompany receivables/payables
        for company_a in companies:
            for company_b in companies:
                if company_a == company_b:
                    continue
                
                # Find receivables in company A from company B
                receivables = self.env['account.move.line'].search([
                    ('company_id', '=', company_a.id),
                    ('partner_id.commercial_partner_id', '=', company_b.partner_id.commercial_partner_id.id),
                    ('account_id.account_type', '=', 'asset_receivable'),
                    ('reconciled', '=', False),
                    ('parent_state', '=', 'posted')
                ])
                
                # Find corresponding payables in company B to company A
                payables = self.env['account.move.line'].search([
                    ('company_id', '=', company_b.id),
                    ('partner_id.commercial_partner_id', '=', company_a.partner_id.commercial_partner_id.id),
                    ('account_id.account_type', '=', 'liability_payable'),
                    ('reconciled', '=', False),
                    ('parent_state', '=', 'posted')
                ])
                
                # Match and create elimination entries
                for receivable in receivables:
                    matching_payable = payables.filtered(
                        lambda p: abs(p.balance + receivable.balance) < 0.01
                    )
                    
                    if matching_payable:
                        elimination_entries.append({
                            'receivable': receivable,
                            'payable': matching_payable[0],
                            'amount': abs(receivable.balance)
                        })
        
        return elimination_entries

    def _create_elimination_move(self, entry_data):
        """Create an elimination move"""
        # Map accounts to consolidation accounts
        receivable_account = self._map_to_consolidation_account(
            entry_data['receivable'].account_id
        )
        payable_account = self._map_to_consolidation_account(
            entry_data['payable'].account_id
        )
        
        if not receivable_account or not payable_account:
            raise UserError(_("Cannot map accounts for elimination entry."))
        
        # Create elimination move
        move_vals = {
            'journal_id': self.id,
            'chart_id': self.consolidation_chart_id.id,
            'date': fields.Date.today(),
            'ref': _('Elimination: %s') % entry_data['receivable'].move_id.name,
            'line_ids': [
                (0, 0, {
                    'account_id': receivable_account.id,
                    'name': _('Eliminate intercompany receivable'),
                    'debit': 0,
                    'credit': entry_data['amount'],
                }),
                (0, 0, {
                    'account_id': payable_account.id,
                    'name': _('Eliminate intercompany payable'),
                    'debit': entry_data['amount'],
                    'credit': 0,
                })
            ]
        }
        
        return self.env['account.consolidation.move'].create(move_vals)

    def _map_to_consolidation_account(self, source_account):
        """Map a source account to a consolidation account"""
        mapping = self.env['account.consolidation.mapping'].search([
            ('source_account_id', '=', source_account.id),
            ('chart_id', '=', self.consolidation_chart_id.id)
        ], limit=1)
        
        return mapping.consolidation_account_id if mapping else False

    def action_reconcile_entries(self):
        """Reconcile consolidation entries"""
        return {
            'name': _('Reconcile Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.consolidation.reconcile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
            }
        }

    @api.model
    def create(self, vals):
        # Create sequence if not provided
        if not vals.get('sequence_id'):
            sequence_vals = {
                'name': _('Consolidation Journal %s') % vals.get('name'),
                'code': 'account.consolidation.journal',
                'prefix': vals.get('code', '') + '/',
                'padding': 4,
                'company_id': False,  # Consolidation sequences are global
            }
            sequence = self.env['ir.sequence'].create(sequence_vals)
            vals['sequence_id'] = sequence.id
        
        return super().create(vals)

    def unlink(self):
        # Check for existing entries
        for journal in self:
            if journal.move_count > 0:
                raise UserError(
                    _("Cannot delete journal '%s' because it contains entries.") % journal.name
                )
        
        # Delete sequences
        sequences = self.mapped('sequence_id')
        result = super().unlink()
        sequences.unlink()
        
        return result