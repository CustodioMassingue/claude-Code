/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GeneralLedgerReport extends Component {
    static template = "account_invoicing_ext_mz.GeneralLedgerReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            accounts: [],
            totalDebit: 0,
            totalCredit: 0,
            totalBalance: 0,
            isLoading: true,
            error: null,
            expandedAccounts: new Set(),
            currencySymbol: 'MZN',
            searchQuery: '',
            filters: {
                date_from: this.getDefaultDateFrom(),
                date_to: this.getDefaultDateTo(),
                journals: 'all',
                journal_ids: [],
                analytic: null,
                posted_entries: true,
                company_id: null
            },
            unpostedWarning: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getDefaultDateFrom() {
        const now = new Date();
        return `${now.getFullYear()}-01-01`;
    }

    getDefaultDateTo() {
        const now = new Date();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${now.getFullYear()}-${month}-${day}`;
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
    }

    async loadReport() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            const result = await this.rpc("/web/dataset/call_kw/account.general.ledger.report/get_general_ledger_data", {
                model: "account.general.ledger.report",
                method: "get_general_ledger_data",
                args: [],
                kwargs: {
                    date_from: this.state.filters.date_from,
                    date_to: this.state.filters.date_to,
                    journals: this.state.filters.journal_ids.length > 0 ? this.state.filters.journal_ids : null,
                    analytic: this.state.filters.analytic,
                    posted_entries: this.state.filters.posted_entries,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.accounts = result.accounts || [];
            this.state.totalDebit = result.total_debit || 0;
            this.state.totalCredit = result.total_credit || 0;
            this.state.totalBalance = result.total_balance || 0;
            this.state.currencySymbol = result.currency_symbol || 'MZN';
            this.state.unpostedWarning = result.unposted_warning || false;

        } catch (error) {
            console.error("Error loading general ledger:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleAccount(accountId) {
        if (this.state.expandedAccounts.has(accountId)) {
            this.state.expandedAccounts.delete(accountId);
        } else {
            this.state.expandedAccounts.add(accountId);
        }
    }

    isExpanded(accountId) {
        return this.state.expandedAccounts.has(accountId);
    }

    getFilteredAccounts() {
        if (!this.state.searchQuery) {
            return this.state.accounts;
        }
        
        const query = this.state.searchQuery.toLowerCase();
        return this.state.accounts.filter(account => 
            account.code.toLowerCase().includes(query) || 
            account.name.toLowerCase().includes(query)
        );
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null) return '0.00';
        return new Intl.NumberFormat('pt-MZ', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount));
    }

    getAmountClass(amount) {
        return amount < 0 ? 'text-danger' : '';
    }

    async onSearchChange(ev) {
        this.state.searchQuery = ev.target.value;
    }

    async onDateFromChange(ev) {
        this.state.filters.date_from = ev.target.value;
        await this.loadReport();
    }

    async onDateToChange(ev) {
        this.state.filters.date_to = ev.target.value;
        await this.loadReport();
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
                report_name: 'account_invoicing_ext_mz.general_ledger_report',
                report_file: 'account_invoicing_ext_mz.general_ledger_report',
                data: {
                    accounts: this.state.accounts,
                    totals: {
                        debit: this.state.totalDebit,
                        credit: this.state.totalCredit,
                        balance: this.state.totalBalance
                    },
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
                report_name: 'account_invoicing_ext_mz.general_ledger_xlsx',
                report_file: 'account_invoicing_ext_mz.general_ledger_xlsx',
                data: {
                    accounts: this.state.accounts,
                    totals: {
                        debit: this.state.totalDebit,
                        credit: this.state.totalCredit,
                        balance: this.state.totalBalance
                    },
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showAccountDetails(account) {
        // Show account details in a dialog
        console.log("Show details for:", account);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_general_ledger_report", GeneralLedgerReport);