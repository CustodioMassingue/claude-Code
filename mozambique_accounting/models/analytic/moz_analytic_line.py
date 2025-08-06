# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MozAnalyticLine(models.Model):
    _name = 'moz.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc, id desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Description',
        required=True
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id'
    )
    
    unit_amount = fields.Float(
        string='Quantity',
        default=1.0
    )
    
    account_id = fields.Many2one(
        'moz.analytic.account',
        string='Analytic Account',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    cost_center_id = fields.Many2one(
        'moz.cost.center',
        string='Cost Center',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )
    
    tag_ids = fields.Many2many(
        'moz.analytic.tag',
        string='Tags'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Source document
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        index=True
    )
    
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        index=True
    )
    
    invoice_id = fields.Many2one(
        'moz.invoice',
        string='Invoice'
    )
    
    # General account
    general_account_id = fields.Many2one(
        'account.account',
        string='General Account',
        domain="[('deprecated', '=', False)]"
    )
    
    # Category for grouping
    category = fields.Selection([
        ('revenue', 'Revenue'),
        ('cost', 'Cost'),
        ('expense', 'Expense'),
        ('investment', 'Investment'),
        ('other', 'Other'),
    ], string='Category', default='other')
    
    # Project fields
    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )
    
    task_id = fields.Many2one(
        'project.task',
        string='Task'
    )
    
    # Product
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    
    # Additional info
    ref = fields.Char(
        string='Reference'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.product_uom_id = self.product_id.uom_id
            if self.product_id.standard_price:
                self.amount = -self.product_id.standard_price * self.unit_amount
    
    @api.onchange('unit_amount')
    def _onchange_unit_amount(self):
        if self.product_id and self.product_id.standard_price:
            self.amount = -self.product_id.standard_price * self.unit_amount
    
    @api.constrains('account_id', 'date')
    def _check_account_dates(self):
        for line in self:
            if line.account_id.date_start and line.date < line.account_id.date_start:
                raise ValidationError(_('Line date cannot be before account start date.'))
            if line.account_id.date_end and line.date > line.account_id.date_end:
                raise ValidationError(_('Line date cannot be after account end date.'))
    
    def action_view_source(self):
        """View source document"""
        self.ensure_one()
        
        if self.move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
            }
        elif self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'moz.invoice',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
            }
        elif self.project_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.project',
                'res_id': self.project_id.id,
                'view_mode': 'form',
            }
        
        return {'type': 'ir.actions.act_window_close'}


class MozAnalyticTag(models.Model):
    _name = 'moz.analytic.tag'
    _description = 'Analytic Tag'
    _order = 'name'
    
    name = fields.Char(
        string='Name',
        required=True
    )
    
    color = fields.Integer(
        string='Color'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    line_ids = fields.Many2many(
        'moz.analytic.line',
        string='Analytic Lines'
    )