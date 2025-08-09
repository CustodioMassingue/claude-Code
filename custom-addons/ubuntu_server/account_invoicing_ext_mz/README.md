# Balance Sheet Implementation for Odoo 17

## Overview
This module extends the Accounting Menu Extras (MZ) with a complete Balance Sheet report implementation similar to Odoo Enterprise, using OWL (Odoo Web Library) components.

## Features Implemented

### 1. **Balance Sheet Report**
- Full hierarchical structure with Assets, Liabilities, and Equity sections
- Expandable/collapsible sections for detailed view
- Real-time data calculation from account moves
- Support for date filtering
- Journal filtering capability
- Comparison mode for period-over-period analysis
- Export to PDF and Excel formats

### 2. **Technical Components**

#### Python Backend
- `account_balance_sheet.py`: Core model for data calculation
- `balance_sheet_controller.py`: HTTP endpoints for AJAX data fetching

#### JavaScript/OWL Frontend
- `balance_sheet.js`: Main OWL component with state management
- `balance_sheet.xml`: QWeb template for UI rendering
- `balance_sheet.scss`: Styling for professional appearance

### 3. **User Interface Features**
- **Date Selection**: Choose any date for balance sheet calculation
- **Journal Filtering**: Select specific journals or all journals
- **Comparison Mode**: Compare with previous periods
- **Analytic Toggle**: Filter by analytic accounts
- **Posted Entries Filter**: Show only posted or include draft entries
- **Export Options**: PDF and Excel export functionality

## Installation Instructions

1. **Update the Module**
   ```bash
   # In Odoo shell or through UI
   # Apps > Update Apps List
   # Search for "Invoicing: Accounting Menu Extras (MZ)"
   # Click Upgrade
   ```

2. **Clear Browser Cache**
   - Clear browser cache to ensure new JavaScript assets are loaded
   - Alternatively, open in incognito/private mode

3. **Access the Balance Sheet**
   - Navigate to: **Accounting > Reporting > Statement Reports > Balance Sheet**

## Usage

### Basic Usage
1. Go to Accounting module
2. Navigate to Reporting > Statement Reports > Balance Sheet
3. The report loads automatically with current date data

### Filtering Options
- **Date**: Click on the date button to select a specific date
- **Journals**: Filter by specific journals using the dropdown
- **Comparison**: Toggle to see period comparisons
- **Posted Entries**: Toggle to include/exclude draft entries

### Exporting
- **PDF Export**: Click the PDF button for a printable version
- **Excel Export**: Click XLSX button for Excel format with full data

## Technical Notes

### Data Structure
The Balance Sheet follows standard accounting principles:
- **Assets = Liabilities + Equity**
- Automatic calculation from account.move.line records
- Real-time aggregation based on account types

### Performance Considerations
- Data is loaded via AJAX for better performance
- Expandable sections load on-demand
- Caching implemented for frequently accessed data

### Customization
To customize account groupings, modify the `get_balance_sheet_data` method in `account_balance_sheet.py`

## Troubleshooting

### Module Not Loading
1. Check that all dependencies are installed (account, analytic, web)
2. Verify file permissions are correct
3. Check Odoo logs for any import errors

### JavaScript Errors
1. Clear browser cache
2. Check browser console for specific errors
3. Ensure Odoo is running in assets debug mode for development

### Data Not Showing
1. Verify user has accounting permissions
2. Check that there are posted journal entries
3. Confirm the selected date range has transactions

## Future Enhancements
- Add drill-down to individual journal entries
- Implement budget comparison
- Add graphical charts for visual analysis
- Include more detailed analytical dimensions
- Add scheduled report generation

## Support
For issues or questions, contact the development team at Tropigalia SA.