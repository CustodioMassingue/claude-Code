# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, format_date
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLineAdvanced(models.Model):
    _inherit = 'account.move.line'
    _description = 'Advanced Journal Entry Line'

    # Advanced Analytics Fields
    cost_center_id = fields.Many2one(
        'account.analytic.account',
        string='Cost Center',
        domain="[('company_id', '=', company_id)]"
    )
    
    profit_center_id = fields.Many2one(
        'account.analytic.account',
        string='Profit Center',
        domain="[('company_id', '=', company_id)]"
    )
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        domain="[('company_id', '=', company_id)]"
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department'
    )
    
    # Multi-dimensional Analysis
    dimension_1_id = fields.Many2one(
        'account.analytic.tag',
        string='Dimension 1',
        domain="[('company_id', '=', company_id)]"
    )
    
    dimension_2_id = fields.Many2one(
        'account.analytic.tag',
        string='Dimension 2',
        domain="[('company_id', '=', company_id)]"
    )
    
    dimension_3_id = fields.Many2one(
        'account.analytic.tag',
        string='Dimension 3',
        domain="[('company_id', '=', company_id)]"
    )
    
    # Advanced Tax Fields
    tax_base_amount = fields.Monetary(
        string='Tax Base Amount',
        currency_field='company_currency_id',
        compute='_compute_tax_base_amount',
        store=True
    )
    
    effective_tax_rate = fields.Float(
        string='Effective Tax Rate',
        compute='_compute_effective_tax_rate',
        digits=(16, 4),
        store=True
    )
    
    tax_audit_trail = fields.Text(
        string='Tax Audit Trail',
        readonly=True
    )
    
    # Performance Tracking
    posting_time = fields.Float(
        string='Posting Time (ms)',
        readonly=True
    )
    
    reconciliation_time = fields.Float(
        string='Reconciliation Time (ms)',
        readonly=True
    )
    
    # Advanced Reconciliation
    partial_reconcile_ids = fields.One2many(
        'account.partial.reconcile',
        'debit_move_id',
        string='Partial Reconciliations'
    )
    
    suggested_reconcile_ids = fields.Many2many(
        'account.move.line',
        'account_move_line_suggested_rel',
        'move_line_id',
        'suggested_id',
        string='Suggested Reconciliations',
        compute='_compute_suggested_reconciliations'
    )
    
    reconcile_score = fields.Float(
        string='Reconciliation Score',
        compute='_compute_reconcile_score',
        help='AI-based reconciliation matching score'
    )
    
    # Compliance Fields
    compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('warning', 'Warning'),
        ('non_compliant', 'Non-Compliant'),
        ('pending', 'Pending Review')
    ], string='Compliance Status', default='pending')
    
    compliance_notes = fields.Text(
        string='Compliance Notes'
    )
    
    sox_relevant = fields.Boolean(
        string='SOX Relevant',
        compute='_compute_sox_relevant',
        store=True
    )
    
    # Cash Flow Classification
    cash_flow_category = fields.Selection([
        ('operating', 'Operating Activities'),
        ('investing', 'Investing Activities'),
        ('financing', 'Financing Activities')
    ], string='Cash Flow Category')
    
    # Budget Tracking
    budget_line_id = fields.Many2one(
        'account.budget.line',
        string='Budget Line'
    )
    
    budget_variance = fields.Monetary(
        string='Budget Variance',
        compute='_compute_budget_variance',
        currency_field='company_currency_id',
        store=True
    )
    
    # Advanced Currency Features
    original_currency_id = fields.Many2one(
        'res.currency',
        string='Original Currency'
    )
    
    original_amount = fields.Float(
        string='Original Amount',
        digits=(16, 4)
    )
    
    exchange_rate_date = fields.Date(
        string='Exchange Rate Date'
    )
    
    fx_revaluation_move_id = fields.Many2one(
        'account.move',
        string='FX Revaluation Entry'
    )
    
    # Allocation Fields
    allocation_key = fields.Char(
        string='Allocation Key'
    )
    
    allocation_percentage = fields.Float(
        string='Allocation %',
        digits=(5, 2)
    )
    
    source_move_line_id = fields.Many2one(
        'account.move.line',
        string='Source Line'
    )
    
    allocated_move_line_ids = fields.One2many(
        'account.move.line',
        'source_move_line_id',
        string='Allocated Lines'
    )
    
    # Audit Fields
    created_by_rule_id = fields.Many2one(
        'account.auto.entry.rule',
        string='Created by Rule'
    )
    
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved By'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date'
    )
    
    audit_log = fields.Text(
        string='Audit Log',
        readonly=True
    )

    @api.depends('debit', 'credit', 'tax_ids', 'tax_line_id')
    def _compute_tax_base_amount(self):
        for line in self:
            if line.tax_line_id:
                # This is a tax line, get base from tax repartition
                base_lines = self.search([
                    ('move_id', '=', line.move_id.id),
                    ('tax_ids', 'in', line.tax_line_id.id)
                ])
                line.tax_base_amount = sum(base_lines.mapped('balance'))
            elif line.tax_ids:
                # This is a base line
                line.tax_base_amount = line.balance
            else:
                line.tax_base_amount = 0.0

    @api.depends('tax_base_amount', 'balance')
    def _compute_effective_tax_rate(self):
        for line in self:
            if line.tax_line_id and line.tax_base_amount:
                line.effective_tax_rate = (abs(line.balance) / abs(line.tax_base_amount)) * 100
            else:
                line.effective_tax_rate = 0.0

    @api.depends('account_id', 'partner_id', 'amount_residual')
    def _compute_suggested_reconciliations(self):
        for line in self:
            if not line.account_id.reconcile or line.reconciled:
                line.suggested_reconcile_ids = False
                continue
            
            # Find potential matches
            domain = [
                ('account_id', '=', line.account_id.id),
                ('partner_id', '=', line.partner_id.id),
                ('reconciled', '=', False),
                ('id', '!=', line.id),
                ('company_id', '=', line.company_id.id)
            ]
            
            # Opposite balance
            if line.balance > 0:
                domain.append(('balance', '<', 0))
            else:
                domain.append(('balance', '>', 0))
            
            suggestions = self.search(domain, limit=10)
            line.suggested_reconcile_ids = suggestions

    @api.depends('suggested_reconcile_ids')
    def _compute_reconcile_score(self):
        for line in self:
            if not line.suggested_reconcile_ids:
                line.reconcile_score = 0.0
                continue
            
            best_score = 0.0
            for suggestion in line.suggested_reconcile_ids:
                score = self._calculate_reconcile_match_score(line, suggestion)
                if score > best_score:
                    best_score = score
            
            line.reconcile_score = best_score

    def _calculate_reconcile_match_score(self, line1, line2):
        """Calculate matching score between two lines for reconciliation"""
        score = 0.0
        
        # Amount matching (40% weight)
        amount_diff = abs(abs(line1.balance) - abs(line2.balance))
        if float_is_zero(amount_diff, precision_rounding=0.01):
            score += 40.0
        elif amount_diff < abs(line1.balance) * 0.01:  # Within 1%
            score += 30.0
        elif amount_diff < abs(line1.balance) * 0.05:  # Within 5%
            score += 20.0
        
        # Date proximity (20% weight)
        date_diff = abs((line1.date - line2.date).days)
        if date_diff == 0:
            score += 20.0
        elif date_diff <= 3:
            score += 15.0
        elif date_diff <= 7:
            score += 10.0
        elif date_diff <= 30:
            score += 5.0
        
        # Reference matching (20% weight)
        if line1.ref and line2.ref:
            if line1.ref == line2.ref:
                score += 20.0
            elif line1.ref in line2.ref or line2.ref in line1.ref:
                score += 10.0
        
        # Partner matching (already filtered, 10% weight)
        score += 10.0
        
        # Currency matching (10% weight)
        if line1.currency_id == line2.currency_id:
            score += 10.0
        
        return score

    @api.depends('account_id', 'amount_currency', 'company_id')
    def _compute_sox_relevant(self):
        for line in self:
            # Check if account is SOX relevant
            sox_accounts = ['1', '2', '4', '5']  # Asset, Liability, Revenue, Expense
            if line.account_id and line.account_id.code and line.account_id.code[0] in sox_accounts:
                # Check materiality threshold
                threshold = line.company_id.currency_id.compute(50000, line.company_currency_id)
                if abs(line.balance) >= threshold:
                    line.sox_relevant = True
                else:
                    line.sox_relevant = False
            else:
                line.sox_relevant = False

    @api.depends('budget_line_id', 'balance')
    def _compute_budget_variance(self):
        for line in self:
            if line.budget_line_id:
                # Get budget amount for the period
                budget_amount = line.budget_line_id.planned_amount
                actual_amount = abs(line.balance)
                line.budget_variance = budget_amount - actual_amount
            else:
                line.budget_variance = 0.0

    def action_auto_reconcile(self):
        """Automatically reconcile lines based on AI suggestions"""
        for line in self:
            if line.reconcile_score >= 95.0 and line.suggested_reconcile_ids:
                # Get best match
                best_match = max(
                    line.suggested_reconcile_ids,
                    key=lambda x: self._calculate_reconcile_match_score(line, x)
                )
                
                # Reconcile if amounts match exactly
                if float_is_zero(
                    abs(line.balance) - abs(best_match.balance),
                    precision_rounding=0.01
                ):
                    (line | best_match).reconcile()
                    self._log_audit_action('auto_reconcile', {
                        'matched_with': best_match.id,
                        'score': line.reconcile_score
                    })

    def action_allocate_costs(self):
        """Allocate costs to multiple cost centers"""
        for line in self:
            if not line.allocation_key:
                continue
            
            # Get allocation rules
            allocation_rules = self._get_allocation_rules(line.allocation_key)
            if not allocation_rules:
                continue
            
            # Create allocation entries
            move_vals = {
                'date': line.date,
                'journal_id': line.journal_id.id,
                'ref': f"Allocation of {line.move_id.name}",
                'line_ids': []
            }
            
            for rule in allocation_rules:
                amount = line.balance * rule['percentage'] / 100
                
                # Debit line
                move_vals['line_ids'].append((0, 0, {
                    'account_id': rule['account_id'],
                    'name': f"Allocation {rule['percentage']}%",
                    'debit': amount if amount > 0 else 0,
                    'credit': -amount if amount < 0 else 0,
                    'cost_center_id': rule['cost_center_id'],
                    'source_move_line_id': line.id,
                }))
            
            # Balancing entry
            move_vals['line_ids'].append((0, 0, {
                'account_id': line.account_id.id,
                'name': f"Allocation reversal",
                'debit': -line.balance if line.balance < 0 else 0,
                'credit': line.balance if line.balance > 0 else 0,
            }))
            
            # Create and post allocation move
            allocation_move = self.env['account.move'].create(move_vals)
            allocation_move.action_post()

    def _get_allocation_rules(self, allocation_key):
        """Get allocation rules based on key"""
        # This would typically fetch from configuration
        # For now, return sample rules
        return [
            {
                'percentage': 60,
                'account_id': self.account_id.id,
                'cost_center_id': self.cost_center_id.id
            },
            {
                'percentage': 40,
                'account_id': self.account_id.id,
                'cost_center_id': self.profit_center_id.id
            }
        ]

    def _log_audit_action(self, action, details):
        """Log audit trail for the line"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': self.env.user.name,
            'action': action,
            'details': details
        }
        
        current_log = json.loads(self.audit_log or '[]')
        current_log.append(log_entry)
        
        self.audit_log = json.dumps(current_log)

    @api.model
    def create(self, vals):
        start_time = datetime.now()
        
        # Add audit trail
        vals['audit_log'] = json.dumps([{
            'timestamp': datetime.now().isoformat(),
            'user': self.env.user.name,
            'action': 'create',
            'details': {'initial_values': str(vals)}
        }])
        
        line = super().create(vals)
        
        # Track performance
        line.posting_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return line

    def write(self, vals):
        # Add audit trail
        for line in self:
            line._log_audit_action('update', {'changed_values': str(vals)})
        
        return super().write(vals)

    @api.constrains('cost_center_id', 'profit_center_id')
    def _check_cost_centers(self):
        for line in self:
            if line.cost_center_id and line.profit_center_id:
                if line.cost_center_id == line.profit_center_id:
                    raise ValidationError(_("Cost Center and Profit Center cannot be the same."))

    def action_check_compliance(self):
        """Check compliance status of the line"""
        for line in self:
            compliance_issues = []
            
            # Check SOX compliance
            if line.sox_relevant and not line.approval_user_id:
                compliance_issues.append("SOX relevant transaction requires approval")
            
            # Check tax compliance
            if line.tax_ids and not line.tax_audit_trail:
                compliance_issues.append("Tax calculation audit trail missing")
            
            # Check budget compliance
            if line.budget_variance < 0:
                compliance_issues.append(f"Over budget by {abs(line.budget_variance)}")
            
            # Update compliance status
            if not compliance_issues:
                line.compliance_status = 'compliant'
            elif len(compliance_issues) == 1:
                line.compliance_status = 'warning'
            else:
                line.compliance_status = 'non_compliant'
            
            line.compliance_notes = '\n'.join(compliance_issues)