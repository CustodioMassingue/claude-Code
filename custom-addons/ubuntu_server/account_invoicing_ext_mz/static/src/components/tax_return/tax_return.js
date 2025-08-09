/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TaxReturnReport extends Component {
    static template = "account_invoicing_ext_mz.TaxReturnReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            lines: [],
            totalTaxes: 0,
            isLoading: true,
            error: null,
            currencySymbol: 'MZN',
            filters: {
                date_from: null,
                date_to: this.getCurrentMonth(),
                comparison: null,
                company_id: null,
                posted_entries: true,
                closing_entry: false,
                report_type: 'tcs' // TCS Report (IN)
            },
            showClosingEntry: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getCurrentMonth() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[date.getMonth()]} ${date.getFullYear()}`;
    }

    async loadReport() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            const result = await this.rpc("/web/dataset/call_kw/account.tax.return.report/get_tax_return_data", {
                model: "account.tax.return.report",
                method: "get_tax_return_data",
                args: [],
                kwargs: {
                    date_from: this.state.filters.date_from,
                    date_to: this.state.filters.date_to ? new Date(this.state.filters.date_to + '-01') : null,
                    comparison: this.state.filters.comparison,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.lines = result.lines || [];
            this.state.totalTaxes = result.total_taxes || 0;
            this.state.currencySymbol = result.currency_symbol || 'MZN';

        } catch (error) {
            console.error("Error loading tax return report:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null) return '0.00';
        return new Intl.NumberFormat('pt-MZ', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount));
    }

    async onDateChange(ev) {
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

    async onClosingEntryToggle() {
        this.state.showClosingEntry = !this.state.showClosingEntry;
        this.state.filters.closing_entry = this.state.showClosingEntry;
    }

    async onReportTypeChange(reportType) {
        this.state.filters.report_type = reportType;
        await this.loadReport();
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.tax_return_report',
                report_file: 'account_invoicing_ext_mz.tax_return_report',
                data: {
                    lines: this.state.lines,
                    total_taxes: this.state.totalTaxes,
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
                report_name: 'account_invoicing_ext_mz.tax_return_xlsx',
                report_file: 'account_invoicing_ext_mz.tax_return_xlsx',
                data: {
                    lines: this.state.lines,
                    total_taxes: this.state.totalTaxes,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showTaxDetails(line) {
        // Show tax details in a dialog
        console.log("Show details for:", line);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }

    getReportTypeLabel() {
        const reportTypes = {
            'tcs': 'Report: TCS Report (IN)',
            'vat': 'Relatório: IVA (MZ)',
            'irps': 'Relatório: IRPS (MZ)',
            'all': 'Relatório: Todos os Impostos'
        };
        return reportTypes[this.state.filters.report_type] || 'Report: TCS Report (IN)';
    }
}

registry.category("actions").add("account_tax_return_report", TaxReturnReport);