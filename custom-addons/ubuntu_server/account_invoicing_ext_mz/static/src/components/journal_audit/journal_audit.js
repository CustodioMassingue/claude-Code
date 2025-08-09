/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class JournalAuditReport extends Component {
    static template = "account_invoicing_ext_mz.JournalAuditReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            journals: [],
            taxSummary: [],
            isLoading: true,
            error: null,
            expandedJournals: new Set(),
            currencySymbol: 'MT',
            filters: {
                date_from: this.getDefaultDateFrom(),
                date_to: this.getDefaultDateTo(),
                journals: 'all',
                journal_ids: [],
                posted_entries: true,
                company_id: null
            },
            unpostedWarning: false,
            taxesApplied: 'Audit'
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getDefaultDateFrom() {
        const now = new Date();
        return `${now.getFullYear()}-${now.getFullYear()}`;
    }

    getDefaultDateTo() {
        const now = new Date();
        return `${now.getFullYear()}-${now.getFullYear() + 1}`;
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
            
            if (this.state.filters.date_from) {
                const parts = this.state.filters.date_from.split('-');
                if (parts.length === 2) {
                    date_from = `${parts[0]}-01-01`;
                    date_to = `${parts[1]}-12-31`;
                }
            }

            const result = await this.rpc("/web/dataset/call_kw/account.journal.audit.report/get_journal_audit_data", {
                model: "account.journal.audit.report",
                method: "get_journal_audit_data",
                args: [],
                kwargs: {
                    date_from: date_from,
                    date_to: date_to,
                    journals: this.state.filters.journal_ids.length > 0 ? this.state.filters.journal_ids : null,
                    posted_entries: this.state.filters.posted_entries,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.journals = result.journals || [];
            this.state.taxSummary = result.tax_summary || [];
            this.state.currencySymbol = result.currency_symbol || 'MT';
            this.state.unpostedWarning = result.unposted_warning || false;

        } catch (error) {
            console.error("Error loading journal audit:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleJournal(journalId) {
        if (this.state.expandedJournals.has(journalId)) {
            this.state.expandedJournals.delete(journalId);
        } else {
            this.state.expandedJournals.add(journalId);
        }
    }

    isExpanded(journalId) {
        return this.state.expandedJournals.has(journalId);
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null) return '0.00';
        return new Intl.NumberFormat('pt-MZ', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount));
    }

    async onDateRangeChange(ev) {
        const value = ev.target.value;
        if (value) {
            this.state.filters.date_from = value;
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

    async onPostedEntriesToggle() {
        this.state.filters.posted_entries = !this.state.filters.posted_entries;
        await this.loadReport();
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.journal_audit_report',
                report_file: 'account_invoicing_ext_mz.journal_audit_report',
                data: {
                    journals: this.state.journals,
                    tax_summary: this.state.taxSummary,
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
                report_name: 'account_invoicing_ext_mz.journal_audit_xlsx',
                report_file: 'account_invoicing_ext_mz.journal_audit_xlsx',
                data: {
                    journals: this.state.journals,
                    tax_summary: this.state.taxSummary,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showJournalDetails(journal) {
        // Show journal details in a dialog
        console.log("Show details for:", journal);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }

    onTaxesAppliedChange(value) {
        this.state.taxesApplied = value;
    }
}

registry.category("actions").add("account_journal_audit_report", JournalAuditReport);