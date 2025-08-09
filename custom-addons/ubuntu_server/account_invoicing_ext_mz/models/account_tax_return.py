from odoo import models, fields, api
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class AccountTaxReturn(models.TransientModel):
    _name = 'account.tax.return.report'
    _description = 'Tax Return Report'
    
    @api.model
    def get_tax_return_data(self, date_from=None, date_to=None, comparison=None, company_id=None):
        """Get tax return data for the report"""
        try:
            if not company_id:
                company_id = self.env.company.id
            
            # Set default dates if not provided
            if not date_to:
                date_to = fields.Date.today()
            else:
                if isinstance(date_to, str):
                    date_to = fields.Date.from_string(date_to)
                    
            if not date_from:
                # Get first day of the month for date_to
                date_from = date(date_to.year, date_to.month, 1)
            else:
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
            
            # Build domain for tax lines
            domain = [
                ('company_id', '=', company_id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                '|',
                ('tax_line_id', '!=', False),
                ('tax_ids', '!=', False)
            ]
            
            # Get all move lines with tax information
            move_lines = self.env['account.move.line'].search(domain)
            
            # Get all taxes
            taxes = self.env['account.tax'].search([('company_id', '=', company_id)])
            
            # Define tax sections (adapting Indian tax sections to Mozambican context)
            tax_sections = [
                {
                    'id': 'vat_sales',
                    'code': 'IVA Vendas',
                    'name': 'IVA sobre Vendas',
                    'description': 'Imposto sobre o Valor Acrescentado - Vendas',
                    'has_info': True
                },
                {
                    'id': 'vat_purchases',
                    'code': 'IVA Compras',
                    'name': 'IVA sobre Compras',
                    'description': 'Imposto sobre o Valor Acrescentado - Compras',
                    'has_info': True
                },
                {
                    'id': 'irps',
                    'code': 'IRPS',
                    'name': 'Imposto sobre o Rendimento de Pessoas Singulares',
                    'description': 'Retenção na fonte sobre salários',
                    'has_info': True
                },
                {
                    'id': 'irpc',
                    'code': 'IRPC',
                    'name': 'Imposto sobre o Rendimento de Pessoas Colectivas',
                    'description': 'Imposto sobre lucros empresariais',
                    'has_info': True
                },
                {
                    'id': 'inss',
                    'code': 'INSS',
                    'name': 'Instituto Nacional de Segurança Social',
                    'description': 'Contribuições para segurança social',
                    'has_info': True
                },
                {
                    'id': 'import_duties',
                    'code': 'Direitos Aduaneiros',
                    'name': 'Direitos de Importação',
                    'description': 'Impostos sobre importações',
                    'has_info': True
                },
                {
                    'id': 'excise_tax',
                    'code': 'ICE',
                    'name': 'Imposto sobre Consumos Específicos',
                    'description': 'Impostos sobre produtos específicos (álcool, tabaco, etc.)',
                    'has_info': True
                },
                {
                    'id': 'stamp_duty',
                    'code': 'Imposto de Selo',
                    'name': 'Imposto de Selo',
                    'description': 'Imposto sobre documentos e transações',
                    'has_info': True
                },
                {
                    'id': 'property_tax',
                    'code': 'IPRA',
                    'name': 'Imposto Predial Autárquico',
                    'description': 'Imposto sobre propriedades',
                    'has_info': True
                },
                {
                    'id': 'vehicle_tax',
                    'code': 'IPV',
                    'name': 'Imposto sobre Veículos',
                    'description': 'Imposto anual sobre veículos',
                    'has_info': True
                },
                {
                    'id': 'mining_tax',
                    'code': 'Imposto Mineiro',
                    'name': 'Impostos sobre Produção Mineira',
                    'description': 'Impostos e royalties sobre mineração',
                    'has_info': True
                },
                {
                    'id': 'tourism_tax',
                    'code': 'Taxa Turismo',
                    'name': 'Taxa de Turismo',
                    'description': 'Taxa sobre serviços turísticos',
                    'has_info': True
                },
                {
                    'id': 'municipal_taxes',
                    'code': 'Taxas Municipais',
                    'name': 'Taxas e Licenças Municipais',
                    'description': 'Taxas diversas municipais',
                    'has_info': True
                },
                {
                    'id': 'other_taxes',
                    'code': 'Outros',
                    'name': 'Outros Impostos e Taxas',
                    'description': 'Outros impostos não classificados',
                    'has_info': True
                }
            ]
            
            # Calculate tax amounts for each section
            tax_lines = []
            
            for section in tax_sections:
                # Calculate amount based on tax type
                amount = 0.0
                
                if section['id'] == 'vat_sales':
                    # IVA on sales (output VAT)
                    vat_sales_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        l.tax_line_id.type_tax_use == 'sale' and
                        'IVA' in (l.tax_line_id.name or '') or 'VAT' in (l.tax_line_id.name or '')
                    )
                    amount = abs(sum(vat_sales_lines.mapped('balance')))
                
                elif section['id'] == 'vat_purchases':
                    # IVA on purchases (input VAT)
                    vat_purchase_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        l.tax_line_id.type_tax_use == 'purchase' and
                        'IVA' in (l.tax_line_id.name or '') or 'VAT' in (l.tax_line_id.name or '')
                    )
                    amount = sum(vat_purchase_lines.mapped('balance'))
                
                elif section['id'] == 'irps':
                    # Payroll taxes
                    irps_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        ('IRPS' in (l.tax_line_id.name or '') or 'Salary' in (l.tax_line_id.name or ''))
                    )
                    amount = abs(sum(irps_lines.mapped('balance')))
                
                elif section['id'] == 'irpc':
                    # Corporate income tax
                    irpc_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        ('IRPC' in (l.tax_line_id.name or '') or 'Corporate' in (l.tax_line_id.name or ''))
                    )
                    amount = abs(sum(irpc_lines.mapped('balance')))
                
                elif section['id'] == 'inss':
                    # Social security
                    inss_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        ('INSS' in (l.tax_line_id.name or '') or 'Social' in (l.tax_line_id.name or ''))
                    )
                    amount = abs(sum(inss_lines.mapped('balance')))
                
                else:
                    # For other tax types, look for matching names
                    other_lines = move_lines.filtered(
                        lambda l: l.tax_line_id and 
                        section['code'].lower() in (l.tax_line_id.name or '').lower()
                    )
                    amount = abs(sum(other_lines.mapped('balance')))
                
                tax_lines.append({
                    'id': section['id'],
                    'code': section['code'],
                    'name': f"{section['code']}: {section['name']}",
                    'description': section['description'],
                    'amount': amount,
                    'has_info': section['has_info']
                })
            
            # Add total line
            total_taxes = sum(line['amount'] for line in tax_lines)
            
            # Format dates for return
            if date_from and isinstance(date_from, str):
                date_from_str = date_from
            elif date_from:
                date_from_str = date_from.strftime('%Y-%m-%d')
            else:
                date_from_str = ''
                
            if date_to and isinstance(date_to, str):
                date_to_str = date_to
            elif date_to:
                date_to_str = date_to.strftime('%Y-%m-%d')
            else:
                date_to_str = ''
            
            return {
                'lines': tax_lines,
                'total_taxes': total_taxes,
                'company_name': self.env.company.name,
                'currency_symbol': 'MZN',
                'date_from': date_from_str,
                'date_to': date_to_str
            }
            
        except Exception as e:
            _logger.error(f"Error getting tax return data: {str(e)}")
            return {
                'lines': [],
                'total_taxes': 0.0,
                'company_name': '',
                'currency_symbol': 'MZN',
                'date_from': '',
                'date_to': '',
                'error': str(e)
            }