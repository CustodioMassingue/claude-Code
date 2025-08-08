# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import json
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentAdvanced(models.Model):
    _inherit = 'account.payment'
    _description = 'Advanced Payment Management'

    # Payment Processing
    payment_processor = fields.Selection([
        ('manual', 'Manual'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('square', 'Square'),
        ('authorize', 'Authorize.net'),
        ('bank_api', 'Bank API'),
        ('sepa', 'SEPA'),
        ('ach', 'ACH'),
        ('wire', 'Wire Transfer')
    ], string='Payment Processor', default='manual')
    
    processor_reference = fields.Char(
        string='Processor Reference',
        help='External payment processor transaction ID'
    )
    
    processor_status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('error', 'Error')
    ], string='Processor Status', default='pending')
    
    processor_message = fields.Text(
        string='Processor Message'
    )
    
    # Batch Payment
    batch_payment_id = fields.Many2one(
        'account.payment.batch',
        string='Batch Payment'
    )
    
    is_batch_payment = fields.Boolean(
        string='Is Batch Payment',
        compute='_compute_is_batch_payment',
        store=True
    )
    
    # Approval Workflow
    approval_required = fields.Boolean(
        string='Approval Required',
        compute='_compute_approval_required'
    )
    
    approval_level = fields.Selection([
        ('level_1', 'Level 1'),
        ('level_2', 'Level 2'),
        ('level_3', 'Level 3'),
        ('ceo', 'CEO Approval')
    ], string='Approval Level')
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date'
    )
    
    approval_notes = fields.Text(
        string='Approval Notes'
    )
    
    # Payment Schedule
    is_scheduled = fields.Boolean(
        string='Is Scheduled Payment'
    )
    
    scheduled_date = fields.Date(
        string='Scheduled Date'
    )
    
    recurring_payment = fields.Boolean(
        string='Recurring Payment'
    )
    
    recurrence_interval = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Recurrence Interval')
    
    recurrence_end_date = fields.Date(
        string='Recurrence End Date'
    )
    
    next_payment_date = fields.Date(
        string='Next Payment Date',
        compute='_compute_next_payment_date',
        store=True
    )
    
    # Advanced Currency Features
    hedge_rate = fields.Float(
        string='Hedge Rate',
        digits=(16, 6)
    )
    
    forward_contract_ref = fields.Char(
        string='Forward Contract Reference'
    )
    
    exchange_gain_loss = fields.Monetary(
        string='Exchange Gain/Loss',
        compute='_compute_exchange_gain_loss',
        currency_field='currency_id',
        store=True
    )
    
    # Payment Fees
    payment_fee = fields.Monetary(
        string='Payment Fee',
        currency_field='currency_id'
    )
    
    payment_fee_account_id = fields.Many2one(
        'account.account',
        string='Payment Fee Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    
    net_amount = fields.Monetary(
        string='Net Amount',
        compute='_compute_net_amount',
        currency_field='currency_id',
        store=True
    )
    
    # Early Payment Discount
    early_payment_discount = fields.Monetary(
        string='Early Payment Discount',
        currency_field='currency_id'
    )
    
    discount_account_id = fields.Many2one(
        'account.account',
        string='Discount Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
    )
    
    discount_date = fields.Date(
        string='Discount Valid Until'
    )
    
    # Payment Matching
    auto_reconcile = fields.Boolean(
        string='Auto Reconcile',
        default=True
    )
    
    matching_rules = fields.Text(
        string='Matching Rules',
        help='JSON format matching rules for auto-reconciliation'
    )
    
    matching_score = fields.Float(
        string='Matching Score',
        compute='_compute_matching_score'
    )
    
    # Bank Integration
    bank_statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line'
    )
    
    bank_reference = fields.Char(
        string='Bank Reference'
    )
    
    value_date = fields.Date(
        string='Value Date'
    )
    
    clearing_date = fields.Date(
        string='Clearing Date'
    )
    
    # Compliance & Risk
    compliance_check = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('manual_review', 'Manual Review Required')
    ], string='Compliance Check', default='pending')
    
    risk_score = fields.Float(
        string='Risk Score',
        compute='_compute_risk_score'
    )
    
    aml_check = fields.Boolean(
        string='AML Check Required',
        compute='_compute_aml_check'
    )
    
    sanctions_check = fields.Boolean(
        string='Sanctions Check Passed'
    )
    
    # Analytics
    payment_performance = fields.Selection([
        ('on_time', 'On Time'),
        ('early', 'Early'),
        ('late', 'Late'),
        ('very_late', 'Very Late')
    ], string='Payment Performance', compute='_compute_payment_performance', store=True)
    
    days_to_pay = fields.Integer(
        string='Days to Pay',
        compute='_compute_days_to_pay',
        store=True
    )
    
    # Audit Trail
    audit_log = fields.Text(
        string='Audit Log',
        readonly=True
    )

    @api.depends('batch_payment_id')
    def _compute_is_batch_payment(self):
        for payment in self:
            payment.is_batch_payment = bool(payment.batch_payment_id)

    @api.depends('amount', 'company_id')
    def _compute_approval_required(self):
        for payment in self:
            # Get approval limits from company settings
            limits = {
                'level_1': 10000,
                'level_2': 50000,
                'level_3': 100000,
                'ceo': 500000
            }
            
            amount_company = payment.currency_id._convert(
                payment.amount,
                payment.company_id.currency_id,
                payment.company_id,
                payment.date or fields.Date.today()
            )
            
            if amount_company >= limits['ceo']:
                payment.approval_level = 'ceo'
                payment.approval_required = True
            elif amount_company >= limits['level_3']:
                payment.approval_level = 'level_3'
                payment.approval_required = True
            elif amount_company >= limits['level_2']:
                payment.approval_level = 'level_2'
                payment.approval_required = True
            elif amount_company >= limits['level_1']:
                payment.approval_level = 'level_1'
                payment.approval_required = True
            else:
                payment.approval_level = False
                payment.approval_required = False

    @api.depends('recurring_payment', 'recurrence_interval', 'date')
    def _compute_next_payment_date(self):
        for payment in self:
            if not payment.recurring_payment or not payment.recurrence_interval:
                payment.next_payment_date = False
                continue
            
            base_date = payment.scheduled_date or payment.date or fields.Date.today()
            
            if payment.recurrence_interval == 'daily':
                payment.next_payment_date = base_date + timedelta(days=1)
            elif payment.recurrence_interval == 'weekly':
                payment.next_payment_date = base_date + timedelta(weeks=1)
            elif payment.recurrence_interval == 'monthly':
                payment.next_payment_date = base_date + timedelta(days=30)
            elif payment.recurrence_interval == 'quarterly':
                payment.next_payment_date = base_date + timedelta(days=90)
            elif payment.recurrence_interval == 'yearly':
                payment.next_payment_date = base_date + timedelta(days=365)

    @api.depends('amount', 'currency_id', 'date')
    def _compute_exchange_gain_loss(self):
        for payment in self:
            if payment.currency_id == payment.company_id.currency_id:
                payment.exchange_gain_loss = 0
                continue
            
            # Calculate exchange difference
            if payment.hedge_rate:
                hedged_amount = payment.amount * payment.hedge_rate
            else:
                hedged_amount = payment.currency_id._convert(
                    payment.amount,
                    payment.company_id.currency_id,
                    payment.company_id,
                    payment.date or fields.Date.today()
                )
            
            actual_amount = payment.currency_id._convert(
                payment.amount,
                payment.company_id.currency_id,
                payment.company_id,
                fields.Date.today()
            )
            
            payment.exchange_gain_loss = actual_amount - hedged_amount

    @api.depends('amount', 'payment_fee', 'early_payment_discount')
    def _compute_net_amount(self):
        for payment in self:
            payment.net_amount = payment.amount - payment.payment_fee - payment.early_payment_discount

    def _compute_matching_score(self):
        for payment in self:
            if not payment.reconciled_invoice_ids:
                payment.matching_score = 0
                continue
            
            # Calculate matching score based on various factors
            score = 0
            invoice = payment.reconciled_invoice_ids[0]
            
            # Amount matching (40 points)
            if abs(payment.amount - invoice.amount_residual) < 0.01:
                score += 40
            elif abs(payment.amount - invoice.amount_residual) / invoice.amount_residual < 0.01:
                score += 35
            elif abs(payment.amount - invoice.amount_residual) / invoice.amount_residual < 0.05:
                score += 25
            
            # Reference matching (30 points)
            if payment.ref and invoice.name:
                if payment.ref == invoice.name:
                    score += 30
                elif invoice.name in payment.ref or payment.ref in invoice.name:
                    score += 20
            
            # Date proximity (20 points)
            if payment.date and invoice.invoice_date:
                days_diff = abs((payment.date - invoice.invoice_date).days)
                if days_diff <= 3:
                    score += 20
                elif days_diff <= 7:
                    score += 15
                elif days_diff <= 30:
                    score += 10
            
            # Partner matching (10 points)
            if payment.partner_id == invoice.partner_id:
                score += 10
            
            payment.matching_score = score

    @api.depends('amount', 'partner_id')
    def _compute_risk_score(self):
        for payment in self:
            risk_score = 0
            
            # Amount-based risk
            amount_company = payment.currency_id._convert(
                payment.amount,
                payment.company_id.currency_id,
                payment.company_id,
                payment.date or fields.Date.today()
            )
            
            if amount_company > 1000000:
                risk_score += 40
            elif amount_company > 500000:
                risk_score += 30
            elif amount_company > 100000:
                risk_score += 20
            elif amount_company > 50000:
                risk_score += 10
            
            # Partner risk
            if payment.partner_id:
                # Check partner credit rating
                if hasattr(payment.partner_id, 'credit_limit'):
                    if payment.amount > payment.partner_id.credit_limit:
                        risk_score += 30
                
                # New partner risk
                partner_age = (fields.Date.today() - payment.partner_id.create_date.date()).days
                if partner_age < 30:
                    risk_score += 20
                elif partner_age < 90:
                    risk_score += 10
            
            # Payment method risk
            if payment.payment_processor in ['wire', 'ach']:
                risk_score += 10
            
            # Country risk (if international)
            if payment.partner_id and payment.partner_id.country_id != payment.company_id.country_id:
                risk_score += 15
            
            payment.risk_score = min(risk_score, 100)

    @api.depends('amount', 'partner_id')
    def _compute_aml_check(self):
        for payment in self:
            # AML check required for high amounts or high-risk countries
            threshold = payment.company_id.currency_id.compute(
                10000,
                payment.currency_id
            )
            
            payment.aml_check = (
                payment.amount >= threshold or
                payment.risk_score >= 50 or
                (payment.partner_id and payment.partner_id.country_id.code in ['IR', 'KP', 'SY'])
            )

    @api.depends('date', 'reconciled_invoice_ids')
    def _compute_payment_performance(self):
        for payment in self:
            if not payment.reconciled_invoice_ids:
                payment.payment_performance = False
                payment.days_to_pay = 0
                continue
            
            invoice = payment.reconciled_invoice_ids[0]
            if not invoice.invoice_date_due:
                payment.payment_performance = False
                payment.days_to_pay = 0
                continue
            
            payment_date = payment.date or fields.Date.today()
            days_diff = (payment_date - invoice.invoice_date_due).days
            
            if days_diff <= 0:
                payment.payment_performance = 'on_time'
            elif days_diff < -5:
                payment.payment_performance = 'early'
            elif days_diff <= 15:
                payment.payment_performance = 'late'
            else:
                payment.payment_performance = 'very_late'

    @api.depends('date', 'reconciled_invoice_ids')
    def _compute_days_to_pay(self):
        for payment in self:
            if not payment.reconciled_invoice_ids:
                payment.days_to_pay = 0
                continue
            
            invoice = payment.reconciled_invoice_ids[0]
            if not invoice.invoice_date:
                payment.days_to_pay = 0
                continue
            
            payment_date = payment.date or fields.Date.today()
            payment.days_to_pay = (payment_date - invoice.invoice_date).days

    def action_approve_payment(self):
        """Approve payment based on approval workflow"""
        for payment in self:
            if not payment.approval_required:
                continue
            
            # Check user has approval rights
            if not self._check_approval_rights(payment.approval_level):
                raise UserError(_("You don't have the required approval level for this payment."))
            
            payment.write({
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
                'state': 'posted' if payment.state == 'draft' else payment.state
            })
            
            # Log approval
            self._log_audit('payment_approved', {
                'amount': payment.amount,
                'approved_by': self.env.user.name,
                'approval_level': payment.approval_level
            })

    def _check_approval_rights(self, level):
        """Check if current user has required approval rights"""
        user = self.env.user
        
        # Map approval levels to groups
        level_groups = {
            'level_1': 'account.group_account_user',
            'level_2': 'account.group_account_manager',
            'level_3': 'base.group_system',
            'ceo': 'base.group_system'  # Would be a custom CEO group in production
        }
        
        required_group = level_groups.get(level)
        if not required_group:
            return True
        
        return user.has_group(required_group)

    def action_process_payment(self):
        """Process payment through external processor"""
        for payment in self:
            if payment.payment_processor == 'manual':
                continue
            
            # Simulate processor API call
            try:
                result = self._process_external_payment(payment)
                
                payment.write({
                    'processor_status': result['status'],
                    'processor_reference': result.get('reference'),
                    'processor_message': result.get('message')
                })
                
                if result['status'] == 'approved':
                    payment.action_post()
                    
            except Exception as e:
                payment.write({
                    'processor_status': 'error',
                    'processor_message': str(e)
                })
                _logger.error(f"Payment processing error: {e}")

    def _process_external_payment(self, payment):
        """Process payment through external API"""
        # This would integrate with actual payment processors
        # For now, simulate success
        return {
            'status': 'approved',
            'reference': f"TXN-{payment.id}-{fields.Date.today()}",
            'message': 'Payment processed successfully'
        }

    def action_create_recurring_payments(self):
        """Create recurring payment schedule"""
        for payment in self:
            if not payment.recurring_payment:
                continue
            
            payments_to_create = []
            current_date = payment.next_payment_date
            end_date = payment.recurrence_end_date or (fields.Date.today() + timedelta(days=365))
            
            while current_date and current_date <= end_date:
                payment_vals = {
                    'payment_type': payment.payment_type,
                    'partner_id': payment.partner_id.id,
                    'amount': payment.amount,
                    'currency_id': payment.currency_id.id,
                    'date': current_date,
                    'journal_id': payment.journal_id.id,
                    'payment_method_line_id': payment.payment_method_line_id.id,
                    'is_scheduled': True,
                    'scheduled_date': current_date,
                    'ref': f"{payment.ref} - {current_date}" if payment.ref else f"Recurring - {current_date}"
                }
                
                payments_to_create.append(payment_vals)
                
                # Calculate next date
                if payment.recurrence_interval == 'daily':
                    current_date += timedelta(days=1)
                elif payment.recurrence_interval == 'weekly':
                    current_date += timedelta(weeks=1)
                elif payment.recurrence_interval == 'monthly':
                    current_date += timedelta(days=30)
                elif payment.recurrence_interval == 'quarterly':
                    current_date += timedelta(days=90)
                elif payment.recurrence_interval == 'yearly':
                    current_date += timedelta(days=365)
            
            # Create scheduled payments
            for vals in payments_to_create:
                self.create(vals)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('%d recurring payments created.') % len(payments_to_create),
                    'type': 'success',
                }
            }

    def action_run_compliance_check(self):
        """Run compliance checks on payment"""
        for payment in self:
            compliance_passed = True
            
            # AML Check
            if payment.aml_check:
                # Would integrate with AML service
                aml_result = self._check_aml_compliance(payment)
                if not aml_result:
                    compliance_passed = False
            
            # Sanctions Check
            sanctions_result = self._check_sanctions(payment)
            payment.sanctions_check = sanctions_result
            if not sanctions_result:
                compliance_passed = False
            
            # Update compliance status
            if compliance_passed:
                payment.compliance_check = 'passed'
            else:
                payment.compliance_check = 'manual_review'
            
            self._log_audit('compliance_check', {
                'aml_check': payment.aml_check,
                'sanctions_check': payment.sanctions_check,
                'result': payment.compliance_check
            })

    def _check_aml_compliance(self, payment):
        """Check AML compliance"""
        # Would integrate with AML service
        # For now, simulate based on risk score
        return payment.risk_score < 70

    def _check_sanctions(self, payment):
        """Check sanctions list"""
        # Would integrate with sanctions database
        # For now, check country
        if payment.partner_id and payment.partner_id.country_id:
            sanctioned_countries = ['IR', 'KP', 'SY', 'CU']
            return payment.partner_id.country_id.code not in sanctioned_countries
        return True

    def _log_audit(self, action, details):
        """Log audit trail"""
        for payment in self:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user': self.env.user.name,
                'action': action,
                'details': details
            }
            
            current_log = json.loads(payment.audit_log or '[]')
            current_log.append(log_entry)
            
            payment.audit_log = json.dumps(current_log)

    @api.model
    def create(self, vals):
        payment = super().create(vals)
        payment._log_audit('created', {'amount': vals.get('amount')})
        return payment

    def write(self, vals):
        for payment in self:
            payment._log_audit('updated', {'changes': list(vals.keys())})
        return super().write(vals)


class AccountPaymentBatch(models.Model):
    _name = 'account.payment.batch'
    _description = 'Batch Payment Processing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Batch Name',
        required=True,
        default=lambda self: _('New')
    )
    
    date = fields.Date(
        string='Batch Date',
        required=True,
        default=fields.Date.today
    )
    
    payment_ids = fields.One2many(
        'account.payment',
        'batch_payment_id',
        string='Payments'
    )
    
    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_payment_stats'
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_payment_stats',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]"
    )
    
    batch_type = fields.Selection([
        ('vendor', 'Vendor Payments'),
        ('customer', 'Customer Refunds'),
        ('payroll', 'Payroll'),
        ('expense', 'Expense Reimbursements')
    ], string='Batch Type', required=True)
    
    @api.depends('payment_ids')
    def _compute_payment_stats(self):
        for batch in self:
            batch.payment_count = len(batch.payment_ids)
            batch.total_amount = sum(batch.payment_ids.mapped('amount'))
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('account.payment.batch') or _('New')
        return super().create(vals)
    
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_process(self):
        self.state = 'processing'
        for payment in self.payment_ids:
            if payment.state == 'draft':
                payment.action_post()
        self.state = 'done'
    
    def action_cancel(self):
        self.state = 'cancelled'