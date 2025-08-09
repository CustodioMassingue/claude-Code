/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CashFlowReport extends Component {
    static template = "account_invoicing_ext_mz.CashFlowReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            lines: [],
            isLoading: true,
            error: null,
            expandedLines: new Set(),
            filters: {
                date_from: null,
                date_to: this.getCurrentMonth(),
                journals: 'all',
                journal_ids: [],
                company_id: null,
                posted_entries: true,
                comparison: null,
                analytic: null
            },
            unpostedWarning: false
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

            const result = await this.rpc("/web/dataset/call_kw/account.cash.flow.report/get_cash_flow_data", {
                model: "account.cash.flow.report",
                method: "get_cash_flow_data",
                args: [],
                kwargs: {
                    date_from: this.state.filters.date_from,
                    date_to: this.state.filters.date_to ? new Date(this.state.filters.date_to + '-01') : null,
                    journals: this.state.filters.journal_ids.length > 0 ? this.state.filters.journal_ids : null,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.lines = result.lines || [];
            this.state.unpostedWarning = !this.state.filters.posted_entries;
            
            // Auto-expand main sections
            this.state.lines.forEach(line => {
                if (line.id === 'net_increase') {
                    this.state.expandedLines.add(line.id);
                }
            });

        } catch (error) {
            console.error("Error loading cash flow report:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleLine(lineId) {
        if (this.state.expandedLines.has(lineId)) {
            this.state.expandedLines.delete(lineId);
        } else {
            this.state.expandedLines.add(lineId);
        }
    }

    isExpanded(lineId) {
        return this.state.expandedLines.has(lineId);
    }

    getVisibleLines() {
        const visibleLines = [];
        
        const processLine = (line) => {
            visibleLines.push(line);
            
            if (line.children && line.children.length > 0 && this.isExpanded(line.id)) {
                line.children.forEach(child => processLine(child));
            }
        };
        
        this.state.lines.forEach(line => processLine(line));
        return visibleLines;
    }

    getIndentStyle(level) {
        return `padding-left: ${20 + (level * 20)}px;`;
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null) return '0.00';
        return new Intl.NumberFormat('en-US', {
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

    async onJournalFilterClick(filter) {
        if (filter === 'all') {
            this.state.filters.journals = 'all';
            this.state.filters.journal_ids = [];
        } else {
            // In real implementation, show journal selection dialog
            this.state.filters.journals = filter;
        }
        await this.loadReport();
    }

    async onComparisonClick() {
        // Show comparison options dialog
        console.log("Comparison filter clicked");
    }

    async onAnalyticClick() {
        // Show analytic filter dialog
        console.log("Analytic filter clicked");
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
                report_name: 'account_invoicing_ext_mz.cash_flow_report',
                report_file: 'account_invoicing_ext_mz.cash_flow_report',
                data: {
                    lines: this.state.lines,
                    filters: this.state.filters
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
                report_name: 'account_invoicing_ext_mz.cash_flow_xlsx',
                report_file: 'account_invoicing_ext_mz.cash_flow_xlsx',
                data: {
                    lines: this.state.lines,
                    filters: this.state.filters
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    getRowClass(line) {
        const classes = [`level-${line.level}`];
        
        if (line.is_header) {
            classes.push('header-line');
        }
        
        if (line.id === 'closing_balance') {
            classes.push('total-line');
        }
        
        return classes.join(' ');
    }

    showAccountDetails(line) {
        // Show account details in a dialog
        console.log("Show details for:", line);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_cash_flow_report", CashFlowReport);