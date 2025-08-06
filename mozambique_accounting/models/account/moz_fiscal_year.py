# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MozFiscalYear(models.Model):
    """Fiscal Year for Mozambican accounting"""
    
    _name = 'moz.fiscal.year'
    _description = 'Mozambican Fiscal Year'
    _order = 'date_from desc'
    _rec_name = 'name'
    
    # Basic Fields
    name = fields.Char(
        string='Fiscal Year',
        required=True,
        index=True,
        help='Name of the fiscal year (e.g., "2024")'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        index=True,
        help='Short code for the fiscal year'
    )
    
    # Date Range
    date_from = fields.Date(
        string='Start Date',
        required=True,
        help='Start date of the fiscal year'
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True,
        help='End date of the fiscal year'
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
       help='Draft: Year is being configured\n'
            'Open: Year is active for transactions\n'
            'Closed: Year is closed, no more transactions allowed'
    )
    
    # Periods
    period_ids = fields.One2many(
        'moz.fiscal.period',
        'fiscal_year_id',
        string='Periods'
    )
    
    period_count = fields.Integer(
        string='Number of Periods',
        compute='_compute_period_count'
    )
    
    # Special Periods
    opening_period_id = fields.Many2one(
        'moz.fiscal.period',
        string='Opening Period',
        help='Special period for opening entries'
    )
    
    closing_period_id = fields.Many2one(
        'moz.fiscal.period',
        string='Closing Period',
        help='Special period for closing entries'
    )
    
    # Statistics
    move_count = fields.Integer(
        string='Number of Entries',
        compute='_compute_move_count'
    )
    
    posted_move_count = fields.Integer(
        string='Posted Entries',
        compute='_compute_move_count'
    )
    
    # Mozambican Specific
    tax_year = fields.Boolean(
        string='Tax Year',
        default=True,
        help='This fiscal year is used for tax reporting'
    )
    
    saft_export_date = fields.Datetime(
        string='Last SAF-T Export',
        readonly=True
    )
    
    # Computed Fields
    @api.depends('period_ids')
    def _compute_period_count(self):
        for year in self:
            year.period_count = len(year.period_ids)
    
    @api.depends('date_from', 'date_to')
    def _compute_move_count(self):
        for year in self:
            domain = [
                ('date', '>=', year.date_from),
                ('date', '<=', year.date_to),
                ('company_id', '=', year.company_id.id)
            ]
            
            year.move_count = self.env['moz.move'].search_count(domain)
            year.posted_move_count = self.env['moz.move'].search_count(
                domain + [('state', '=', 'posted')]
            )
    
    # Constraints
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for year in self:
            if year.date_from >= year.date_to:
                raise ValidationError(
                    _("Start date must be before end date!")
                )
            
            # Check for overlapping years
            overlapping = self.search([
                ('company_id', '=', year.company_id.id),
                ('id', '!=', year.id),
                '|', '|',
                '&', ('date_from', '<=', year.date_from), ('date_to', '>=', year.date_from),
                '&', ('date_from', '<=', year.date_to), ('date_to', '>=', year.date_to),
                '&', ('date_from', '>=', year.date_from), ('date_to', '<=', year.date_to)
            ])
            
            if overlapping:
                raise ValidationError(
                    _("Fiscal year dates overlap with %s") % overlapping[0].name
                )
    
    @api.constrains('state', 'period_ids')
    def _check_periods_state(self):
        for year in self:
            if year.state == 'closed':
                open_periods = year.period_ids.filtered(lambda p: p.state != 'closed')
                if open_periods:
                    raise ValidationError(
                        _("Cannot close fiscal year with open periods!")
                    )
    
    # CRUD Methods
    @api.model
    def create(self, vals):
        year = super().create(vals)
        
        # Auto-create periods if requested
        if self.env.context.get('create_periods'):
            year.create_periods()
        
        return year
    
    def unlink(self):
        for year in self:
            if year.state != 'draft':
                raise UserError(
                    _("Cannot delete fiscal year %s in %s state!") % 
                    (year.name, year.state)
                )
            
            if year.move_count > 0:
                raise UserError(
                    _("Cannot delete fiscal year %s with existing entries!") % year.name
                )
        
        return super().unlink()
    
    # Business Methods
    def action_open(self):
        """Open fiscal year for transactions"""
        for year in self:
            if year.state != 'draft':
                continue
            
            # Check if periods exist
            if not year.period_ids:
                raise UserError(
                    _("Cannot open fiscal year without periods!")
                )
            
            # Open all draft periods
            draft_periods = year.period_ids.filtered(lambda p: p.state == 'draft')
            draft_periods.action_open()
            
            year.write({'state': 'open'})
            
            _logger.info("Fiscal year %s opened", year.name)
        
        return True
    
    def action_close(self):
        """Close fiscal year"""
        for year in self:
            if year.state != 'open':
                continue
            
            # Check for unposted entries
            unposted_moves = self.env['moz.move'].search([
                ('date', '>=', year.date_from),
                ('date', '<=', year.date_to),
                ('company_id', '=', year.company_id.id),
                ('state', '=', 'draft')
            ])
            
            if unposted_moves:
                raise UserError(
                    _("Cannot close fiscal year with %d unposted entries!") % 
                    len(unposted_moves)
                )
            
            # Close all open periods
            open_periods = year.period_ids.filtered(lambda p: p.state == 'open')
            open_periods.action_close()
            
            year.write({'state': 'closed'})
            
            _logger.info("Fiscal year %s closed", year.name)
        
        return True
    
    def action_draft(self):
        """Return fiscal year to draft"""
        for year in self:
            if year.state == 'closed':
                raise UserError(
                    _("Cannot reopen closed fiscal year %s!") % year.name
                )
            
            if year.state == 'open':
                # Check if there are posted entries
                if year.posted_move_count > 0:
                    raise UserError(
                        _("Cannot return fiscal year %s to draft with posted entries!") % 
                        year.name
                    )
                
                year.write({'state': 'draft'})
        
        return True
    
    def create_periods(self, interval: int = 1, period_type: str = 'month'):
        """Create periods for the fiscal year"""
        self.ensure_one()
        
        if self.period_ids:
            raise UserError(
                _("Fiscal year %s already has periods!") % self.name
            )
        
        if self.state != 'draft':
            raise UserError(
                _("Can only create periods for draft fiscal years!")
            )
        
        period_start = self.date_from
        period_number = 1
        
        while period_start < self.date_to:
            # Calculate period end
            if period_type == 'month':
                period_end = period_start + relativedelta(months=interval) - timedelta(days=1)
            elif period_type == 'quarter':
                period_end = period_start + relativedelta(months=3*interval) - timedelta(days=1)
            else:  # year
                period_end = period_start + relativedelta(years=interval) - timedelta(days=1)
            
            # Ensure period doesn't exceed fiscal year
            if period_end > self.date_to:
                period_end = self.date_to
            
            # Create period
            period_name = f"{self.code}/{period_number:02d}"
            
            self.env['moz.fiscal.period'].create({
                'name': period_name,
                'code': f"{self.code}-{period_number:02d}",
                'date_from': period_start,
                'date_to': period_end,
                'fiscal_year_id': self.id,
                'company_id': self.company_id.id,
                'state': 'draft'
            })
            
            # Next period
            period_start = period_end + timedelta(days=1)
            period_number += 1
        
        # Create special periods
        self._create_special_periods()
        
        _logger.info("Created %d periods for fiscal year %s", period_number - 1, self.name)
        
        return True
    
    def _create_special_periods(self):
        """Create opening and closing periods"""
        self.ensure_one()
        
        # Opening period
        opening_period = self.env['moz.fiscal.period'].create({
            'name': f"{self.code}/00 - Opening",
            'code': f"{self.code}-00",
            'date_from': self.date_from,
            'date_to': self.date_from,
            'fiscal_year_id': self.id,
            'company_id': self.company_id.id,
            'special': True,
            'state': 'draft'
        })
        
        self.opening_period_id = opening_period
        
        # Closing period
        closing_period = self.env['moz.fiscal.period'].create({
            'name': f"{self.code}/99 - Closing",
            'code': f"{self.code}-99",
            'date_from': self.date_to,
            'date_to': self.date_to,
            'fiscal_year_id': self.id,
            'company_id': self.company_id.id,
            'special': True,
            'state': 'draft'
        })
        
        self.closing_period_id = closing_period
    
    def action_create_closing_entries(self):
        """Create year-end closing entries"""
        self.ensure_one()
        
        if self.state != 'open':
            raise UserError(
                _("Can only create closing entries for open fiscal years!")
            )
        
        # This would open a wizard for creating closing entries
        return {
            'name': _('Create Closing Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.year.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fiscal_year_id': self.id,
                'default_closing_date': self.date_to,
            }
        }
    
    def action_export_saft(self):
        """Export SAF-T file for this fiscal year"""
        self.ensure_one()
        
        # This would generate the SAF-T XML file
        return {
            'name': _('Export SAF-T'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.saft.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fiscal_year_id': self.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }
    
    def action_view_periods(self):
        """View all periods for this fiscal year"""
        self.ensure_one()
        
        return {
            'name': _('Fiscal Periods'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.fiscal.period',
            'view_mode': 'tree,form',
            'domain': [('fiscal_year_id', '=', self.id)],
            'context': {
                'default_fiscal_year_id': self.id,
                'default_company_id': self.company_id.id,
            }
        }
    
    def action_view_entries(self):
        """View all entries for this fiscal year"""
        self.ensure_one()
        
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.move',
            'view_mode': 'tree,form',
            'domain': [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {
                'default_company_id': self.company_id.id,
            }
        }
    
    @api.model
    def find_fiscal_year(self, date_val: date, company_id: Optional[int] = None) -> Optional['MozFiscalYear']:
        """Find fiscal year for a given date"""
        if not company_id:
            company_id = self.env.company.id
        
        fiscal_year = self.search([
            ('date_from', '<=', date_val),
            ('date_to', '>=', date_val),
            ('company_id', '=', company_id),
            ('state', '!=', 'closed')
        ], limit=1)
        
        return fiscal_year if fiscal_year else None
    
    @api.model
    def get_current_fiscal_year(self) -> Optional['MozFiscalYear']:
        """Get current fiscal year"""
        today = fields.Date.today()
        return self.find_fiscal_year(today)