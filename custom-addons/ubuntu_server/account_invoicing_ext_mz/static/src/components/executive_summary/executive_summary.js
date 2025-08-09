/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ExecutiveSummaryReport extends Component {
    static template = "account_invoicing_ext_mz.ExecutiveSummaryReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            sections: [],
            isLoading: true,
            error: null,
            currencySymbol: 'MZN',
            filters: {
                date_from: null,
                date_to: this.getCurrentYearRange(),
                comparison: null,
                company_id: null,
                posted_entries: true
            },
            unpostedWarning: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getCurrentYearRange() {
        const now = new Date();
        return `${now.getFullYear()}-${now.getFullYear()}`;
    }

    formatDateRange(yearRange) {
        if (!yearRange) return '';
        const parts = yearRange.split('-');
        if (parts.length === 2) {
            return `${parts[0]} - ${parts[1]}`;
        }
        return yearRange;
    }

    async loadReport() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            // Parse year range for date_from and date_to
            let date_from = null;
            let date_to = null;
            
            if (this.state.filters.date_to) {
                const parts = this.state.filters.date_to.split('-');
                if (parts.length === 2) {
                    date_from = `${parts[0]}-01-01`;
                    date_to = `${parts[1]}-12-31`;
                }
            }

            const result = await this.rpc("/web/dataset/call_kw/account.executive.summary.report/get_executive_summary_data", {
                model: "account.executive.summary.report",
                method: "get_executive_summary_data",
                args: [],
                kwargs: {
                    date_from: date_from,
                    date_to: date_to,
                    comparison: this.state.filters.comparison,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.sections = result.sections || [];
            this.state.currencySymbol = result.currency_symbol || 'MZN';
            this.state.unpostedWarning = !this.state.filters.posted_entries;

        } catch (error) {
            console.error("Error loading executive summary:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    formatValue(item) {
        const value = item.value || 0;
        
        if (item.is_percentage) {
            return `${value.toFixed(1)}%`;
        } else if (item.is_days) {
            return value.toFixed(1);
        } else if (item.is_ratio) {
            return value.toFixed(2);
        } else {
            // Format as currency
            const formatted = new Intl.NumberFormat('pt-MZ', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(Math.abs(value));
            return `${this.state.currencySymbol} ${formatted}`;
        }
    }

    getRowClass(item) {
        const classes = [];
        
        // Color coding for values
        if (!item.is_percentage && !item.is_days && !item.is_ratio) {
            if (item.value < 0) {
                classes.push('text-danger');
            }
        }
        
        return classes.join(' ');
    }

    getSectionHeaderClass(section) {
        const colorMap = {
            'cash': '#c9cccf',
            'profitability': '#b8d7e8',
            'balance_sheet': '#b8d7e8',
            'performance': '#c9cccf',
            'position': '#c9cccf'
        };
        
        return colorMap[section.id] || '#e7e8e9';
    }

    async onDateRangeChange(ev) {
        const value = ev.target.value;
        if (value) {
            this.state.filters.date_to = value;
            await this.loadReport();
        }
    }

    async onComparisonClick() {
        // Show comparison options dialog
        console.log("Comparison filter clicked");
    }

    async onPostedEntriesToggle() {
        this.state.filters.posted_entries = !this.state.filters.posted_entries;
        await this.loadReport();
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.executive_summary_report',
                report_file: 'account_invoicing_ext_mz.executive_summary_report',
                data: {
                    sections: this.state.sections,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to PDF:", error);
        }
    }

    async exportToXLSX() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'xlsx',
                report_name: 'account_invoicing_ext_mz.executive_summary_xlsx',
                report_file: 'account_invoicing_ext_mz.executive_summary_xlsx',
                data: {
                    sections: this.state.sections,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showItemDetails(item) {
        // Show item details in a dialog
        console.log("Show details for:", item);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_executive_summary_report", ExecutiveSummaryReport);