# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import csv
import io
import xlrd
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class MozBankStatementImport(models.TransientModel):
    _name = 'moz.bank.statement.import'
    _description = 'Bank Statement Import'
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', '=', 'bank')]"
    )
    
    file_type = fields.Selection([
        ('csv', 'CSV'),
        ('xls', 'Excel'),
        ('ofx', 'OFX'),
        ('mt940', 'MT940'),
    ], string='File Type', required=True, default='csv')
    
    file_data = fields.Binary(
        string='File',
        required=True
    )
    
    filename = fields.Char(
        string='Filename'
    )
    
    date_format = fields.Selection([
        ('%Y-%m-%d', 'YYYY-MM-DD'),
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%d-%m-%Y', 'DD-MM-YYYY'),
    ], string='Date Format', default='%Y-%m-%d', required=True)
    
    encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin1', 'Latin-1'),
        ('cp1252', 'Windows-1252'),
    ], string='Encoding', default='utf-8', required=True)
    
    delimiter = fields.Selection([
        (',', 'Comma'),
        (';', 'Semicolon'),
        ('\t', 'Tab'),
        ('|', 'Pipe'),
    ], string='Delimiter', default=',')
    
    # Column mapping
    date_column = fields.Integer(
        string='Date Column',
        default=0,
        help='Column index for date (0-based)'
    )
    
    description_column = fields.Integer(
        string='Description Column',
        default=1,
        help='Column index for description'
    )
    
    amount_column = fields.Integer(
        string='Amount Column',
        default=2,
        help='Column index for amount'
    )
    
    reference_column = fields.Integer(
        string='Reference Column',
        default=3,
        help='Column index for reference'
    )
    
    balance_column = fields.Integer(
        string='Balance Column',
        default=4,
        help='Column index for balance'
    )
    
    skip_header = fields.Boolean(
        string='Skip Header Row',
        default=True
    )
    
    decimal_separator = fields.Selection([
        ('.', 'Point (.)'),
        (',', 'Comma (,)'),
    ], string='Decimal Separator', default='.')
    
    thousands_separator = fields.Selection([
        (',', 'Comma (,)'),
        ('.', 'Point (.)'),
        (' ', 'Space'),
        ('', 'None'),
    ], string='Thousands Separator', default=',')
    
    def import_file(self):
        """Import the bank statement file"""
        self.ensure_one()
        
        if not self.file_data:
            raise UserError(_('Please select a file to import.'))
        
        # Decode file
        file_content = base64.b64decode(self.file_data)
        
        # Parse based on file type
        if self.file_type == 'csv':
            lines = self._parse_csv(file_content)
        elif self.file_type == 'xls':
            lines = self._parse_excel(file_content)
        elif self.file_type == 'ofx':
            lines = self._parse_ofx(file_content)
        elif self.file_type == 'mt940':
            lines = self._parse_mt940(file_content)
        else:
            raise UserError(_('Unsupported file type.'))
        
        if not lines:
            raise UserError(_('No data found in the file.'))
        
        # Create statement
        statement = self._create_statement(lines)
        
        # Return action to open the statement
        return {
            'name': _('Imported Bank Statement'),
            'type': 'ir.actions.act_window',
            'res_model': 'moz.bank.statement',
            'res_id': statement.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _parse_csv(self, file_content):
        """Parse CSV file"""
        lines = []
        
        try:
            # Decode and create CSV reader
            file_str = file_content.decode(self.encoding)
            reader = csv.reader(io.StringIO(file_str), delimiter=self.delimiter)
            
            # Skip header if needed
            if self.skip_header:
                next(reader)
            
            for row in reader:
                if len(row) <= max(self.date_column, self.description_column, self.amount_column):
                    continue
                
                try:
                    # Parse date
                    date_str = row[self.date_column].strip()
                    date = datetime.strptime(date_str, self.date_format).date()
                    
                    # Parse amount
                    amount_str = row[self.amount_column].strip()
                    amount = self._parse_amount(amount_str)
                    
                    # Get other fields
                    description = row[self.description_column].strip() if self.description_column < len(row) else ''
                    reference = row[self.reference_column].strip() if self.reference_column < len(row) else ''
                    
                    lines.append({
                        'date': date,
                        'name': description,
                        'ref': reference,
                        'amount': amount,
                    })
                    
                except (ValueError, IndexError) as e:
                    _logger.warning(f"Failed to parse row: {row}. Error: {e}")
                    continue
                    
        except Exception as e:
            raise UserError(_('Error parsing CSV file: %s') % str(e))
        
        return lines
    
    def _parse_excel(self, file_content):
        """Parse Excel file"""
        lines = []
        
        try:
            # Open workbook
            workbook = xlrd.open_workbook(file_contents=file_content)
            sheet = workbook.sheet_by_index(0)
            
            # Skip header if needed
            start_row = 1 if self.skip_header else 0
            
            for row_idx in range(start_row, sheet.nrows):
                try:
                    # Parse date
                    date_cell = sheet.cell(row_idx, self.date_column)
                    if date_cell.ctype == xlrd.XL_CELL_DATE:
                        date_tuple = xlrd.xldate_as_tuple(date_cell.value, workbook.datemode)
                        date = datetime(*date_tuple[:3]).date()
                    else:
                        date_str = str(date_cell.value).strip()
                        date = datetime.strptime(date_str, self.date_format).date()
                    
                    # Parse amount
                    amount_cell = sheet.cell(row_idx, self.amount_column)
                    amount = float(amount_cell.value)
                    
                    # Get other fields
                    description = str(sheet.cell(row_idx, self.description_column).value).strip()
                    reference = ''
                    if self.reference_column < sheet.ncols:
                        reference = str(sheet.cell(row_idx, self.reference_column).value).strip()
                    
                    lines.append({
                        'date': date,
                        'name': description,
                        'ref': reference,
                        'amount': amount,
                    })
                    
                except Exception as e:
                    _logger.warning(f"Failed to parse row {row_idx}: {e}")
                    continue
                    
        except Exception as e:
            raise UserError(_('Error parsing Excel file: %s') % str(e))
        
        return lines
    
    def _parse_ofx(self, file_content):
        """Parse OFX file (simplified implementation)"""
        lines = []
        
        try:
            content = file_content.decode('utf-8')
            
            # Simple OFX parsing (should use proper OFX library in production)
            import re
            
            # Find transactions
            trans_pattern = r'<STMTTRN>(.*?)</STMTTRN>'
            transactions = re.findall(trans_pattern, content, re.DOTALL)
            
            for trans in transactions:
                # Extract fields
                date_match = re.search(r'<DTPOSTED>(\d{8})', trans)
                amount_match = re.search(r'<TRNAMT>([-\d.]+)', trans)
                desc_match = re.search(r'<NAME>(.*?)<', trans)
                ref_match = re.search(r'<FITID>(.*?)<', trans)
                
                if date_match and amount_match:
                    date = datetime.strptime(date_match.group(1), '%Y%m%d').date()
                    amount = float(amount_match.group(1))
                    description = desc_match.group(1) if desc_match else 'Transaction'
                    reference = ref_match.group(1) if ref_match else ''
                    
                    lines.append({
                        'date': date,
                        'name': description,
                        'ref': reference,
                        'amount': amount,
                    })
                    
        except Exception as e:
            raise UserError(_('Error parsing OFX file: %s') % str(e))
        
        return lines
    
    def _parse_mt940(self, file_content):
        """Parse MT940 file (simplified implementation)"""
        lines = []
        
        try:
            content = file_content.decode(self.encoding)
            
            # Simple MT940 parsing (should use proper MT940 library in production)
            for line in content.split('\n'):
                if line.startswith(':61:'):
                    # Transaction line
                    parts = line[4:].split()
                    if len(parts) >= 2:
                        date_str = parts[0][:6]
                        date = datetime.strptime('20' + date_str, '%Y%m%d').date()
                        
                        amount_str = parts[1]
                        if amount_str[0] in ['C', 'D']:
                            amount = float(amount_str[1:].replace(',', '.'))
                            if amount_str[0] == 'D':
                                amount = -amount
                        else:
                            amount = float(amount_str.replace(',', '.'))
                        
                        description = ' '.join(parts[2:]) if len(parts) > 2 else 'Transaction'
                        
                        lines.append({
                            'date': date,
                            'name': description,
                            'ref': '',
                            'amount': amount,
                        })
                        
        except Exception as e:
            raise UserError(_('Error parsing MT940 file: %s') % str(e))
        
        return lines
    
    def _parse_amount(self, amount_str):
        """Parse amount string to float"""
        # Remove thousands separator
        if self.thousands_separator:
            amount_str = amount_str.replace(self.thousands_separator, '')
        
        # Replace decimal separator
        if self.decimal_separator == ',':
            amount_str = amount_str.replace(',', '.')
        
        # Parse
        return float(amount_str)
    
    def _create_statement(self, lines):
        """Create bank statement from parsed lines"""
        # Get or calculate starting balance
        last_statement = self.env['moz.bank.statement'].search([
            ('journal_id', '=', self.journal_id.id),
            ('state', '=', 'confirm')
        ], order='date desc', limit=1)
        
        balance_start = last_statement.balance_end_real if last_statement else 0.0
        
        # Create statement
        statement_vals = {
            'journal_id': self.journal_id.id,
            'date': lines[-1]['date'] if lines else fields.Date.today(),
            'balance_start': balance_start,
        }
        
        if lines:
            statement_vals['date_from'] = lines[0]['date']
            statement_vals['date_to'] = lines[-1]['date']
        
        statement = self.env['moz.bank.statement'].create(statement_vals)
        
        # Create lines
        for line_data in lines:
            self.env['moz.bank.statement.line'].create({
                'statement_id': statement.id,
                'date': line_data['date'],
                'name': line_data['name'],
                'ref': line_data.get('ref', ''),
                'amount': line_data['amount'],
            })
        
        # Calculate ending balance
        total_amount = sum(line['amount'] for line in lines)
        statement.balance_end_real = balance_start + total_amount
        
        return statement