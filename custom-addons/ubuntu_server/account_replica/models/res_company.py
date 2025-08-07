# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    # ==== Fiscal and Legal ====
    fiscalyear_last_day = fields.Integer(string='Last Day', default=31, required=True)
    fiscalyear_last_month = fields.Selection([
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ], string='Last Month', default=12, required=True)
    
    period_lock_date = fields.Date(string="Lock Date for Non-Advisers",
                                  help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(string="Lock Date",
                                      help="No users, including Advisers, can edit accounts prior to and inclusive of this date. Use it for fiscal year locking for example.")
    
    # ==== Default Accounts ====
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template',
                                       help="The chart template for the company.")
    bank_account_code_prefix = fields.Char(string='Bank Accounts Prefix', size=32)
    cash_account_code_prefix = fields.Char(string='Cash Accounts Prefix', size=32)
    code_digits = fields.Integer(string='# of Digits', default=6, help="No. of Digits to use for account code")
    
    # Transfer Account
    transfer_account_id = fields.Many2one('account.account',
                                         domain="[('internal_type', '=', 'liquidity'), ('company_id', '=', id)]",
                                         string="Inter-Banks Transfer Account",
                                         help="Intermediary account used when moving money from a liquidity account to another")
    
    # ==== Default Journals ====
    currency_exchange_journal_id = fields.Many2one('account.journal',
                                                   string="Exchange Gain or Loss Journal",
                                                   domain="[('type', '=', 'general'), ('company_id', '=', id)]")
    
    # ==== Income/Expense Accounts ====
    income_currency_exchange_account_id = fields.Many2one('account.account',
                                                         string="Gain Exchange Rate Account",
                                                         domain="[('internal_type', '=', 'other'), ('company_id', '=', id)]")
    expense_currency_exchange_account_id = fields.Many2one('account.account',
                                                          string="Loss Exchange Rate Account", 
                                                          domain="[('internal_type', '=', 'other'), ('company_id', '=', id)]")
    
    # ==== Outstanding Payments ====
    account_journal_payment_debit_account_id = fields.Many2one('account.account',
                                                              string="Outstanding Receipts Account",
                                                              domain="[('internal_type', 'in', ('other', 'liquidity')), ('company_id', '=', id)]")
    account_journal_payment_credit_account_id = fields.Many2one('account.account',
                                                               string="Outstanding Payments Account",
                                                               domain="[('internal_type', 'in', ('other', 'liquidity')), ('company_id', '=', id)]")
    
    # ==== Default Taxes ====
    account_sale_tax_id = fields.Many2one('account.tax', string="Default Sales Tax",
                                         domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', id)]")
    account_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax",
                                             domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', id)]")
    
    # ==== Tax Configuration ====
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
    ], string='Tax Calculation Rounding Method', default='round_per_line',
       help="If you select 'Round per Line': for each tax, the tax amount will first be computed and rounded per line and then aggregated. If you select 'Round Globally': for each tax, the tax amount will be computed for each line, then aggregated and finally rounded.")
    
    tax_exigibility = fields.Boolean(string='Use Cash Basis', default=False)
    
    # ==== Account Storno ====
    account_storno = fields.Boolean(string='Storno Accounting', default=False,
                                   help="Enables the Storno accounting method, where negative amounts are displayed in red and prefixed with a minus sign instead of being moved to the opposite column.")
    
    # ==== Fiscal Country ====
    account_fiscal_country_id = fields.Many2one('res.country', string="Fiscal Country",
                                               help="The country to use the fiscal position accounts/taxes defined on the fiscal positions.")
    
    # ==== Invoice Configuration ====
    invoice_is_email = fields.Boolean('Send by Email', default=True,
                                     help="Allow sending invoices by email.")
    invoice_is_print = fields.Boolean('Print', default=True,
                                     help="Allow printing invoices.")
    
    # ==== QR Code Configuration ====
    qr_code = fields.Boolean(string='Display QR Code on Invoices', default=False)
    
    # ==== Account Opening ====
    account_opening_move_id = fields.Many2one('account.move', string="Opening Journal Entry",
                                             copy=False, readonly=True,
                                             help="The journal entry containing the initial balance of all this company's accounts.")
    account_opening_date = fields.Date(string="Opening Date")
    
    # ==== Fiscal Position ====
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    
    # ==== Analytic ====
    analytic_plan_id = fields.Many2one('account.analytic.plan', string='Default Analytic Plan')
    
    # ==== Multi-currency ====
    currency_interval_unit = fields.Selection([
        ('manually', 'Manually'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Interval Unit', default='manually')
    currency_provider = fields.Selection([
        ('ecb', 'European Central Bank'),
        ('fixer', 'Fixer.io'),
        ('manual', 'Manual'),
    ], string='Service Provider', default='manual')
    currency_next_execution_date = fields.Date(string="Next Execution Date")

    # ==== Constraints ====
    @api.constrains('fiscalyear_last_day', 'fiscalyear_last_month')
    def _check_fiscalyear(self):
        """Check fiscal year date constraints."""
        for company in self:
            if company.fiscalyear_last_day < 1 or company.fiscalyear_last_day > 31:
                raise ValidationError(_('Fiscal year last day must be between 1 and 31.'))
            
            # Check if day exists in the selected month  
            import calendar
            try:
                max_day = calendar.monthrange(2020, company.fiscalyear_last_month)[1]  # Using 2020 as it's not leap year
                if company.fiscalyear_last_day > max_day:
                    raise ValidationError(_('Day %s does not exist in month %s.') % (company.fiscalyear_last_day, company.fiscalyear_last_month))
            except ValueError:
                raise ValidationError(_('Invalid fiscal year end date.'))

    @api.constrains('period_lock_date', 'fiscalyear_lock_date')
    def _check_lock_dates(self):
        """Check lock date constraints."""
        for company in self:
            if company.period_lock_date and company.fiscalyear_lock_date:
                if company.period_lock_date > company.fiscalyear_lock_date:
                    raise ValidationError(_('Period lock date cannot be later than fiscal year lock date.'))

    # ==== Business methods ====
    def compute_fiscalyear_dates(self, date):
        """Compute fiscal year dates for a given date."""
        self.ensure_one()
        
        # Get the fiscal year end day/month
        last_month = self.fiscalyear_last_month
        last_day = self.fiscalyear_last_day
        
        # Determine fiscal year end
        try:
            fiscal_year_end = date.replace(month=last_month, day=last_day)
        except ValueError:
            # Handle case where day doesn't exist in month (e.g., Feb 31)
            import calendar
            last_day_of_month = calendar.monthrange(date.year, last_month)[1]
            fiscal_year_end = date.replace(month=last_month, day=min(last_day, last_day_of_month))
        
        if date <= fiscal_year_end:
            return {
                'date_from': fiscal_year_end.replace(year=fiscal_year_end.year - 1) + relativedelta(days=1),
                'date_to': fiscal_year_end,
            }
        else:
            return {
                'date_from': fiscal_year_end + relativedelta(days=1),
                'date_to': fiscal_year_end.replace(year=fiscal_year_end.year + 1),
            }

    def get_new_account_code(self, current_code, old_prefix, new_prefix):
        """Generate new account code when changing prefix."""
        if not current_code or not old_prefix:
            return current_code
            
        if current_code.startswith(old_prefix):
            return current_code.replace(old_prefix, new_prefix, 1)
        return current_code

    def get_chart_of_accounts_or_fail(self):
        """Get chart of accounts for company or raise error."""
        account = self.env['account.account'].search([('company_id', '=', self.id)], limit=1)
        if not account:
            action = self.env.ref('account_replica.action_account_config')
            msg = _(
                "No chart of accounts found for company %s.\n"
                "Please configure a chart of accounts before proceeding."
            ) % self.name
            raise UserError(msg)
        return True

    def create_op_move_if_non_existing(self):
        """Create opening move if it doesn't exist."""
        if not self.account_opening_move_id:
            opening_vals = self._get_opening_move_vals()
            if opening_vals:
                move = self.env['account.move'].create(opening_vals)
                self.account_opening_move_id = move
        return self.account_opening_move_id

    def _get_opening_move_vals(self):
        """Get values for opening move."""
        if not self.account_opening_date:
            return False
            
        return {
            'ref': _('Opening Balance'),
            'company_id': self.id,
            'journal_id': self._get_default_misc_journal().id,
            'date': self.account_opening_date,
            'line_ids': [],  # Lines would be computed based on existing balances
        }

    def _get_default_misc_journal(self):
        """Get default miscellaneous journal."""
        journal = self.env['account.journal'].search([
            ('company_id', '=', self.id),
            ('type', '=', 'general'),
        ], limit=1)
        
        if not journal:
            # Create a default misc journal
            journal = self.env['account.journal'].create({
                'name': _('Miscellaneous Operations'),
                'code': 'MISC',
                'type': 'general',
                'company_id': self.id,
            })
        
        return journal

    def opening_move_posted(self):
        """Check if opening move is posted."""
        return self.account_opening_move_id and self.account_opening_move_id.state == 'posted'

    def get_unaffected_earnings_account(self):
        """Get unaffected earnings account."""
        unaffected_earnings_type = self.env.ref('account_replica.data_unaffected_earnings')
        account = self.env['account.account'].search([
            ('user_type_id', '=', unaffected_earnings_type.id), 
            ('company_id', '=', self.id)
        ], limit=1)
        return account

    def get_currency_rates_company(self):
        """Get currency rates for this company."""
        return self.env['res.currency.rate'].search([
            ('company_id', '=', self.id)
        ])

    def update_currency_rates(self):
        """Update currency rates based on provider."""
        if self.currency_provider == 'manual':
            return True
            
        # Implementation would depend on the selected provider
        # This would typically involve API calls to currency services
        pass

    # ==== Onchange methods ====
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """Update fiscal country when country changes."""
        if self.country_id:
            self.account_fiscal_country_id = self.country_id

    @api.onchange('chart_template_id')
    def _onchange_chart_template_id(self):
        """Update accounts when chart template changes."""
        if self.chart_template_id:
            # Set account code digits
            self.code_digits = self.chart_template_id.code_digits
            
            # Set currency if defined in template
            if self.chart_template_id.currency_id:
                self.currency_id = self.chart_template_id.currency_id

    # ==== Setup methods ====
    def _setup_accounting(self):
        """Setup basic accounting configuration for company."""
        # Create basic journals
        self._create_basic_journals()
        
        # Set default accounts
        self._set_default_accounts()
        
        # Create default taxes
        self._create_default_taxes()

    def _create_basic_journals(self):
        """Create basic journals for the company."""
        journals_data = [
            {'name': _('Customer Invoices'), 'code': 'INV', 'type': 'sale'},
            {'name': _('Vendor Bills'), 'code': 'BILL', 'type': 'purchase'},
            {'name': _('Miscellaneous Operations'), 'code': 'MISC', 'type': 'general'},
            {'name': _('Exchange Rate Differences'), 'code': 'EXCH', 'type': 'general'},
        ]
        
        for journal_data in journals_data:
            journal_data['company_id'] = self.id
            existing = self.env['account.journal'].search([
                ('code', '=', journal_data['code']),
                ('company_id', '=', self.id)
            ])
            if not existing:
                self.env['account.journal'].create(journal_data)

    def _set_default_accounts(self):
        """Set default accounts on company."""
        # This would typically be called when installing chart of accounts
        pass

    def _create_default_taxes(self):
        """Create default taxes for the company."""
        # This would create basic tax configurations
        pass

    # ==== Multi-company methods ====
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to setup accounting."""
        companies = super().create(vals_list)
        
        for i, company in enumerate(companies):
            vals = vals_list[i] if isinstance(vals_list, list) else vals_list
            # Setup basic accounting structure
            if not vals.get('chart_template_id'):
                company._setup_accounting()
        
        return companies

    def write(self, vals):
        """Override write to handle account updates."""
        # Handle bank/cash account prefix changes
        if 'bank_account_code_prefix' in vals or 'cash_account_code_prefix' in vals:
            self._update_account_codes(vals)
        
        return super().write(vals)

    def _update_account_codes(self, vals):
        """Update account codes when prefixes change."""
        for company in self:
            if 'bank_account_code_prefix' in vals:
                old_prefix = company.bank_account_code_prefix
                new_prefix = vals['bank_account_code_prefix']
                if old_prefix != new_prefix:
                    bank_accounts = company.env['account.account'].search([
                        ('code', 'like', f'{old_prefix}%'),
                        ('internal_type', '=', 'liquidity'),
                        ('company_id', '=', company.id)
                    ])
                    for account in bank_accounts:
                        new_code = company.get_new_account_code(account.code, old_prefix, new_prefix)
                        if new_code != account.code:
                            account.code = new_code

    @api.model
    def _cron_update_currency_rates(self):
        """Cron method to update currency rates."""
        companies = self.search([
            ('currency_interval_unit', '!=', 'manually'),
            ('currency_next_execution_date', '<=', fields.Date.today())
        ])
        
        for company in companies:
            company.update_currency_rates()
            
            # Set next execution date
            if company.currency_interval_unit == 'daily':
                company.currency_next_execution_date = fields.Date.today() + relativedelta(days=1)
            elif company.currency_interval_unit == 'weekly':
                company.currency_next_execution_date = fields.Date.today() + relativedelta(weeks=1)
            elif company.currency_interval_unit == 'monthly':
                company.currency_next_execution_date = fields.Date.today() + relativedelta(months=1)