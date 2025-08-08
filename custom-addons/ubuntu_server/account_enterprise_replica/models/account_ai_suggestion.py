# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountAiSuggestion(models.Model):
    _name = 'account.ai.suggestion'
    _description = 'AI Account Suggestion'
    _order = 'confidence desc'
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade'
    )
    
    line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        ondelete='cascade'
    )
    
    suggested_account_id = fields.Many2one(
        'account.account',
        string='Suggested Account',
        required=True
    )
    
    current_account_id = fields.Many2one(
        'account.account',
        string='Current Account'
    )
    
    confidence = fields.Float(
        string='Confidence Score',
        digits=(5, 2),
        help='AI confidence score for this suggestion (0-100)'
    )
    
    suggestion_type = fields.Selection([
        ('account', 'Account Suggestion'),
        ('partner', 'Partner Suggestion'),
        ('tax', 'Tax Suggestion'),
        ('analytic', 'Analytic Suggestion'),
    ], string='Type', default='account')
    
    reason = fields.Text(
        string='Suggestion Reason',
        help='Explanation for why this suggestion was made'
    )
    
    applied = fields.Boolean(
        string='Applied',
        default=False
    )
    
    applied_date = fields.Datetime(
        string='Applied Date'
    )
    
    applied_by = fields.Many2one(
        'res.users',
        string='Applied By'
    )
    
    def action_apply_suggestion(self):
        """Apply the AI suggestion"""
        self.ensure_one()
        if self.line_id and self.suggested_account_id:
            self.line_id.account_id = self.suggested_account_id
            self.applied = True
            self.applied_date = fields.Datetime.now()
            self.applied_by = self.env.user
        return True
    
    def action_reject_suggestion(self):
        """Reject the AI suggestion"""
        self.ensure_one()
        self.unlink()
        return True