# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountApprovalHistory(models.Model):
    _name = 'account.approval.history'
    _description = 'Approval History'
    _order = 'date desc'
    _rec_name = 'status'
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )
    
    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now
    )
    
    status = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True)
    
    comments = fields.Text(
        string='Comments'
    )
    
    approval_level = fields.Integer(
        string='Approval Level',
        default=1
    )
    
    duration = fields.Float(
        string='Duration (hours)',
        compute='_compute_duration',
        store=True
    )
    
    @api.depends('date', 'move_id.create_date')
    def _compute_duration(self):
        for record in self:
            if record.date and record.move_id.create_date:
                delta = record.date - record.move_id.create_date
                record.duration = delta.total_seconds() / 3600
            else:
                record.duration = 0