# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class MozFiscalPeriod(models.Model):
    """Fiscal Period for Mozambican accounting"""
    
    _name = 'moz.fiscal.period'
    _description = 'Mozambican Fiscal Period'
    _order = 'date_from'
    _rec_name = 'display_name'
    
    # Basic Fields
    name = fields.Char(
        string='Period Name',
        required=True,
        index=True,
        help='Name of the fiscal period'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        index=True,
        help='Unique code for the period'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Date Range
    date_from = fields.Date(
        string='Start Date',
        required=True,
        index=True,
        help='Start date of the period'
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True,
        index=True,
        help='End date of the period'
    )
    
    # Fiscal Year
    fiscal_year_id = fields.Many2one(
        'moz.fiscal.year',
        string='Fiscal Year',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status',
       default='draft',
       required=True,
       tracking=True,
       help='Draft: Period is being configured\n'
            'Open: Period is active for transactions\n'
            'Closed: Period is closed, no more transactions allowed'
    )
    
    # Special Period
    special = fields.Boolean(
        string='Special Period',
        default=False,
        help='Special period for opening/closing entries'
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
    
    draft_move_count = fields.Integer(
        string='Draft Entries',
        compute='_compute_statistics'
    )
    
    # Balances
    total_debit = fields.Monetary(
        string='Total Debit',
        compute='_compute_balances',
        currency_field='company_currency_id'
    )
    
    total_credit = fields.Monetary(
        string='Total Credit',
        compute='_compute_balances',
        currency_field='company_currency_id'
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )
    
    # Mozambican Specific
    vat_declaration_done = fields.Boolean(
        string='VAT Declaration Done',
        default=False,
        help='VAT declaration has been submitted for this period'
    )
    
    vat_declaration_date = fields.Date(
        string='VAT Declaration Date',
        help='Date when VAT was declared'
    )
    
    irps_declaration_done = fields.Boolean(
        string='IRPS Declaration Done',
        default=False,
        help='IRPS declaration has been submitted for this period'
    )
    
    irps_declaration_date = fields.Date(
        string='IRPS Declaration Date',
        help='Date when IRPS was declared'
    )
    
    # Computed Fields
    @api.depends('name', 'fiscal_year_id.name')
    def _compute_display_name(self):
        for period in self:
            if period.fiscal_year_id:
                period.display_name = f"{period.fiscal_year_id.name} - {period.name}"
            else:
                period.display_name = period.name
    
    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_statistics(self):
        for period in self:
            domain = [
                ('date', '>=', period.date_from),
                ('date', '<=', period.date_to),
                ('company_id', '=', period.company_id.id)
            ]
            
            period.move_count = self.env['moz.move'].search_count(domain)
            period.posted_move_count = self.env['moz.move'].search_count(
                domain + [('state', '=', 'posted')]
            )
            period.draft_move_count = self.env['moz.move'].search_count(
                domain + [('state', '=', 'draft')]
            )
    
    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_balances(self):
        for period in self:
            move_lines = self.env['moz.move.line'].search([
                ('date', '>=', period.date_from),
                ('date', '<=', period.date_to),
                ('company_id', '=', period.company_id.id),
                ('parent_state', '=', 'posted')
            ])
            
            period.total_debit = sum(move_lines.mapped('debit'))
            period.total_credit = sum(move_lines.mapped('credit'))
    
    # Constraints
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for period in self:
            if period.date_from > period.date_to:
                raise ValidationError(
                    _("Start date must be before or equal to end date!")
                )
            
            # Check if dates are within fiscal year
            if period.fiscal_year_id:
                if (period.date_from < period.fiscal_year_id.date_from or 
                    period.date_to > period.fiscal_year_id.date_to):
                    raise ValidationError(
                        _("Period dates must be within fiscal year dates!")
                    )
            
            # Check for overlapping periods in same fiscal year
            if not period.special:
                overlapping = self.search([
                    ('fiscal_year_id', '=', period.fiscal_year_id.id),
                    ('id', '!=', period.id),
                    ('special', '=', False),
                    '|',
                    '&', ('date_from', '<=', period.date_from), ('date_to', '>=', period.date_from),
                    '&', ('date_from', '<=', period.date_to), ('date_to', '>=', period.date_to)
                ])
                
                if overlapping:
                    raise ValidationError(
                        _("Period dates overlap with %s") % overlapping[0].name
                    )
    
    @api.constrains('state', 'move_count')
    def _check_can_close(self):
        for period in self:
            if period.state == 'closed' and period.draft_move_count > 0:
                raise ValidationError(
                    _("Cannot close period %s with draft entries!") % period.name
                )
    
    @api.constrains('code', 'company_id')
    def _check_code_unique(self):
        for period in self:
            duplicate = self.search([
                ('code', '=', period.code),
                ('company_id', '=', period.company_id.id),
                ('id', '!=', period.id)
            ])
            
            if duplicate:
                raise ValidationError(
                    _("Period code '%s' already exists!") % period.code
                )
    
    # CRUD Methods
    def unlink(self):
        for period in self:
            if period.state != 'draft':
                raise UserError(
                    _("Cannot delete period %s in %s state!") % 
                    (period.name, period.state)
                )
            
            if period.move_count > 0:
                raise UserError(
                    _("Cannot delete period %s with existing entries!") % period.name
                )
        
        return super().unlink()
    
    # Business Methods
    def action_open(self):
        """Open period for transactions"""
        for period in self:
            if period.state != 'draft':
                continue
            
            # Check if fiscal year is open
            if period.fiscal_year_id.state != 'open':
                raise UserError(
                    _("Cannot open period in fiscal year that is not open!")
                )
            
            period.write({'state': 'open'})
            
            _logger.info("Period %s opened", period.name)
        
        return True
    
    def action_close(self):
        """Close period"""
        for period in self:
            if period.state != 'open':
                continue
            
            # Check for draft entries
            if period.draft_move_count > 0:
                raise UserError(
                    _("Cannot close period %s with %d draft entries!") % 
                    (period.name, period.draft_move_count)
                )
            
            # Check tax declarations
            if not period.special:
                if not period.vat_declaration_done:
                    raise UserError(
                        _("Cannot close period %s without VAT declaration!") % period.name
                    )
                
                if not period.irps_declaration_done:
                    # This is a warning, not blocking
                    _logger.warning("Closing period %s without IRPS declaration", period.name)
            
            period.write({'state': 'closed'})
            
            _logger.info("Period %s closed", period.name)
        
        return True
    
    def action_draft(self):
        """Return period to draft"""
        for period in self:
            if period.state == 'closed':
                # Check if fiscal year allows reopening
                if period.fiscal_year_id.state == 'closed':
                    raise UserError(
                        _("Cannot reopen period in closed fiscal year!")
                    )
                
                # Check if there are entries in next periods
                next_period = self.search([
                    ('fiscal_year_id', '=', period.fiscal_year_id.id),
                    ('date_from', '>', period.date_to),
                    ('move_count', '>', 0)
                ], limit=1)
                
                if next_period:
                    raise UserError(
                        _("Cannot reopen period %s as subsequent periods have entries!") % 
                        period.name
                    )
            
            if period.posted_move_count > 0:
                raise UserError(
                    _("Cannot return period %s to draft with posted entries!") % 
                    period.name
                )
            
            period.write({'state': 'draft'})
        
        return True
    
    def action_view_entries(self):
        """View all entries for this period"""
        self.ensure_one()
        
        return {
            'name': _('Journal Entries - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move',
            'view_mode': 'tree,form',
            'domain': [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {
                'default_date': self.date_from,
                'default_company_id': self.company_id.id,
            }
        }
    
    def action_declare_vat(self):
        """Open VAT declaration wizard"""
        self.ensure_one()
        
        if self.state != 'open':
            raise UserError(
                _("Can only declare VAT for open periods!")
            )
        
        return {
            'name': _('VAT Declaration'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.vat.declaration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_period_id': self.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }
    
    def action_declare_irps(self):
        """Open IRPS declaration wizard"""
        self.ensure_one()
        
        if self.state != 'open':
            raise UserError(
                _("Can only declare IRPS for open periods!")
            )
        
        return {
            'name': _('IRPS Declaration'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.irps.declaration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_period_id': self.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }
    
    def action_period_close_wizard(self):
        """Open period closing wizard"""
        self.ensure_one()
        
        if self.state != 'open':
            raise UserError(
                _("Can only run closing process for open periods!")
            )
        
        return {
            'name': _('Close Period'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.period.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_period_id': self.id,
            }
        }
    
    @api.model
    def find_period(self, date_val: date, company_id: Optional[int] = None,
                   special: bool = False) -> Optional['MozFiscalPeriod']:
        """Find period for a given date"""
        if not company_id:
            company_id = self.env.company.id
        
        domain = [
            ('date_from', '<=', date_val),
            ('date_to', '>=', date_val),
            ('company_id', '=', company_id),
            ('special', '=', special),
            ('state', '!=', 'closed')
        ]
        
        period = self.search(domain, limit=1)
        
        return period if period else None
    
    @api.model
    def get_current_period(self) -> Optional['MozFiscalPeriod']:
        """Get current period"""
        today = fields.Date.today()
        return self.find_period(today)
    
    def get_period_balance_data(self) -> Dict:
        """Get balance sheet data for this period"""
        self.ensure_one()
        
        # Get all posted move lines for the period
        move_lines = self.env['moz.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted')
        ])
        
        # Group by account type
        balance_data = {
            'assets': {},
            'liabilities': {},
            'equity': {},
            'income': {},
            'expenses': {}
        }
        
        for line in move_lines:
            account = line.account_id
            balance = line.balance
            
            # Determine category
            if account.internal_group == 'asset':
                category = 'assets'
            elif account.internal_group == 'liability':
                category = 'liabilities'
            elif account.internal_group == 'equity':
                category = 'equity'
            elif account.internal_group == 'income':
                category = 'income'
            elif account.internal_group == 'expense':
                category = 'expenses'
            else:
                continue
            
            # Add to balance data
            if account.code not in balance_data[category]:
                balance_data[category][account.code] = {
                    'account': account.display_name,
                    'balance': 0
                }
            
            balance_data[category][account.code]['balance'] += balance
        
        return balance_data
    
    def mark_vat_declared(self):
        """Mark VAT as declared for this period"""
        self.ensure_one()
        
        self.write({
            'vat_declaration_done': True,
            'vat_declaration_date': fields.Date.today()
        })
        
        _logger.info("VAT marked as declared for period %s", self.name)
    
    def mark_irps_declared(self):
        """Mark IRPS as declared for this period"""
        self.ensure_one()
        
        self.write({
            'irps_declaration_done': True,
            'irps_declaration_date': fields.Date.today()
        })
        
        _logger.info("IRPS marked as declared for period %s", self.name)