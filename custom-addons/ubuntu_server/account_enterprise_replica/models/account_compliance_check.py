# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountComplianceCheck(models.Model):
    _name = 'account.compliance.check'
    _description = 'Account Compliance Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        ondelete='cascade'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], string='Status', default='draft', tracking=True)
    
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_done(self):
        self.state = 'done'
