# Partner Ledger Implementation

## Summary
Successfully implemented the Partner Ledger report for the Odoo 17 accounting module following the same pattern as other financial reports.

## Completed Features

### 1. Backend Model (account_partner_ledger.py)
- Created TransientModel for data processing
- Groups accounting entries by partner
- Calculates debit, credit, and balance for each partner
- Supports filtering by:
  - Date range
  - Account type (all/receivable/payable)
  - Specific partners
  - Posted/unposted entries
- Shows cumulative balance for each line

### 2. Frontend Component (partner_ledger.js/xml)
- OWL 2.0 reactive component
- Expandable partner rows showing detailed moves
- Date range filters with date pickers
- Account type dropdown (All Partners/Customers/Vendors)
- Partner filter button
- Posted Entries toggle
- Export to PDF and XLSX buttons
- Currency display in MT (Metical)

### 3. Visual Design
- Full-width layout matching Enterprise version
- Header background color: #c9cccf
- Expandable rows with caret icons
- Hierarchical display with indented detail rows
- Partner header with totals
- Grand total row at bottom
- Negative balances shown in parentheses

### 4. Integration
- Added to Reporting > Partner Reports menu
- Security access rules configured
- Assets properly registered in __manifest__.py
- SCSS styles integrated with other financial reports

## Key Technical Details

### Model Structure
```python
class AccountPartnerLedger(models.TransientModel):
    _name = 'account.partner.ledger.report'
    
    def get_partner_ledger_data(self, date_from=None, date_to=None, 
                                partner_ids=None, account_type='all', 
                                posted_entries=True, company_id=None):
        # Groups move lines by partner
        # Calculates cumulative balances
```

### JavaScript Component
```javascript
export class PartnerLedgerReport extends Component {
    static template = "account_invoicing_ext_mz.PartnerLedgerReport";
    
    // Manages expandable state for partners
    // Handles filtering and data loading
    // Format currency in MT (Metical)
}
```

### Template Structure
- Control panel with filters and export buttons
- Main table with expandable partner rows
- Each partner shows:
  - Header with name and totals
  - Expandable detail lines with date, reference, account, amounts
  - Cumulative balance for each line

## Testing Instructions

1. Navigate to Accounting > Reporting > Partner Reports > Partner Ledger
2. Verify expandable partner rows work correctly
3. Test date range filters
4. Test account type filtering (All/Customers/Vendors)
5. Toggle Posted Entries on/off
6. Verify totals calculation
7. Test export to PDF/XLSX functionality

## Files Created

### New Files
- `models/account_partner_ledger.py`
- `static/src/components/partner_ledger/partner_ledger.js`
- `static/src/components/partner_ledger/partner_ledger.xml`

### Modified Files
- `models/__init__.py` - Added partner ledger import
- `views/account_menu_ext.xml` - Updated menu to use client action
- `security/ir.model.access.csv` - Added access rules
- `__manifest__.py` - Added assets
- `static/src/scss/financial_reports.scss` - Added styles

## Notes
- All partner rows are expandable
- Currency set to MT (Metical) for Mozambique
- Full-width layout maintained with Odoo header intact
- 100% functionality preserved from previous implementations
- Follows same pattern as other financial reports