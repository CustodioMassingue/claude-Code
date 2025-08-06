# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MozAssetDepreciationLine(models.Model):
    _name = 'moz.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'depreciation_date'
    
    asset_id = fields.Many2one(
        'moz.asset',
        string='Asset',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        required=True
    )
    
    depreciation_date = fields.Date(
        string='Depreciation Date',
        required=True,
        index=True
    )
    
    depreciation_value = fields.Monetary(
        string='Depreciation Amount',
        required=True,
        currency_field='currency_id'
    )
    
    remaining_value = fields.Monetary(
        string='Remaining Value',
        required=True,
        currency_field='currency_id'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True
    )
    
    move_posted = fields.Boolean(
        string='Posted',
        compute='_compute_move_posted',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        string='Currency'
    )
    
    company_id = fields.Many2one(
        related='asset_id.company_id',
        string='Company',
        store=True
    )
    
    @api.depends('move_id', 'move_id.state')
    def _compute_move_posted(self):
        for line in self:
            line.move_posted = line.move_id and line.move_id.state == 'posted'
    
    def create_move(self):
        """Create journal entry for depreciation"""
        for line in self:
            if line.move_id:
                raise UserError(_('Depreciation entry already exists.'))
            
            asset = line.asset_id
            
            # Create journal entry
            move_vals = {
                'journal_id': asset.journal_id.id,
                'date': line.depreciation_date,
                'ref': f"{asset.name} - Depreciation {line.sequence}",
                'line_ids': [
                    # Depreciation expense
                    (0, 0, {
                        'name': f"{asset.name} - Depreciation",
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': line.depreciation_value,
                        'credit': 0,
                        'analytic_account_id': asset.analytic_account_id.id if asset.analytic_account_id else False,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)] if asset.analytic_tag_ids else False,
                    }),
                    # Accumulated depreciation
                    (0, 0, {
                        'name': f"{asset.name} - Accumulated Depreciation",
                        'account_id': asset.account_depreciation_id.id,
                        'debit': 0,
                        'credit': line.depreciation_value,
                    }),
                ],
            }
            
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            
            line.move_id = move
        
        return True
    
    def action_post_depreciation(self):
        """Post depreciation entry"""
        for line in self:
            if not line.move_id:
                line.create_move()
            elif line.move_id.state == 'draft':
                line.move_id.action_post()
        
        return True
    
    def action_cancel_depreciation(self):
        """Cancel depreciation entry"""
        for line in self:
            if line.move_id:
                if line.move_id.state == 'posted':
                    line.move_id.button_cancel()
                line.move_id.unlink()
        
        return True
    
    def unlink(self):
        for line in self:
            if line.move_id:
                raise UserError(_('You cannot delete a depreciation line that has a journal entry.'))
        return super().unlink()