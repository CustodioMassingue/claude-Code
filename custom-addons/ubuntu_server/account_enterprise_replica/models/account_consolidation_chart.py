# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
from collections import defaultdict
from datetime import datetime, timedelta


class AccountConsolidationChart(models.Model):
    _name = 'account.consolidation.chart'
    _description = 'Consolidation Chart of Accounts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Chart Name',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Chart Code',
        required=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Consolidation Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Consolidation Currency',
        required=True,
        related='company_id.currency_id'
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        default=10
    )
    
    # ==================== Chart Structure ====================
    
    account_ids = fields.One2many(
        'account.consolidation.account',
        'chart_id',
        string='Consolidation Accounts'
    )
    
    journal_ids = fields.One2many(
        'account.consolidation.journal',
        'consolidation_chart_id',
        string='Consolidation Journals'
    )
    
    company_ids = fields.One2many(
        'account.consolidation.company',
        'chart_id',
        string='Consolidated Companies'
    )
    
    # ==================== Consolidation Settings ====================
    
    consolidation_method = fields.Selection([
        ('full', 'Full Consolidation'),
        ('proportional', 'Proportional Consolidation'),
        ('equity', 'Equity Method'),
        ('cost', 'Cost Method')
    ], string='Default Method', default='full', required=True)
    
    elimination_journal_id = fields.Many2one(
        'account.consolidation.journal',
        string='Elimination Journal',
        domain="[('chart_id', '=', id), ('type', '=', 'elimination')]"
    )
    
    conversion_journal_id = fields.Many2one(
        'account.consolidation.journal',
        string='Currency Conversion Journal',
        domain="[('chart_id', '=', id), ('type', '=', 'conversion')]"
    )
    
    minority_interest_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Minority Interest Account',
        domain="[('chart_id', '=', id)]"
    )
    
    goodwill_account_id = fields.Many2one(
        'account.consolidation.account',
        string='Goodwill Account',
        domain="[('chart_id', '=', id)]"
    )
    
    # ==================== Period Settings ====================
    
    period_ids = fields.One2many(
        'account.consolidation.period',
        'chart_id',
        string='Consolidation Periods'
    )
    
    current_period_id = fields.Many2one(
        'account.consolidation.period',
        string='Current Period',
        domain="[('chart_id', '=', id)]"
    )
    
    auto_create_periods = fields.Boolean(
        string='Auto-create Periods',
        default=True
    )
    
    period_type = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly')
    ], string='Period Type', default='month')
    
    # ==================== Mapping & Rules ====================
    
    account_mapping_ids = fields.One2many(
        'account.consolidation.mapping',
        'chart_id',
        string='Account Mappings'
    )
    
    elimination_rule_ids = fields.One2many(
        'account.consolidation.elimination.rule',
        'chart_id',
        string='Elimination Rules'
    )
    
    conversion_rate_ids = fields.One2many(
        'account.consolidation.rate',
        'chart_id',
        string='Conversion Rates'
    )
    
    # ==================== Status & Statistics ====================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('consolidating', 'Consolidating'),
        ('done', 'Consolidated')
    ], string='Status', default='draft', tracking=True)
    
    last_consolidation_date = fields.Datetime(
        string='Last Consolidation',
        readonly=True
    )
    
    next_consolidation_date = fields.Datetime(
        string='Next Consolidation',
        compute='_compute_next_consolidation'
    )
    
    total_assets = fields.Monetary(
        string='Total Assets',
        compute='_compute_totals',
        currency_field='currency_id'
    )
    
    total_liabilities = fields.Monetary(
        string='Total Liabilities',
        compute='_compute_totals',
        currency_field='currency_id'
    )
    
    total_equity = fields.Monetary(
        string='Total Equity',
        compute='_compute_totals',
        currency_field='currency_id'
    )
    
    # ==================== Methods ====================
    
    @api.depends('period_type', 'last_consolidation_date')
    def _compute_next_consolidation(self):
        for chart in self:
            if not chart.last_consolidation_date:
                chart.next_consolidation_date = fields.Datetime.now()
            else:
                if chart.period_type == 'month':
                    delta = timedelta(days=30)
                elif chart.period_type == 'quarter':
                    delta = timedelta(days=90)
                else:
                    delta = timedelta(days=365)
                chart.next_consolidation_date = chart.last_consolidation_date + delta
    
    @api.depends('account_ids')
    def _compute_totals(self):
        for chart in self:
            assets = sum(acc.balance for acc in chart.account_ids.filtered(
                lambda a: a.account_type in ['asset_current', 'asset_non_current', 'asset_fixed']
            ))
            liabilities = sum(acc.balance for acc in chart.account_ids.filtered(
                lambda a: a.account_type in ['liability_current', 'liability_non_current']
            ))
            equity = sum(acc.balance for acc in chart.account_ids.filtered(
                lambda a: a.account_type == 'equity'
            ))
            
            chart.total_assets = assets
            chart.total_liabilities = liabilities
            chart.total_equity = equity
    
    def action_consolidate(self):
        """Main consolidation process"""
        self.ensure_one()
        if self.state != 'ready':
            raise UserError(_('Chart must be in Ready state to consolidate.'))
        
        self.state = 'consolidating'
        
        try:
            # Step 1: Import data from subsidiaries
            self._import_subsidiary_data()
            
            # Step 2: Convert currencies
            self._convert_currencies()
            
            # Step 3: Apply mappings
            self._apply_account_mappings()
            
            # Step 4: Process eliminations
            self._process_eliminations()
            
            # Step 5: Calculate minority interest
            self._calculate_minority_interest()
            
            # Step 6: Generate consolidated entries
            self._generate_consolidated_entries()
            
            # Step 7: Update balances
            self._update_consolidated_balances()
            
            self.state = 'done'
            self.last_consolidation_date = fields.Datetime.now()
            
        except Exception as e:
            self.state = 'ready'
            raise UserError(_('Consolidation failed: %s') % str(e))
    
    def _import_subsidiary_data(self):
        """Import data from all subsidiary companies"""
        for company in self.company_ids:
            if company.active and company.include_in_consolidation:
                # Get accounting data from subsidiary
                domain = [
                    ('company_id', '=', company.subsidiary_id.id),
                    ('date', '>=', self.current_period_id.date_from),
                    ('date', '<=', self.current_period_id.date_to),
                    ('state', '=', 'posted')
                ]
                
                moves = self.env['account.move'].search(domain)
                
                # Process each move
                for move in moves:
                    self._process_subsidiary_move(move, company)
    
    def _process_subsidiary_move(self, move, consolidation_company):
        """Process a single move from subsidiary"""
        # Create consolidation entries
        for line in move.line_ids:
            # Find mapped consolidation account
            mapping = self.account_mapping_ids.filtered(
                lambda m: m.subsidiary_account_id == line.account_id and
                         m.company_id == consolidation_company.subsidiary_id
            )
            
            if mapping:
                self._create_consolidation_line(line, mapping, consolidation_company)
    
    def _create_consolidation_line(self, source_line, mapping, consolidation_company):
        """Create consolidation journal entry line"""
        # Calculate amounts based on consolidation method
        if consolidation_company.consolidation_method == 'full':
            factor = 1.0
        elif consolidation_company.consolidation_method == 'proportional':
            factor = consolidation_company.ownership_percentage / 100
        else:
            return  # Skip for equity/cost methods
        
        vals = {
            'account_id': mapping.consolidation_account_id.id,
            'debit': source_line.debit * factor,
            'credit': source_line.credit * factor,
            'name': source_line.name,
            'partner_id': source_line.partner_id.id,
            'consolidation_company_id': consolidation_company.id,
            'original_line_id': source_line.id,
        }
        
        return self.env['account.consolidation.move.line'].create(vals)
    
    def _convert_currencies(self):
        """Convert all amounts to consolidation currency"""
        for company in self.company_ids:
            if company.subsidiary_id.currency_id != self.currency_id:
                # Get conversion rate
                rate = self._get_conversion_rate(
                    company.subsidiary_id.currency_id,
                    self.currency_id,
                    self.current_period_id.date_to
                )
                
                # Apply conversion to all lines
                lines = self.env['account.consolidation.move.line'].search([
                    ('consolidation_company_id', '=', company.id),
                    ('period_id', '=', self.current_period_id.id)
                ])
                
                for line in lines:
                    line.debit *= rate
                    line.credit *= rate
    
    def _get_conversion_rate(self, from_currency, to_currency, date):
        """Get currency conversion rate"""
        # Check for specific consolidation rate
        consol_rate = self.conversion_rate_ids.filtered(
            lambda r: r.currency_from_id == from_currency and
                     r.currency_to_id == to_currency and
                     r.date <= date
        ).sorted('date', reverse=True)
        
        if consol_rate:
            return consol_rate[0].rate
        else:
            # Use standard Odoo currency rate
            return from_currency._get_conversion_rate(
                from_currency, to_currency, self.company_id, date
            )
    
    def _apply_account_mappings(self):
        """Apply account mappings to consolidation accounts"""
        # Already handled in _process_subsidiary_move
        pass
    
    def _process_eliminations(self):
        """Process intercompany eliminations"""
        for rule in self.elimination_rule_ids:
            if rule.active:
                self._apply_elimination_rule(rule)
    
    def _apply_elimination_rule(self, rule):
        """Apply a single elimination rule"""
        # Find matching transactions
        if rule.rule_type == 'intercompany_ar_ap':
            self._eliminate_intercompany_ar_ap(rule)
        elif rule.rule_type == 'intercompany_revenue_expense':
            self._eliminate_intercompany_revenue_expense(rule)
        elif rule.rule_type == 'intercompany_investment':
            self._eliminate_investment_equity(rule)
        elif rule.rule_type == 'custom':
            self._apply_custom_elimination(rule)
    
    def _eliminate_intercompany_ar_ap(self, rule):
        """Eliminate intercompany receivables and payables"""
        # Find matching AR/AP pairs
        ar_lines = self.env['account.consolidation.move.line'].search([
            ('period_id', '=', self.current_period_id.id),
            ('account_id.account_type', '=', 'asset_receivable'),
        ])
        
        ap_lines = self.env['account.consolidation.move.line'].search([
            ('period_id', '=', self.current_period_id.id),
            ('account_id.account_type', '=', 'liability_payable'),
        ])
        
        # Match and eliminate
        for ar_line in ar_lines:
            matching_ap = ap_lines.filtered(
                lambda ap: ap.partner_id == ar_line.partner_id and
                          abs(ap.balance + ar_line.balance) < 0.01
            )
            
            if matching_ap:
                self._create_elimination_entry(ar_line, matching_ap[0], rule)
    
    def _eliminate_intercompany_revenue_expense(self, rule):
        """Eliminate intercompany revenues and expenses"""
        # Similar logic for revenue/expense elimination
        pass
    
    def _eliminate_investment_equity(self, rule):
        """Eliminate investment in subsidiary against equity"""
        # Complex elimination for investment accounts
        pass
    
    def _apply_custom_elimination(self, rule):
        """Apply custom elimination rule"""
        # Execute custom elimination logic
        pass
    
    def _create_elimination_entry(self, line1, line2, rule):
        """Create elimination journal entry"""
        vals = {
            'journal_id': self.elimination_journal_id.id,
            'date': self.current_period_id.date_to,
            'ref': _('Elimination: %s') % rule.name,
            'line_ids': [
                (0, 0, {
                    'account_id': line1.account_id.id,
                    'debit': line1.credit,
                    'credit': line1.debit,
                    'name': _('Elimination of %s') % line1.name,
                }),
                (0, 0, {
                    'account_id': line2.account_id.id,
                    'debit': line2.credit,
                    'credit': line2.debit,
                    'name': _('Elimination of %s') % line2.name,
                }),
            ]
        }
        
        return self.env['account.consolidation.move'].create(vals)
    
    def _calculate_minority_interest(self):
        """Calculate minority interest for partial ownership"""
        for company in self.company_ids.filtered(lambda c: c.ownership_percentage < 100):
            minority_percentage = (100 - company.ownership_percentage) / 100
            
            # Calculate minority share of net assets
            net_assets = self._calculate_company_net_assets(company)
            minority_interest = net_assets * minority_percentage
            
            # Create minority interest entry
            if minority_interest and self.minority_interest_account_id:
                vals = {
                    'journal_id': self.elimination_journal_id.id,
                    'date': self.current_period_id.date_to,
                    'ref': _('Minority Interest: %s') % company.name,
                    'line_ids': [
                        (0, 0, {
                            'account_id': self.minority_interest_account_id.id,
                            'debit': 0,
                            'credit': minority_interest,
                            'name': _('Minority Interest in %s') % company.name,
                        }),
                    ]
                }
                self.env['account.consolidation.move'].create(vals)
    
    def _calculate_company_net_assets(self, company):
        """Calculate net assets for a company"""
        lines = self.env['account.consolidation.move.line'].search([
            ('consolidation_company_id', '=', company.id),
            ('period_id', '=', self.current_period_id.id)
        ])
        
        assets = sum(l.balance for l in lines if l.account_id.account_type.startswith('asset'))
        liabilities = sum(l.balance for l in lines if l.account_id.account_type.startswith('liability'))
        
        return assets - liabilities
    
    def _generate_consolidated_entries(self):
        """Generate final consolidated journal entries"""
        # Group all consolidation lines by account
        lines = self.env['account.consolidation.move.line'].search([
            ('period_id', '=', self.current_period_id.id)
        ])
        
        account_balances = defaultdict(float)
        for line in lines:
            account_balances[line.account_id] += line.balance
        
        # Create consolidated journal entry
        journal = self.journal_ids.filtered(lambda j: j.type == 'general')[0]
        
        move_lines = []
        for account, balance in account_balances.items():
            if abs(balance) > 0.01:
                move_lines.append((0, 0, {
                    'account_id': account.id,
                    'debit': balance if balance > 0 else 0,
                    'credit': -balance if balance < 0 else 0,
                    'name': _('Consolidated Balance'),
                }))
        
        if move_lines:
            vals = {
                'journal_id': journal.id,
                'date': self.current_period_id.date_to,
                'ref': _('Consolidation for %s') % self.current_period_id.name,
                'line_ids': move_lines,
            }
            self.env['account.consolidation.move'].create(vals)
    
    def _update_consolidated_balances(self):
        """Update account balances after consolidation"""
        for account in self.account_ids:
            lines = self.env['account.consolidation.move.line'].search([
                ('account_id', '=', account.id),
                ('period_id', '=', self.current_period_id.id)
            ])
            
            account.balance = sum(lines.mapped('balance'))
            account.debit = sum(lines.mapped('debit'))
            account.credit = sum(lines.mapped('credit'))
    
    def action_validate(self):
        """Validate chart configuration"""
        self.ensure_one()
        
        # Check required settings
        if not self.account_ids:
            raise ValidationError(_('No consolidation accounts defined.'))
        
        if not self.journal_ids:
            raise ValidationError(_('No consolidation journals defined.'))
        
        if not self.company_ids:
            raise ValidationError(_('No companies to consolidate.'))
        
        if not self.elimination_journal_id:
            raise ValidationError(_('Elimination journal not configured.'))
        
        self.state = 'ready'
    
    def action_reset_to_draft(self):
        """Reset chart to draft state"""
        self.ensure_one()
        self.state = 'draft'
    
    @api.model
    def create_default_chart(self):
        """Create default consolidation chart"""
        chart = self.create({
            'name': 'Default Consolidation Chart',
            'code': 'DEFAULT',
            'consolidation_method': 'full',
        })
        
        # Create default accounts
        chart._create_default_accounts()
        
        # Create default journals
        chart._create_default_journals()
        
        return chart
    
    def _create_default_accounts(self):
        """Create default consolidation accounts"""
        account_types = [
            ('1000', 'Current Assets', 'asset_current'),
            ('1500', 'Fixed Assets', 'asset_fixed'),
            ('2000', 'Current Liabilities', 'liability_current'),
            ('2500', 'Long-term Liabilities', 'liability_non_current'),
            ('3000', 'Equity', 'equity'),
            ('4000', 'Revenue', 'income'),
            ('5000', 'Cost of Sales', 'expense_direct_cost'),
            ('6000', 'Operating Expenses', 'expense'),
            ('9000', 'Other Income/Expense', 'income_other'),
            ('9999', 'Minority Interest', 'equity'),
        ]
        
        for code, name, acc_type in account_types:
            self.env['account.consolidation.account'].create({
                'code': code,
                'name': name,
                'account_type': acc_type,
                'chart_id': self.id,
            })
    
    def _create_default_journals(self):
        """Create default consolidation journals"""
        journals = [
            ('CONS', 'Consolidation Journal', 'general'),
            ('ELIM', 'Elimination Journal', 'elimination'),
            ('CONV', 'Currency Conversion Journal', 'conversion'),
            ('ADJ', 'Adjustment Journal', 'general'),
        ]
        
        for code, name, j_type in journals:
            journal = self.env['account.consolidation.journal'].create({
                'code': code,
                'name': name,
                'type': j_type,
                'chart_id': self.id,
            })
            
            if j_type == 'elimination':
                self.elimination_journal_id = journal
            elif j_type == 'conversion':
                self.conversion_journal_id = journal
    
    def action_view_consolidated_balance_sheet(self):
        """View consolidated balance sheet"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'account_enterprise_replica.consolidated_balance_sheet',
            'report_type': 'qweb-html',
            'data': {'chart_id': self.id},
            'context': self.env.context,
        }
    
    def action_view_consolidated_pnl(self):
        """View consolidated P&L"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'account_enterprise_replica.consolidated_profit_loss',
            'report_type': 'qweb-html',
            'data': {'chart_id': self.id},
            'context': self.env.context,
        }
    
    def archive_all_data(self):
        """Archive all consolidation data for cleanup"""
        # Archive all related records
        self.account_ids.write({'active': False})
        self.journal_ids.write({'active': False})
        self.company_ids.write({'active': False})
        self.write({'active': False})