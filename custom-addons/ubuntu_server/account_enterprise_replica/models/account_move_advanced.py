# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json
import base64
from collections import defaultdict


class AccountMoveAdvanced(models.Model):
    _inherit = 'account.move'
    
    # ==================== Enterprise Dashboard Fields ====================
    
    dashboard_data = fields.Text(
        string='Dashboard Data',
        compute='_compute_dashboard_data',
        store=False
    )
    
    kpi_data = fields.Text(
        string='KPI Data',
        compute='_compute_kpi_data',
        store=False
    )
    
    # ==================== Consolidation Fields ====================
    
    consolidation_journal_id = fields.Many2one(
        'account.consolidation.journal',
        string='Consolidation Journal',
        ondelete='restrict'
    )
    
    consolidation_chart_id = fields.Many2one(
        'account.consolidation.chart',
        string='Consolidation Chart',
        ondelete='restrict'
    )
    
    is_consolidation_move = fields.Boolean(
        string='Is Consolidation Entry',
        default=False
    )
    
    consolidation_rate = fields.Float(
        string='Consolidation Rate',
        digits=(16, 6),
        default=1.0
    )
    
    ownership_percentage = fields.Float(
        string='Ownership %',
        digits=(5, 2)
    )
    
    # ==================== OCR & AI Fields ====================
    
    ocr_status = fields.Selection([
        ('none', 'No OCR'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('review', 'Needs Review')
    ], string='OCR Status', default='none')
    
    ocr_confidence_score = fields.Float(
        string='OCR Confidence',
        digits=(5, 2)
    )
    
    ai_suggested_account_ids = fields.One2many(
        'account.ai.suggestion',
        'move_id',
        string='AI Suggestions'
    )
    
    anomaly_score = fields.Float(
        string='Anomaly Score',
        compute='_compute_anomaly_score',
        store=True,
        help='AI-detected anomaly score (0-100)'
    )
    
    # ==================== Advanced Workflow Fields ====================
    
    approval_matrix_id = fields.Many2one(
        'account.approval.matrix',
        string='Approval Matrix',
        compute='_compute_approval_matrix',
        store=True
    )
    
    approval_status = fields.Selection([
        ('none', 'No Approval Needed'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated')
    ], string='Approval Status', default='none', tracking=True)
    
    approver_ids = fields.Many2many(
        'res.users',
        'account_move_approvers_rel',
        'move_id',
        'user_id',
        string='Approvers'
    )
    
    approval_history_ids = fields.One2many(
        'account.approval.history',
        'move_id',
        string='Approval History'
    )
    
    # ==================== Cash Flow Forecast Fields ====================
    
    cash_flow_category_id = fields.Many2one(
        'account.cash.flow.category',
        string='Cash Flow Category'
    )
    
    forecast_date = fields.Date(
        string='Forecast Payment Date',
        compute='_compute_forecast_date',
        store=True
    )
    
    payment_probability = fields.Float(
        string='Payment Probability %',
        compute='_compute_payment_probability',
        store=True,
        digits=(5, 2)
    )
    
    # ==================== Budget Management Fields ====================
    
    budget_line_id = fields.Many2one(
        'account.budget.line',
        string='Budget Line'
    )
    
    budget_variance = fields.Monetary(
        string='Budget Variance',
        compute='_compute_budget_variance',
        store=True,
        currency_field='currency_id'
    )
    
    budget_utilization = fields.Float(
        string='Budget Utilization %',
        compute='_compute_budget_utilization',
        store=True,
        digits=(5, 2)
    )
    
    # ==================== Advanced Multi-currency ====================
    
    hedge_accounting = fields.Boolean(
        string='Hedge Accounting',
        default=False
    )
    
    hedge_item_id = fields.Many2one(
        'account.hedge.item',
        string='Hedged Item'
    )
    
    fx_revaluation_move_id = fields.Many2one(
        'account.move',
        string='FX Revaluation Entry'
    )
    
    unrealized_gain_loss = fields.Monetary(
        string='Unrealized Gain/Loss',
        compute='_compute_unrealized_gain_loss',
        store=True,
        currency_field='company_currency_id'
    )
    
    # ==================== Advanced Analytics ====================
    
    profitability_analysis = fields.Text(
        string='Profitability Analysis',
        compute='_compute_profitability_analysis'
    )
    
    cost_center_ids = fields.Many2many(
        'account.cost.center',
        'account_move_cost_center_rel',
        'move_id',
        'cost_center_id',
        string='Cost Centers'
    )
    
    profit_center_id = fields.Many2one(
        'account.profit.center',
        string='Profit Center'
    )
    
    segment_ids = fields.Many2many(
        'account.business.segment',
        'account_move_segment_rel',
        'move_id',
        'segment_id',
        string='Business Segments'
    )
    
    # ==================== Compliance & Audit ====================
    
    sox_compliant = fields.Boolean(
        string='SOX Compliant',
        compute='_compute_sox_compliance',
        store=True
    )
    
    audit_trail = fields.Text(
        string='Audit Trail',
        readonly=True
    )
    
    digital_signature = fields.Text(
        string='Digital Signature'
    )
    
    compliance_check_ids = fields.One2many(
        'account.compliance.check',
        'move_id',
        string='Compliance Checks'
    )
    
    # ==================== Performance Fields ====================
    
    cached_totals = fields.Text(
        string='Cached Totals',
        help='JSON cached computations for performance'
    )
    
    last_cache_update = fields.Datetime(
        string='Cache Updated'
    )
    
    # ==================== Methods ====================
    
    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.amount_currency')
    def _compute_dashboard_data(self):
        """Compute dashboard data for each move"""
        for move in self:
            data = {
                'total_debit': sum(move.line_ids.mapped('debit')),
                'total_credit': sum(move.line_ids.mapped('credit')),
                'line_count': len(move.line_ids),
                'currency_count': len(move.line_ids.mapped('currency_id')),
                'account_count': len(move.line_ids.mapped('account_id')),
                'tax_amount': move.amount_tax,
                'profitability': self._calculate_profitability(move),
                'aging_days': (fields.Date.today() - move.invoice_date).days if move.invoice_date else 0,
                'payment_status': move.payment_state,
                'reconciliation_status': self._get_reconciliation_status(move),
            }
            move.dashboard_data = json.dumps(data)
    
    @api.depends('amount_total', 'amount_residual', 'state')
    def _compute_kpi_data(self):
        """Compute KPI metrics for executive dashboard"""
        for move in self:
            kpi_data = {
                'dso': self._calculate_dso(move),
                'dpo': self._calculate_dpo(move),
                'collection_efficiency': self._calculate_collection_efficiency(move),
                'discount_impact': self._calculate_discount_impact(move),
                'tax_efficiency': self._calculate_tax_efficiency(move),
                'margin': self._calculate_margin(move),
                'forecast_accuracy': self._calculate_forecast_accuracy(move),
            }
            move.kpi_data = json.dumps(kpi_data)
    
    @api.depends('line_ids', 'partner_id', 'amount_total')
    def _compute_anomaly_score(self):
        """Use ML to detect anomalies in accounting entries"""
        for move in self:
            if not move.line_ids:
                move.anomaly_score = 0
                continue
                
            # Call AI model for anomaly detection
            ai_model = self.env['account.ai.prediction']
            features = ai_model._extract_move_features(move)
            move.anomaly_score = ai_model.predict_anomaly(features)
    
    @api.depends('amount_total', 'company_id')
    def _compute_approval_matrix(self):
        """Determine approval matrix based on amount and type"""
        for move in self:
            matrix = self.env['account.approval.matrix'].search([
                ('company_id', '=', move.company_id.id),
                ('move_type', '=', move.move_type),
                ('min_amount', '<=', move.amount_total),
                ('max_amount', '>=', move.amount_total),
            ], limit=1)
            move.approval_matrix_id = matrix
    
    @api.depends('invoice_date_due', 'partner_id', 'amount_residual')
    def _compute_forecast_date(self):
        """AI prediction of actual payment date"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # Use ML model to predict payment date
                ai_model = self.env['account.ai.prediction']
                move.forecast_date = ai_model.predict_payment_date(move)
            else:
                move.forecast_date = move.invoice_date_due
    
    @api.depends('partner_id', 'amount_total', 'invoice_date_due')
    def _compute_payment_probability(self):
        """Calculate probability of on-time payment"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                ai_model = self.env['account.ai.prediction']
                move.payment_probability = ai_model.predict_payment_probability(move)
            else:
                move.payment_probability = 100.0
    
    @api.depends('line_ids.debit', 'line_ids.credit', 'budget_line_id')
    def _compute_budget_variance(self):
        """Calculate variance from budget"""
        for move in self:
            if move.budget_line_id:
                actual = sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit'))
                move.budget_variance = move.budget_line_id.planned_amount - actual
            else:
                move.budget_variance = 0
    
    @api.depends('budget_variance', 'budget_line_id')
    def _compute_budget_utilization(self):
        """Calculate budget utilization percentage"""
        for move in self:
            if move.budget_line_id and move.budget_line_id.planned_amount:
                actual = sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit'))
                move.budget_utilization = (actual / move.budget_line_id.planned_amount) * 100
            else:
                move.budget_utilization = 0
    
    @api.depends('line_ids.amount_currency', 'line_ids.balance')
    def _compute_unrealized_gain_loss(self):
        """Calculate unrealized FX gain/loss"""
        for move in self:
            total_gain_loss = 0
            for line in move.line_ids.filtered(lambda l: l.currency_id and l.currency_id != move.company_currency_id):
                current_rate = line.currency_id._get_conversion_rate(
                    line.currency_id,
                    move.company_currency_id,
                    move.company_id,
                    fields.Date.today()
                )
                historical_rate = abs(line.balance / line.amount_currency) if line.amount_currency else 0
                if historical_rate:
                    total_gain_loss += line.amount_currency * (current_rate - historical_rate)
            move.unrealized_gain_loss = total_gain_loss
    
    @api.depends('state', 'line_ids')
    def _compute_sox_compliance(self):
        """Check SOX compliance requirements"""
        for move in self:
            move.sox_compliant = all([
                move.state in ('draft', 'posted'),
                all(line.account_id for line in move.line_ids),
                abs(sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit'))) < 0.01,
                move.journal_id.restrict_mode_hash_table,
                bool(move.audit_trail),
            ])
    
    def _compute_profitability_analysis(self):
        """Advanced profitability analysis"""
        for move in self:
            analysis = {
                'gross_margin': self._calculate_gross_margin(move),
                'operating_margin': self._calculate_operating_margin(move),
                'net_margin': self._calculate_net_margin(move),
                'contribution_margin': self._calculate_contribution_margin(move),
                'roi': self._calculate_roi(move),
                'by_segment': self._calculate_segment_profitability(move),
                'by_product': self._calculate_product_profitability(move),
                'by_customer': self._calculate_customer_profitability(move),
            }
            move.profitability_analysis = json.dumps(analysis)
    
    # ==================== Helper Methods ====================
    
    def _calculate_profitability(self, move):
        """Calculate move profitability"""
        if move.move_type in ('out_invoice', 'out_refund'):
            revenue = move.amount_untaxed
            cost = sum(line.purchase_price * line.quantity for line in move.invoice_line_ids if hasattr(line, 'purchase_price'))
            return ((revenue - cost) / revenue * 100) if revenue else 0
        return 0
    
    def _get_reconciliation_status(self, move):
        """Get detailed reconciliation status"""
        if move.payment_state == 'paid':
            return 'fully_reconciled'
        elif move.payment_state == 'partial':
            return 'partially_reconciled'
        elif move.payment_state == 'in_payment':
            return 'in_payment'
        else:
            return 'not_reconciled'
    
    def _calculate_dso(self, move):
        """Days Sales Outstanding calculation"""
        if move.move_type == 'out_invoice' and move.invoice_date:
            payment_date = move.invoice_date_due or move.invoice_date
            return (payment_date - move.invoice_date).days
        return 0
    
    def _calculate_dpo(self, move):
        """Days Payables Outstanding calculation"""
        if move.move_type == 'in_invoice' and move.invoice_date:
            payment_date = move.invoice_date_due or move.invoice_date
            return (payment_date - move.invoice_date).days
        return 0
    
    def _calculate_collection_efficiency(self, move):
        """Calculate collection efficiency percentage"""
        if move.move_type == 'out_invoice' and move.amount_total:
            return ((move.amount_total - move.amount_residual) / move.amount_total * 100)
        return 0
    
    def _calculate_discount_impact(self, move):
        """Calculate discount impact on margin"""
        if move.invoice_line_ids:
            total_discount = sum(line.price_unit * line.quantity * line.discount / 100 
                               for line in move.invoice_line_ids)
            return total_discount
        return 0
    
    def _calculate_tax_efficiency(self, move):
        """Calculate tax efficiency ratio"""
        if move.amount_total:
            return (move.amount_tax / move.amount_total * 100)
        return 0
    
    def _calculate_margin(self, move):
        """Calculate gross margin"""
        if move.move_type in ('out_invoice', 'out_refund') and move.amount_untaxed:
            cost = sum(line.purchase_price * line.quantity 
                      for line in move.invoice_line_ids 
                      if hasattr(line, 'purchase_price'))
            return ((move.amount_untaxed - cost) / move.amount_untaxed * 100)
        return 0
    
    def _calculate_forecast_accuracy(self, move):
        """Calculate forecast accuracy based on historical data"""
        # Implementation would compare forecast vs actual
        return 85.0  # Placeholder
    
    def _calculate_gross_margin(self, move):
        """Calculate gross margin"""
        if move.amount_untaxed:
            cogs = sum(line.purchase_price * line.quantity 
                      for line in move.invoice_line_ids 
                      if hasattr(line, 'purchase_price'))
            return ((move.amount_untaxed - cogs) / move.amount_untaxed * 100)
        return 0
    
    def _calculate_operating_margin(self, move):
        """Calculate operating margin"""
        # Would include operating expenses
        return self._calculate_gross_margin(move) * 0.7  # Simplified
    
    def _calculate_net_margin(self, move):
        """Calculate net margin"""
        if move.amount_total:
            net_income = move.amount_total - move.amount_tax
            return (net_income / move.amount_total * 100)
        return 0
    
    def _calculate_contribution_margin(self, move):
        """Calculate contribution margin"""
        if move.amount_untaxed:
            variable_costs = sum(line.purchase_price * line.quantity 
                               for line in move.invoice_line_ids 
                               if hasattr(line, 'purchase_price'))
            return ((move.amount_untaxed - variable_costs) / move.amount_untaxed * 100)
        return 0
    
    def _calculate_roi(self, move):
        """Calculate return on investment"""
        # Simplified ROI calculation
        if move.move_type == 'out_invoice':
            return 15.5  # Placeholder
        return 0
    
    def _calculate_segment_profitability(self, move):
        """Calculate profitability by business segment"""
        segment_profit = {}
        for segment in move.segment_ids:
            segment_profit[segment.name] = self._calculate_margin(move)
        return segment_profit
    
    def _calculate_product_profitability(self, move):
        """Calculate profitability by product"""
        product_profit = {}
        for line in move.invoice_line_ids:
            if line.product_id:
                margin = ((line.price_subtotal - (line.purchase_price * line.quantity if hasattr(line, 'purchase_price') else 0)) 
                         / line.price_subtotal * 100) if line.price_subtotal else 0
                product_profit[line.product_id.name] = margin
        return product_profit
    
    def _calculate_customer_profitability(self, move):
        """Calculate customer lifetime profitability"""
        if move.partner_id:
            # Would calculate based on historical data
            return {move.partner_id.name: self._calculate_margin(move)}
        return {}
    
    # ==================== Actions ====================
    
    def action_process_ocr(self):
        """Process invoice with OCR"""
        self.ensure_one()
        if self.message_main_attachment_id:
            processor = self.env['account.ocr.processor']
            processor.process_document(self)
    
    def action_approve(self):
        """Approve the move through approval matrix"""
        self.ensure_one()
        if self.approval_matrix_id:
            self.approval_status = 'approved'
            self.approver_ids = [(4, self.env.user.id)]
            self._create_approval_history('approved')
    
    def action_reject(self):
        """Reject the move"""
        self.ensure_one()
        self.approval_status = 'rejected'
        self._create_approval_history('rejected')
    
    def action_request_approval(self):
        """Request approval based on matrix"""
        self.ensure_one()
        if self.approval_matrix_id:
            self.approval_status = 'pending'
            self._notify_approvers()
    
    def action_generate_forecast(self):
        """Generate cash flow forecast"""
        self.ensure_one()
        forecast = self.env['account.cash.flow.forecast']
        forecast.generate_forecast_from_move(self)
    
    def action_check_compliance(self):
        """Run compliance checks"""
        self.ensure_one()
        checker = self.env['account.compliance.check']
        checker.run_checks(self)
    
    def action_revalue_currency(self):
        """Revalue foreign currency"""
        self.ensure_one()
        if self.line_ids.filtered('currency_id'):
            revaluation = self.env['account.fx.revaluation']
            revaluation.revalue_move(self)
    
    def _create_approval_history(self, status):
        """Create approval history record"""
        self.env['account.approval.history'].create({
            'move_id': self.id,
            'user_id': self.env.user.id,
            'status': status,
            'date': fields.Datetime.now(),
            'comments': '',
        })
    
    def _notify_approvers(self):
        """Send notification to approvers"""
        if self.approval_matrix_id and self.approval_matrix_id.approver_ids:
            # Send email/notification to approvers
            pass
    
    @api.model
    def create(self, vals):
        """Override create to add audit trail"""
        move = super().create(vals)
        move.audit_trail = json.dumps({
            'created_by': self.env.user.name,
            'created_at': fields.Datetime.now().isoformat(),
            'ip_address': self.env.context.get('remote_ip', ''),
        })
        return move
    
    def write(self, vals):
        """Override write to update audit trail"""
        result = super().write(vals)
        for move in self:
            if move.audit_trail:
                audit = json.loads(move.audit_trail)
            else:
                audit = {}
            
            if 'changes' not in audit:
                audit['changes'] = []
            
            audit['changes'].append({
                'modified_by': self.env.user.name,
                'modified_at': fields.Datetime.now().isoformat(),
                'fields': list(vals.keys()),
            })
            move.audit_trail = json.dumps(audit)
        return result